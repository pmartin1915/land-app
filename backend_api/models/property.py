"""
Pydantic models for Property API operations
Models match iOS Core Data schema and enable API request/response validation
"""

from pydantic import BaseModel, Field, field_validator
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


class SaleType(str, Enum):
    """Property sale type enumeration for multi-state support."""
    TAX_LIEN = "tax_lien"
    TAX_DEED = "tax_deed"
    REDEEMABLE_DEED = "redeemable_deed"
    HYBRID = "hybrid"


class OwnerType(str, Enum):
    """Property owner type enumeration for wholesaling."""
    INDIVIDUAL = "individual"
    CORPORATE = "corporate"
    ESTATE = "estate"
    ABSENTEE = "absentee"
    UNKNOWN = "unknown"


class WholesalePipelineStatus(str, Enum):
    """Wholesale deal status enumeration."""
    IDENTIFIED = "identified"
    CONTACTED = "contacted"
    UNDER_CONTRACT = "under_contract"
    ASSIGNED = "assigned"
    CLOSED = "closed"
    DEAD = "dead"

class PropertyCreate(BaseModel):
    """Model for creating a new property."""
    parcel_id: str = Field(..., description="Unique parcel identifier", min_length=1)
    amount: float = Field(..., description="Bid/sale amount in USD", gt=0)
    acreage: Optional[float] = Field(None, description="Property acreage", ge=0)
    description: Optional[str] = Field(None, description="Legal property description")
    county: Optional[str] = Field(None, description="County name")
    owner_name: Optional[str] = Field(None, description="Property owner name")
    year_sold: Optional[str] = Field(None, description="Sale year")
    assessed_value: Optional[float] = Field(None, description="County assessed value", ge=0)
    device_id: Optional[str] = Field(None, description="Device that created this record")

    # Multi-state and wholesale fields (Pivot 2025)
    state: Optional[str] = Field('AL', description="State code (AL, AR, TX, FL)", max_length=2)
    sale_type: Optional[str] = Field(None, description="Tax lien, tax deed, redeemable deed, or hybrid")
    redemption_period_days: Optional[int] = Field(None, description="Days until ownership clear", ge=0)
    time_to_ownership_days: Optional[int] = Field(None, description="Total days to marketable title", ge=0)
    estimated_market_value: Optional[float] = Field(None, description="Estimated market value", ge=0)
    wholesale_spread: Optional[float] = Field(None, description="Market value - asking price")
    owner_type: Optional[str] = Field(None, description="Owner type for wholesaling")
    data_source: Optional[str] = Field(None, description="Scraper/platform source", max_length=100)
    auction_date: Optional[datetime] = Field(None, description="Scheduled auction date")
    auction_platform: Optional[str] = Field(None, description="Auction platform name", max_length=100)

    @field_validator('parcel_id')
    @classmethod
    def validate_parcel_id_secure(cls, v: str) -> str:
        """Enhanced parcel ID validation with security checks."""
        result = PropertyValidator.validate_parcel_id(v)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return result.sanitized_value

    @field_validator('amount')
    @classmethod
    def validate_amount_secure(cls, v: float) -> float:
        """Enhanced amount validation with security checks."""
        result = PropertyValidator.validate_amount(v)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return result.sanitized_value

    @field_validator('acreage')
    @classmethod
    def validate_acreage_secure(cls, v: Optional[float]) -> Optional[float]:
        """Enhanced acreage validation with security checks."""
        if v is None:
            return v
        result = PropertyValidator.validate_acreage(v)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return result.sanitized_value

    @field_validator('county')
    @classmethod
    def validate_county_secure(cls, v: Optional[str]) -> Optional[str]:
        """Enhanced county validation with security checks."""
        if v is None:
            return v
        result = PropertyValidator.validate_county(v)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return result.sanitized_value

    @field_validator('description')
    @classmethod
    def validate_description_secure(cls, v: Optional[str]) -> Optional[str]:
        """Enhanced description validation with security checks."""
        if v is None:
            return v
        result = PropertyValidator.validate_description(v)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return result.sanitized_value

    @field_validator('owner_name')
    @classmethod
    def validate_owner_name_secure(cls, v: Optional[str]) -> Optional[str]:
        """Enhanced owner name validation with security checks."""
        if v is None:
            return v
        result = PropertyValidator.validate_owner_name(v)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return result.sanitized_value

    @field_validator('year_sold')
    @classmethod
    def validate_year_sold_secure(cls, v: Optional[str]) -> Optional[str]:
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

    # Validation uses same logic as PropertyCreate
    @field_validator('county')
    @classmethod
    def validate_county_secure(cls, v: Optional[str]) -> Optional[str]:
        """Enhanced county validation with security checks."""
        if v is None:
            return v
        result = PropertyValidator.validate_county(v)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return result.sanitized_value

    @field_validator('year_sold')
    @classmethod
    def validate_year_sold_secure(cls, v: Optional[str]) -> Optional[str]:
        """Enhanced year sold validation with security checks."""
        if v is None:
            return v
        result = PropertyValidator.validate_year_sold(v)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return result.sanitized_value

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
    sync_timestamp: Optional[datetime] = Field(None, description="Last sync timestamp")
    is_deleted: bool = Field(default=False, description="Soft delete flag for sync")

    # Research workflow status
    status: str = Field(default="new", description="Research status: new, reviewing, bid_ready, rejected, purchased")
    triage_notes: Optional[str] = Field(None, description="Research notes from triage review")
    triaged_at: Optional[datetime] = Field(None, description="When property was triaged")
    triaged_by: Optional[str] = Field(None, description="Device/user that triaged this property")

    # Multi-state and wholesale fields (Pivot 2025)
    state: str = Field(default='AL', description="State code")
    sale_type: Optional[str] = Field(None, description="Tax lien, tax deed, redeemable deed, or hybrid")
    redemption_period_days: Optional[int] = Field(None, description="Days until ownership clear")
    time_to_ownership_days: Optional[int] = Field(None, description="Total days to marketable title")
    estimated_market_value: Optional[float] = Field(None, description="Estimated market value")
    wholesale_spread: Optional[float] = Field(None, description="Market value - asking price")
    owner_type: Optional[str] = Field(None, description="Owner type for wholesaling")
    data_source: Optional[str] = Field(None, description="Scraper/platform source")
    auction_date: Optional[datetime] = Field(None, description="Scheduled auction date")
    auction_platform: Optional[str] = Field(None, description="Auction platform name")

    # Multi-State Scoring Fields (Milestone 3)
    buy_hold_score: Optional[float] = Field(None, description="Time-adjusted buy-and-hold investment score (0-100)")
    wholesale_score: Optional[float] = Field(None, description="Wholesale flip viability score (0-100)")
    effective_cost: Optional[float] = Field(None, description="Total cost including quiet title fees")
    time_penalty_factor: Optional[float] = Field(None, description="Time decay multiplier (0-1)")

    model_config = {"from_attributes": True}  # Enable ORM mode for SQLAlchemy compatibility

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

    model_config = {"use_enum_values": True}


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
    year_sold: Optional[str] = Field(None, description="Filter by exact sale year")
    search_query: Optional[str] = Field(None, description="Search in description and owner name")
    min_year_sold: Optional[int] = Field(None, description="Minimum delinquency year (exclude pre-X properties)", ge=1900, le=2100)
    created_after: Optional[datetime] = Field(None, description="Filter by created_at date (period filter)")

    # Advanced Intelligence Filters
    min_county_market_score: Optional[float] = Field(None, description="Minimum county market score", ge=0)
    min_geographic_score: Optional[float] = Field(None, description="Minimum geographic score", ge=0)
    min_market_timing_score: Optional[float] = Field(None, description="Minimum market timing score", ge=0)
    min_total_description_score: Optional[float] = Field(None, description="Minimum total description score", ge=0)
    min_road_access_score: Optional[float] = Field(None, description="Minimum road access score", ge=0)

    # Multi-state filters (Pivot 2025)
    state: Optional[str] = Field(None, description="Filter by state code", max_length=2)
    sale_type: Optional[str] = Field(None, description="Filter by sale type")
    max_time_to_ownership_days: Optional[int] = Field(None, description="Maximum days to ownership", ge=0)
    min_wholesale_spread: Optional[float] = Field(None, description="Minimum wholesale spread", ge=0)
    owner_type: Optional[str] = Field(None, description="Filter by owner type")
    upcoming_auctions_only: Optional[bool] = Field(False, description="Only show properties with future auction dates")
    exclude_delta_region: Optional[bool] = Field(None, description="Exclude Delta region counties (AR high-risk)")

    # Multi-state scoring filters (Milestone 3)
    min_buy_hold_score: Optional[float] = Field(None, description="Minimum buy & hold score", ge=0, le=100)
    min_wholesale_score: Optional[float] = Field(None, description="Minimum wholesale score", ge=0, le=100)
    max_effective_cost: Optional[float] = Field(None, description="Maximum effective cost", ge=0)

    # Pagination
    page: int = Field(1, description="Page number (1-based)", ge=1)
    page_size: int = Field(100, description="Number of items per page", ge=1, le=1000)

    # Sorting
    sort_by: Optional[str] = Field("investment_score", description="Sort field")
    sort_order: Optional[str] = Field("desc", description="Sort order: asc or desc")

    @field_validator('sort_by')
    @classmethod
    def validate_sort_by(cls, v: Optional[str]) -> Optional[str]:
        """Validate sort field."""
        valid_fields = {
            "investment_score", "amount", "acreage", "price_per_acre", "water_score",
            "assessed_value_ratio", "county", "year_sold", "created_at", "updated_at",
            "county_market_score", "geographic_score", "market_timing_score",
            "total_description_score", "road_access_score",
            # Multi-state fields
            "state", "sale_type", "time_to_ownership_days", "wholesale_spread", "auction_date",
            # Multi-state scoring fields (Milestone 3)
            "buy_hold_score", "wholesale_score", "effective_cost", "time_penalty_factor"
        }
        if v not in valid_fields:
            raise ValueError(f"Invalid sort field: {v}. Valid fields: {valid_fields}")
        return v

    @field_validator('sort_order')
    @classmethod
    def validate_sort_order(cls, v: Optional[str]) -> Optional[str]:
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

    @field_validator('operation')
    @classmethod
    def validate_operation(cls, v: str) -> str:
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


# Dashboard Stats Models
class TopCounty(BaseModel):
    """Model for top county in dashboard stats."""
    name: str = Field(..., description="County name")
    count: int = Field(..., description="Number of properties in county")
    avg_investment_score: float = Field(..., description="Average investment score for county")


class RecentActivity(BaseModel):
    """Model for recent activity in dashboard."""
    type: str = Field(..., description="Activity type: new, updated, reviewed")
    description: str = Field(..., description="Activity description")
    timestamp: str = Field(..., description="ISO timestamp")


class PriceDistribution(BaseModel):
    """Model for price distribution chart data."""
    ranges: List[str] = Field(..., description="Price range labels")
    counts: List[int] = Field(..., description="Count of properties in each range")


class ScoreDistribution(BaseModel):
    """Model for score distribution radar chart."""
    water_score: float = Field(..., description="Average water score")
    investment_score: float = Field(..., description="Average investment score")
    county_market_score: float = Field(..., description="Average county market score")
    geographic_score: float = Field(..., description="Average geographic score")
    description_score: float = Field(..., description="Average description score")


class ActivityTimeline(BaseModel):
    """Model for activity timeline chart."""
    dates: List[str] = Field(..., description="Date labels for chart")
    new_properties: List[int] = Field(..., description="New properties count per date")


class DashboardStats(BaseModel):
    """Model for dashboard statistics."""
    # Scalar metrics
    total_properties: int = Field(..., description="Total number of properties")
    upcoming_auctions: int = Field(0, description="Properties with upcoming auctions")
    new_items_7d: int = Field(..., description="Properties added in last 7 days")
    new_items_trend: str = Field(..., description="Trend compared to previous week")
    watchlist_count: int = Field(0, description="Properties on watchlist")
    avg_investment_score: float = Field(..., description="Average investment score")
    water_access_percentage: float = Field(..., description="Percentage with water access")
    avg_price_per_acre: float = Field(..., description="Average price per acre")

    # Chart data
    top_counties: List[TopCounty] = Field(..., description="Top counties by property count")
    recent_activity: List[RecentActivity] = Field(..., description="Recent property activity")
    price_distribution: PriceDistribution = Field(..., description="Price distribution for chart")
    score_distribution: ScoreDistribution = Field(..., description="Score averages for radar chart")
    activity_timeline: ActivityTimeline = Field(..., description="Activity timeline for chart")


# Multi-State Configuration Models (Pivot 2025)

class StateConfigResponse(BaseModel):
    """Model for state configuration API responses."""
    id: int
    state_code: str
    state_name: str
    sale_type: str
    redemption_period_days: Optional[int]
    interest_rate: Optional[float]
    quiet_title_cost_estimate: Optional[float]
    time_to_ownership_days: int
    auction_platform: Optional[str]
    scraper_module: Optional[str]
    is_active: bool
    recommended_for_beginners: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StateConfigListResponse(BaseModel):
    """Model for state configuration list API responses."""
    states: List[StateConfigResponse] = Field(..., description="List of state configurations")
    total_count: int = Field(..., description="Total number of states")
    active_count: int = Field(..., description="Number of active states")


# Wholesale Pipeline Models (Pivot 2025)

class WholesalePipelineCreate(BaseModel):
    """Model for creating a wholesale pipeline entry."""
    property_id: str = Field(..., description="Property ID")
    status: WholesalePipelineStatus = Field(WholesalePipelineStatus.IDENTIFIED, description="Deal status")
    contract_price: Optional[float] = Field(None, description="Contract price", gt=0)
    assignment_fee: Optional[float] = Field(None, description="Wholesale fee", gt=0)
    earnest_money: Optional[float] = Field(None, description="Earnest money", ge=0)
    buyer_name: Optional[str] = Field(None, description="End buyer name", max_length=200)
    buyer_email: Optional[str] = Field(None, description="End buyer email", max_length=200)
    contract_date: Optional[datetime] = Field(None, description="Contract signing date")
    closing_date: Optional[datetime] = Field(None, description="Expected closing date")
    marketing_notes: Optional[str] = Field(None, description="Marketing notes", max_length=2000)
    notes: Optional[str] = Field(None, description="General notes", max_length=2000)


class WholesalePipelineUpdate(BaseModel):
    """Model for updating a wholesale pipeline entry."""
    status: Optional[WholesalePipelineStatus] = None
    contract_price: Optional[float] = Field(None, gt=0)
    assignment_fee: Optional[float] = Field(None, gt=0)
    earnest_money: Optional[float] = Field(None, ge=0)
    buyer_name: Optional[str] = Field(None, max_length=200)
    buyer_email: Optional[str] = Field(None, max_length=200)
    contract_date: Optional[datetime] = None
    closing_date: Optional[datetime] = None
    marketing_notes: Optional[str] = Field(None, max_length=2000)
    notes: Optional[str] = Field(None, max_length=2000)


class WholesalePipelineResponse(BaseModel):
    """Model for wholesale pipeline API responses."""
    id: str
    property_id: str
    status: str
    contract_price: Optional[float]
    assignment_fee: Optional[float]
    earnest_money: Optional[float]
    buyer_id: Optional[str]
    buyer_name: Optional[str]
    buyer_email: Optional[str]
    contract_date: Optional[datetime]
    closing_date: Optional[datetime]
    closed_at: Optional[datetime]
    marketing_notes: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WholesalePipelineListResponse(BaseModel):
    """Model for wholesale pipeline list API responses."""
    deals: List[WholesalePipelineResponse] = Field(..., description="List of wholesale deals")
    total_count: int = Field(..., description="Total number of deals")
    by_status: dict = Field(..., description="Count of deals by status")
