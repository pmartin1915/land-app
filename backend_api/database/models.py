"""
SQLAlchemy database models for Alabama Auction Watcher API
Models exactly match iOS Core Data schema for perfect compatibility
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Text, Boolean, Date
from sqlalchemy.sql import func
from .connection import Base
import uuid

class Property(Base):
    """
    Property model matching iOS Core Data Property entity exactly.
    All field names and types must remain compatible with iOS Swift implementation.
    """
    __tablename__ = "properties"

    # Primary key - using UUID for cross-platform compatibility
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Core property data matching iOS Core Data schema
    parcel_id = Column(String, nullable=False, index=True, comment="Unique parcel identifier")
    amount = Column(Float, nullable=False, comment="Bid/sale amount in USD")
    acreage = Column(Float, nullable=True, comment="Property acreage")
    price_per_acre = Column(Float, nullable=True, comment="Calculated: amount / acreage")

    # Acreage data lineage (for tracking data quality)
    acreage_source = Column(String(20), nullable=True, comment="Source: api, parsed_explicit, parsed_plss, parsed_dimensions")
    acreage_confidence = Column(String(10), nullable=True, comment="Confidence: high, medium, low")
    acreage_raw_text = Column(String(200), nullable=True, comment="Original text that was parsed for acreage")

    # Calculated algorithm fields - MUST use exact Python algorithms
    water_score = Column(Float, default=0.0, comment="Water feature score (0.0-15.0+)")
    investment_score = Column(Float, nullable=True, comment="Investment score (0.0-100.0)")
    estimated_all_in_cost = Column(Float, nullable=True, comment="Total cost including fees")

    # Enhanced Description Intelligence Fields (Phase 1 Enhancement)
    lot_dimensions_score = Column(Float, default=0.0, comment="Property shape and dimension quality score")
    shape_efficiency_score = Column(Float, default=0.0, comment="Lot shape efficiency and frontage score")
    corner_lot_bonus = Column(Float, default=0.0, comment="Corner lot premium bonus")
    irregular_shape_penalty = Column(Float, default=0.0, comment="Irregular shape penalty")
    subdivision_quality_score = Column(Float, default=0.0, comment="Subdivision/neighborhood quality score")
    road_access_score = Column(Float, default=0.0, comment="Road access quality score")
    location_type_score = Column(Float, default=0.0, comment="Location type classification score")
    title_complexity_score = Column(Float, default=0.0, comment="Legal title complexity risk score")
    survey_requirement_score = Column(Float, default=0.0, comment="Survey requirement complexity score")
    premium_water_access_score = Column(Float, default=0.0, comment="Premium water feature access score")
    total_description_score = Column(Float, default=0.0, comment="Total enhanced description intelligence score")

    # County Intelligence Fields (Future Phase 1)
    county_market_score = Column(Float, default=0.0, comment="County market conditions score")
    geographic_score = Column(Float, default=0.0, comment="Geographic advantages score")
    market_timing_score = Column(Float, default=0.0, comment="Market timing and opportunity score")

    # Financial data
    assessed_value = Column(Float, nullable=True, comment="County assessed value")
    assessed_value_ratio = Column(Float, nullable=True, comment="Calculated: amount / assessed_value")

    # Property details
    description = Column(Text, nullable=True, comment="Legal property description")
    county = Column(String, nullable=True, comment="Alabama county name")
    owner_name = Column(String, nullable=True, comment="Property owner name")
    year_sold = Column(String, nullable=True, comment="Sale year")

    # Ranking and metadata
    rank = Column(Integer, nullable=True, comment="Investment score ranking")
    created_at = Column(DateTime, default=func.now(), comment="Record creation timestamp")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="Last update timestamp")

    # Sync metadata for cross-platform compatibility
    device_id = Column(String, nullable=True, comment="Device that last modified this record")
    sync_timestamp = Column(DateTime, default=func.now(), comment="Last sync timestamp")
    is_deleted = Column(Boolean, default=False, comment="Soft delete flag for sync")

    # Research workflow status
    status = Column(String, default="new", comment="Research status: new, reviewing, bid_ready, rejected, purchased")
    triage_notes = Column(Text, nullable=True, comment="Research notes from triage review")
    triaged_at = Column(DateTime, nullable=True, comment="When property was triaged")
    triaged_by = Column(String, nullable=True, comment="Device/user that triaged this property")

    # Multi-State and Wholesale Fields (Pivot 2025)
    state = Column(String(2), default='AL', nullable=True, index=True, comment="State code (AL, AR, TX, FL)")
    sale_type = Column(String(20), nullable=True, comment="Tax lien, tax deed, redeemable deed, or hybrid")
    redemption_period_days = Column(Integer, nullable=True, comment="Days until ownership is clear")
    time_to_ownership_days = Column(Integer, nullable=True, comment="Total days to marketable title")
    estimated_market_value = Column(Float, nullable=True, comment="Estimated market value for wholesale spread")
    wholesale_spread = Column(Float, nullable=True, comment="Market value - asking price")
    owner_type = Column(String(20), nullable=True, comment="Individual, corporate, estate, absentee")
    data_source = Column(String(100), nullable=True, comment="Which scraper/platform sourced this")
    auction_date = Column(Date, nullable=True, comment="Scheduled auction date")
    auction_platform = Column(String(100), nullable=True, comment="GovEase, COSL, county-specific")

    # Multi-State Scoring Fields (Milestone 3)
    buy_hold_score = Column(Float, nullable=True, comment="Time-adjusted investment score (0-100)")
    wholesale_score = Column(Float, nullable=True, comment="Wholesale viability score (0-100)")
    effective_cost = Column(Float, nullable=True, comment="Total cost including quiet title fees")
    time_penalty_factor = Column(Float, nullable=True, comment="Time decay multiplier (0-1)")

    # Market reject and regional risk flags (Milestone 3+)
    is_market_reject = Column(Boolean, default=False, comment="Pre-2015 delinquency (stale inventory)")
    is_delta_region = Column(Boolean, default=False, comment="Arkansas Delta region county")
    delta_penalty_factor = Column(Float, default=1.0, comment="Delta region penalty multiplier")

    def __repr__(self):
        return f"<Property(id={self.id}, parcel_id={self.parcel_id}, amount={self.amount})>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "parcel_id": self.parcel_id,
            "amount": self.amount,
            "acreage": self.acreage,
            "price_per_acre": self.price_per_acre,
            "acreage_source": self.acreage_source,
            "acreage_confidence": self.acreage_confidence,
            "acreage_raw_text": self.acreage_raw_text,
            "water_score": self.water_score,
            "investment_score": self.investment_score,
            "estimated_all_in_cost": self.estimated_all_in_cost,
            "assessed_value": self.assessed_value,
            "assessed_value_ratio": self.assessed_value_ratio,

            # Enhanced Description Intelligence Fields
            "lot_dimensions_score": self.lot_dimensions_score,
            "shape_efficiency_score": self.shape_efficiency_score,
            "corner_lot_bonus": self.corner_lot_bonus,
            "irregular_shape_penalty": self.irregular_shape_penalty,
            "subdivision_quality_score": self.subdivision_quality_score,
            "road_access_score": self.road_access_score,
            "location_type_score": self.location_type_score,
            "title_complexity_score": self.title_complexity_score,
            "survey_requirement_score": self.survey_requirement_score,
            "premium_water_access_score": self.premium_water_access_score,
            "total_description_score": self.total_description_score,

            # County Intelligence Fields
            "county_market_score": self.county_market_score,
            "geographic_score": self.geographic_score,
            "market_timing_score": self.market_timing_score,

            "description": self.description,
            "county": self.county,
            "owner_name": self.owner_name,
            "year_sold": self.year_sold,
            "rank": self.rank,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "device_id": self.device_id,
            "sync_timestamp": self.sync_timestamp.isoformat() if self.sync_timestamp else None,
            "is_deleted": self.is_deleted,
            # Research workflow
            "status": self.status or "new",
            "triage_notes": self.triage_notes,
            "triaged_at": self.triaged_at.isoformat() if self.triaged_at else None,
            "triaged_by": self.triaged_by,
            # Multi-state and wholesale fields
            "state": self.state or "AL",
            "sale_type": self.sale_type,
            "redemption_period_days": self.redemption_period_days,
            "time_to_ownership_days": self.time_to_ownership_days,
            "estimated_market_value": self.estimated_market_value,
            "wholesale_spread": self.wholesale_spread,
            # Multi-state scoring fields
            "buy_hold_score": self.buy_hold_score,
            "wholesale_score": self.wholesale_score,
            "effective_cost": self.effective_cost,
            "time_penalty_factor": self.time_penalty_factor,
            # Market reject and regional risk flags
            "is_market_reject": self.is_market_reject,
            "is_delta_region": self.is_delta_region,
            "delta_penalty_factor": self.delta_penalty_factor,
            "owner_type": self.owner_type,
            "data_source": self.data_source,
            "auction_date": self.auction_date.isoformat() if self.auction_date else None,
            "auction_platform": self.auction_platform
        }

class County(Base):
    """
    Alabama County model with ADOR alphabetical mapping.
    CRITICAL: Must use exact same mapping as iOS CountyValidator.swift
    """
    __tablename__ = "counties"

    # Use ADOR alphabetical codes (NOT FIPS codes)
    code = Column(String(2), primary_key=True, comment="ADOR alphabetical county code (01-67)")
    name = Column(String(50), nullable=False, unique=True, comment="County name")

    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<County(code={self.code}, name={self.name})>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "code": self.code,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class SyncLog(Base):
    """
    Sync operation logging for debugging and monitoring.
    Tracks synchronization between iOS devices and backend.
    """
    __tablename__ = "sync_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String, nullable=False, comment="iOS device identifier")
    operation = Column(String, nullable=False, comment="Sync operation: delta, full, upload, download")
    status = Column(String, nullable=False, comment="Status: success, failed, partial")

    # Sync metrics
    records_processed = Column(Integer, default=0, comment="Number of records processed")
    conflicts_detected = Column(Integer, default=0, comment="Number of conflicts detected")
    conflicts_resolved = Column(Integer, default=0, comment="Number of conflicts resolved")

    # Timing data
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True, comment="Operation duration in seconds")

    # Error information
    error_message = Column(Text, nullable=True, comment="Error details if operation failed")

    # Algorithm validation
    algorithm_validation_passed = Column(Boolean, default=True, comment="Algorithm compatibility check")

    def __repr__(self):
        return f"<SyncLog(id={self.id}, device_id={self.device_id}, operation={self.operation}, status={self.status})>"

# Property Application Assistant Models
class UserProfile(Base):
    """
    User profile for application assistance - stores applicant information.
    Used to help users organize data for manual government form submission.
    """
    __tablename__ = "user_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Personal information
    full_name = Column(String, nullable=False, comment="Full legal name for applications")
    email = Column(String, nullable=False, comment="Email address for notifications")
    phone = Column(String, nullable=False, comment="Phone number")
    address = Column(String, nullable=False, comment="Street address")
    city = Column(String, nullable=False, comment="City")
    state = Column(String, nullable=False, comment="State")
    zip_code = Column(String, nullable=False, comment="ZIP code")

    # Investment preferences
    max_investment_amount = Column(Float, nullable=True, comment="Maximum willing to invest")
    min_acreage = Column(Float, nullable=True, comment="Minimum desired acreage")
    max_acreage = Column(Float, nullable=True, comment="Maximum desired acreage")
    preferred_counties = Column(Text, nullable=True, comment="JSON list of preferred counties")

    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True, comment="Profile active status")

    def __repr__(self):
        return f"<UserProfile(id={self.id}, name={self.full_name})>"


class PropertyApplication(Base):
    """
    Property application tracking for organizing data for manual form submission.
    LEGAL COMPLIANCE: This is for data organization only, not automated submission.
    """
    __tablename__ = "property_applications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_profile_id = Column(String, nullable=False, comment="Associated user profile")
    property_id = Column(String, nullable=False, comment="Property ID from our database")

    # State form data
    cs_number = Column(String, nullable=True, comment="CS Number from state records")
    parcel_number = Column(String, nullable=False, comment="Official parcel number")
    sale_year = Column(String, nullable=False, comment="Tax sale year")
    county = Column(String, nullable=False, comment="Alabama county name")
    description = Column(Text, nullable=False, comment="Legal property description")
    assessed_name = Column(String, nullable=True, comment="Name property was assessed in")

    # Financial data
    amount = Column(Float, nullable=False, comment="Minimum bid amount")
    acreage = Column(Float, nullable=True, comment="Property acreage")
    investment_score = Column(Float, nullable=True, comment="Our calculated investment score")
    estimated_total_cost = Column(Float, nullable=True, comment="Estimated all-in cost")
    roi_estimate = Column(Float, nullable=True, comment="Estimated ROI percentage")

    # Application status
    status = Column(String, default="draft", comment="Application status")
    notes = Column(Text, nullable=True, comment="User notes about this property")

    # Price tracking
    price_request_date = Column(DateTime, nullable=True, comment="When price was requested")
    price_received_date = Column(DateTime, nullable=True, comment="When price notification received")
    final_price = Column(Float, nullable=True, comment="Final price from state")

    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<PropertyApplication(id={self.id}, property_id={self.property_id}, status={self.status})>"


class ApplicationBatch(Base):
    """
    Batch of applications for processing efficiency.
    Helps users organize multiple property applications together.
    """
    __tablename__ = "application_batches"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_profile_id = Column(String, nullable=False, comment="Associated user profile")
    batch_name = Column(String, nullable=True, comment="User-defined batch name")

    # Financial summary
    total_estimated_investment = Column(Float, nullable=True, comment="Total estimated investment")

    # Processing tracking
    forms_generated = Column(Integer, default=0, comment="Number of forms generated")
    applications_submitted = Column(Integer, default=0, comment="Number manually submitted by user")
    prices_received = Column(Integer, default=0, comment="Number of price notifications received")

    # Status
    status = Column(String, default="draft", comment="Overall batch status")

    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ApplicationBatch(id={self.id}, name={self.batch_name}, status={self.status})>"


class ApplicationNotification(Base):
    """
    Notification tracking for application process.
    Tracks communications and state email notifications.
    """
    __tablename__ = "application_notifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_profile_id = Column(String, nullable=False, comment="User profile ID")
    property_id = Column(String, nullable=True, comment="Property ID if property-specific")

    # Notification details
    notification_type = Column(String, nullable=False, comment="Type of notification")
    title = Column(String, nullable=False, comment="Notification title")
    message = Column(Text, nullable=False, comment="Notification message")

    # State communication tracking
    state_email_expected = Column(Boolean, default=False, comment="Expecting email from state")
    state_email_received = Column(Boolean, default=False, comment="State email received")
    price_amount = Column(Float, nullable=True, comment="Price from state notification")

    # User interaction
    read_at = Column(DateTime, nullable=True, comment="When user read notification")
    action_required = Column(Boolean, default=False, comment="User action required")
    action_deadline = Column(DateTime, nullable=True, comment="Deadline for action")

    # Metadata
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<ApplicationNotification(id={self.id}, type={self.notification_type})>"


# Initialize Alabama counties with ADOR alphabetical mapping
# CRITICAL: This mapping MUST match iOS CountyValidator.swift exactly
ALABAMA_COUNTIES = {
    "01": "Autauga", "02": "Mobile", "03": "Baldwin", "04": "Barbour", "05": "Bibb",
    "06": "Blount", "07": "Bullock", "08": "Butler", "09": "Calhoun", "10": "Chambers",
    "11": "Cherokee", "12": "Chilton", "13": "Choctaw", "14": "Clarke", "15": "Clay",
    "16": "Cleburne", "17": "Coffee", "18": "Colbert", "19": "Conecuh", "20": "Coosa",
    "21": "Covington", "22": "Crenshaw", "23": "Cullman", "24": "Dale", "25": "Dallas",
    "26": "DeKalb", "27": "Elmore", "28": "Escambia", "29": "Etowah", "30": "Fayette",
    "31": "Franklin", "32": "Geneva", "33": "Greene", "34": "Hale", "35": "Henry",
    "36": "Houston", "37": "Jackson", "38": "Jefferson", "39": "Lamar", "40": "Lauderdale",
    "41": "Lawrence", "42": "Lee", "43": "Limestone", "44": "Lowndes", "45": "Macon",
    "46": "Madison", "47": "Marengo", "48": "Marion", "49": "Marshall", "50": "Monroe",
    "51": "Montgomery", "52": "Morgan", "53": "Perry", "54": "Pickens", "55": "Pike",
    "56": "Randolph", "57": "Russell", "58": "St. Clair", "59": "Shelby", "60": "Sumter",
    "61": "Talladega", "62": "Tallapoosa", "63": "Tuscaloosa", "64": "Walker", "65": "Washington",
    "66": "Wilcox", "67": "Winston"
}

def initialize_counties():
    """
    Initialize Alabama counties in database.
    Call this during application startup to ensure county data is available.
    """
    from .connection import SessionLocal

    db = SessionLocal()
    try:
        # Check if counties already exist
        existing_count = db.query(County).count()
        if existing_count > 0:
            return

        # Insert all Alabama counties
        for code, name in ALABAMA_COUNTIES.items():
            county = County(code=code, name=name)
            db.add(county)

        db.commit()
        print(f" Initialized {len(ALABAMA_COUNTIES)} Alabama counties")

    except Exception as e:
        db.rollback()
        print(f"L Failed to initialize counties: {str(e)}")
        raise
    finally:
        db.close()


# Multi-State Support Models (Pivot 2025)

class StateConfig(Base):
    """
    Multi-state configuration for tax deed/lien support.
    Stores state-specific rules, costs, and platform information.
    """
    __tablename__ = "state_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    state_code = Column(String(2), unique=True, nullable=False, comment="2-letter state code")
    state_name = Column(String(50), nullable=False, comment="Full state name")
    sale_type = Column(String(20), nullable=False, comment="tax_lien, tax_deed, redeemable_deed, or hybrid")
    redemption_period_days = Column(Integer, nullable=True, comment="Days until clear ownership")
    interest_rate = Column(Float, nullable=True, comment="Interest rate as decimal (0.12 = 12%)")
    quiet_title_cost_estimate = Column(Float, nullable=True, comment="Estimated legal costs")
    time_to_ownership_days = Column(Integer, nullable=False, comment="Total days to marketable title")
    auction_platform = Column(String(100), nullable=True, comment="Primary auction website")
    scraper_module = Column(String(100), nullable=True, comment="Python module path for scraper")
    is_active = Column(Boolean, default=True, comment="Whether to actively scrape this state")
    recommended_for_beginners = Column(Boolean, default=False, comment="Suitable for <$25k investors")
    notes = Column(Text, nullable=True, comment="Additional context and warnings")

    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<StateConfig(state={self.state_code}, type={self.sale_type})>"

    def to_dict(self):
        return {
            "id": self.id,
            "state_code": self.state_code,
            "state_name": self.state_name,
            "sale_type": self.sale_type,
            "redemption_period_days": self.redemption_period_days,
            "interest_rate": self.interest_rate,
            "quiet_title_cost_estimate": self.quiet_title_cost_estimate,
            "time_to_ownership_days": self.time_to_ownership_days,
            "auction_platform": self.auction_platform,
            "scraper_module": self.scraper_module,
            "is_active": self.is_active,
            "recommended_for_beginners": self.recommended_for_beginners,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class WholesalePipeline(Base):
    """
    Wholesale deal pipeline tracking.
    Tracks properties from identification through contract assignment.
    """
    __tablename__ = "wholesale_pipeline"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    property_id = Column(String, nullable=False, index=True, comment="FK to properties.id")
    status = Column(String(20), nullable=False, default='identified',
                   comment="identified, contacted, under_contract, assigned, closed, dead")

    # Financial details
    contract_price = Column(Float, nullable=True, comment="Purchase contract price")
    assignment_fee = Column(Float, nullable=True, comment="Wholesale fee to collect")
    earnest_money = Column(Float, nullable=True, comment="Earnest money deposit")

    # Buyer information
    buyer_id = Column(String, nullable=True, comment="End buyer identifier")
    buyer_name = Column(String(200), nullable=True, comment="End buyer name")
    buyer_email = Column(String(200), nullable=True, comment="End buyer email")

    # Timeline
    contract_date = Column(Date, nullable=True, comment="PSA signing date")
    closing_date = Column(Date, nullable=True, comment="Expected/actual closing")
    closed_at = Column(DateTime, nullable=True, comment="When deal was won/lost")

    # Notes
    marketing_notes = Column(Text, nullable=True, comment="Notes for marketing to buyers")
    notes = Column(Text, nullable=True, comment="General deal notes")

    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<WholesalePipeline(id={self.id}, property_id={self.property_id}, status={self.status})>"

    def to_dict(self):
        return {
            "id": self.id,
            "property_id": self.property_id,
            "status": self.status,
            "contract_price": self.contract_price,
            "assignment_fee": self.assignment_fee,
            "earnest_money": self.earnest_money,
            "buyer_id": self.buyer_id,
            "buyer_name": self.buyer_name,
            "buyer_email": self.buyer_email,
            "contract_date": self.contract_date.isoformat() if self.contract_date else None,
            "closing_date": self.closing_date.isoformat() if self.closing_date else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "marketing_notes": self.marketing_notes,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }