"""
Pydantic models for Portfolio Analytics API.
Provides aggregate analysis of user's watched properties.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


# ============================================================================
# Portfolio Summary Models
# ============================================================================

class PortfolioSummaryResponse(BaseModel):
    """Aggregate metrics for all watched properties."""
    total_count: int = Field(..., description="Total watched properties")
    total_value: float = Field(..., description="Sum of all property amounts")
    total_acreage: float = Field(..., description="Sum of all acreage")
    total_effective_cost: float = Field(..., description="Sum of effective costs (amount + quiet title)")

    # Averages
    avg_investment_score: float = Field(..., description="Average investment score (0-100)")
    avg_buy_hold_score: Optional[float] = Field(None, description="Average buy-hold score (0-100)")
    avg_wholesale_score: Optional[float] = Field(None, description="Average wholesale score (0-100)")
    avg_price_per_acre: float = Field(..., description="Average price per acre")

    # Capital utilization
    capital_budget: Optional[float] = Field(None, description="User's investment budget")
    capital_utilized: float = Field(..., description="Total effective cost of watched properties")
    capital_utilization_pct: Optional[float] = Field(None, description="Percentage of budget committed")
    capital_remaining: Optional[float] = Field(None, description="Remaining budget")

    # Water features
    properties_with_water: int = Field(..., description="Count with water_score > 0")
    water_access_percentage: float = Field(..., description="Percentage with water features")

    timestamp: datetime = Field(..., description="When stats were calculated")


# ============================================================================
# Geographic Breakdown Models
# ============================================================================

class CountyBreakdown(BaseModel):
    """Stats for a single county."""
    county: str = Field(..., description="County name")
    state: str = Field(..., description="State code")
    count: int = Field(..., description="Number of watched properties")
    total_value: float = Field(..., description="Sum of amounts")
    avg_investment_score: float = Field(..., description="Average score")
    percentage_of_portfolio: float = Field(..., description="Percentage of total portfolio")


class StateBreakdown(BaseModel):
    """Stats for a single state."""
    state: str = Field(..., description="State code")
    state_name: str = Field(..., description="Full state name")
    count: int = Field(..., description="Number of watched properties")
    total_value: float = Field(..., description="Sum of amounts")
    total_acreage: float = Field(..., description="Sum of acreage")
    avg_investment_score: float = Field(..., description="Average investment score")
    avg_buy_hold_score: Optional[float] = Field(None, description="Average buy-hold score")
    percentage_of_portfolio: float = Field(..., description="Percentage of total portfolio")
    counties: List[CountyBreakdown] = Field(default_factory=list, description="County breakdown")


class GeographicBreakdownResponse(BaseModel):
    """Geographic distribution of portfolio."""
    total_states: int = Field(..., description="Number of states represented")
    total_counties: int = Field(..., description="Number of counties represented")
    states: List[StateBreakdown] = Field(..., description="Breakdown by state")
    top_state: Optional[str] = Field(None, description="State with most properties")
    top_county: Optional[str] = Field(None, description="County with most properties")
    timestamp: datetime = Field(..., description="When stats were calculated")


# ============================================================================
# Score Distribution Models
# ============================================================================

class ScoreBucket(BaseModel):
    """Properties in a score range."""
    range_label: str = Field(..., description="Range label (e.g., '80-100')")
    min_score: int = Field(..., description="Minimum score in bucket")
    max_score: int = Field(..., description="Maximum score in bucket")
    count: int = Field(..., description="Number of properties")
    percentage: float = Field(..., description="Percentage of portfolio")
    property_ids: List[str] = Field(default_factory=list, description="IDs in this bucket")


class ScoreDistributionResponse(BaseModel):
    """Investment quality breakdown."""
    # Investment score distribution
    investment_score_buckets: List[ScoreBucket] = Field(..., description="Distribution buckets")

    # Buy-hold score distribution
    buy_hold_score_buckets: List[ScoreBucket] = Field(..., description="Buy-hold distribution")

    # Top performers (score > 80)
    top_performers_count: int = Field(..., description="Count with investment_score > 80")
    top_performers: List[str] = Field(..., description="Property IDs of top performers")

    # Underperformers (score < 40)
    underperformers_count: int = Field(..., description="Count with investment_score < 40")
    underperformers: List[str] = Field(..., description="Property IDs of underperformers")

    # Averages
    median_investment_score: Optional[float] = Field(None, description="Median investment score")
    score_std_deviation: Optional[float] = Field(None, description="Score standard deviation")

    timestamp: datetime = Field(..., description="When stats were calculated")


# ============================================================================
# Risk Analysis Models
# ============================================================================

class ConcentrationRisk(BaseModel):
    """Geographic concentration risk metrics."""
    highest_state_concentration: float = Field(..., description="Percentage in single state")
    highest_state: Optional[str] = Field(None, description="Most concentrated state")
    highest_county_concentration: float = Field(..., description="Percentage in single county")
    highest_county: Optional[str] = Field(None, description="Most concentrated county")
    diversification_score: float = Field(..., description="0-100, higher = more diversified")


class RiskAnalysisResponse(BaseModel):
    """Portfolio risk metrics."""
    # Concentration risk
    concentration: ConcentrationRisk = Field(..., description="Geographic concentration")

    # Time-to-ownership exposure
    avg_time_to_ownership_days: Optional[float] = Field(None, description="Average days to clear title")
    properties_over_1_year: int = Field(..., description="Properties with >365 days to ownership")
    properties_over_3_years: int = Field(..., description="Properties with >1095 days to ownership")

    # Delta region exposure (AR economic distress areas)
    delta_region_count: int = Field(..., description="Properties in Delta region counties")
    delta_region_percentage: float = Field(..., description="Percentage in Delta region")
    delta_region_counties: List[str] = Field(default_factory=list, description="Delta counties in portfolio")

    # Market reject exposure (pre-2015 delinquency)
    market_reject_count: int = Field(..., description="Properties with stale delinquency")
    market_reject_percentage: float = Field(..., description="Percentage of market rejects")

    # Capital concentration
    largest_single_property_pct: float = Field(..., description="Largest property as % of portfolio value")
    top_3_properties_pct: float = Field(..., description="Top 3 properties as % of portfolio value")

    # Risk summary
    overall_risk_level: str = Field(..., description="low, medium, high, critical")
    risk_flags: List[str] = Field(default_factory=list, description="Active risk warnings")

    timestamp: datetime = Field(..., description="When stats were calculated")


# ============================================================================
# Performance Tracking Models
# ============================================================================

class StarRatingBreakdown(BaseModel):
    """Properties by user star rating."""
    rating: int = Field(..., description="Star rating (1-5)")
    count: int = Field(..., description="Number of properties")
    avg_investment_score: float = Field(..., description="Average score for this rating")


class RecentAddition(BaseModel):
    """Recently added property summary."""
    property_id: str = Field(..., description="Property ID")
    parcel_id: str = Field(..., description="Parcel identifier")
    county: Optional[str] = Field(None, description="County name")
    state: str = Field(..., description="State code")
    amount: float = Field(..., description="Property amount")
    investment_score: Optional[float] = Field(None, description="Investment score")
    added_at: datetime = Field(..., description="When added to watchlist")


class PerformanceTrackingResponse(BaseModel):
    """Performance and activity tracking."""
    # Recent additions
    additions_last_7_days: int = Field(..., description="Properties added in last 7 days")
    additions_last_30_days: int = Field(..., description="Properties added in last 30 days")
    recent_additions: List[RecentAddition] = Field(..., description="Recent additions with details")

    # Star ratings
    star_rating_breakdown: List[StarRatingBreakdown] = Field(..., description="By star rating")
    rated_count: int = Field(..., description="Total properties with ratings")
    unrated_count: int = Field(..., description="Properties without ratings")
    avg_star_rating: Optional[float] = Field(None, description="Average star rating")

    # First deal tracking
    has_first_deal: bool = Field(..., description="Whether user has assigned first deal")
    first_deal_stage: Optional[str] = Field(None, description="Current first deal pipeline stage")
    first_deal_property_id: Optional[str] = Field(None, description="First deal property ID")

    # Activity timeline
    activity_by_week: Dict[str, int] = Field(default_factory=dict, description="Additions by week")

    timestamp: datetime = Field(..., description="When stats were calculated")


# ============================================================================
# Full Export Model
# ============================================================================

class PortfolioAnalyticsExport(BaseModel):
    """Complete portfolio analytics export."""
    summary: PortfolioSummaryResponse
    geographic: GeographicBreakdownResponse
    scores: ScoreDistributionResponse
    risk: RiskAnalysisResponse
    performance: PerformanceTrackingResponse
    exported_at: datetime = Field(..., description="Export timestamp")
