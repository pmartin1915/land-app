"""
Pydantic models for Property API operations
Models match iOS Core Data schema and enable API request/response validation
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
import sys
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.validation import (
    PropertyValidator
)

class PropertyStatus(str, Enum):
    """Property status enumeration for research workflow."""
    NEW = "new"              # Freshly imported, not yet reviewed
    REVIEWING = "reviewing"  # Under active investigation
    BID_READY = "bid_ready"  # Ready to bid on
    REJECTED = "rejected"    # Not a good investment
    PURCHASED = "purchased"  # Successfully acquired
    # Legacy statuses for compatibility
    ACTIVE = "active"
    SOLD = "sold"
    PENDING = "pending"
    WITHDRAWN = "withdrawn"

class PropertyCreate(BaseModel):
    """Model for creating a new property."""
    parcel_id: str = Field(..., description="Unique parcel identifier", min_length=1)
    amount: float = Field(..., description="Bid/sale amount in USD", gt=0)
    acreage: Optional[float] = Field(None, description="Property acreage", ge=0)
    description: Optional[str] = Field(None, description="Legal property description")
    county: Optional[str] = Field(None, description="Alabama county name")
    owner_name: Optional[str] = Field(None, description="Property owner name")
    year_sold: Optional[str] = Field(None, description="Sale year")
    assessed_value: Optional[float] = Field(None, description="County assessed value", ge=0)
    device_id: Optional[str] = Field(None, description="Device that created this record")

    @validator('parcel_id')
    def validate_parcel_id_secure(cls, v):
        """Enhanced parcel ID validation with security checks."""
        result = PropertyValidator.validate_parcel_id(v)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return result.sanitized_value

    @validator('amount')
    def validate_amount_secure(cls, v):
        """Enhanced amount validation with security checks."""
        result = PropertyValidator.validate_amount(v)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return result.sanitized_value

    @validator('acreage')
    def validate_acreage_secure(cls, v):
        """Enhanced acreage validation with security checks."""
        if v is None:
            return v
        result = PropertyValidator.validate_acreage(v)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return result.sanitized_value

    @validator('county')
    def validate_county_secure(cls, v):
        """Enhanced county validation with security checks."""
        if v is None:
            return v
        result = PropertyValidator.validate_county(v)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return result.sanitized_value

    @validator('description')
    def validate_description_secure(cls, v):
        """Enhanced description validation with security checks."""
        if v is None:
            return v
        result = PropertyValidator.validate_description(v)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return result.sanitized_value

    @validator('owner_name')
    def validate_owner_name_secure(cls, v):
        """Enhanced owner name validation with security checks."""
        if v is None:
            return v
        result = PropertyValidator.validate_owner_name(v)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return result.sanitized_value

    @validator('year_sold')
    def validate_year_sold_secure(cls, v):
        """Enhanced year sold validation with security checks."""
        if v is None:
            return v
        result = PropertyValidator.validate_year_sold(v)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return result.sanitized_value

class PropertyUpdate(BaseModel):
    """Model for updating an existing property."""
    amount: Optional[float] = Field(None, description="Bid/sale amount in USD", gt=0)
    acreage: Optional[float] = Field(None, description="Property acreage", ge=0)
    description: Optional[str] = Field(None, description="Legal property description")
    county: Optional[str] = Field(None, description="Alabama county name")
    owner_name: Optional[str] = Field(None, description="Property owner name")
    year_sold: Optional[str] = Field(None, description="Sale year")
    assessed_value: Optional[float] = Field(None, description="County assessed value", ge=0)
    device_id: Optional[str] = Field(None, description="Device that modified this record")

    # Validation uses same validators as PropertyCreate
    _validate_county = validator('county', allow_reuse=True)(PropertyCreate.validate_county_secure)
    _validate_year_sold = validator('year_sold', allow_reuse=True)(PropertyCreate.validate_year_sold_secure)

class PropertyResponse(BaseModel):
    """Model for property API responses - includes all fields."""
    id: str = Field(..., description="Unique property identifier")
    parcel_id: str = Field(..., description="Unique parcel identifier")
    amount: float = Field(..., description="Bid/sale amount in USD")
    acreage: Optional[float] = Field(None, description="Property acreage")

    # Calculated fields (computed by exact Python algorithms)
    price_per_acre: Optional[float] = Field(None, description="Calculated: amount / acreage")
    water_score: float = Field(default=0.0, description="Water feature score (0.0-15.0+)")
    investment_score: Optional[float] = Field(None, description="Investment score (0.0-100.0)")
    estimated_all_in_cost: Optional[float] = Field(None, description="Total cost including fees")
    assessed_value_ratio: Optional[float] = Field(None, description="Calculated: amount / assessed_value")

    # Enhanced Description Intelligence Fields (Phase 1 Enhancement)
    lot_dimensions_score: float = Field(default=0.0, description="Property shape and dimension quality score")
    shape_efficiency_score: float = Field(default=0.0, description="Lot shape efficiency and frontage score")
    corner_lot_bonus: float = Field(default=0.0, description="Corner lot premium bonus")
    irregular_shape_penalty: float = Field(default=0.0, description="Irregular shape penalty")
    subdivision_quality_score: float = Field(default=0.0, description="Subdivision/neighborhood quality score")
    road_access_score: float = Field(default=0.0, description="Road access quality score")
    location_type_score: float = Field(default=0.0, description="Location type classification score")
    title_complexity_score: float = Field(default=0.0, description="Legal title complexity risk score")
    survey_requirement_score: float = Field(default=0.0, description="Survey requirement complexity score")
    premium_water_access_score: float = Field(default=0.0, description="Premium water feature access score")
    total_description_score: float = Field(default=0.0, description="Total enhanced description intelligence score")

    # County Intelligence Fields (Future Phase 1)
    county_market_score: float = Field(default=0.0, description="County market conditions score")
    geographic_score: float = Field(default=0.0, description="Geographic advantages score")
    market_timing_score: float = Field(default=0.0, description="Market timing and opportunity score")

    # Property details
    description: Optional[str] = Field(None, description="Legal property description")
    county: Optional[str] = Field(None, description="Alabama county name")
    owner_name: Optional[str] = Field(None, description="Property owner name")
    year_sold: Optional[str] = Field(None, description="Sale year")
    assessed_value: Optional[float] = Field(None, description="County assessed value")

    # Metadata
    rank: Optional[int] = Field(None, description="Investment score ranking")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    device_id: Optional[str] = Field(None, description="Device that last modified this record")
    sync_timestamp: datetime = Field(..., description="Last sync timestamp")
    is_deleted: bool = Field(default=False, description="Soft delete flag for sync")

    # Research workflow status
    status: str = Field(default="new", description="Research status: new, reviewing, bid_ready, rejected, purchased")
    triage_notes: Optional[str] = Field(None, description="Research notes from triage review")
    triaged_at: Optional[datetime] = Field(None, description="When property was triaged")
    triaged_by: Optional[str] = Field(None, description="Device/user that triaged this property")

    class Config:
        from_attributes = True  # Enable ORM mode for SQLAlchemy compatibility
        # Include fields with default values in serialization
        fields = {
            "lot_dimensions_score": {"exclude": False},
            "shape_efficiency_score": {"exclude": False},
            "corner_lot_bonus": {"exclude": False},
            "irregular_shape_penalty": {"exclude": False},
            "subdivision_quality_score": {"exclude": False},
            "road_access_score": {"exclude": False},
            "location_type_score": {"exclude": False},
            "title_complexity_score": {"exclude": False},
            "survey_requirement_score": {"exclude": False},
            "premium_water_access_score": {"exclude": False},
            "total_description_score": {"exclude": False},
            "county_market_score": {"exclude": False},
            "geographic_score": {"exclude": False},
            "market_timing_score": {"exclude": False},
        }

class PropertyListResponse(BaseModel):
    """Model for property list API responses with pagination."""
    properties: List[PropertyResponse] = Field(..., description="List of properties")
    total_count: int = Field(..., description="Total number of properties matching filters")
    page: int = Field(..., description="Current page number (1-based)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")


class PropertyStatusUpdate(BaseModel):
    """Model for updating property research status."""
    status: PropertyStatus = Field(..., description="New research status")
    triage_notes: Optional[str] = Field(None, description="Research notes", max_length=2000)
    device_id: Optional[str] = Field(None, description="Device/user making the update")

    class Config:
        use_enum_values = True


class PropertyStatusResponse(BaseModel):
    """Response after updating property status."""
    id: str = Field(..., description="Property ID")
    status: str = Field(..., description="New status")
    triage_notes: Optional[str] = Field(None, description="Research notes")
    triaged_at: datetime = Field(..., description="When status was updated")
    triaged_by: Optional[str] = Field(None, description="Who updated the status")
    message: str = Field(..., description="Success message")

class PropertyFilters(BaseModel):
    """Model for property filtering and search parameters."""
    county: Optional[str] = Field(None, description="Filter by Alabama county")
    min_price: Optional[float] = Field(None, description="Minimum bid amount", ge=0)
    max_price: Optional[float] = Field(None, description="Maximum bid amount", ge=0)
    min_acreage: Optional[float] = Field(None, description="Minimum acreage", ge=0)
    max_acreage: Optional[float] = Field(None, description="Maximum acreage", ge=0)
    water_features: Optional[bool] = Field(None, description="Has water features (water_score > 0)")
    min_investment_score: Optional[float] = Field(None, description="Minimum investment score", ge=0, le=100)
    max_investment_score: Optional[float] = Field(None, description="Maximum investment score", ge=0, le=100)
    year_sold: Optional[str] = Field(None, description="Filter by sale year")
    search_query: Optional[str] = Field(None, description="Search in description and owner name")

    # Advanced Intelligence Filters
    min_county_market_score: Optional[float] = Field(None, description="Minimum county market score", ge=0)
    min_geographic_score: Optional[float] = Field(None, description="Minimum geographic score", ge=0)
    min_market_timing_score: Optional[float] = Field(None, description="Minimum market timing score", ge=0)
    min_total_description_score: Optional[float] = Field(None, description="Minimum total description score", ge=0)
    min_road_access_score: Optional[float] = Field(None, description="Minimum road access score", ge=0)

    # Pagination
    page: int = Field(1, description="Page number (1-based)", ge=1)
    page_size: int = Field(100, description="Number of items per page", ge=1, le=1000)

    # Sorting
    sort_by: Optional[str] = Field("investment_score", description="Sort field")
    sort_order: Optional[str] = Field("desc", description="Sort order: asc or desc")

    @validator('sort_by')
    def validate_sort_by(cls, v):
        """Validate sort field."""
        valid_fields = {
            "investment_score", "amount", "acreage", "price_per_acre", "water_score",
            "assessed_value_ratio", "county", "year_sold", "created_at", "updated_at",
            "county_market_score", "geographic_score", "market_timing_score",
            "total_description_score", "road_access_score"
        }
        if v not in valid_fields:
            raise ValueError(f"Invalid sort field: {v}. Valid fields: {valid_fields}")
        return v

    @validator('sort_order')
    def validate_sort_order(cls, v):
        """Validate sort order."""
        if v not in ["asc", "desc"]:
            raise ValueError("Sort order must be 'asc' or 'desc'")
        return v

class PropertyCalculationRequest(BaseModel):
    """Model for requesting property metric calculations using Python algorithms."""
    amount: float = Field(..., description="Bid/sale amount in USD", gt=0)
    acreage: Optional[float] = Field(None, description="Property acreage", ge=0)
    description: Optional[str] = Field(None, description="Property description for water feature detection")
    assessed_value: Optional[float] = Field(None, description="County assessed value", ge=0)

class PropertyCalculationResponse(BaseModel):
    """Model for property calculation results."""
    price_per_acre: Optional[float] = Field(None, description="Calculated: amount / acreage")
    water_score: float = Field(..., description="Water feature score calculated from description")
    investment_score: Optional[float] = Field(None, description="Overall investment score (0.0-100.0)")
    estimated_all_in_cost: float = Field(..., description="Total cost including Alabama fees")
    assessed_value_ratio: Optional[float] = Field(None, description="Calculated: amount / assessed_value")

    # Algorithm validation
    algorithm_version: str = Field(..., description="Algorithm version used for calculations")
    calculation_timestamp: datetime = Field(..., description="When calculations were performed")

class PropertyBulkOperation(BaseModel):
    """Model for bulk property operations."""
    operation: str = Field(..., description="Operation type: create, update, delete")
    properties: List[dict] = Field(..., description="List of property data")

    @validator('operation')
    def validate_operation(cls, v):
        """Validate bulk operation type."""
        if v not in ["create", "update", "delete"]:
            raise ValueError("Operation must be 'create', 'update', or 'delete'")
        return v

class PropertyBulkResponse(BaseModel):
    """Model for bulk operation responses."""
    operation: str = Field(..., description="Operation type performed")
    total_requested: int = Field(..., description="Total number of operations requested")
    successful: int = Field(..., description="Number of successful operations")
    failed: int = Field(..., description="Number of failed operations")
    errors: List[dict] = Field(default=[], description="List of errors for failed operations")
    processing_time_seconds: float = Field(..., description="Total processing time")

class PropertyMetrics(BaseModel):
    """Model for property analysis metrics."""
    total_properties: int = Field(..., description="Total number of properties")
    average_investment_score: float = Field(..., description="Average investment score")
    average_water_score: float = Field(..., description="Average water score")
    average_price_per_acre: float = Field(..., description="Average price per acre")
    properties_with_water: int = Field(..., description="Number of properties with water features")
    county_distribution: dict = Field(..., description="Distribution of properties by county")
    year_distribution: dict = Field(..., description="Distribution of properties by year")
    score_ranges: dict = Field(..., description="Investment score distribution by ranges")
