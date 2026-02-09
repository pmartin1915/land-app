"""
Application Assistant API endpoints for Auction Watcher
Provides data organization and workflow assistance for manual government form submission

LEGAL COMPLIANCE NOTE:
All endpoints are designed for data organization assistance only.
No automated form submission or security bypass is performed.
Users must manually review and submit all government applications.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import logging
import json
from datetime import datetime, timedelta, timezone

from ..database.connection import get_db
from ..config import limiter
from ..database.models import UserProfile, PropertyApplication, ApplicationBatch, ApplicationNotification, Property
from ..models.application import (
    UserProfile as UserProfileModel,
    PropertyApplicationData,
    ApplicationFormData,
    ApplicationBatch as ApplicationBatchModel,
    ApplicationWorkflowResponse,
    ROICalculation,
    ApplicationNotification as ApplicationNotificationModel
)
from ..auth import require_property_read, require_property_write

logger = logging.getLogger(__name__)

router = APIRouter()


# User Profile Management
@router.post("/profiles", response_model=Dict[str, Any])
@limiter.limit("10/minute")
def create_user_profile(
    request: Request,
    profile: UserProfileModel,
    auth_data: dict = Depends(require_property_write),
    db: Session = Depends(get_db)
):
    """
    Create a new user profile for application assistance.
    Stores applicant information for form pre-population.
    """
    try:
        # Convert preferred_counties list to JSON string
        preferred_counties_json = json.dumps(profile.preferred_counties) if profile.preferred_counties else None

        db_profile = UserProfile(
            full_name=profile.full_name,
            email=profile.email,
            phone=profile.phone,
            address=profile.address,
            city=profile.city,
            state=profile.state,
            zip_code=profile.zip_code,
            max_investment_amount=profile.max_investment_amount,
            min_acreage=profile.min_acreage,
            max_acreage=profile.max_acreage,
            preferred_counties=preferred_counties_json
        )

        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)

        logger.info(f"Created user profile for {profile.full_name}")

        return {
            "success": True,
            "message": "User profile created successfully",
            "profile_id": db_profile.id,
            "legal_notice": "Profile created for data organization assistance only. User must manually submit all applications."
        }

    except Exception as e:
        logger.error(f"Failed to create user profile: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create user profile")


@router.get("/profiles", response_model=List[Dict[str, Any]])
@limiter.limit("30/minute")
def get_user_profiles(
    request: Request,
    auth_data: dict = Depends(require_property_read),
    db: Session = Depends(get_db)
):
    """Get all user profiles for the authenticated user."""
    try:
        profiles = db.query(UserProfile).filter(UserProfile.is_active == True).all()

        result = []
        for profile in profiles:
            preferred_counties = []
            if profile.preferred_counties:
                try:
                    preferred_counties = json.loads(profile.preferred_counties)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Failed to parse preferred_counties for profile {profile.id}: {e}")
                    preferred_counties = []

            result.append({
                "id": profile.id,
                "full_name": profile.full_name,
                "email": profile.email,
                "phone": profile.phone,
                "address": profile.address,
                "city": profile.city,
                "state": profile.state,
                "zip_code": profile.zip_code,
                "max_investment_amount": profile.max_investment_amount,
                "min_acreage": profile.min_acreage,
                "max_acreage": profile.max_acreage,
                "preferred_counties": preferred_counties,
                "created_at": profile.created_at.isoformat() if profile.created_at else None,
                "updated_at": profile.updated_at.isoformat() if profile.updated_at else None
            })

        return result

    except Exception as e:
        logger.error(f"Failed to get user profiles: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user profiles")


# Property Application Tracking
@router.post("/properties/{property_id}/application", response_model=ApplicationWorkflowResponse)
@limiter.limit("20/minute")
def create_property_application(
    request: Request,
    property_id: str,
    user_profile_id: str = Query(..., description="User profile ID"),
    notes: Optional[str] = Query(None, description="Optional notes about this property"),
    auth_data: dict = Depends(require_property_write),
    db: Session = Depends(get_db)
):
    """
    Add a property to the application queue for data organization assistance.
    Extracts and organizes data for manual form completion.
    """
    try:
        # Verify user profile exists
        user_profile = db.query(UserProfile).filter(UserProfile.id == user_profile_id).first()
        if not user_profile:
            raise HTTPException(status_code=404, detail="User profile not found")

        # Get property data
        property_obj = db.query(Property).filter(Property.id == property_id, Property.is_deleted == False).first()
        if not property_obj:
            raise HTTPException(status_code=404, detail="Property not found")

        # Check if application already exists
        existing_app = db.query(PropertyApplication).filter(
            PropertyApplication.property_id == property_id,
            PropertyApplication.user_profile_id == user_profile_id
        ).first()

        if existing_app:
            return ApplicationWorkflowResponse(
                success=False,
                message="Property already in application queue",
                warnings=["This property is already being tracked for application"],
                legal_notice="Applications must be manually reviewed and submitted by the user."
            )

        # Create property application record
        application = PropertyApplication(
            user_profile_id=user_profile_id,
            property_id=property_id,
            parcel_number=property_obj.parcel_id,
            sale_year=property_obj.year_sold or "Unknown",
            county=property_obj.county or "Unknown",
            description=property_obj.description or "No description available",
            assessed_name=property_obj.owner_name,
            amount=property_obj.amount,
            acreage=property_obj.acreage,
            investment_score=property_obj.investment_score,
            estimated_total_cost=property_obj.estimated_all_in_cost,
            notes=notes
        )

        db.add(application)
        db.commit()
        db.refresh(application)

        logger.info(f"Created application tracking for property {property_id}")

        # Calculate ROI estimate
        roi_estimate = None
        if property_obj.investment_score and property_obj.investment_score > 0:
            # Simple ROI estimate based on investment score
            roi_estimate = min(property_obj.investment_score * 1.5, 100.0)

        return ApplicationWorkflowResponse(
            success=True,
            message=f"Property added to application queue for {user_profile.full_name}",
            data={
                "application_id": application.id,
                "property_id": property_id,
                "estimated_roi": roi_estimate,
                "next_step": "Generate form data for manual submission"
            },
            next_steps=[
                "Review property details and investment analysis",
                "Generate pre-populated form data",
                "Manually submit application to Alabama State Land Commissioner",
                "Monitor for price notification email"
            ],
            legal_notice="Property added to queue for data organization only. User must manually submit application."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create property application: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create property application")


@router.get("/profiles/{profile_id}/applications", response_model=List[Dict[str, Any]])
@limiter.limit("30/minute")
def get_user_applications(
    request: Request,
    profile_id: str,
    status: Optional[str] = Query(None, description="Filter by application status"),
    auth_data: dict = Depends(require_property_read),
    db: Session = Depends(get_db)
):
    """Get all property applications for a user profile."""
    try:
        query = db.query(PropertyApplication).filter(PropertyApplication.user_profile_id == profile_id)

        if status:
            query = query.filter(PropertyApplication.status == status)

        applications = query.order_by(PropertyApplication.created_at.desc()).all()

        result = []
        for app in applications:
            # Get property details
            property_obj = db.query(Property).filter(Property.id == app.property_id).first()

            result.append({
                "id": app.id,
                "property_id": app.property_id,
                "parcel_number": app.parcel_number,
                "county": app.county,
                "amount": app.amount,
                "acreage": app.acreage,
                "investment_score": app.investment_score,
                "estimated_total_cost": app.estimated_total_cost,
                "roi_estimate": app.roi_estimate,
                "status": app.status,
                "notes": app.notes,
                "description": app.description,
                "assessed_name": app.assessed_name,
                "price_request_date": app.price_request_date.isoformat() if app.price_request_date else None,
                "price_received_date": app.price_received_date.isoformat() if app.price_received_date else None,
                "final_price": app.final_price,
                "created_at": app.created_at.isoformat() if app.created_at else None,
                "property_details": property_obj.to_dict() if property_obj else None
            })

        return result

    except Exception as e:
        logger.error(f"Failed to get user applications: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve applications")


# Form Data Generation
@router.get("/applications/{application_id}/form-data", response_model=ApplicationFormData)
@limiter.limit("50/minute")
def generate_form_data(
    request: Request,
    application_id: str,
    auth_data: dict = Depends(require_property_read),
    db: Session = Depends(get_db)
):
    """
    Generate pre-populated form data for manual copy-paste into state application.
    LEGAL COMPLIANCE: Data is for assistance only, not automated submission.
    """
    try:
        # Get application and user profile
        application = db.query(PropertyApplication).filter(PropertyApplication.id == application_id).first()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        user_profile = db.query(UserProfile).filter(UserProfile.id == application.user_profile_id).first()
        if not user_profile:
            raise HTTPException(status_code=404, detail="User profile not found")

        # Generate today's date for application
        today = datetime.now().strftime("%B %d, %Y")

        # Create form data
        form_data = ApplicationFormData(
            application_date=today,
            cs_number=application.cs_number,
            parcel_number=application.parcel_number,
            property_description=application.description,
            assessed_name=application.assessed_name,
            applicant_name=user_profile.full_name,
            email=user_profile.email,
            phone=user_profile.phone,
            address=user_profile.address,
            city=user_profile.city,
            state=user_profile.state,
            zip_code=user_profile.zip_code,
            our_estimated_value=application.estimated_total_cost,
            investment_score=application.investment_score,
            total_estimated_cost=application.estimated_total_cost
        )

        logger.info(f"Generated form data for application {application_id}")

        return form_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate form data: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate form data")


# ROI Calculator
@router.get("/properties/{property_id}/roi", response_model=ROICalculation)
@limiter.limit("100/minute")
def calculate_property_roi(
    request: Request,
    property_id: str,
    auth_data: dict = Depends(require_property_read),
    db: Session = Depends(get_db)
):
    """Calculate ROI and investment analysis for a property."""
    try:
        property_obj = db.query(Property).filter(Property.id == property_id, Property.is_deleted == False).first()
        if not property_obj:
            raise HTTPException(status_code=404, detail="Property not found")

        # Calculate estimated fees (Alabama typical fees)
        base_amount = property_obj.amount
        estimated_fees = base_amount * 0.15  # Rough estimate of additional costs

        # Estimate market value based on our scoring algorithm
        estimated_market_value = None
        roi_percentage = None
        estimated_equity = None

        if property_obj.investment_score and property_obj.investment_score > 0:
            # Conservative market value estimate
            score_multiplier = 1 + (property_obj.investment_score / 100)
            estimated_market_value = base_amount * score_multiplier * 2  # Conservative estimate

            total_cost = base_amount + estimated_fees
            estimated_equity = max(0, estimated_market_value - total_cost)

            if total_cost > 0:
                roi_percentage = (estimated_equity / total_cost) * 100

        # Risk assessment
        risk_score = 50.0  # Default medium risk
        if property_obj.investment_score:
            # Higher investment score = lower risk
            risk_score = max(10, 100 - property_obj.investment_score)

        # Estimate redemption period end (Alabama is 3 years)
        redemption_period_ends = None
        estimated_possession_date = None
        if property_obj.year_sold:
            try:
                sale_year = int(property_obj.year_sold)
                redemption_period_ends = datetime(sale_year + 3, 12, 31)
                estimated_possession_date = redemption_period_ends + timedelta(days=30)
            except (ValueError, TypeError) as e:
                logger.debug(f"Could not parse year_sold '{property_obj.year_sold}' for property {property_id}: {e}")

        roi_calc = ROICalculation(
            property_id=property_id,
            minimum_bid=base_amount,
            estimated_fees=estimated_fees,
            estimated_total_cost=base_amount + estimated_fees,
            estimated_market_value=estimated_market_value,
            estimated_equity=estimated_equity,
            roi_percentage=roi_percentage,
            risk_score=risk_score,
            redemption_period_ends=redemption_period_ends,
            estimated_possession_date=estimated_possession_date,
            confidence_level="Medium" if property_obj.investment_score and property_obj.investment_score > 50 else "Low"
        )

        return roi_calc

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to calculate ROI: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to calculate ROI")


# Application Status Updates
@router.put("/applications/{application_id}/status", response_model=ApplicationWorkflowResponse)
@limiter.limit("30/minute")
def update_application_status(
    request: Request,
    application_id: str,
    status: str = Query(..., description="New application status"),
    final_price: Optional[float] = Query(None, description="Final price if received from state"),
    notes: Optional[str] = Query(None, description="Additional notes"),
    auth_data: dict = Depends(require_property_write),
    db: Session = Depends(get_db)
):
    """Update application status and tracking information."""
    try:
        application = db.query(PropertyApplication).filter(PropertyApplication.id == application_id).first()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        # Update status
        old_status = application.status
        application.status = status

        # Update timestamps based on status changes
        if status == "price_received" and old_status != "price_received":
            application.price_received_date = datetime.now(timezone.utc)
            if final_price:
                application.final_price = final_price

        if notes:
            application.notes = f"{application.notes or ''}\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {notes}"

        db.commit()
        db.refresh(application)

        # Create notification if status changed significantly
        if old_status != status and status in ["price_received", "accepted", "rejected", "completed"]:
            notification = ApplicationNotification(
                user_profile_id=application.user_profile_id,
                property_id=application.property_id,
                notification_type="status_update",
                title=f"Application Status Updated: {status.title()}",
                message=f"Property {application.parcel_number} status changed from {old_status} to {status}",
                action_required=(status == "price_received")
            )
            db.add(notification)
            db.commit()

        logger.info(f"Updated application {application_id} status from {old_status} to {status}")

        return ApplicationWorkflowResponse(
            success=True,
            message=f"Application status updated to {status}",
            data={
                "application_id": application_id,
                "old_status": old_status,
                "new_status": status,
                "final_price": final_price
            },
            next_steps=_get_next_steps_for_status(status),
            legal_notice="Status updated for tracking purposes only. User maintains full control of application process."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update application status: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update application status")


def _get_next_steps_for_status(status: str) -> List[str]:
    """Get recommended next steps based on application status."""
    status_steps = {
        "draft": [
            "Review property details and investment analysis",
            "Generate form data for manual submission",
            "Submit application to Alabama State Land Commissioner"
        ],
        "submitted": [
            "Monitor email for price notification from DoNotReply@LandSales.Alabama.Gov",
            "Check spam/clutter folders for state communications",
            "Wait for state to determine final price"
        ],
        "price_received": [
            "Review final price against investment analysis",
            "Make decision to accept or decline offer",
            "Submit response to state within deadline"
        ],
        "accepted": [
            "Prepare payment for property purchase",
            "Review closing documentation",
            "Plan for 3-year redemption period"
        ],
        "completed": [
            "Property purchase complete",
            "Begin property management planning",
            "Monitor redemption period"
        ]
    }
    return status_steps.get(status, ["Continue monitoring application progress"])