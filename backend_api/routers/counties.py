"""
Counties API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
import logging

from ..database.connection import get_db
from ..database.models import County
from ..models.county import (
    CountyResponse, CountyListResponse, CountyValidationRequest,
    CountyValidationResponse, CountyLookupRequest, CountyLookupResponse,
    CountyStatistics, CountyStatisticsResponse, ADOR_COUNTY_MAPPING,
    get_county_by_code, get_county_by_name, search_counties
)
from ..config import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=CountyListResponse)
@limiter.limit("100/minute")
def list_counties(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    List all Alabama counties with ADOR alphabetical codes.
    """
    try:
        counties = db.query(County).order_by(County.code).all()

        # If no counties in database, return static mapping
        if not counties:
            county_responses = [
                CountyResponse(
                    code=code,
                    name=name,
                    created_at=None,
                    updated_at=None
                )
                for code, name in ADOR_COUNTY_MAPPING.items()
            ]
        else:
            county_responses = [CountyResponse.from_orm(county) for county in counties]

        return CountyListResponse(
            counties=county_responses,
            total_count=len(county_responses)
        )

    except Exception as e:
        logger.error(f"Failed to list counties: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve counties")

@router.get("/{county_code}", response_model=CountyResponse)
@limiter.limit("200/minute")
def get_county(
    request: Request,
    county_code: str,
    db: Session = Depends(get_db)
):
    """Get specific county by ADOR code."""
    try:
        # Validate county code format
        if len(county_code) != 2 or not county_code.isdigit():
            raise HTTPException(status_code=400, detail="County code must be 2-digit numeric string")

        # Try database first
        county = db.query(County).filter(County.code == county_code).first()

        if county:
            return CountyResponse.from_orm(county)

        # Fall back to static mapping
        county_name = get_county_by_code(county_code)
        if not county_name:
            raise HTTPException(status_code=404, detail="County not found")

        return CountyResponse(
            code=county_code,
            name=county_name,
            created_at=None,
            updated_at=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get county {county_code}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve county")

@router.post("/validate", response_model=CountyValidationResponse)
@limiter.limit("100/minute")
async def validate_county(
    request: Request,
    validation_request: CountyValidationRequest
):
    """
    Validate county code or name.
    """
    try:
        if not validation_request.code and not validation_request.name:
            raise HTTPException(status_code=400, detail="Either code or name must be provided")

        # Validate county code
        if validation_request.code:
            county_name = get_county_by_code(validation_request.code)
            if county_name:
                return CountyValidationResponse(
                    is_valid=True,
                    code=validation_request.code,
                    name=county_name
                )
            else:
                return CountyValidationResponse(
                    is_valid=False,
                    error_message=f"Invalid county code: {validation_request.code}"
                )

        # Validate county name
        if validation_request.name:
            county_code = get_county_by_name(validation_request.name)
            if county_code:
                return CountyValidationResponse(
                    is_valid=True,
                    code=county_code,
                    name=validation_request.name
                )
            else:
                return CountyValidationResponse(
                    is_valid=False,
                    error_message=f"Invalid county name: {validation_request.name}"
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"County validation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="County validation failed")

@router.post("/lookup", response_model=CountyLookupResponse)
@limiter.limit("100/minute")
async def lookup_county(
    request: Request,
    lookup_request: CountyLookupRequest
):
    """
    Lookup counties by code, name, or partial name.
    Supports autocomplete functionality for iOS app.
    """
    try:
        matches = []
        exact_match = False
        suggestions = []

        # Lookup by code
        if lookup_request.code:
            county_name = get_county_by_code(lookup_request.code)
            if county_name:
                matches.append(CountyResponse(
                    code=lookup_request.code,
                    name=county_name,
                    created_at=None,
                    updated_at=None
                ))
                exact_match = True

        # Lookup by exact name
        elif lookup_request.name:
            county_code = get_county_by_name(lookup_request.name)
            if county_code:
                matches.append(CountyResponse(
                    code=county_code,
                    name=lookup_request.name,
                    created_at=None,
                    updated_at=None
                ))
                exact_match = True

        # Lookup by partial name (for autocomplete)
        elif lookup_request.partial_name:
            search_results = search_counties(lookup_request.partial_name)
            matches = [
                CountyResponse(
                    code=result["code"],
                    name=result["name"],
                    created_at=None,
                    updated_at=None
                )
                for result in search_results
            ]

            # Generate suggestions for better matches
            suggestions = [result["name"] for result in search_results[:5]]

        return CountyLookupResponse(
            matches=matches,
            exact_match=exact_match,
            suggestions=suggestions
        )

    except Exception as e:
        logger.error(f"County lookup failed: {str(e)}")
        raise HTTPException(status_code=500, detail="County lookup failed")

@router.get("/analytics/statistics", response_model=CountyStatisticsResponse)
@limiter.limit("10/minute")
def get_county_statistics(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get property statistics by county.
    Useful for analytics and regional analysis.
    """
    try:
        from ..database.models import Property
        from datetime import datetime, timezone

        # Get statistics for each county
        county_stats = []
        total_properties = 0

        for code, name in ADOR_COUNTY_MAPPING.items():
            # Count properties in this county
            property_count = db.query(Property).filter(
                Property.county == name,
                Property.is_deleted == False
            ).count()

            if property_count > 0:
                # Calculate averages for this county
                county_properties = db.query(Property).filter(
                    Property.county == name,
                    Property.is_deleted == False
                ).all()

                avg_investment = sum(p.investment_score or 0 for p in county_properties) / property_count
                avg_water = sum(p.water_score or 0 for p in county_properties) / property_count
                avg_price_per_acre = sum(p.price_per_acre or 0 for p in county_properties if p.price_per_acre) / len([p for p in county_properties if p.price_per_acre]) if any(p.price_per_acre for p in county_properties) else 0
                total_sales = sum(p.amount for p in county_properties)
                properties_with_water = len([p for p in county_properties if p.water_score > 0])

                county_stats.append(CountyStatistics(
                    county_code=code,
                    county_name=name,
                    property_count=property_count,
                    average_investment_score=round(avg_investment, 2),
                    average_price_per_acre=round(avg_price_per_acre, 2),
                    average_water_score=round(avg_water, 2),
                    total_sales_volume=round(total_sales, 2),
                    properties_with_water=properties_with_water
                ))

                total_properties += property_count

            else:
                # County with no properties
                county_stats.append(CountyStatistics(
                    county_code=code,
                    county_name=name,
                    property_count=0,
                    average_investment_score=0.0,
                    average_price_per_acre=0.0,
                    average_water_score=0.0,
                    total_sales_volume=0.0,
                    properties_with_water=0
                ))

        return CountyStatisticsResponse(
            statistics=county_stats,
            generated_at=datetime.now(timezone.utc),
            total_properties_analyzed=total_properties
        )

    except Exception as e:
        logger.error(f"Failed to get county statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get county statistics")

@router.get("/search/autocomplete")
@limiter.limit("50/minute")
async def county_autocomplete(
    request: Request,
    query: str = Query(..., description="Partial county name", min_length=1),
    limit: int = Query(10, description="Maximum suggestions", ge=1, le=20)
):
    """
    Autocomplete suggestions for county names.
    Used by iOS app for improved user experience.
    """
    try:
        search_results = search_counties(query)

        # Limit results and format for autocomplete
        suggestions = []
        for result in search_results[:limit]:
            suggestions.append({
                "code": result["code"],
                "name": result["name"],
                "display_text": f"{result['name']} ({result['code']})"
            })

        return {
            "query": query,
            "suggestions": suggestions,
            "total_matches": len(search_results)
        }

    except Exception as e:
        logger.error(f"County autocomplete failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Autocomplete failed")

@router.get("/mapping/ador-codes")
@limiter.limit("20/minute")
async def get_ador_mapping(request: Request):
    """
    Get complete ADOR county code mapping.
    Used for iOS app initialization and validation.
    """
    try:
        return {
            "mapping": ADOR_COUNTY_MAPPING,
            "total_counties": len(ADOR_COUNTY_MAPPING),
            "note": "ADOR alphabetical mapping (not FIPS codes)",
            "last_updated": "2025-09-19"
        }

    except Exception as e:
        logger.error(f"Failed to get ADOR mapping: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get ADOR mapping")