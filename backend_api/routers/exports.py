"""
Export API endpoints.
Provides CSV and JSON export of filtered property data.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field
import logging
import csv
import json
import io
from datetime import datetime

from ..database.connection import get_db
from ..database.models import Property
from ..auth import get_current_user_auth
from ..config import limiter
from ..services.property_service import PropertyService
from ..models.property import PropertyFilters

logger = logging.getLogger(__name__)

router = APIRouter()


# Default columns for export
DEFAULT_EXPORT_COLUMNS = [
    "parcel_id", "state", "county", "amount", "acreage", "price_per_acre",
    "investment_score", "buy_hold_score", "wholesale_score",
    "water_score", "road_access_score", "county_market_score",
    "description", "owner_name", "year_sold", "status",
    "sale_type", "redemption_period_days", "assessed_value",
    "created_at"
]

# All exportable columns
ALL_EXPORT_COLUMNS = [
    "id", "parcel_id", "state", "county", "amount", "acreage", "price_per_acre",
    "acreage_source", "acreage_confidence",
    "water_score", "investment_score", "buy_hold_score", "wholesale_score",
    "road_access_score", "county_market_score", "geographic_score",
    "market_timing_score", "total_description_score",
    "lot_dimensions_score", "shape_efficiency_score", "subdivision_quality_score",
    "assessed_value", "assessed_value_ratio", "estimated_market_value", "wholesale_spread",
    "description", "owner_name", "year_sold", "status", "triage_notes",
    "sale_type", "redemption_period_days", "time_to_ownership_days",
    "effective_cost", "time_penalty_factor",
    "is_market_reject", "is_delta_region", "delta_penalty_factor",
    "auction_date", "auction_platform", "data_source",
    "created_at", "updated_at"
]


class ExportRequest(BaseModel):
    """Request model for export."""
    columns: Optional[List[str]] = Field(None, description="Columns to include")
    # Filters
    state: Optional[str] = None
    county: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_acreage: Optional[float] = None
    max_acreage: Optional[float] = None
    min_investment_score: Optional[float] = None
    min_year_sold: Optional[int] = None
    exclude_delta_region: Optional[bool] = None
    exclude_market_rejects: Optional[bool] = None
    status: Optional[str] = None
    max_results: Optional[int] = Field(10000, le=50000, description="Maximum results to export")


class ExportColumnsResponse(BaseModel):
    """Response model for available export columns."""
    default_columns: List[str]
    all_columns: List[str]


def get_property_service(db: Session = Depends(get_db)) -> PropertyService:
    """Dependency to get PropertyService instance."""
    return PropertyService(db)


@router.get("/columns", response_model=ExportColumnsResponse)
@limiter.limit("60/minute")
async def get_export_columns(request: Request):
    """
    Get available columns for export.
    """
    return ExportColumnsResponse(
        default_columns=DEFAULT_EXPORT_COLUMNS,
        all_columns=ALL_EXPORT_COLUMNS
    )


@router.post("/csv")
@limiter.limit("10/minute")
def export_csv(
    request: Request,
    export_request: ExportRequest,
    auth_data: dict = Depends(get_current_user_auth),
    db: Session = Depends(get_db)
):
    """
    Export filtered properties to CSV.
    Returns a streaming CSV file download.
    """
    try:
        # Determine columns to export
        columns = export_request.columns or DEFAULT_EXPORT_COLUMNS
        # Validate columns
        invalid_columns = [c for c in columns if c not in ALL_EXPORT_COLUMNS]
        if invalid_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid columns: {', '.join(invalid_columns)}"
            )

        # Build filters
        filters = PropertyFilters(
            state=export_request.state,
            county=export_request.county,
            min_price=export_request.min_price,
            max_price=export_request.max_price,
            min_acreage=export_request.min_acreage,
            max_acreage=export_request.max_acreage,
            min_investment_score=export_request.min_investment_score,
            min_year_sold=export_request.min_year_sold,
            page=1,
            page_size=export_request.max_results or 10000
        )

        # Get properties
        property_service = PropertyService(db)
        properties, total_count = property_service.list_properties(filters)

        # Apply additional filters not in PropertyFilters
        if export_request.exclude_delta_region:
            properties = [p for p in properties if not p.is_delta_region]
        if export_request.exclude_market_rejects:
            properties = [p for p in properties if not p.is_market_reject]
        if export_request.status:
            properties = [p for p in properties if p.status == export_request.status]

        # Generate CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()

        for prop in properties:
            prop_dict = prop.to_dict()
            # Format datetime fields
            for key in ['created_at', 'updated_at', 'auction_date', 'triaged_at']:
                if key in prop_dict and prop_dict[key]:
                    if isinstance(prop_dict[key], str):
                        # Already formatted
                        pass
                    else:
                        prop_dict[key] = prop_dict[key].isoformat()
            writer.writerow(prop_dict)

        # Create streaming response
        output.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"auction_properties_{timestamp}.csv"

        logger.info(f"Exported {len(properties)} properties to CSV")

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Total-Count": str(len(properties))
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export CSV: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate CSV export")


@router.post("/json")
@limiter.limit("10/minute")
def export_json(
    request: Request,
    export_request: ExportRequest,
    auth_data: dict = Depends(get_current_user_auth),
    db: Session = Depends(get_db)
):
    """
    Export filtered properties to JSON.
    Returns a streaming JSON file download.
    """
    try:
        # Build filters
        filters = PropertyFilters(
            state=export_request.state,
            county=export_request.county,
            min_price=export_request.min_price,
            max_price=export_request.max_price,
            min_acreage=export_request.min_acreage,
            max_acreage=export_request.max_acreage,
            min_investment_score=export_request.min_investment_score,
            min_year_sold=export_request.min_year_sold,
            page=1,
            page_size=export_request.max_results or 10000
        )

        # Get properties
        property_service = PropertyService(db)
        properties, total_count = property_service.list_properties(filters)

        # Apply additional filters
        if export_request.exclude_delta_region:
            properties = [p for p in properties if not p.is_delta_region]
        if export_request.exclude_market_rejects:
            properties = [p for p in properties if not p.is_market_reject]
        if export_request.status:
            properties = [p for p in properties if p.status == export_request.status]

        # Filter columns if specified
        columns = export_request.columns
        if columns:
            # Validate columns
            invalid_columns = [c for c in columns if c not in ALL_EXPORT_COLUMNS]
            if invalid_columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid columns: {', '.join(invalid_columns)}"
                )

        # Generate JSON
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "total_count": len(properties),
            "filters_applied": {
                "state": export_request.state,
                "county": export_request.county,
                "min_price": export_request.min_price,
                "max_price": export_request.max_price,
                "min_investment_score": export_request.min_investment_score,
            },
            "properties": []
        }

        for prop in properties:
            prop_dict = prop.to_dict()
            if columns:
                # Filter to requested columns
                prop_dict = {k: v for k, v in prop_dict.items() if k in columns}
            export_data["properties"].append(prop_dict)

        # Create streaming response
        json_str = json.dumps(export_data, indent=2, default=str)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"auction_properties_{timestamp}.json"

        logger.info(f"Exported {len(properties)} properties to JSON")

        return StreamingResponse(
            iter([json_str]),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Total-Count": str(len(properties))
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export JSON: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate JSON export")


@router.get("/preview")
@limiter.limit("30/minute")
def preview_export(
    request: Request,
    state: Optional[str] = None,
    county: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_investment_score: Optional[float] = None,
    exclude_delta_region: bool = False,
    exclude_market_rejects: bool = False,
    auth_data: dict = Depends(get_current_user_auth),
    db: Session = Depends(get_db)
):
    """
    Preview export - returns count and sample of what would be exported.
    """
    try:
        # Build filters
        filters = PropertyFilters(
            state=state,
            county=county,
            min_price=min_price,
            max_price=max_price,
            min_investment_score=min_investment_score,
            page=1,
            page_size=5  # Just get a sample
        )

        # Get properties
        property_service = PropertyService(db)
        properties, total_count = property_service.list_properties(filters)

        # Apply additional filters to count
        count_query = db.query(Property).filter(Property.is_deleted == False)
        if state:
            count_query = count_query.filter(Property.state == state)
        if county:
            count_query = count_query.filter(Property.county == county)
        if min_price:
            count_query = count_query.filter(Property.amount >= min_price)
        if max_price:
            count_query = count_query.filter(Property.amount <= max_price)
        if min_investment_score:
            count_query = count_query.filter(Property.investment_score >= min_investment_score)
        if exclude_delta_region:
            count_query = count_query.filter(Property.is_delta_region == False)
        if exclude_market_rejects:
            count_query = count_query.filter(Property.is_market_reject == False)

        actual_count = count_query.count()

        # Get sample
        sample = [p.to_dict() for p in properties[:5]]

        return {
            "total_matching": actual_count,
            "sample_count": len(sample),
            "sample": sample,
            "filters_applied": {
                "state": state,
                "county": county,
                "min_price": min_price,
                "max_price": max_price,
                "min_investment_score": min_investment_score,
                "exclude_delta_region": exclude_delta_region,
                "exclude_market_rejects": exclude_market_rejects
            }
        }

    except Exception as e:
        logger.error(f"Failed to preview export: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate preview")
