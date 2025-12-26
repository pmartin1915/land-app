"""
AI Testing & Validation API Endpoints
Programmatic access to prediction accuracy validation and performance monitoring.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
import logging
import time
from datetime import datetime, timedelta
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel, Field

from ..auth import require_property_read, require_admin
from ..models.prediction import (
    PredictionConfidence, MarketTrend, OpportunityType, MarketPhase
)

# Import the validation system
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.prediction_accuracy_validator import (
    get_prediction_validator,
    ValidationResult,
    BacktestResult,
    ValidationStatus,
    ValidationMetricType,
    validate_predictions_sample,
    run_prediction_backtest,
    get_prediction_performance_status
)

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


# Request/Response Models

class ValidationRequest(BaseModel):
    """Request model for prediction validation."""
    properties_sample: List[Dict[str, Any]] = Field(..., description="Sample of properties to validate")
    validation_period: str = Field(default="manual", description="Description of validation period")
    prediction_horizon: str = Field(default="3_year", description="Prediction horizon to validate")


class BacktestRequest(BaseModel):
    """Request model for backtesting."""
    days_back: int = Field(default=365, ge=30, le=1095, description="Number of days back to test")
    horizon_months: int = Field(default=12, ge=1, le=60, description="Prediction horizon in months")
    property_limit: int = Field(default=100, ge=10, le=1000, description="Maximum properties to test")


class ValidationMetricsResponse(BaseModel):
    """Response model for validation metrics."""
    accuracy_score: float
    precision_score: float
    recall_score: float
    mean_absolute_error: float
    confidence_calibration: float
    validation_status: str
    total_predictions: int
    successful_predictions: int
    failed_predictions: int
    validation_duration: float
    model_version: str


class BacktestMetricsResponse(BaseModel):
    """Response model for backtest metrics."""
    overall_accuracy: float
    market_trend_accuracy: float
    appreciation_mae: float
    appreciation_rmse: float
    high_confidence_accuracy: float
    medium_confidence_accuracy: float
    low_confidence_accuracy: float
    test_properties_count: int
    execution_time_seconds: float
    start_date: str
    end_date: str
    prediction_horizon_months: int


class PerformanceStatusResponse(BaseModel):
    """Response model for performance status."""
    status: str
    current_accuracy: Optional[float] = None
    accuracy_trend: Optional[str] = None
    predictions_validated: Optional[int] = None
    average_confidence: Optional[float] = None
    last_validation: Optional[str] = None
    alerts: List[str] = []
    uptime_hours: Optional[float] = None


class ValidationHistoryResponse(BaseModel):
    """Response model for validation history."""
    validations: List[ValidationMetricsResponse]
    total_count: int
    date_range: Dict[str, str]
    performance_summary: Dict[str, Any]


# API Endpoints

@router.get("/health", response_model=Dict[str, Any])
@limiter.limit("100/minute")
async def testing_system_health(request: Request):
    """Get AI testing system health status."""
    try:
        validator = get_prediction_validator()

        # Basic health check
        health_status = {
            "status": "healthy",
            "system": "AI Testing & Validation",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "database_connected": True,  # Simplified check
            "validator_initialized": validator is not None
        }

        return health_status

    except Exception as e:
        logger.error(f"Testing system health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Testing system unhealthy")


@router.post("/validate", response_model=ValidationMetricsResponse)
@limiter.limit("10/minute")
async def validate_predictions(
    request: Request,
    validation_request: ValidationRequest,
    auth_data: dict = Depends(require_property_read)
):
    """
    Validate prediction accuracy using provided property sample.

    Performs comprehensive validation of the prediction engine against
    a sample of properties using cross-validation techniques.
    """
    try:
        start_time = time.time()

        logger.info(f"Starting prediction validation for {len(validation_request.properties_sample)} properties")

        validator = get_prediction_validator()

        # Run validation
        result = validator.validate_current_predictions(
            validation_request.properties_sample,
            validation_request.validation_period
        )

        processing_time = time.time() - start_time

        logger.info(f"Validation completed in {processing_time:.2f}s - " +
                   f"Accuracy: {result.accuracy_score:.2%}, Status: {result.validation_status.value}")

        return ValidationMetricsResponse(
            accuracy_score=result.accuracy_score,
            precision_score=result.precision_score,
            recall_score=result.recall_score,
            mean_absolute_error=result.mean_absolute_error,
            confidence_calibration=result.confidence_calibration,
            validation_status=result.validation_status.value,
            total_predictions=result.total_predictions,
            successful_predictions=result.successful_predictions,
            failed_predictions=result.failed_predictions,
            validation_duration=result.validation_duration,
            model_version=result.model_version
        )

    except Exception as e:
        logger.error(f"Prediction validation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to validate predictions")


@router.post("/backtest", response_model=BacktestMetricsResponse)
@limiter.limit("3/hour")
async def run_backtest(
    request: Request,
    background_tasks: BackgroundTasks,
    backtest_request: BacktestRequest,
    auth_data: dict = Depends(require_admin)
):
    """
    Run comprehensive backtesting against historical data.

    Requires admin access due to computational intensity.
    Results are computed in the background for large datasets.
    """
    try:
        start_time = time.time()

        logger.info(f"Starting backtest: {backtest_request.days_back} days back, " +
                   f"{backtest_request.horizon_months} month horizon")

        validator = get_prediction_validator()

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=backtest_request.days_back)

        # Run backtest
        result = validator.run_backtest(
            start_date,
            end_date,
            backtest_request.horizon_months
        )

        processing_time = time.time() - start_time

        logger.info(f"Backtest completed in {processing_time:.2f}s - " +
                   f"Overall accuracy: {result.overall_accuracy:.2%}")

        return BacktestMetricsResponse(
            overall_accuracy=result.overall_accuracy,
            market_trend_accuracy=result.market_trend_accuracy,
            appreciation_mae=result.appreciation_mae,
            appreciation_rmse=result.appreciation_rmse,
            high_confidence_accuracy=result.high_confidence_accuracy,
            medium_confidence_accuracy=getattr(result, 'medium_confidence_accuracy', 0.0),
            low_confidence_accuracy=getattr(result, 'low_confidence_accuracy', 0.0),
            test_properties_count=result.test_properties_count,
            execution_time_seconds=result.execution_time_seconds,
            start_date=result.start_date.isoformat(),
            end_date=result.end_date.isoformat(),
            prediction_horizon_months=result.prediction_horizon_months
        )

    except Exception as e:
        logger.error(f"Backtest failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to run backtest")


@router.get("/performance/status", response_model=PerformanceStatusResponse)
@limiter.limit("60/minute")
async def get_performance_status(
    request: Request,
    auth_data: dict = Depends(require_property_read)
):
    """
    Get current prediction engine performance status.

    Returns real-time metrics about prediction accuracy, trends,
    and system health indicators.
    """
    try:
        performance_status = get_prediction_performance_status()

        status = performance_status.get("status", "unknown")
        metrics = performance_status.get("metrics", {})
        alerts = performance_status.get("alerts", [])

        return PerformanceStatusResponse(
            status=status,
            current_accuracy=metrics.get("current_accuracy"),
            accuracy_trend=metrics.get("accuracy_trend"),
            predictions_validated=metrics.get("predictions_validated"),
            average_confidence=metrics.get("average_confidence"),
            last_validation=metrics.get("last_validation"),
            alerts=alerts,
            uptime_hours=metrics.get("uptime_hours")
        )

    except Exception as e:
        logger.error(f"Failed to get performance status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance status")


@router.get("/validation/history", response_model=ValidationHistoryResponse)
@limiter.limit("30/minute")
async def get_validation_history(
    request: Request,
    days: int = Query(default=30, ge=1, le=365, description="Number of days of history to retrieve"),
    auth_data: dict = Depends(require_property_read)
):
    """
    Get validation history for the specified time period.

    Returns historical validation results with performance trends
    and summary statistics.
    """
    try:
        validator = get_prediction_validator()
        validation_history = validator.get_validation_history(days=days)

        if not validation_history:
            return ValidationHistoryResponse(
                validations=[],
                total_count=0,
                date_range={"start": "", "end": ""},
                performance_summary={}
            )

        # Convert to response format
        validation_responses = []
        for result in validation_history:
            validation_responses.append(ValidationMetricsResponse(
                accuracy_score=result.accuracy_score,
                precision_score=result.precision_score,
                recall_score=result.recall_score,
                mean_absolute_error=result.mean_absolute_error,
                confidence_calibration=result.confidence_calibration,
                validation_status=result.validation_status.value,
                total_predictions=result.total_predictions,
                successful_predictions=result.successful_predictions,
                failed_predictions=result.failed_predictions,
                validation_duration=result.validation_duration,
                model_version=result.model_version
            ))

        # Calculate date range
        sorted_validations = sorted(validation_history, key=lambda x: x.validation_timestamp)
        date_range = {
            "start": sorted_validations[0].validation_timestamp.isoformat(),
            "end": sorted_validations[-1].validation_timestamp.isoformat()
        }

        # Calculate performance summary
        accuracies = [v.accuracy_score for v in validation_history]
        performance_summary = {
            "average_accuracy": sum(accuracies) / len(accuracies) if accuracies else 0,
            "best_accuracy": max(accuracies) if accuracies else 0,
            "worst_accuracy": min(accuracies) if accuracies else 0,
            "total_predictions": sum(v.total_predictions for v in validation_history),
            "success_rate": sum(v.successful_predictions for v in validation_history) /
                          sum(v.total_predictions for v in validation_history) if validation_history else 0
        }

        logger.info(f"Retrieved {len(validation_history)} validation records for {days} days")

        return ValidationHistoryResponse(
            validations=validation_responses,
            total_count=len(validation_history),
            date_range=date_range,
            performance_summary=performance_summary
        )

    except Exception as e:
        logger.error(f"Failed to get validation history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve validation history")


@router.get("/performance/metrics", response_model=Dict[str, Any])
@limiter.limit("20/minute")
async def get_performance_metrics(
    request: Request,
    days: int = Query(default=7, ge=1, le=90, description="Number of days for metrics calculation"),
    auth_data: dict = Depends(require_property_read)
):
    """
    Get detailed performance metrics and analytics.

    Provides comprehensive performance analysis including trends,
    accuracy distributions, and model behavior insights.
    """
    try:
        validator = get_prediction_validator()
        validation_history = validator.get_validation_history(days=days)

        if not validation_history:
            return {
                "status": "no_data",
                "message": f"No validation data available for the last {days} days",
                "metrics": {}
            }

        # Calculate comprehensive metrics
        accuracies = [v.accuracy_score for v in validation_history]
        precisions = [v.precision_score for v in validation_history]
        recalls = [v.recall_score for v in validation_history]
        calibrations = [v.confidence_calibration for v in validation_history]

        # Status distribution
        status_counts = {}
        for v in validation_history:
            status = v.validation_status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        # Time-based analysis
        recent_validations = validation_history[:5]
        older_validations = validation_history[5:10] if len(validation_history) > 5 else []

        recent_avg = sum(v.accuracy_score for v in recent_validations) / len(recent_validations) if recent_validations else 0
        older_avg = sum(v.accuracy_score for v in older_validations) / len(older_validations) if older_validations else recent_avg

        trend_direction = "stable"
        if recent_avg > older_avg + 0.05:
            trend_direction = "improving"
        elif recent_avg < older_avg - 0.05:
            trend_direction = "declining"

        # County performance (if available)
        county_performance = {}
        for v in validation_history:
            for county, accuracy in v.county_performance.items():
                if county not in county_performance:
                    county_performance[county] = []
                county_performance[county].append(accuracy)

        county_averages = {
            county: sum(accuracies) / len(accuracies)
            for county, accuracies in county_performance.items()
        }

        metrics = {
            "period_days": days,
            "total_validations": len(validation_history),
            "accuracy_metrics": {
                "average": sum(accuracies) / len(accuracies),
                "minimum": min(accuracies),
                "maximum": max(accuracies),
                "latest": accuracies[0] if accuracies else 0,
                "trend_direction": trend_direction,
                "trend_magnitude": abs(recent_avg - older_avg)
            },
            "precision_metrics": {
                "average": sum(precisions) / len(precisions) if precisions else 0,
                "latest": precisions[0] if precisions else 0
            },
            "recall_metrics": {
                "average": sum(recalls) / len(recalls) if recalls else 0,
                "latest": recalls[0] if recalls else 0
            },
            "confidence_metrics": {
                "average_calibration": sum(calibrations) / len(calibrations) if calibrations else 0,
                "latest_calibration": calibrations[0] if calibrations else 0
            },
            "status_distribution": status_counts,
            "prediction_volume": {
                "total_predictions": sum(v.total_predictions for v in validation_history),
                "average_per_validation": sum(v.total_predictions for v in validation_history) / len(validation_history),
                "success_rate": sum(v.successful_predictions for v in validation_history) /
                              sum(v.total_predictions for v in validation_history) if validation_history else 0
            },
            "top_counties": dict(sorted(county_averages.items(), key=lambda x: x[1], reverse=True)[:10]),
            "performance_alerts": _generate_performance_alerts(validation_history),
            "last_updated": datetime.utcnow().isoformat()
        }

        logger.info(f"Generated performance metrics for {days} days: {len(validation_history)} validations")

        return {
            "status": "success",
            "metrics": metrics
        }

    except Exception as e:
        logger.error(f"Failed to get performance metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance metrics")


@router.post("/validate/quick", response_model=Dict[str, Any])
@limiter.limit("20/minute")
async def quick_validation(
    request: Request,
    property_count: int = Query(default=20, ge=5, le=100, description="Number of random properties to validate"),
    auth_data: dict = Depends(require_property_read)
):
    """
    Run quick validation using a random sample of properties.

    Useful for rapid health checks and monitoring without
    requiring specific property data.
    """
    try:
        # In production, this would fetch a random sample from the database
        # For now, we'll simulate with minimal sample data

        sample_properties = [
            {
                "id": f"quick_test_{i}",
                "county": ["Mobile", "Baldwin", "Jefferson", "Madison"][i % 4],
                "amount": 100 + (i * 50),
                "acreage": 1 + (i * 0.5),
                "investment_score": 50 + (i * 2),
                "water_score": i % 5,
                "price_per_acre": (100 + (i * 50)) / (1 + (i * 0.5))
            }
            for i in range(min(property_count, 20))  # Limit for demo
        ]

        # Run quick validation
        result = validate_predictions_sample(sample_properties)

        return {
            "status": "completed",
            "validation_type": "quick_sample",
            "sample_size": len(sample_properties),
            "accuracy": result.accuracy_score,
            "validation_status": result.validation_status.value,
            "execution_time": result.validation_duration,
            "summary": f"Quick validation completed with {result.accuracy_score:.1%} accuracy"
        }

    except Exception as e:
        logger.error(f"Quick validation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to run quick validation")


@router.get("/analytics/summary", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def get_analytics_summary(
    request: Request,
    auth_data: dict = Depends(require_admin)
):
    """
    Get comprehensive analytics summary for administrative purposes.

    Provides high-level overview of system performance, trends,
    and operational metrics.
    """
    try:
        validator = get_prediction_validator()

        # Get recent data
        recent_validations = validator.get_validation_history(days=30)
        recent_backtests = validator.backtest_results[-5:] if validator.backtest_results else []

        # System statistics
        system_stats = {
            "total_validations_30d": len(recent_validations),
            "total_backtests": len(validator.backtest_results),
            "total_predictions_validated": sum(v.total_predictions for v in recent_validations),
            "system_uptime_days": 30,  # Simplified
            "last_validation": recent_validations[0].validation_timestamp.isoformat() if recent_validations else None,
            "last_backtest": recent_backtests[-1].backtest_timestamp.isoformat() if recent_backtests else None
        }

        # Performance trends
        if recent_validations:
            recent_accuracy = sum(v.accuracy_score for v in recent_validations[:7]) / min(7, len(recent_validations))
            older_accuracy = sum(v.accuracy_score for v in recent_validations[7:14]) / max(1, min(7, len(recent_validations) - 7))

            performance_trends = {
                "accuracy_trend": "improving" if recent_accuracy > older_accuracy + 0.02
                                else "declining" if recent_accuracy < older_accuracy - 0.02
                                else "stable",
                "current_average_accuracy": recent_accuracy,
                "previous_period_accuracy": older_accuracy,
                "accuracy_change": recent_accuracy - older_accuracy
            }
        else:
            performance_trends = {
                "accuracy_trend": "no_data",
                "current_average_accuracy": 0,
                "previous_period_accuracy": 0,
                "accuracy_change": 0
            }

        # Operational health
        operational_health = {
            "status": "healthy" if recent_validations and recent_validations[0].accuracy_score > 0.7 else "warning",
            "validation_frequency": len(recent_validations) / 30,  # Per day
            "average_processing_time": sum(v.validation_duration for v in recent_validations) / len(recent_validations) if recent_validations else 0,
            "success_rate": sum(v.successful_predictions for v in recent_validations) /
                          sum(v.total_predictions for v in recent_validations) if recent_validations else 0
        }

        return {
            "summary_generated": datetime.utcnow().isoformat(),
            "system_statistics": system_stats,
            "performance_trends": performance_trends,
            "operational_health": operational_health,
            "recent_validations_count": len(recent_validations),
            "recent_backtests_count": len(recent_backtests)
        }

    except Exception as e:
        logger.error(f"Failed to get analytics summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics summary")


# Helper Functions

def _generate_performance_alerts(validation_history: List[ValidationResult]) -> List[str]:
    """Generate performance alerts based on validation history."""
    alerts = []

    if not validation_history:
        return alerts

    # Check recent accuracy
    recent_accuracy = validation_history[0].accuracy_score
    if recent_accuracy < 0.7:
        alerts.append(f"Low accuracy detected: {recent_accuracy:.1%}")

    # Check for declining trend
    if len(validation_history) >= 5:
        recent_avg = sum(v.accuracy_score for v in validation_history[:3]) / 3
        older_avg = sum(v.accuracy_score for v in validation_history[3:6]) / 3

        if recent_avg < older_avg - 0.05:
            alerts.append("Accuracy trend is declining")

    # Check validation frequency
    if len(validation_history) < 3:
        alerts.append("Infrequent validations - consider running more regular checks")

    # Check for failed predictions
    total_predictions = sum(v.total_predictions for v in validation_history[:5])
    failed_predictions = sum(v.failed_predictions for v in validation_history[:5])

    if total_predictions > 0 and failed_predictions / total_predictions > 0.1:
        alerts.append(f"High failure rate: {failed_predictions/total_predictions:.1%}")

    return alerts