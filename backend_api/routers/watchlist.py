"""
Watchlist API endpoints.
Manages user property interactions (watchlist, notes, ratings).
Uses separate overlay table to survive scraper re-runs.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import logging
import math

from ..database.connection import get_db
from ..database.models import PropertyInteraction, Property
from ..auth import get_current_user_or_api_key
from ..config import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class PropertyInteractionUpdate(BaseModel):
    """Request model for updating property interaction."""
    is_watched: Optional[bool] = None
    star_rating: Optional[int] = Field(None, ge=1, le=5)
    user_notes: Optional[str] = None
    dismissed: Optional[bool] = None


class PropertyInteractionResponse(BaseModel):
    """Response model for property interaction."""
    id: str
    device_id: str
    property_id: str
    is_watched: bool
    star_rating: Optional[int]
    user_notes: Optional[str]
    dismissed: bool
    created_at: Optional[str]
    updated_at: Optional[str]


class WatchlistPropertyResponse(BaseModel):
    """Response model for watchlist item with property data."""
    interaction: dict
    property: dict


class WatchlistResponse(BaseModel):
    """Paginated watchlist response."""
    items: List[WatchlistPropertyResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


def get_device_id_from_auth(auth_data: dict) -> str:
    """Extract user identifier from auth data for DB queries."""
    return auth_data.get("user_id", "unknown")


@router.get("/", response_model=WatchlistResponse)
@limiter.limit("60/minute")
def get_watchlist(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    include_dismissed: bool = Query(False, description="Include dismissed properties"),
    min_rating: Optional[int] = Query(None, ge=1, le=5, description="Minimum star rating"),
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Get user's watchlist with property details.
    Only returns properties that are watched (is_watched=True).
    """
    try:
        device_id = get_device_id_from_auth(auth_data)

        # Build query
        query = db.query(PropertyInteraction, Property).join(
            Property, PropertyInteraction.property_id == Property.id
        ).filter(
            PropertyInteraction.device_id == device_id,
            PropertyInteraction.is_watched == True,
            Property.is_deleted == False
        )

        if not include_dismissed:
            query = query.filter(PropertyInteraction.dismissed == False)

        if min_rating:
            query = query.filter(PropertyInteraction.star_rating >= min_rating)

        # Get total count
        total_count = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        results = query.order_by(
            PropertyInteraction.updated_at.desc()
        ).offset(offset).limit(page_size).all()

        # Format response
        items = []
        for interaction, prop in results:
            items.append(WatchlistPropertyResponse(
                interaction=interaction.to_dict(),
                property=prop.to_dict()
            ))

        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

        return WatchlistResponse(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Failed to get watchlist: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve watchlist")


@router.get("/property/{property_id}", response_model=PropertyInteractionResponse)
@limiter.limit("120/minute")
def get_property_interaction(
    request: Request,
    property_id: str,
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Get interaction status for a specific property.
    Returns 404 if no interaction exists.
    """
    try:
        device_id = get_device_id_from_auth(auth_data)

        interaction = db.query(PropertyInteraction).filter(
            PropertyInteraction.device_id == device_id,
            PropertyInteraction.property_id == property_id
        ).first()

        if not interaction:
            raise HTTPException(status_code=404, detail="No interaction found for this property")

        return interaction.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get property interaction: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve interaction")


@router.post("/property/{property_id}/watch")
@limiter.limit("60/minute")
def toggle_watch(
    request: Request,
    property_id: str,
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Toggle watch status for a property.
    Creates interaction if it doesn't exist.
    """
    try:
        device_id = get_device_id_from_auth(auth_data)

        # Verify property exists
        prop = db.query(Property).filter(Property.id == property_id).first()
        if not prop:
            raise HTTPException(status_code=404, detail="Property not found")

        # Find or create interaction
        interaction = db.query(PropertyInteraction).filter(
            PropertyInteraction.device_id == device_id,
            PropertyInteraction.property_id == property_id
        ).first()

        if interaction:
            # Toggle watch status
            interaction.is_watched = not interaction.is_watched
        else:
            # Create new interaction with watched=True
            interaction = PropertyInteraction(
                device_id=device_id,
                property_id=property_id,
                is_watched=True
            )
            db.add(interaction)

        db.commit()
        db.refresh(interaction)

        logger.info(f"Toggled watch for property {property_id}: {interaction.is_watched}")

        return {
            "property_id": property_id,
            "is_watched": interaction.is_watched,
            "message": "Added to watchlist" if interaction.is_watched else "Removed from watchlist"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle watch: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update watchlist")


@router.put("/property/{property_id}", response_model=PropertyInteractionResponse)
@limiter.limit("60/minute")
def update_property_interaction(
    request: Request,
    property_id: str,
    updates: PropertyInteractionUpdate,
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Update interaction for a property (notes, rating, etc.).
    Creates interaction if it doesn't exist.
    """
    try:
        device_id = get_device_id_from_auth(auth_data)

        # Verify property exists
        prop = db.query(Property).filter(Property.id == property_id).first()
        if not prop:
            raise HTTPException(status_code=404, detail="Property not found")

        # Find or create interaction
        interaction = db.query(PropertyInteraction).filter(
            PropertyInteraction.device_id == device_id,
            PropertyInteraction.property_id == property_id
        ).first()

        if not interaction:
            interaction = PropertyInteraction(
                device_id=device_id,
                property_id=property_id
            )
            db.add(interaction)

        # Update fields
        if updates.is_watched is not None:
            interaction.is_watched = updates.is_watched
        if updates.star_rating is not None:
            interaction.star_rating = updates.star_rating
        if updates.user_notes is not None:
            interaction.user_notes = updates.user_notes
        if updates.dismissed is not None:
            interaction.dismissed = updates.dismissed

        db.commit()
        db.refresh(interaction)

        logger.info(f"Updated interaction for property {property_id}")

        return interaction.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update interaction: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update interaction")


@router.delete("/property/{property_id}")
@limiter.limit("30/minute")
def delete_property_interaction(
    request: Request,
    property_id: str,
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Delete interaction for a property (remove from watchlist and clear notes).
    """
    try:
        device_id = get_device_id_from_auth(auth_data)

        interaction = db.query(PropertyInteraction).filter(
            PropertyInteraction.device_id == device_id,
            PropertyInteraction.property_id == property_id
        ).first()

        if not interaction:
            raise HTTPException(status_code=404, detail="No interaction found")

        db.delete(interaction)
        db.commit()

        logger.info(f"Deleted interaction for property {property_id}")

        return {"message": "Interaction deleted", "property_id": property_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete interaction: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete interaction")


@router.get("/stats")
@limiter.limit("60/minute")
def get_watchlist_stats(
    request: Request,
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Get watchlist statistics for the user.
    """
    try:
        device_id = get_device_id_from_auth(auth_data)

        # Count watched properties
        watched_count = db.query(PropertyInteraction).filter(
            PropertyInteraction.device_id == device_id,
            PropertyInteraction.is_watched == True,
            PropertyInteraction.dismissed == False
        ).count()

        # Count rated properties
        rated_count = db.query(PropertyInteraction).filter(
            PropertyInteraction.device_id == device_id,
            PropertyInteraction.star_rating.isnot(None)
        ).count()

        # Count dismissed
        dismissed_count = db.query(PropertyInteraction).filter(
            PropertyInteraction.device_id == device_id,
            PropertyInteraction.dismissed == True
        ).count()

        # Count with notes
        noted_count = db.query(PropertyInteraction).filter(
            PropertyInteraction.device_id == device_id,
            PropertyInteraction.user_notes.isnot(None),
            PropertyInteraction.user_notes != ""
        ).count()

        return {
            "watched": watched_count,
            "rated": rated_count,
            "dismissed": dismissed_count,
            "with_notes": noted_count,
            "total_interactions": watched_count + dismissed_count
        }

    except Exception as e:
        logger.error(f"Failed to get watchlist stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve stats")


@router.get("/bulk-status")
@limiter.limit("30/minute")
def get_bulk_watch_status(
    request: Request,
    property_ids: str = Query(..., description="Comma-separated property IDs"),
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Get watch status for multiple properties at once.
    Useful for rendering star icons in property lists.
    """
    try:
        device_id = get_device_id_from_auth(auth_data)

        # Parse property IDs
        ids = [id.strip() for id in property_ids.split(",") if id.strip()]

        if len(ids) > 100:
            raise HTTPException(status_code=400, detail="Maximum 100 property IDs per request")

        # Get all interactions for these properties
        interactions = db.query(PropertyInteraction).filter(
            PropertyInteraction.device_id == device_id,
            PropertyInteraction.property_id.in_(ids)
        ).all()

        # Build response map
        status_map = {}
        for interaction in interactions:
            status_map[interaction.property_id] = {
                "is_watched": interaction.is_watched,
                "star_rating": interaction.star_rating,
                "dismissed": interaction.dismissed,
                "has_notes": bool(interaction.user_notes)
            }

        # Fill in missing properties (no interaction = not watched)
        for id in ids:
            if id not in status_map:
                status_map[id] = {
                    "is_watched": False,
                    "star_rating": None,
                    "dismissed": False,
                    "has_notes": False
                }

        return {"status": status_map}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get bulk status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve status")


# =============================================================================
# First Deal Tracking Endpoints (My First Deal feature)
# =============================================================================

# Valid pipeline stages for first deal tracking
FIRST_DEAL_STAGES = ["research", "bid", "won", "quiet_title", "sold", "holding"]


class FirstDealStageUpdate(BaseModel):
    """Request model for updating first deal pipeline stage."""
    stage: str = Field(..., pattern="^(research|bid|won|quiet_title|sold|holding)$")


class FirstDealResponse(BaseModel):
    """Response model for first deal with property data."""
    property: Optional[dict] = None
    interaction: Optional[dict] = None
    stage: Optional[str] = None
    has_first_deal: bool


@router.get("/first-deal", response_model=FirstDealResponse)
@limiter.limit("60/minute")
def get_first_deal(
    request: Request,
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Get the user's current first deal property (if any).
    Returns the property marked as is_first_deal=True.
    """
    try:
        device_id = get_device_id_from_auth(auth_data)

        # Find the first deal interaction
        result = db.query(PropertyInteraction, Property).join(
            Property, PropertyInteraction.property_id == Property.id
        ).filter(
            PropertyInteraction.device_id == device_id,
            PropertyInteraction.is_first_deal == True,
            Property.is_deleted == False
        ).first()

        if not result:
            return FirstDealResponse(
                property=None,
                interaction=None,
                stage=None,
                has_first_deal=False
            )

        interaction, prop = result
        return FirstDealResponse(
            property=prop.to_dict(),
            interaction=interaction.to_dict(),
            stage=interaction.first_deal_stage,
            has_first_deal=True
        )

    except Exception as e:
        logger.error(f"Failed to get first deal: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve first deal")


@router.post("/property/{property_id}/set-first-deal")
@limiter.limit("30/minute")
def set_first_deal(
    request: Request,
    property_id: str,
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Set a property as the user's first deal.
    Only one property can be the first deal at a time.
    Automatically clears any previous first deal assignment.
    """
    try:
        device_id = get_device_id_from_auth(auth_data)

        # Verify property exists
        prop = db.query(Property).filter(Property.id == property_id).first()
        if not prop:
            raise HTTPException(status_code=404, detail="Property not found")

        # Clear any existing first deal for this device
        db.query(PropertyInteraction).filter(
            PropertyInteraction.device_id == device_id,
            PropertyInteraction.is_first_deal == True
        ).update({
            "is_first_deal": False,
            "first_deal_stage": None,
            "first_deal_assigned_at": None,
            "first_deal_updated_at": None
        })

        # Find or create interaction for this property
        interaction = db.query(PropertyInteraction).filter(
            PropertyInteraction.device_id == device_id,
            PropertyInteraction.property_id == property_id
        ).first()

        now = datetime.now(timezone.utc)

        if interaction:
            interaction.is_first_deal = True
            interaction.first_deal_stage = "research"
            interaction.first_deal_assigned_at = now
            interaction.first_deal_updated_at = now
            # Also add to watchlist if not already
            interaction.is_watched = True
        else:
            interaction = PropertyInteraction(
                device_id=device_id,
                property_id=property_id,
                is_watched=True,
                is_first_deal=True,
                first_deal_stage="research",
                first_deal_assigned_at=now,
                first_deal_updated_at=now
            )
            db.add(interaction)

        db.commit()
        db.refresh(interaction)

        logger.info(f"Set first deal for property {property_id}, device {device_id}")

        return {
            "property_id": property_id,
            "is_first_deal": True,
            "stage": interaction.first_deal_stage,
            "message": "Property set as your first deal"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set first deal: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to set first deal")


@router.put("/first-deal/stage")
@limiter.limit("60/minute")
def update_first_deal_stage(
    request: Request,
    update: FirstDealStageUpdate,
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Update the pipeline stage for the user's first deal.
    Valid stages: research, bid, won, quiet_title, sold, holding
    """
    try:
        device_id = get_device_id_from_auth(auth_data)

        # Find the first deal interaction
        interaction = db.query(PropertyInteraction).filter(
            PropertyInteraction.device_id == device_id,
            PropertyInteraction.is_first_deal == True
        ).first()

        if not interaction:
            raise HTTPException(status_code=404, detail="No first deal assigned")

        # Validate stage
        if update.stage not in FIRST_DEAL_STAGES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stage. Must be one of: {', '.join(FIRST_DEAL_STAGES)}"
            )

        # Update stage
        interaction.first_deal_stage = update.stage
        interaction.first_deal_updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(interaction)

        logger.info(f"Updated first deal stage to {update.stage} for device {device_id}")

        return {
            "property_id": interaction.property_id,
            "stage": interaction.first_deal_stage,
            "updated_at": interaction.first_deal_updated_at.isoformat(),
            "message": f"Stage updated to {update.stage}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update first deal stage: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update stage")


@router.delete("/first-deal")
@limiter.limit("30/minute")
def remove_first_deal(
    request: Request,
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Remove the first deal assignment.
    The property remains on the watchlist but is no longer tracked as first deal.
    """
    try:
        device_id = get_device_id_from_auth(auth_data)

        # Find and update the first deal interaction
        interaction = db.query(PropertyInteraction).filter(
            PropertyInteraction.device_id == device_id,
            PropertyInteraction.is_first_deal == True
        ).first()

        if not interaction:
            raise HTTPException(status_code=404, detail="No first deal assigned")

        property_id = interaction.property_id

        # Clear first deal fields but keep other interaction data
        interaction.is_first_deal = False
        interaction.first_deal_stage = None
        interaction.first_deal_assigned_at = None
        interaction.first_deal_updated_at = None

        db.commit()

        logger.info(f"Removed first deal for device {device_id}")

        return {
            "property_id": property_id,
            "message": "First deal assignment removed"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove first deal: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to remove first deal")
