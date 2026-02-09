"""
Portfolio Analytics API endpoints.
Provides aggregate analysis of user's watched properties.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import logging

from ..database.connection import get_db
from ..auth import get_current_user_or_api_key
from ..config import limiter
from ..services.portfolio_service import PortfolioService
from ..models.portfolio import (
    PortfolioSummaryResponse,
    GeographicBreakdownResponse,
    ScoreDistributionResponse,
    RiskAnalysisResponse,
    PerformanceTrackingResponse,
    PortfolioAnalyticsExport
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_device_id_from_auth(auth_data: dict) -> str:
    """Extract user identifier from auth data for DB queries."""
    return auth_data.get("user_id", "unknown")


def get_portfolio_service(
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
) -> PortfolioService:
    """Dependency to get PortfolioService instance scoped to user."""
    device_id = get_device_id_from_auth(auth_data)
    return PortfolioService(db, device_id)


@router.get("/summary", response_model=PortfolioSummaryResponse)
@limiter.limit("60/minute")
def get_portfolio_summary(
    request: Request,
    portfolio_service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Get portfolio summary with aggregate metrics.

    Returns:
    - Total count, value, and acreage of watched properties
    - Average scores (investment, buy-hold, wholesale)
    - Capital utilization against user's budget
    - Water feature statistics
    """
    try:
        return portfolio_service.get_summary()
    except Exception as e:
        logger.error(f"Failed to get portfolio summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve portfolio summary")


@router.get("/geographic", response_model=GeographicBreakdownResponse)
@limiter.limit("60/minute")
def get_geographic_breakdown(
    request: Request,
    portfolio_service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Get geographic distribution of portfolio.

    Returns:
    - Properties per state with averages
    - Properties per county within each state
    - Concentration metrics
    """
    try:
        return portfolio_service.get_geographic_breakdown()
    except Exception as e:
        logger.error(f"Failed to get geographic breakdown: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve geographic breakdown")


@router.get("/scores", response_model=ScoreDistributionResponse)
@limiter.limit("60/minute")
def get_score_distribution(
    request: Request,
    portfolio_service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Get investment quality breakdown.

    Returns:
    - Score distribution buckets (0-20, 20-40, etc.)
    - Top performers (score > 80)
    - Underperformers (score < 40)
    - Statistical measures (median, std deviation)
    """
    try:
        return portfolio_service.get_score_distribution()
    except Exception as e:
        logger.error(f"Failed to get score distribution: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve score distribution")


@router.get("/risk", response_model=RiskAnalysisResponse)
@limiter.limit("30/minute")
def get_risk_analysis(
    request: Request,
    portfolio_service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Get portfolio risk analysis.

    Returns:
    - Concentration risk (state/county percentages)
    - Time-to-ownership exposure
    - Delta region exposure (AR economic distress)
    - Market reject exposure (stale delinquency)
    - Overall risk level with flags
    """
    try:
        return portfolio_service.get_risk_analysis()
    except Exception as e:
        logger.error(f"Failed to get risk analysis: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve risk analysis")


@router.get("/performance", response_model=PerformanceTrackingResponse)
@limiter.limit("60/minute")
def get_performance_tracking(
    request: Request,
    portfolio_service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Get performance and activity tracking.

    Returns:
    - Recent additions (7/30 days)
    - Star rating breakdown
    - First deal pipeline status
    - Activity timeline by week
    """
    try:
        return portfolio_service.get_performance_tracking()
    except Exception as e:
        logger.error(f"Failed to get performance tracking: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance tracking")


@router.get("/export", response_model=PortfolioAnalyticsExport)
@limiter.limit("10/minute")
def export_portfolio_analytics(
    request: Request,
    portfolio_service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Export complete portfolio analytics.

    Returns all analytics in a single response:
    - Summary
    - Geographic breakdown
    - Score distribution
    - Risk analysis
    - Performance tracking
    """
    try:
        return portfolio_service.get_full_export()
    except Exception as e:
        logger.error(f"Failed to export portfolio analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to export portfolio analytics")
