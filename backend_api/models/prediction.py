"""
Prediction API Models for Market Intelligence Engine
Pydantic models for property appreciation forecasts, market timing, and opportunities.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class PredictionConfidence(str, Enum):
    """Prediction confidence levels."""
    very_low = "very_low"
    low = "low"
    medium = "medium"
    high = "high"
    very_high = "very_high"


class MarketTrend(str, Enum):
    """Market trend directions."""
    declining = "declining"
    stable = "stable"
    growing = "growing"
    booming = "booming"


class OpportunityType(str, Enum):
    """Types of investment opportunities."""
    undervalued_property = "undervalued_property"
    emerging_market = "emerging_market"
    water_frontage_deal = "water_frontage_deal"
    large_acreage_opportunity = "large_acreage_opportunity"
    county_growth_play = "county_growth_play"


class MarketPhase(str, Enum):
    """Current market phase."""
    buyer_market = "buyer_market"
    seller_market = "seller_market"
    balanced = "balanced"


# Request Models
class PropertyAppreciationRequest(BaseModel):
    """Request model for property appreciation prediction."""
    property_data: Dict[str, Any] = Field(..., description="Property data for prediction")
    county: str = Field(..., description="Alabama county name")
    current_investment_score: float = Field(..., description="Current investment score", ge=0, le=100)

    class Config:
        json_schema_extra = {
            "example": {
                "property_data": {
                    "id": "test_1",
                    "amount": 138.87,
                    "acreage": 3.546,
                    "price_per_acre": 39.16,
                    "water_score": 0.0,
                    "investment_score": 80.0,
                    "county": "Mobile"
                },
                "county": "Mobile",
                "current_investment_score": 80.0
            }
        }


class MarketTimingRequest(BaseModel):
    """Request model for market timing analysis."""
    county: str = Field(..., description="Alabama county name")

    class Config:
        json_schema_extra = {
            "example": {
                "county": "Mobile"
            }
        }


class OpportunityDetectionRequest(BaseModel):
    """Request model for opportunity detection."""
    properties_data: List[Dict[str, Any]] = Field(..., description="List of properties to analyze")
    top_n: int = Field(default=10, description="Number of top opportunities to return", ge=1, le=50)

    class Config:
        json_schema_extra = {
            "example": {
                "properties_data": [
                    {
                        "id": "test_1",
                        "amount": 138.87,
                        "acreage": 3.546,
                        "price_per_acre": 39.16,
                        "water_score": 0.0,
                        "investment_score": 80.0,
                        "county": "Mobile"
                    }
                ],
                "top_n": 10
            }
        }


# Response Models
class PropertyAppreciationResponse(BaseModel):
    """Response model for property appreciation forecast."""
    property_id: str = Field(..., description="Property identifier")
    county: str = Field(..., description="Alabama county")
    one_year_appreciation: float = Field(..., description="Predicted 1-year appreciation rate")
    three_year_appreciation: float = Field(..., description="Predicted 3-year appreciation rate")
    five_year_appreciation: float = Field(..., description="Predicted 5-year appreciation rate")
    market_trend: MarketTrend = Field(..., description="Predicted market trend")
    confidence_level: PredictionConfidence = Field(..., description="Prediction confidence")
    risk_score: float = Field(..., description="Risk assessment score", ge=0, le=1)
    prediction_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When prediction was generated")

    class Config:
        json_schema_extra = {
            "example": {
                "property_id": "test_1",
                "county": "Mobile",
                "one_year_appreciation": 1.62,
                "three_year_appreciation": 4.55,
                "five_year_appreciation": 7.28,
                "market_trend": "growing",
                "confidence_level": "high",
                "risk_score": 0.15,
                "prediction_timestamp": "2025-09-20T12:00:00Z"
            }
        }


class MarketTimingResponse(BaseModel):
    """Response model for market timing analysis."""
    county: str = Field(..., description="Alabama county")
    current_market_phase: MarketPhase = Field(..., description="Current market phase")
    optimal_buy_window: List[int] = Field(..., description="Optimal buying window in months [start, end]")
    optimal_sell_window: List[int] = Field(..., description="Optimal selling window in months [start, end]")
    price_momentum: float = Field(..., description="Price momentum indicator", ge=-1, le=1)
    market_volatility: float = Field(..., description="Market volatility measure", ge=0, le=1)
    confidence_score: float = Field(..., description="Analysis confidence", ge=0, le=1)
    prediction_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When analysis was generated")

    class Config:
        json_schema_extra = {
            "example": {
                "county": "Mobile",
                "current_market_phase": "buyer_market",
                "optimal_buy_window": [1, 6],
                "optimal_sell_window": [18, 24],
                "price_momentum": 0.25,
                "market_volatility": 0.3,
                "confidence_score": 0.8,
                "prediction_timestamp": "2025-09-20T12:00:00Z"
            }
        }


class EmergingOpportunityResponse(BaseModel):
    """Response model for individual emerging opportunity."""
    property_id: str = Field(..., description="Property identifier")
    county: str = Field(..., description="Alabama county")
    opportunity_type: OpportunityType = Field(..., description="Type of opportunity")
    opportunity_score: float = Field(..., description="Opportunity score out of 100", ge=0, le=100)
    potential_appreciation: float = Field(..., description="Potential appreciation rate")
    risk_adjusted_return: float = Field(..., description="Risk-adjusted return estimate")
    expected_timeline_months: int = Field(..., description="Expected timeline in months", ge=1)
    confidence_level: PredictionConfidence = Field(..., description="Prediction confidence")
    primary_drivers: List[str] = Field(..., description="Key drivers for this opportunity")
    risk_factors: List[str] = Field(..., description="Major risk factors to consider")
    prediction_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When prediction was generated")

    class Config:
        json_schema_extra = {
            "example": {
                "property_id": "test_1",
                "county": "Mobile",
                "opportunity_type": "undervalued_property",
                "opportunity_score": 85.2,
                "potential_appreciation": 2.45,
                "risk_adjusted_return": 1.89,
                "expected_timeline_months": 18,
                "confidence_level": "high",
                "primary_drivers": ["Below-market pricing", "Strong county fundamentals"],
                "risk_factors": ["Market volatility", "Liquidity constraints"],
                "prediction_timestamp": "2025-09-20T12:00:00Z"
            }
        }


class OpportunityDetectionResponse(BaseModel):
    """Response model for opportunity detection results."""
    total_properties_analyzed: int = Field(..., description="Number of properties analyzed")
    opportunities_found: int = Field(..., description="Number of opportunities detected")
    opportunities: List[EmergingOpportunityResponse] = Field(..., description="List of detected opportunities")
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When analysis was performed")

    class Config:
        json_schema_extra = {
            "example": {
                "total_properties_analyzed": 150,
                "opportunities_found": 10,
                "opportunities": [],
                "analysis_timestamp": "2025-09-20T12:00:00Z"
            }
        }


# Batch prediction models
class BatchAppreciationRequest(BaseModel):
    """Request model for batch property appreciation predictions."""
    properties: List[PropertyAppreciationRequest] = Field(..., description="List of properties for prediction")

    class Config:
        json_schema_extra = {
            "example": {
                "properties": [
                    {
                        "property_data": {"id": "test_1", "amount": 138.87, "county": "Mobile"},
                        "county": "Mobile",
                        "current_investment_score": 80.0
                    }
                ]
            }
        }


class BatchAppreciationResponse(BaseModel):
    """Response model for batch appreciation predictions."""
    total_requested: int = Field(..., description="Number of predictions requested")
    successful_predictions: int = Field(..., description="Number of successful predictions")
    failed_predictions: int = Field(..., description="Number of failed predictions")
    predictions: List[PropertyAppreciationResponse] = Field(..., description="List of predictions")
    errors: List[Dict[str, Any]] = Field(default=[], description="List of errors for failed predictions")
    processing_time_seconds: float = Field(..., description="Total processing time")
    batch_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When batch was processed")


class PredictionHealthResponse(BaseModel):
    """Response model for prediction engine health check."""
    engine_status: str = Field(..., description="Prediction engine status")
    algorithm_version: str = Field(..., description="Algorithm version")
    last_model_update: datetime = Field(..., description="Last model update timestamp")
    available_counties: List[str] = Field(..., description="Counties with prediction capability")
    performance_metrics: Dict[str, float] = Field(..., description="Engine performance metrics")
    uptime_seconds: float = Field(..., description="Engine uptime in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "engine_status": "healthy",
                "algorithm_version": "1.0.0",
                "last_model_update": "2025-09-20T10:00:00Z",
                "available_counties": ["Mobile", "Baldwin", "Jefferson"],
                "performance_metrics": {
                    "avg_prediction_time_ms": 125.5,
                    "accuracy_score": 0.87,
                    "cache_hit_rate": 0.92
                },
                "uptime_seconds": 3600.0
            }
        }