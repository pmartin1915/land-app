"""
Predictive Market Intelligence API Endpoints
Advanced prediction algorithms for property appreciation, market timing, and opportunity detection.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import List, Optional
import logging
import time
from datetime import datetime

from ..models.prediction import (
    PropertyAppreciationRequest, PropertyAppreciationResponse,
    MarketTimingRequest, MarketTimingResponse,
    OpportunityDetectionRequest, OpportunityDetectionResponse,
    EmergingOpportunityResponse,
    BatchAppreciationRequest, BatchAppreciationResponse,
    PredictionHealthResponse,
    PredictionConfidence, MarketTrend, OpportunityType, MarketPhase
)
from ..auth import require_property_read

# Import the predictive engine
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.predictive_market_engine import (
    get_predictive_engine,
    PropertyAppreciationForecast,
    MarketTimingAnalysis,
    EmergingOpportunity
)

from ..config import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

# Engine startup tracking
_engine_start_time = time.time()


@router.get("/health", response_model=PredictionHealthResponse)
@limiter.limit("100/minute")
async def prediction_engine_health(request: Request):
    """Get prediction engine health status and performance metrics."""
    try:
        engine = get_predictive_engine()

        # Get available counties (static list for now, could be dynamic)
        available_counties = [
            "Mobile", "Baldwin", "Jefferson", "Madison", "Montgomery",
            "Tuscaloosa", "Shelby", "Lee", "Houston", "Etowah"
        ]

        # Calculate basic performance metrics
        uptime = time.time() - _engine_start_time

        # Mock performance metrics (in production, these would be real metrics)
        performance_metrics = {
            "avg_prediction_time_ms": 145.2,
            "accuracy_score": 0.89,
            "cache_hit_rate": 0.94,
            "requests_per_minute": 25.3
        }

        return PredictionHealthResponse(
            engine_status="healthy",
            algorithm_version="1.0.0",
            last_model_update=datetime.utcnow(),
            available_counties=available_counties,
            performance_metrics=performance_metrics,
            uptime_seconds=uptime
        )

    except Exception as e:
        logger.error(f"Prediction engine health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Prediction engine unhealthy")


@router.post("/appreciation", response_model=PropertyAppreciationResponse)
@limiter.limit("50/minute")
async def predict_property_appreciation(
    request: Request,
    prediction_request: PropertyAppreciationRequest,
    auth_data: dict = Depends(require_property_read)
):
    """
    Predict property appreciation rates using advanced market intelligence algorithms.

    Provides 1-year, 3-year, and 5-year appreciation forecasts with confidence levels.
    """
    try:
        start_time = time.time()

        engine = get_predictive_engine()

        # Generate appreciation forecast
        forecast = engine.predict_property_appreciation(
            prediction_request.property_data,
            prediction_request.county,
            prediction_request.current_investment_score
        )

        # Map enum values to response model
        response = PropertyAppreciationResponse(
            property_id=prediction_request.property_data.get("id", "unknown"),
            county=prediction_request.county,
            one_year_appreciation=forecast.one_year_appreciation,
            three_year_appreciation=forecast.three_year_appreciation,
            five_year_appreciation=forecast.five_year_appreciation,
            market_trend=MarketTrend(forecast.market_trend.value),
            confidence_level=PredictionConfidence(forecast.confidence_level.value),
            risk_score=forecast.risk_score
        )

        processing_time = time.time() - start_time
        logger.info(f"Property appreciation prediction completed in {processing_time:.3f}s - " +
                   f"Property: {response.property_id}, County: {response.county}, " +
                   f"3yr forecast: {response.three_year_appreciation:.2%}")

        return response

    except Exception as e:
        logger.error(f"Property appreciation prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate appreciation forecast")


@router.post("/market-timing", response_model=MarketTimingResponse)
@limiter.limit("30/minute")
async def analyze_market_timing(
    request: Request,
    timing_request: MarketTimingRequest,
    auth_data: dict = Depends(require_property_read)
):
    """
    Analyze market timing for optimal buy/sell windows in a specific county.

    Provides market phase analysis, momentum indicators, and optimal timing windows.
    """
    try:
        start_time = time.time()

        engine = get_predictive_engine()

        # Generate market timing analysis
        timing = engine.analyze_market_timing(timing_request.county)

        # Map enum values to response model
        response = MarketTimingResponse(
            county=timing_request.county,
            current_market_phase=MarketPhase(timing.current_market_phase),
            optimal_buy_window=timing.optimal_buy_window,
            optimal_sell_window=timing.optimal_sell_window,
            price_momentum=timing.price_momentum,
            market_volatility=timing.market_volatility,
            confidence_score=timing.confidence_score
        )

        processing_time = time.time() - start_time
        logger.info(f"Market timing analysis completed in {processing_time:.3f}s - " +
                   f"County: {response.county}, Phase: {response.current_market_phase}, " +
                   f"Momentum: {response.price_momentum:.2f}")

        return response

    except Exception as e:
        logger.error(f"Market timing analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to analyze market timing")


@router.post("/opportunities", response_model=OpportunityDetectionResponse)
@limiter.limit("20/minute")
async def detect_emerging_opportunities(
    request: Request,
    opportunity_request: OpportunityDetectionRequest,
    auth_data: dict = Depends(require_property_read)
):
    """
    Detect emerging investment opportunities from a set of properties.

    Uses advanced pattern recognition to identify undervalued properties and market opportunities.
    """
    try:
        start_time = time.time()

        engine = get_predictive_engine()

        # Detect opportunities
        opportunities_data = engine.detect_emerging_opportunities(
            opportunity_request.properties_data,
            top_n=opportunity_request.top_n
        )

        # Convert to response format
        opportunities = []
        for opp in opportunities_data:
            opportunity = EmergingOpportunityResponse(
                property_id=opp.property_id,
                county=opp.county,
                opportunity_type=OpportunityType(opp.opportunity_type),
                opportunity_score=opp.opportunity_score,
                potential_appreciation=opp.potential_appreciation,
                risk_adjusted_return=opp.risk_adjusted_return,
                expected_timeline_months=opp.expected_timeline_months,
                confidence_level=PredictionConfidence(opp.confidence_level.value),
                primary_drivers=opp.primary_drivers,
                risk_factors=opp.risk_factors
            )
            opportunities.append(opportunity)

        response = OpportunityDetectionResponse(
            total_properties_analyzed=len(opportunity_request.properties_data),
            opportunities_found=len(opportunities),
            opportunities=opportunities
        )

        processing_time = time.time() - start_time
        logger.info(f"Opportunity detection completed in {processing_time:.3f}s - " +
                   f"Analyzed: {response.total_properties_analyzed} properties, " +
                   f"Found: {response.opportunities_found} opportunities")

        return response

    except Exception as e:
        logger.error(f"Opportunity detection failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to detect opportunities")


@router.post("/appreciation/batch", response_model=BatchAppreciationResponse)
@limiter.limit("10/minute")
async def batch_appreciation_predictions(
    request: Request,
    batch_request: BatchAppreciationRequest,
    auth_data: dict = Depends(require_property_read)
):
    """
    Generate appreciation predictions for multiple properties in a single request.

    Efficient batch processing for large-scale analysis.
    """
    try:
        start_time = time.time()

        engine = get_predictive_engine()

        total_requested = len(batch_request.properties)
        successful_predictions = 0
        failed_predictions = 0
        predictions = []
        errors = []

        logger.info(f"Starting batch appreciation prediction for {total_requested} properties")

        for i, prop_request in enumerate(batch_request.properties):
            try:
                # Generate forecast for this property
                forecast = engine.predict_property_appreciation(
                    prop_request.property_data,
                    prop_request.county,
                    prop_request.current_investment_score
                )

                # Create response
                prediction = PropertyAppreciationResponse(
                    property_id=prop_request.property_data.get("id", f"batch_{i}"),
                    county=prop_request.county,
                    one_year_appreciation=forecast.one_year_appreciation,
                    three_year_appreciation=forecast.three_year_appreciation,
                    five_year_appreciation=forecast.five_year_appreciation,
                    market_trend=MarketTrend(forecast.market_trend.value),
                    confidence_level=PredictionConfidence(forecast.confidence_level.value),
                    risk_score=forecast.risk_score
                )

                predictions.append(prediction)
                successful_predictions += 1

            except Exception as e:
                failed_predictions += 1
                errors.append({
                    "index": i,
                    "property_id": prop_request.property_data.get("id", f"batch_{i}"),
                    "error": str(e)
                })
                logger.warning(f"Failed to predict for property {i}: {str(e)}")

        processing_time = time.time() - start_time

        response = BatchAppreciationResponse(
            total_requested=total_requested,
            successful_predictions=successful_predictions,
            failed_predictions=failed_predictions,
            predictions=predictions,
            errors=errors,
            processing_time_seconds=processing_time
        )

        logger.info(f"Batch prediction completed in {processing_time:.3f}s - " +
                   f"Success: {successful_predictions}/{total_requested}")

        return response

    except Exception as e:
        logger.error(f"Batch appreciation prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process batch predictions")


@router.get("/counties/timing-overview")
@limiter.limit("20/minute")
async def get_counties_timing_overview(
    request: Request,
    auth_data: dict = Depends(require_property_read),
    counties: Optional[List[str]] = Query(None, description="Specific counties to analyze")
):
    """
    Get market timing overview for multiple counties.

    Provides a consolidated view of market conditions across Alabama counties.
    """
    try:
        start_time = time.time()

        engine = get_predictive_engine()

        # Default counties if none specified
        if not counties:
            counties = ["Mobile", "Baldwin", "Jefferson", "Madison", "Montgomery",
                       "Tuscaloosa", "Shelby", "Lee", "Houston", "Etowah"]

        timing_overview = {}

        for county in counties:
            try:
                timing = engine.analyze_market_timing(county)

                timing_overview[county] = {
                    "current_market_phase": timing.current_market_phase,
                    "optimal_buy_window": timing.optimal_buy_window,
                    "optimal_sell_window": timing.optimal_sell_window,
                    "price_momentum": timing.price_momentum,
                    "market_volatility": timing.market_volatility,
                    "confidence_score": timing.confidence_score
                }

            except Exception as e:
                logger.warning(f"Failed to analyze timing for {county}: {str(e)}")
                timing_overview[county] = {
                    "error": str(e),
                    "status": "analysis_failed"
                }

        processing_time = time.time() - start_time

        logger.info(f"Counties timing overview completed in {processing_time:.3f}s - " +
                   f"Analyzed {len(counties)} counties")

        return {
            "counties_analyzed": len(counties),
            "successful_analyses": len([c for c in timing_overview.values() if "error" not in c]),
            "timing_data": timing_overview,
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "processing_time_seconds": processing_time
        }

    except Exception as e:
        logger.error(f"Counties timing overview failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate timing overview")


@router.get("/analytics/performance")
@limiter.limit("10/minute")
async def get_prediction_analytics(
    request: Request,
    auth_data: dict = Depends(require_property_read)
):
    """
    Get prediction engine performance analytics and statistics.

    Provides insights into prediction accuracy, processing times, and usage patterns.
    """
    try:
        # Mock analytics data (in production, this would come from monitoring systems)
        analytics = {
            "prediction_stats": {
                "total_predictions_generated": 15247,
                "predictions_last_24h": 892,
                "avg_confidence_score": 0.78,
                "high_confidence_percentage": 64.2
            },
            "performance_metrics": {
                "avg_response_time_ms": 156.8,
                "95th_percentile_response_time_ms": 284.3,
                "cache_efficiency": 0.91,
                "error_rate_percentage": 0.8
            },
            "market_coverage": {
                "counties_supported": 67,
                "properties_analyzed_total": 125000,
                "active_opportunity_alerts": 342
            },
            "algorithm_metrics": {
                "model_accuracy": 0.87,
                "last_model_training": "2025-09-15T10:00:00Z",
                "feature_importance_top3": [
                    "county_market_dynamics",
                    "property_characteristics",
                    "historical_price_trends"
                ]
            },
            "uptime_info": {
                "engine_uptime_hours": (time.time() - _engine_start_time) / 3600,
                "last_restart": datetime.fromtimestamp(_engine_start_time).isoformat(),
                "availability_percentage": 99.7
            }
        }

        return analytics

    except Exception as e:
        logger.error(f"Failed to get prediction analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")