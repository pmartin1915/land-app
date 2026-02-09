"""
Property CRUD endpoints with scoring and investment calculations.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from typing import Optional
import logging
import math
from datetime import datetime, timezone

from ..database.connection import get_db
from ..services.property_service import PropertyService
from ..models.property import (
    PropertyCreate, PropertyUpdate, PropertyResponse, PropertyListResponse,
    PropertyFilters, PropertyCalculationRequest, PropertyCalculationResponse,
    PropertyMetrics, PropertyBulkOperation, PropertyBulkResponse,
    PropertyStatusUpdate, PropertyStatusResponse
)
from ..auth import require_property_read, require_property_write
from ..config import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

def get_property_service(db: Session = Depends(get_db)) -> PropertyService:
    """Dependency to get PropertyService instance."""
    return PropertyService(db)

@router.get("/", response_model=PropertyListResponse)
@limiter.limit("100/minute")
def list_properties(
    request: Request,
    auth_data: dict = Depends(require_property_read),
    state: Optional[str] = Query(None, description="Filter by state code (AL, AR, TX, FL)"),
    county: Optional[str] = Query(None, description="Filter by county"),
    min_price: Optional[float] = Query(None, description="Minimum bid amount", ge=0),
    max_price: Optional[float] = Query(None, description="Maximum bid amount", ge=0),
    min_acreage: Optional[float] = Query(None, description="Minimum acreage", ge=0),
    max_acreage: Optional[float] = Query(None, description="Maximum acreage", ge=0),
    water_features: Optional[bool] = Query(None, description="Has water features"),
    min_investment_score: Optional[float] = Query(None, description="Minimum investment score", ge=0, le=100),
    max_investment_score: Optional[float] = Query(None, description="Maximum investment score", ge=0, le=100),
    year_sold: Optional[str] = Query(None, description="Filter by exact sale year"),
    min_year_sold: Optional[int] = Query(None, description="Minimum delinquency year (exclude pre-X properties)", ge=1900, le=2100),
    search_query: Optional[str] = Query(None, description="Search in description and owner name"),
    # Advanced Intelligence Filters
    min_county_market_score: Optional[float] = Query(None, description="Minimum county market score", ge=0),
    min_geographic_score: Optional[float] = Query(None, description="Minimum geographic score", ge=0),
    min_market_timing_score: Optional[float] = Query(None, description="Minimum market timing score", ge=0),
    min_total_description_score: Optional[float] = Query(None, description="Minimum total description score", ge=0),
    min_road_access_score: Optional[float] = Query(None, description="Minimum road access score", ge=0),
    # Multi-state scoring filters
    max_effective_cost: Optional[float] = Query(None, description="Maximum effective cost (bid + quiet title)", ge=0),
    min_buy_hold_score: Optional[float] = Query(None, description="Minimum buy & hold score", ge=0, le=100),
    page: int = Query(1, description="Page number (1-based)", ge=1),
    page_size: int = Query(100, description="Number of items per page", ge=1, le=1000),
    sort_by: str = Query("investment_score", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    property_service: PropertyService = Depends(get_property_service)
):
    """
    List properties with filtering, sorting, and pagination.
    Uses exact Python algorithms for all calculated fields.
    """
    try:
        # Create filters object
        filters = PropertyFilters(
            state=state,
            county=county,
            min_price=min_price,
            max_price=max_price,
            min_acreage=min_acreage,
            max_acreage=max_acreage,
            water_features=water_features,
            min_investment_score=min_investment_score,
            max_investment_score=max_investment_score,
            year_sold=year_sold,
            min_year_sold=min_year_sold,
            search_query=search_query,
            # Advanced Intelligence Filters
            min_county_market_score=min_county_market_score,
            min_geographic_score=min_geographic_score,
            min_market_timing_score=min_market_timing_score,
            min_total_description_score=min_total_description_score,
            min_road_access_score=min_road_access_score,
            # Multi-state scoring filters
            max_effective_cost=max_effective_cost,
            min_buy_hold_score=min_buy_hold_score,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )

        # Get properties and total count
        properties, total_count = property_service.list_properties(filters)

        # Calculate pagination metadata
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        has_next = page < total_pages
        has_previous = page > 1

        # Convert to response models using model_validate for Pydantic v2 compatibility
        property_responses = [PropertyResponse.model_validate(prop) for prop in properties]

        return PropertyListResponse(
            properties=property_responses,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous
        )

    except Exception as e:
        logger.error(f"Failed to list properties: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve properties")


@router.get("/workflow/stats")
@limiter.limit("60/minute")
def get_workflow_stats(
    request: Request,
    auth_data: dict = Depends(require_property_read),
    db: Session = Depends(get_db)
):
    """
    Get property counts by research workflow status.
    Returns counts for: new, reviewing, bid_ready, rejected, purchased
    """
    from ..database.models import Property
    from sqlalchemy import func

    try:
        # Get counts by status
        status_counts = db.query(
            Property.status,
            func.count(Property.id).label('count')
        ).filter(
            Property.is_deleted == False
        ).group_by(Property.status).all()

        # Convert to dict with defaults
        stats = {
            "new": 0,
            "reviewing": 0,
            "bid_ready": 0,
            "rejected": 0,
            "purchased": 0,
            "total": 0
        }

        for status, count in status_counts:
            status_key = status if status else "new"
            if status_key in stats:
                stats[status_key] = count
            stats["total"] += count

        return stats

    except Exception as e:
        logger.error(f"Failed to get workflow stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get workflow statistics")


@router.get("/stats")
@limiter.limit("60/minute")
def get_dashboard_stats(
    request: Request,
    auth_data: dict = Depends(require_property_read),
    property_service: PropertyService = Depends(get_property_service)
):
    """
    Get aggregated statistics for the dashboard.
    Returns metrics, distributions, and chart data for frontend visualization.
    """
    try:
        stats = property_service.get_dashboard_stats()
        return stats

    except Exception as e:
        logger.error(f"Failed to get dashboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard statistics")


@router.get("/{property_id}", response_model=PropertyResponse)
@limiter.limit("200/minute")
def get_property(
    request: Request,
    property_id: str,
    auth_data: dict = Depends(require_property_read),
    property_service: PropertyService = Depends(get_property_service)
):
    """Get specific property by ID with all calculated metrics."""
    try:
        property_obj = property_service.get_property(property_id)
        if not property_obj:
            raise HTTPException(status_code=404, detail="Property not found")

        return PropertyResponse.from_orm(property_obj)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get property {property_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve property")

@router.post("/", response_model=PropertyResponse, status_code=201)
@limiter.limit("50/minute")
def create_property(
    request: Request,
    property_data: PropertyCreate,
    auth_data: dict = Depends(require_property_write),
    device_id: Optional[str] = Query(None, description="Device identifier"),
    property_service: PropertyService = Depends(get_property_service)
):
    """
    Create new property with calculated metrics using exact Python algorithms.
    Metrics are calculated using the scoring algorithms.
    """
    try:
        property_obj = property_service.create_property(property_data, device_id)

        logger.info(f"Created property {property_obj.id} with investment score {property_obj.investment_score}")
        return PropertyResponse.from_orm(property_obj)

    except Exception as e:
        logger.error(f"Failed to create property: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create property")

@router.put("/{property_id}", response_model=PropertyResponse)
@limiter.limit("50/minute")
def update_property(
    request: Request,
    property_id: str,
    property_data: PropertyUpdate,
    auth_data: dict = Depends(require_property_write),
    device_id: Optional[str] = Query(None, description="Device identifier"),
    property_service: PropertyService = Depends(get_property_service)
):
    """
    Update property and recalculate metrics using exact Python algorithms.
    """
    try:
        property_obj = property_service.update_property(property_id, property_data, device_id)
        if not property_obj:
            raise HTTPException(status_code=404, detail="Property not found")

        logger.info(f"Updated property {property_id} with new investment score {property_obj.investment_score}")
        return PropertyResponse.from_orm(property_obj)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update property {property_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update property")

@router.delete("/{property_id}", status_code=204)
@limiter.limit("20/minute")
def delete_property(
    request: Request,
    property_id: str,
    auth_data: dict = Depends(require_property_write),
    device_id: Optional[str] = Query(None, description="Device identifier"),
    property_service: PropertyService = Depends(get_property_service)
):
    """
    Soft delete property (maintains record for sync compatibility).
    """
    try:
        success = property_service.delete_property(property_id, device_id)
        if not success:
            raise HTTPException(status_code=404, detail="Property not found")

        logger.info(f"Deleted property {property_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete property {property_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete property")


@router.patch("/{property_id}/status", response_model=PropertyStatusResponse)
@limiter.limit("100/minute")
def update_property_status(
    request: Request,
    property_id: str,
    status_update: PropertyStatusUpdate,
    auth_data: dict = Depends(require_property_write),
    db: Session = Depends(get_db)
):
    """
    Update property research status for triage workflow.
    Status transitions: new -> reviewing -> bid_ready/rejected -> purchased
    """
    from ..database.models import Property

    try:
        # Find the property
        property_obj = db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            raise HTTPException(status_code=404, detail="Property not found")

        # Update status and metadata
        property_obj.status = status_update.status
        if status_update.triage_notes:
            property_obj.triage_notes = status_update.triage_notes
        property_obj.triaged_at = datetime.now(timezone.utc)
        property_obj.triaged_by = status_update.device_id

        db.commit()
        db.refresh(property_obj)

        logger.info(f"Updated property {property_id} status to {status_update.status}")

        return PropertyStatusResponse(
            id=property_obj.id,
            status=property_obj.status,
            triage_notes=property_obj.triage_notes,
            triaged_at=property_obj.triaged_at,
            triaged_by=property_obj.triaged_by,
            message=f"Property status updated to {property_obj.status}"
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update property status {property_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update property status")


@router.post("/calculate", response_model=PropertyCalculationResponse)
@limiter.limit("100/minute")
def calculate_metrics(
    request: Request,
    calculation_request: PropertyCalculationRequest,
    auth_data: dict = Depends(require_property_read),
    property_service: PropertyService = Depends(get_property_service)
):
    """Calculate property metrics using exact Python algorithms."""
    try:
        result = property_service.calculate_metrics_for_request(calculation_request)

        logger.info(f"Calculated metrics: investment_score={result.investment_score}, water_score={result.water_score}")
        return result

    except Exception as e:
        logger.error(f"Failed to calculate metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to calculate metrics")

@router.get("/analytics/metrics", response_model=PropertyMetrics)
@limiter.limit("10/minute")
def get_property_metrics(
    request: Request,
    auth_data: dict = Depends(require_property_read),
    property_service: PropertyService = Depends(get_property_service)
):
    """Get overall property analytics and statistics."""
    try:
        metrics = property_service.get_property_metrics()
        return metrics

    except Exception as e:
        logger.error(f"Failed to get property metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get property metrics")

@router.post("/analytics/recalculate-ranks", status_code=200)
@limiter.limit("1/minute")
def recalculate_ranks(
    request: Request,
    auth_data: dict = Depends(require_property_write),
    property_service: PropertyService = Depends(get_property_service)
):
    """
    Recalculate investment score rankings for all properties.
    Use sparingly - resource intensive operation.
    """
    try:
        property_service.recalculate_all_ranks()
        return {"message": "Property rankings recalculated successfully"}

    except Exception as e:
        logger.error(f"Failed to recalculate ranks: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to recalculate rankings")

@router.post("/bulk", response_model=PropertyBulkResponse)
@limiter.limit("5/minute")
def bulk_operations(
    request: Request,
    bulk_request: PropertyBulkOperation,
    auth_data: dict = Depends(require_property_write),
    property_service: PropertyService = Depends(get_property_service)
):
    """Perform bulk property operations (create, update, delete)."""
    try:
        import time
        start_time = time.time()

        total_requested = len(bulk_request.properties)
        successful = 0
        failed = 0
        errors = []

        for i, property_data in enumerate(bulk_request.properties):
            try:
                if bulk_request.operation == "create":
                    property_create = PropertyCreate(**property_data)
                    property_service.create_property(property_create, device_id)
                    successful += 1

                elif bulk_request.operation == "update":
                    property_id = property_data.get('id')
                    if not property_id:
                        raise ValueError("Property ID required for update operation")

                    property_update = PropertyUpdate(**{k: v for k, v in property_data.items() if k != 'id'})
                    result = property_service.update_property(property_id, property_update, device_id)
                    if result:
                        successful += 1
                    else:
                        raise ValueError("Property not found")

                elif bulk_request.operation == "delete":
                    property_id = property_data.get('id')
                    if not property_id:
                        raise ValueError("Property ID required for delete operation")

                    result = property_service.delete_property(property_id, device_id)
                    if result:
                        successful += 1
                    else:
                        raise ValueError("Property not found")

            except Exception as e:
                failed += 1
                errors.append({
                    "index": i,
                    "property_data": property_data,
                    "error": str(e)
                })

        processing_time = time.time() - start_time

        return PropertyBulkResponse(
            operation=bulk_request.operation,
            total_requested=total_requested,
            successful=successful,
            failed=failed,
            errors=errors,
            processing_time_seconds=processing_time
        )

    except Exception as e:
        logger.error(f"Bulk operation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Bulk operation failed")

@router.get("/search/suggestions")
@limiter.limit("50/minute")
def search_suggestions(
    request: Request,
    auth_data: dict = Depends(require_property_read),
    query: str = Query(..., description="Search query", min_length=2),
    limit: int = Query(10, description="Number of suggestions", ge=1, le=50),
    property_service: PropertyService = Depends(get_property_service)
):
    """
    Get search suggestions for property descriptions and owner names.
    Useful for autocomplete functionality.
    """
    try:
        # This is a simple implementation - could be enhanced with full-text search
        filters = PropertyFilters(
            search_query=query,
            page=1,
            page_size=limit,
            sort_by="investment_score",
            sort_order="desc"
        )

        properties, _ = property_service.list_properties(filters)

        suggestions = []
        for prop in properties:
            # Add property description suggestions
            if prop.description and query.lower() in prop.description.lower():
                suggestions.append({
                    "type": "description",
                    "text": prop.description[:100] + "..." if len(prop.description) > 100 else prop.description,
                    "property_id": prop.id
                })

            # Add owner name suggestions
            if prop.owner_name and query.lower() in prop.owner_name.lower():
                suggestions.append({
                    "type": "owner",
                    "text": prop.owner_name,
                    "property_id": prop.id
                })

            if len(suggestions) >= limit:
                break

        return {"suggestions": suggestions}

    except Exception as e:
        logger.error(f"Search suggestions failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get search suggestions")
