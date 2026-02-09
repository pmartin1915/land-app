"""
SQLAlchemy database models for Auction Watcher API.
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Text, Boolean, Date, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .connection import Base
import uuid

class Property(Base):
    """Core property model for auction listings across all states."""
    __tablename__ = "properties"

    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Core property data
    parcel_id = Column(String, nullable=False, index=True, comment="Unique parcel identifier")
    amount = Column(Float, nullable=False, comment="Bid/sale amount in USD")
    acreage = Column(Float, nullable=True, comment="Property acreage")
    price_per_acre = Column(Float, nullable=True, comment="Calculated: amount / acreage")

    # Acreage data lineage (for tracking data quality)
    acreage_source = Column(String(20), nullable=True, comment="Source: api, parsed_explicit, parsed_plss, parsed_dimensions")
    acreage_confidence = Column(String(10), nullable=True, comment="Confidence: high, medium, low")
    acreage_raw_text = Column(String(200), nullable=True, comment="Original text that was parsed for acreage")

    # Calculated algorithm fields
    water_score = Column(Float, default=0.0, comment="Water feature score (0.0-15.0+)")
    investment_score = Column(Float, nullable=True, index=True, comment="Investment score (0.0-100.0)")
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
    county = Column(String, nullable=True, index=True, comment="County name")
    owner_name = Column(String, nullable=True, comment="Property owner name")
    year_sold = Column(String, nullable=True, index=True, comment="Sale year")

    # Ranking and metadata
    rank = Column(Integer, nullable=True, comment="Investment score ranking")
    created_at = Column(DateTime, default=func.now(), index=True, comment="Record creation timestamp")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="Last update timestamp")

    # Sync metadata for cross-platform compatibility
    device_id = Column(String, nullable=True, comment="Device that last modified this record")
    sync_timestamp = Column(DateTime, default=func.now(), comment="Last sync timestamp")
    is_deleted = Column(Boolean, default=False, index=True, comment="Soft delete flag for sync")

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

class County(Base):
    """
    Alabama County model with ADOR alphabetical mapping.
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

class SyncLog(Base):
    """Sync operation logging for debugging and monitoring."""
    __tablename__ = "sync_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String, nullable=False, comment="Device/user identifier")
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
    algorithm_validation_passed = Column(Boolean, default=True, comment="Algorithm validation check")

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
    county = Column(String, nullable=False, comment="County name")
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


# Alabama counties with ADOR (Dept of Revenue) official codes
# Source: https://www.revenue.alabama.gov/property-tax/delinquent-search/
# Note: ADOR uses non-sequential codes. Jefferson County is split into Birmingham (01) and Bessemer (68).
ALABAMA_COUNTIES = {
    "01": "Jefferson-Bham", "02": "Mobile", "03": "Montgomery",
    "04": "Autauga", "05": "Baldwin", "06": "Barbour", "07": "Bibb", "08": "Blount",
    "09": "Bullock", "10": "Butler", "11": "Calhoun", "12": "Chambers", "13": "Cherokee",
    "14": "Chilton", "15": "Choctaw", "16": "Clarke", "17": "Clay", "18": "Cleburne",
    "19": "Coffee", "20": "Colbert", "21": "Conecuh", "22": "Coosa", "23": "Covington",
    "24": "Crenshaw", "25": "Cullman", "26": "Dale", "27": "Dallas", "28": "DeKalb",
    "29": "Elmore", "30": "Escambia", "31": "Etowah", "32": "Fayette", "33": "Franklin",
    "34": "Geneva", "35": "Greene", "36": "Hale", "37": "Henry", "38": "Houston",
    "39": "Jackson", "40": "Lamar", "41": "Lauderdale", "42": "Lawrence", "43": "Lee",
    "44": "Limestone", "45": "Lowndes", "46": "Macon", "47": "Madison", "48": "Marengo",
    "49": "Marion", "50": "Marshall", "51": "Monroe", "52": "Morgan", "53": "Perry",
    "54": "Pickens", "55": "Pike", "56": "Randolph", "57": "Russell", "58": "Shelby",
    "59": "St_Clair", "60": "Sumter", "61": "Talladega", "62": "Tallapoosa",
    "63": "Tuscaloosa", "64": "Walker", "65": "Washington", "66": "Wilcox", "67": "Winston",
    "68": "Jefferson-Bess"
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

class UserPreference(Base):
    """
    User preferences for investment settings, budget, and filter defaults.
    One row per device_id - survives scraper re-runs.
    """
    __tablename__ = "user_preferences"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String, unique=True, index=True, nullable=False,
                       comment="Links to device auth - one preference set per device")
    investment_budget = Column(Float, default=10000.0, nullable=True,
                               comment="User investment capital budget in USD")
    excluded_states = Column(String, nullable=True,
                             comment="JSON array of state codes to exclude from results")
    default_filters = Column(Text, nullable=True,
                             comment="JSON of saved filter presets")
    max_property_price = Column(Float, nullable=True,
                                comment="Maximum price per property (derived from budget)")
    preferred_states = Column(String, nullable=True,
                              comment="JSON array of preferred state codes")
    notifications_enabled = Column(Boolean, default=True,
                                   comment="Whether to show notifications")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<UserPreference(device_id={self.device_id}, budget={self.investment_budget})>"

    def to_dict(self):
        """Override: JSON-stored fields need parsing before serialization."""
        import json
        d = super().to_dict()
        d["excluded_states"] = json.loads(d["excluded_states"]) if d.get("excluded_states") else []
        d["default_filters"] = json.loads(d["default_filters"]) if d.get("default_filters") else {}
        d["preferred_states"] = json.loads(d["preferred_states"]) if d.get("preferred_states") else []
        return d


class PropertyInteraction(Base):
    """
    User overlay for property watchlist and notes.
    IMPORTANT: Separate from Property table to survive scraper re-runs.
    """
    __tablename__ = "property_interactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String, index=True, nullable=False,
                       comment="Device that created this interaction")
    property_id = Column(String, ForeignKey("properties.id", ondelete="CASCADE"),
                         index=True, nullable=False,
                         comment="FK to properties table")
    is_watched = Column(Boolean, default=False, index=True,
                        comment="Whether property is on watchlist")
    star_rating = Column(Integer, nullable=True,
                         comment="User rating 1-5 stars")
    user_notes = Column(Text, nullable=True,
                        comment="User notes about this property")
    dismissed = Column(Boolean, default=False,
                       comment="User dismissed/hidden this property")

    # First Deal Tracking (My First Deal feature)
    is_first_deal = Column(Boolean, default=False, index=True,
                           comment="Whether this is the user's first deal property")
    first_deal_stage = Column(String(20), nullable=True,
                              comment="Pipeline stage: research, bid, won, quiet_title, sold, holding")
    first_deal_assigned_at = Column(DateTime, nullable=True,
                                    comment="When property was assigned as first deal")
    first_deal_updated_at = Column(DateTime, nullable=True,
                                   comment="Last pipeline stage update timestamp")

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationship to Property
    property = relationship("Property", backref="interactions")

    def __repr__(self):
        return f"<PropertyInteraction(property_id={self.property_id}, watched={self.is_watched})>"

class ScrapeJob(Base):
    """
    Scrape job tracking for visibility into data freshness.
    """
    __tablename__ = "scrape_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    state = Column(String(2), nullable=False, index=True,
                   comment="State code being scraped")
    county = Column(String(100), nullable=True,
                    comment="County name if county-specific, NULL for all counties")
    status = Column(String(20), nullable=False, default='pending',
                    comment="pending, running, completed, failed, cancelled")
    items_found = Column(Integer, default=0,
                         comment="Total properties found during scrape")
    items_added = Column(Integer, default=0,
                         comment="New properties added to database")
    items_updated = Column(Integer, default=0,
                           comment="Existing properties updated")
    started_at = Column(DateTime, nullable=True,
                        comment="When scrape job started")
    completed_at = Column(DateTime, nullable=True,
                          comment="When scrape job completed")
    error_message = Column(Text, nullable=True,
                           comment="Error details if job failed")
    triggered_by = Column(String, nullable=True,
                          comment="Device ID or system that triggered the job")
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<ScrapeJob(id={self.id}, state={self.state}, status={self.status})>"

class WholesalePipeline(Base):
    """
    Wholesale deal pipeline tracking.
    Tracks properties from identification through contract assignment.
    """
    __tablename__ = "wholesale_pipeline"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    property_id = Column(String, ForeignKey("properties.id", ondelete="CASCADE"),
                         nullable=False, index=True, comment="FK to properties.id")

    # Relationship to Property
    property = relationship("Property", backref="wholesale_pipeline")
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

