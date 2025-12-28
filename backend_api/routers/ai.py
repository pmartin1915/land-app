"""
AI Investment Triage API Endpoints
Returns prioritized investment recommendations for properties.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import List, Optional
import logging
import time
import uuid as uuid_module
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..models.ai import AISuggestionResponse
from ..database.connection import get_db
from ..database.models import Property
from ..auth import require_property_read

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


def safe_uuid_from_string(s: str) -> UUID:
    """
    Convert a string to UUID, generating a deterministic UUID if not valid format.
    Uses UUID5 with DNS namespace to create consistent IDs from non-UUID strings.
    """
    if not s:
        return uuid_module.uuid4()
    try:
        return UUID(s)
    except (ValueError, AttributeError):
        # Generate deterministic UUID from the string
        return uuid_module.uuid5(uuid_module.NAMESPACE_DNS, s)


def classify_property_tier(prop: Property) -> Optional[tuple]:
    """
    Classify a property into an investment tier.

    Returns tuple of (tier_name, reasons_list) or None if no tier matches.

    Tier Priority (first match wins):
    1. Tier 1: Elite - investment_score >= 85
    2. Tier 2: Waterfront - water_score >= 12
    3. Tier 2: Deep Value - assessed_value_ratio <= 0.4
    """
    reasons = []

    # Get scores with null handling (treat None as 0)
    investment_score = prop.investment_score or 0
    water_score = prop.water_score or 0
    assessed_value_ratio = prop.assessed_value_ratio

    # Tier 1: Elite - Top investment scores
    if investment_score >= 85:
        reasons.append(f"Top 5% investment score ({investment_score:.1f}/100)")
        if water_score >= 10:
            reasons.append("Water features present")
        if assessed_value_ratio and assessed_value_ratio <= 0.5:
            reasons.append(f"Priced at {int(assessed_value_ratio * 100)}% of assessed value")
        if prop.county:
            reasons.append(f"Located in {prop.county} County")
        return ("Tier 1: Elite", reasons)

    # Tier 2: Waterfront - Significant water features
    if water_score >= 12:
        reasons.append(f"Significant water features (score: {water_score:.1f})")
        if investment_score >= 60:
            reasons.append(f"Solid investment score ({investment_score:.1f}/100)")
        if prop.acreage and prop.acreage > 1:
            reasons.append(f"{prop.acreage:.2f} acres")
        return ("Tier 2: Waterfront", reasons)

    # Tier 2: Deep Value - Undervalued properties
    if assessed_value_ratio is not None and assessed_value_ratio <= 0.4:
        reasons.append(f"Deep value: priced at {int(assessed_value_ratio * 100)}% of assessed value")
        if investment_score >= 50:
            reasons.append(f"Reasonable investment score ({investment_score:.1f}/100)")
        if prop.road_access_score and prop.road_access_score > 50:
            reasons.append("Good road access")
        return ("Tier 2: Deep Value", reasons)

    return None


def calculate_confidence(prop: Property, tier: str) -> float:
    """
    Calculate confidence score for a property suggestion.

    Base: investment_score (0-100)
    Modifiers:
        +5 for water_score > 10
        +5 for assessed_value_ratio < 0.4
    Cap: Max 99
    """
    base_score = prop.investment_score or 0

    # Apply modifiers
    if (prop.water_score or 0) > 10:
        base_score += 5

    if prop.assessed_value_ratio is not None and prop.assessed_value_ratio < 0.4:
        base_score += 5

    # Cap at 99 (never 100% confident)
    return min(base_score, 99)


@router.get("/triage", response_model=List[AISuggestionResponse])
@limiter.limit("50/minute")
async def get_triage_queue(
    request: Request,
    limit: int = Query(50, ge=1, le=100, description="Maximum suggestions to return"),
    db: Session = Depends(get_db)
):
    """
    Get AI-generated investment priority triage queue.

    Returns properties classified into investment tiers:
    - Tier 1: Elite - Top investment scores (>= 85)
    - Tier 2: Waterfront - Significant water features (score >= 12)
    - Tier 2: Deep Value - Undervalued properties (ratio <= 0.4)

    Properties are sorted by confidence score (highest first).
    """
    start_time = time.time()

    try:
        # Query top properties by investment_score for analysis
        # Fetch more than we need to allow for filtering
        candidates = (
            db.query(Property)
            .filter(Property.is_deleted == False)
            .filter(Property.investment_score.isnot(None))
            .order_by(Property.investment_score.desc())
            .limit(200)
            .all()
        )

        suggestions = []
        tier_counts = {"Tier 1: Elite": 0, "Tier 2: Waterfront": 0, "Tier 2: Deep Value": 0}

        for prop in candidates:
            result = classify_property_tier(prop)

            if result:
                tier_name, reasons = result
                confidence = calculate_confidence(prop, tier_name)

                # Build reason string
                reason_text = ". ".join(reasons) + "."

                # Convert property ID to UUID safely
                prop_uuid = safe_uuid_from_string(prop.id)

                suggestion = AISuggestionResponse(
                    id=uuid_module.uuid4(),
                    parcel_id=prop_uuid,
                    field="investment_priority",
                    proposed_value=tier_name,
                    confidence=confidence,
                    reason=reason_text,
                    source_ids=[prop_uuid],
                    created_at=datetime.utcnow(),
                    applied_by=None,
                    applied_at=None
                )

                suggestions.append(suggestion)
                tier_counts[tier_name] = tier_counts.get(tier_name, 0) + 1

        # Sort by confidence (highest first) and limit
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        suggestions = suggestions[:limit]

        processing_time = time.time() - start_time

        logger.info(
            f"Triage queue generated in {processing_time:.3f}s - "
            f"Total: {len(suggestions)}, "
            f"Elite: {tier_counts.get('Tier 1: Elite', 0)}, "
            f"Waterfront: {tier_counts.get('Tier 2: Waterfront', 0)}, "
            f"DeepValue: {tier_counts.get('Tier 2: Deep Value', 0)}"
        )

        return suggestions

    except Exception as e:
        logger.error(f"Failed to generate triage queue: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate investment triage queue"
        )


@router.get("/triage/health")
@limiter.limit("100/minute")
async def triage_health(request: Request, db: Session = Depends(get_db)):
    """Health check for AI triage service."""
    try:
        # Quick count of eligible properties
        total_properties = (
            db.query(Property)
            .filter(Property.is_deleted == False)
            .filter(Property.investment_score.isnot(None))
            .count()
        )

        return {
            "status": "healthy",
            "eligible_properties": total_properties,
            "tiers": ["Tier 1: Elite", "Tier 2: Waterfront", "Tier 2: Deep Value"],
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Triage health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Triage service unhealthy")
