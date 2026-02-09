"""
User settings and preferences API endpoints.
Manages investment budget, state preferences, and default filters.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field
import logging
import json

from ..database.connection import get_db
from ..database.models import UserPreference
from ..auth import get_current_user_or_api_key
from ..config import limiter

# Import state configs for budget recommendations
import sys
sys.path.insert(0, 'c:/auction')
from config.states import STATE_CONFIGS, get_active_states

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models for request/response
class UserPreferenceUpdate(BaseModel):
    """Request model for updating user preferences."""
    investment_budget: Optional[float] = Field(None, ge=0, description="Investment capital in USD")
    excluded_states: Optional[List[str]] = Field(None, description="State codes to exclude")
    preferred_states: Optional[List[str]] = Field(None, description="Preferred state codes")
    default_filters: Optional[dict] = Field(None, description="Default filter presets")
    max_property_price: Optional[float] = Field(None, ge=0, description="Max price per property")
    notifications_enabled: Optional[bool] = Field(None, description="Enable notifications")


class UserPreferenceResponse(BaseModel):
    """Response model for user preferences."""
    id: str
    device_id: str
    investment_budget: Optional[float]
    excluded_states: List[str]
    preferred_states: List[str]
    default_filters: dict
    max_property_price: Optional[float]
    notifications_enabled: bool
    created_at: Optional[str]
    updated_at: Optional[str]


class StateRecommendation(BaseModel):
    """State recommendation based on budget."""
    state_code: str
    state_name: str
    sale_type: str
    recommended: bool
    reason: str
    time_to_ownership_days: int
    quiet_title_cost: float
    min_budget_recommended: float


class BudgetRecommendationsResponse(BaseModel):
    """Response model for budget-based state recommendations."""
    budget: float
    recommendations: List[StateRecommendation]
    summary: str


def get_device_id_from_auth(auth_data: dict) -> str:
    """Extract user identifier from auth data for DB queries."""
    return auth_data.get("user_id", "unknown")


@router.get("/", response_model=UserPreferenceResponse)
@limiter.limit("60/minute")
def get_settings(
    request: Request,
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Get current user preferences.
    Creates default preferences if none exist for this device.
    """
    try:
        device_id = get_device_id_from_auth(auth_data)

        # Find or create preferences for this device
        prefs = db.query(UserPreference).filter(
            UserPreference.device_id == device_id
        ).first()

        if not prefs:
            # Create default preferences
            prefs = UserPreference(
                device_id=device_id,
                investment_budget=10000.0,
                excluded_states=json.dumps([]),
                preferred_states=json.dumps(["AR"]),  # Default to AR (beginner friendly)
                default_filters=json.dumps({}),
                max_property_price=None,
                notifications_enabled=True
            )
            db.add(prefs)
            db.commit()
            db.refresh(prefs)
            logger.info(f"Created default preferences for device {device_id}")

        return prefs.to_dict()

    except Exception as e:
        logger.error(f"Failed to get settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve settings")


@router.put("/", response_model=UserPreferenceResponse)
@limiter.limit("30/minute")
def update_settings(
    request: Request,
    updates: UserPreferenceUpdate,
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Update user preferences.
    Creates preferences if none exist.
    """
    try:
        device_id = get_device_id_from_auth(auth_data)

        # Find or create preferences
        prefs = db.query(UserPreference).filter(
            UserPreference.device_id == device_id
        ).first()

        if not prefs:
            prefs = UserPreference(device_id=device_id)
            db.add(prefs)

        # Update fields that were provided
        if updates.investment_budget is not None:
            prefs.investment_budget = updates.investment_budget
            # Auto-calculate max property price if not explicitly set
            if updates.max_property_price is None and prefs.max_property_price is None:
                # Default max property = 50% of budget (leave room for quiet title + fees)
                prefs.max_property_price = updates.investment_budget * 0.5

        if updates.excluded_states is not None:
            prefs.excluded_states = json.dumps(updates.excluded_states)

        if updates.preferred_states is not None:
            prefs.preferred_states = json.dumps(updates.preferred_states)

        if updates.default_filters is not None:
            prefs.default_filters = json.dumps(updates.default_filters)

        if updates.max_property_price is not None:
            prefs.max_property_price = updates.max_property_price

        if updates.notifications_enabled is not None:
            prefs.notifications_enabled = updates.notifications_enabled

        db.commit()
        db.refresh(prefs)

        logger.info(f"Updated preferences for device {device_id}")
        return prefs.to_dict()

    except Exception as e:
        logger.error(f"Failed to update settings: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update settings")


@router.get("/budget-recommendations", response_model=BudgetRecommendationsResponse)
@limiter.limit("60/minute")
def get_budget_recommendations(
    request: Request,
    budget: Optional[float] = None,
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Get state recommendations based on investment budget.
    Uses state configs to determine which states are viable for the given budget.

    Budget thresholds:
    - < $10k: Only tax deed states with short redemption (AR recommended)
    - $10k-$25k: Tax deed + redeemable deed states
    - > $25k: All states including tax lien (AL)
    """
    try:
        # If no budget provided, get from user preferences
        if budget is None:
            device_id = get_device_id_from_auth(auth_data)
            prefs = db.query(UserPreference).filter(
                UserPreference.device_id == device_id
            ).first()
            budget = prefs.investment_budget if prefs else 10000.0

        recommendations = []

        for state_code, config in STATE_CONFIGS.items():
            # Calculate minimum recommended budget for this state
            # Formula: quiet_title_cost + minimum viable property + buffer
            min_property_cost = 500  # Assume minimum viable property
            buffer_multiplier = 1.5  # 50% buffer for fees/contingencies
            min_budget = (config.quiet_title_cost_estimate + min_property_cost) * buffer_multiplier

            # Adjust for time value of money for long redemption periods
            if config.time_to_ownership_days > 365:
                # Long redemption = need more capital buffer
                years_to_ownership = config.time_to_ownership_days / 365
                min_budget *= (1 + (years_to_ownership * 0.2))  # 20% per year opportunity cost

            # Determine if recommended for this budget
            recommended = budget >= min_budget and config.is_active

            # Generate reason
            if not config.is_active:
                reason = "Scraper not yet implemented"
            elif budget < min_budget:
                reason = f"Budget too low. Minimum ${min_budget:,.0f} recommended (quiet title ${config.quiet_title_cost_estimate:,.0f} + {config.time_to_ownership_days} days to ownership)"
            elif config.time_to_ownership_days > 1000 and budget < 25000:
                reason = f"Long redemption period ({config.time_to_ownership_days} days) ties up capital. Consider with budget > $25k"
                recommended = False
            elif config.recommended_for_beginners:
                reason = f"Recommended for beginners. {config.sale_type.replace('_', ' ').title()} with {config.redemption_period_days}-day redemption"
            else:
                reason = f"{config.sale_type.replace('_', ' ').title()} - {config.time_to_ownership_days} days to clear title"

            recommendations.append(StateRecommendation(
                state_code=state_code,
                state_name=config.state_name,
                sale_type=config.sale_type,
                recommended=recommended,
                reason=reason,
                time_to_ownership_days=config.time_to_ownership_days,
                quiet_title_cost=config.quiet_title_cost_estimate,
                min_budget_recommended=min_budget
            ))

        # Sort: recommended first, then by min budget
        recommendations.sort(key=lambda x: (not x.recommended, x.min_budget_recommended))

        # Generate summary
        recommended_states = [r.state_code for r in recommendations if r.recommended]
        if not recommended_states:
            summary = f"With ${budget:,.0f} budget, no states are currently recommended. Consider increasing budget to $10,000+."
        elif len(recommended_states) == 1:
            summary = f"With ${budget:,.0f} budget, focus on {recommended_states[0]} for best ROI."
        else:
            summary = f"With ${budget:,.0f} budget, {', '.join(recommended_states[:-1])} and {recommended_states[-1]} are viable options."

        return BudgetRecommendationsResponse(
            budget=budget,
            recommendations=recommendations,
            summary=summary
        )

    except Exception as e:
        logger.error(f"Failed to get budget recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")


@router.delete("/")
@limiter.limit("10/minute")
def reset_settings(
    request: Request,
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Reset user preferences to defaults.
    """
    try:
        device_id = get_device_id_from_auth(auth_data)

        prefs = db.query(UserPreference).filter(
            UserPreference.device_id == device_id
        ).first()

        if prefs:
            db.delete(prefs)
            db.commit()
            logger.info(f"Reset preferences for device {device_id}")

        return {"message": "Settings reset to defaults"}

    except Exception as e:
        logger.error(f"Failed to reset settings: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to reset settings")
