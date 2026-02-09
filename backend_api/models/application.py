"""
Pydantic models for Property Application Assistant
Legal compliance focused models for helping users organize data for manual government form submission
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import sys
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.validation import PropertyValidator


class ApplicationStatus(str, Enum):
    """Application status enumeration."""
    DRAFT = "draft"
    READY = "ready"
    SUBMITTED = "submitted"
    PRICE_RECEIVED = "price_received"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"


class UserProfile(BaseModel):
    """User profile for application assistance - stores applicant information."""
    id: Optional[str] = Field(None, description="Unique profile identifier")
    full_name: str = Field(..., description="Full legal name for applications", min_length=1)
    email: str = Field(..., description="Email address for notifications")
    phone: str = Field(..., description="Phone number")
    address: str = Field(..., description="Street address")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State")
    zip_code: str = Field(..., description="ZIP code")

    # Preferences
    max_investment_amount: Optional[float] = Field(None, description="Maximum willing to invest", ge=0)
    preferred_counties: List[str] = Field(default=[], description="Preferred counties")
    min_acreage: Optional[float] = Field(None, description="Minimum desired acreage", ge=0)
    max_acreage: Optional[float] = Field(None, description="Maximum desired acreage", ge=0)

    # Metadata
    created_at: Optional[datetime] = Field(None, description="Profile creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    is_active: bool = Field(True, description="Profile active status")

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        if '@' not in v or '.' not in v:
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator('state')
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Validate state is a supported state."""
        supported = ['AL', 'AR', 'TX', 'FL', 'ALABAMA', 'ARKANSAS', 'TEXAS', 'FLORIDA']
        if v.upper() not in supported:
            raise ValueError(f"Unsupported state: {v}. Supported: AL, AR, TX, FL")
        return v.upper()

    @field_validator('zip_code')
    @classmethod
    def validate_zip_code(cls, v: str) -> str:
        """Validate ZIP code format."""
        if not v.isdigit() or len(v) not in [5, 9]:
            raise ValueError("ZIP code must be 5 or 9 digits")
        return v


class PropertyApplicationData(BaseModel):
    """Organized data for property application form assistance."""
    property_id: str = Field(..., description="Property ID from our database")
    cs_number: Optional[str] = Field(None, description="CS Number from state records")
    parcel_number: str = Field(..., description="Official parcel number")
    sale_year: str = Field(..., description="Tax sale year")
    county: str = Field(..., description="County name")

    # Property details
    description: str = Field(..., description="Legal property description")
    assessed_name: Optional[str] = Field(None, description="Name property was assessed in")
    amount: float = Field(..., description="Minimum bid amount", gt=0)
    acreage: Optional[float] = Field(None, description="Property acreage", ge=0)

    # Investment analysis
    investment_score: Optional[float] = Field(None, description="Our calculated investment score")
    estimated_total_cost: Optional[float] = Field(None, description="Estimated all-in cost")
    roi_estimate: Optional[float] = Field(None, description="Estimated ROI percentage")

    # Application status
    status: ApplicationStatus = Field(default=ApplicationStatus.DRAFT, description="Application status")
    notes: Optional[str] = Field(None, description="User notes about this property")

    # Timestamps
    created_at: Optional[datetime] = Field(None, description="When added to application queue")
    price_request_date: Optional[datetime] = Field(None, description="When price was requested")
    price_received_date: Optional[datetime] = Field(None, description="When price notification received")
    final_price: Optional[float] = Field(None, description="Final price from state", ge=0)


class ApplicationFormData(BaseModel):
    """Pre-populated form data for copy-paste into state application."""
    # State form fields
    application_date: str = Field(..., description="Today's date for application")
    cs_number: Optional[str] = Field(None, description="CS Number")
    parcel_number: str = Field(..., description="Parcel number")
    property_description: str = Field(..., description="Legal description")
    assessed_name: Optional[str] = Field(None, description="Previous assessed name")

    # Applicant information (from user profile)
    applicant_name: str = Field(..., description="Applicant's full legal name")
    email: str = Field(..., description="Email for price notifications")
    phone: str = Field(..., description="Phone number")
    address: str = Field(..., description="Street address")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State")
    zip_code: str = Field(..., description="ZIP code")

    # Investment analysis for reference
    our_estimated_value: Optional[float] = Field(None, description="Our value estimate")
    investment_score: Optional[float] = Field(None, description="Our investment score")
    total_estimated_cost: Optional[float] = Field(None, description="Estimated total cost")

    # Legal disclaimer
    legal_notice: str = Field(
        default="IMPORTANT: This data is for form assistance only. User must manually review, verify, and submit all applications. No automated submission is performed.",
        description="Legal compliance notice"
    )


class ApplicationBatch(BaseModel):
    """Batch of applications for processing efficiency."""
    id: Optional[str] = Field(None, description="Batch identifier")
    user_profile_id: str = Field(..., description="Associated user profile")
    property_applications: List[PropertyApplicationData] = Field(..., description="Properties in this batch")

    # Batch metadata
    batch_name: Optional[str] = Field(None, description="User-defined batch name")
    total_estimated_investment: Optional[float] = Field(None, description="Total estimated investment", ge=0)
    created_at: Optional[datetime] = Field(None, description="Batch creation time")
    status: ApplicationStatus = Field(default=ApplicationStatus.DRAFT, description="Overall batch status")

    # Processing tracking
    forms_generated: int = Field(default=0, description="Number of forms generated")
    applications_submitted: int = Field(default=0, description="Number manually submitted by user")
    prices_received: int = Field(default=0, description="Number of price notifications received")


class ROICalculation(BaseModel):
    """ROI and investment analysis for property applications."""
    property_id: str = Field(..., description="Property identifier")

    # Cost analysis
    minimum_bid: float = Field(..., description="Minimum bid amount", gt=0)
    estimated_fees: float = Field(..., description="Estimated additional fees", ge=0)
    estimated_total_cost: float = Field(..., description="Total estimated cost", gt=0)

    # Value analysis
    estimated_market_value: Optional[float] = Field(None, description="Estimated market value", ge=0)
    comparable_sales: List[Dict[str, Any]] = Field(default=[], description="Comparable sales data")

    # ROI calculations
    estimated_equity: Optional[float] = Field(None, description="Estimated immediate equity")
    roi_percentage: Optional[float] = Field(None, description="Estimated ROI percentage")
    risk_score: Optional[float] = Field(None, description="Risk assessment score", ge=0, le=100)

    # Investment timeline
    redemption_period_ends: Optional[datetime] = Field(None, description="When redemption period ends")
    estimated_possession_date: Optional[datetime] = Field(None, description="Estimated possession date")

    # Analysis metadata
    calculation_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When calculation was performed")
    confidence_level: Optional[str] = Field(None, description="Confidence level in estimates")


class ApplicationNotification(BaseModel):
    """Notification tracking for application process."""
    id: Optional[str] = Field(None, description="Notification ID")
    user_profile_id: str = Field(..., description="User profile ID")
    property_id: str = Field(..., description="Property ID")

    # Notification details
    notification_type: str = Field(..., description="Type of notification")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")

    # State communication tracking
    state_email_expected: bool = Field(default=False, description="Expecting email from DoNotReply@LandSales.Alabama.Gov")
    state_email_received: bool = Field(default=False, description="State email received")
    price_amount: Optional[float] = Field(None, description="Price from state notification", ge=0)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Notification creation time")
    read_at: Optional[datetime] = Field(None, description="When user read notification")
    action_required: bool = Field(default=False, description="User action required")
    action_deadline: Optional[datetime] = Field(None, description="Deadline for action")


class ApplicationWorkflowResponse(BaseModel):
    """Response model for application workflow operations."""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation result message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")

    # Workflow tracking
    next_steps: List[str] = Field(default=[], description="Recommended next steps")
    warnings: List[str] = Field(default=[], description="Important warnings or notices")

    # Legal compliance
    legal_notice: str = Field(
        default="All applications must be manually reviewed and submitted by the user. This system provides data organization assistance only.",
        description="Legal compliance reminder"
    )