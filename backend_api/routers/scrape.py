"""
Scrape Jobs API endpoints.
Provides visibility into scraper runs and data freshness.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional, List
from pydantic import BaseModel, Field
import logging
from datetime import datetime, timedelta, timezone
import math

from ..database.connection import get_db
from ..database.models import ScrapeJob, Property
from ..auth import get_current_user_or_api_key
from ..config import limiter

# Import state configs
import sys
sys.path.insert(0, 'c:/auction')
from config.states import STATE_CONFIGS, get_active_states

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class ScrapeJobResponse(BaseModel):
    """Response model for scrape job."""
    id: str
    state: str
    county: Optional[str]
    status: str
    items_found: int
    items_added: int
    items_updated: int
    started_at: Optional[str]
    completed_at: Optional[str]
    error_message: Optional[str]
    triggered_by: Optional[str]
    created_at: Optional[str]
    duration_seconds: Optional[float] = None


class ScrapeJobsListResponse(BaseModel):
    """Paginated list of scrape jobs."""
    jobs: List[ScrapeJobResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class TriggerScrapeRequest(BaseModel):
    """Request to trigger a scrape job."""
    state: str = Field(..., min_length=2, max_length=2, description="State code")
    county: Optional[str] = Field(None, description="County name (optional, null = all counties)")


class DataFreshnessResponse(BaseModel):
    """Data freshness info for a state/county."""
    state: str
    county: Optional[str]
    last_scrape: Optional[str]
    last_scrape_status: Optional[str]
    properties_count: int
    oldest_property: Optional[str]
    newest_property: Optional[str]
    freshness_score: float  # 0-100, higher = fresher


class StateFreshnessResponse(BaseModel):
    """Data freshness summary by state."""
    states: List[DataFreshnessResponse]


def get_device_id_from_auth(auth_data: dict) -> str:
    """Extract user identifier from auth data for DB queries."""
    return auth_data.get("user_id", "unknown")


@router.get("/jobs", response_model=ScrapeJobsListResponse)
@limiter.limit("60/minute")
def list_scrape_jobs(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    state: Optional[str] = Query(None, description="Filter by state"),
    status: Optional[str] = Query(None, description="Filter by status"),
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    List scrape jobs with pagination and filtering.
    """
    try:
        query = db.query(ScrapeJob)

        if state:
            query = query.filter(ScrapeJob.state == state.upper())
        if status:
            query = query.filter(ScrapeJob.status == status)

        # Get total count
        total_count = query.count()

        # Apply pagination and ordering
        offset = (page - 1) * page_size
        jobs = query.order_by(
            desc(ScrapeJob.created_at)
        ).offset(offset).limit(page_size).all()

        # Format response
        job_responses = []
        for job in jobs:
            job_dict = job.to_dict()
            # Calculate duration
            if job.started_at and job.completed_at:
                duration = (job.completed_at - job.started_at).total_seconds()
                job_dict["duration_seconds"] = duration
            job_responses.append(ScrapeJobResponse(**job_dict))

        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

        return ScrapeJobsListResponse(
            jobs=job_responses,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Failed to list scrape jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve scrape jobs")


@router.get("/jobs/{job_id}", response_model=ScrapeJobResponse)
@limiter.limit("120/minute")
def get_scrape_job(
    request: Request,
    job_id: str,
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific scrape job.
    """
    try:
        job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()

        if not job:
            raise HTTPException(status_code=404, detail="Scrape job not found")

        job_dict = job.to_dict()
        if job.started_at and job.completed_at:
            job_dict["duration_seconds"] = (job.completed_at - job.started_at).total_seconds()

        return ScrapeJobResponse(**job_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get scrape job: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve scrape job")


@router.post("/trigger", response_model=ScrapeJobResponse)
@limiter.limit("5/minute")
def trigger_scrape(
    request: Request,
    scrape_request: TriggerScrapeRequest,
    background_tasks: BackgroundTasks,
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Trigger a new scrape job.
    The scrape runs in the background.
    """
    try:
        device_id = get_device_id_from_auth(auth_data)
        state = scrape_request.state.upper()

        # Validate state
        if state not in STATE_CONFIGS:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown state: {state}. Valid states: {', '.join(STATE_CONFIGS.keys())}"
            )

        state_config = STATE_CONFIGS[state]
        if not state_config.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Scraper for {state} is not yet implemented"
            )

        # Check for running job for same state/county
        existing = db.query(ScrapeJob).filter(
            ScrapeJob.state == state,
            ScrapeJob.status.in_(['pending', 'running'])
        )
        if scrape_request.county:
            existing = existing.filter(ScrapeJob.county == scrape_request.county)

        if existing.first():
            raise HTTPException(
                status_code=409,
                detail=f"A scrape job for {state}{' - ' + scrape_request.county if scrape_request.county else ''} is already running"
            )

        # Create job record
        job = ScrapeJob(
            state=state,
            county=scrape_request.county,
            status='pending',
            triggered_by=device_id
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # Schedule background task
        background_tasks.add_task(run_scrape_job, job.id, state, scrape_request.county)

        logger.info(f"Triggered scrape job {job.id} for {state}")

        return ScrapeJobResponse(**job.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger scrape: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to trigger scrape job")


async def run_scrape_job(job_id: str, state: str, county: Optional[str]):
    """
    Background task to run scrape job.
    Updates job status as it progresses.
    """
    from ..database.connection import SessionLocal
    from datetime import timezone

    db = SessionLocal()
    job = None

    try:
        # Update job to running
        job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.status = 'running'
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"Running scrape for {state}" + (f" - {county}" if county else ""))

        # Run the appropriate scraper via factory
        from core.scrapers.factory import ScraperFactory
        result = await ScraperFactory.scrape(state=state, county=county)

        # Check for scraper errors
        if result.error_message:
            job.status = 'failed'
            job.error_message = result.error_message
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            logger.error(f"Scrape job {job_id} failed: {result.error_message}")
            return

        job.items_found = result.items_found
        db.commit()

        # Process properties with upsert logic
        items_added = 0
        items_updated = 0
        scrape_timestamp = datetime.now(timezone.utc)

        # Initialize scoring engine
        from core.scoring import ScoringEngine
        scoring_engine = ScoringEngine(capital_limit=10000.0)

        for prop_dict in result.properties:
            try:
                parcel_id = prop_dict.get('parcel_id')
                prop_state = prop_dict.get('state', state)

                if not parcel_id:
                    continue

                # Check if exists
                existing = db.query(Property).filter(
                    Property.parcel_id == parcel_id,
                    Property.state == prop_state
                ).first()

                if existing:
                    # Update existing property
                    _update_existing_property(existing, prop_dict, scrape_timestamp)

                    # Re-score if acreage now available but no score yet
                    if existing.acreage and existing.acreage > 0 and existing.buy_hold_score is None:
                        _calculate_scores(existing, scoring_engine)

                    items_updated += 1
                else:
                    # Create new property
                    new_prop = _create_new_property(prop_dict, scrape_timestamp)
                    _calculate_scores(new_prop, scoring_engine)
                    db.add(new_prop)
                    items_added += 1

                # Batch commit every 50 properties for progress visibility
                if (items_added + items_updated) % 50 == 0:
                    db.flush()
                    job.items_added = items_added
                    job.items_updated = items_updated
                    db.commit()

            except Exception as e:
                logger.warning(f"Failed to process property {prop_dict.get('parcel_id')}: {e}")
                continue

        # Final commit
        job.status = 'completed'
        job.completed_at = datetime.now(timezone.utc)
        job.items_added = items_added
        job.items_updated = items_updated
        db.commit()

        logger.info(f"Completed scrape job {job_id}: {items_added} added, {items_updated} updated")

    except Exception as e:
        logger.error(f"Scrape job {job_id} failed: {str(e)}")
        if job:
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


def _update_existing_property(existing: Property, prop_dict: dict, timestamp) -> None:
    """Update an existing property with new scraped data."""
    # Update mutable fields
    existing.amount = prop_dict.get('amount', existing.amount)
    existing.owner_name = prop_dict.get('owner_name', existing.owner_name)
    existing.description = prop_dict.get('description', existing.description)
    existing.updated_at = timestamp

    # Update acreage if we have new data and didn't have it before
    new_acreage = prop_dict.get('acreage')
    if new_acreage and new_acreage > 0:
        if not existing.acreage or existing.acreage <= 0:
            existing.acreage = new_acreage
            existing.acreage_source = prop_dict.get('acreage_source')
            existing.acreage_confidence = prop_dict.get('acreage_confidence')
            existing.acreage_raw_text = prop_dict.get('acreage_raw_text')


def _create_new_property(prop_dict: dict, timestamp) -> Property:
    """Create a new Property from scraped data."""
    from core.scoring import DELTA_REGION_COUNTIES, DELTA_REGION_PENALTY

    county = prop_dict.get('county', '').upper()
    is_delta = county in DELTA_REGION_COUNTIES

    return Property(
        parcel_id=prop_dict['parcel_id'],
        county=prop_dict.get('county'),
        owner_name=prop_dict.get('owner_name'),
        acreage=prop_dict.get('acreage'),
        amount=prop_dict.get('amount'),
        description=prop_dict.get('description'),
        state=prop_dict.get('state', 'AR'),
        sale_type=prop_dict.get('sale_type'),
        redemption_period_days=prop_dict.get('redemption_period_days'),
        time_to_ownership_days=prop_dict.get('time_to_ownership_days'),
        data_source=prop_dict.get('data_source'),
        auction_platform=prop_dict.get('auction_platform'),
        year_sold=prop_dict.get('year_sold'),
        status='new',
        updated_at=timestamp,
        acreage_source=prop_dict.get('acreage_source'),
        acreage_confidence=prop_dict.get('acreage_confidence'),
        acreage_raw_text=prop_dict.get('acreage_raw_text'),
        is_delta_region=is_delta,
        delta_penalty_factor=DELTA_REGION_PENALTY if is_delta else 1.0,
    )


def _calculate_scores(prop: Property, engine) -> None:
    """Calculate buy-hold and wholesale scores for a property."""
    if not (prop.amount and prop.amount > 0 and prop.acreage and prop.acreage > 0):
        return

    from core.scoring import PropertyScoreInput

    score_input = PropertyScoreInput(
        state=prop.state or 'AR',
        sale_type=prop.sale_type or 'tax_deed',
        amount=prop.amount,
        acreage=prop.acreage,
        water_score=prop.water_score or 0.0,
        year_sold=prop.year_sold,
        county=prop.county
    )

    result = engine.calculate_scores(score_input)
    prop.buy_hold_score = result.buy_hold_score
    prop.wholesale_score = result.wholesale_score
    prop.effective_cost = result.effective_cost
    prop.time_penalty_factor = result.time_penalty_factor
    prop.is_market_reject = result.is_market_reject
    prop.is_delta_region = result.is_delta_region
    prop.delta_penalty_factor = result.delta_penalty_factor


@router.get("/freshness", response_model=StateFreshnessResponse)
@limiter.limit("30/minute")
def get_data_freshness(
    request: Request,
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Get data freshness summary for all states.
    """
    try:
        states = []

        for state_code in STATE_CONFIGS.keys():
            # Get property counts and dates
            state_query = db.query(Property).filter(
                Property.state == state_code,
                Property.is_deleted == False
            )

            count = state_query.count()

            # Get date range
            oldest = state_query.order_by(Property.created_at.asc()).first()
            newest = state_query.order_by(Property.created_at.desc()).first()

            # Get last scrape
            last_job = db.query(ScrapeJob).filter(
                ScrapeJob.state == state_code,
                ScrapeJob.status == 'completed'
            ).order_by(desc(ScrapeJob.completed_at)).first()

            # Calculate freshness score (0-100)
            # Based on: days since last scrape, property count
            freshness = 0.0
            if last_job and last_job.completed_at:
                days_old = (datetime.now(timezone.utc) - last_job.completed_at).days
                if days_old <= 1:
                    freshness = 100.0
                elif days_old <= 7:
                    freshness = 80.0 - (days_old * 5)
                elif days_old <= 30:
                    freshness = 50.0 - (days_old - 7)
                else:
                    freshness = max(0, 20 - (days_old - 30) * 0.5)
            elif count > 0:
                # Has data but no recorded scrape job
                freshness = 30.0

            states.append(DataFreshnessResponse(
                state=state_code,
                county=None,
                last_scrape=last_job.completed_at.isoformat() if last_job and last_job.completed_at else None,
                last_scrape_status=last_job.status if last_job else None,
                properties_count=count,
                oldest_property=oldest.created_at.isoformat() if oldest and oldest.created_at else None,
                newest_property=newest.created_at.isoformat() if newest and newest.created_at else None,
                freshness_score=freshness
            ))

        return StateFreshnessResponse(states=states)

    except Exception as e:
        logger.error(f"Failed to get freshness: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve data freshness")


@router.get("/freshness/{state}", response_model=DataFreshnessResponse)
@limiter.limit("60/minute")
def get_state_freshness(
    request: Request,
    state: str,
    county: Optional[str] = None,
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Get data freshness for a specific state (and optionally county).
    """
    try:
        state = state.upper()

        # Get property counts and dates
        query = db.query(Property).filter(
            Property.state == state,
            Property.is_deleted == False
        )
        if county:
            query = query.filter(Property.county == county)

        count = query.count()
        oldest = query.order_by(Property.created_at.asc()).first()
        newest = query.order_by(Property.created_at.desc()).first()

        # Get last scrape
        job_query = db.query(ScrapeJob).filter(
            ScrapeJob.state == state,
            ScrapeJob.status == 'completed'
        )
        if county:
            job_query = job_query.filter(ScrapeJob.county == county)

        last_job = job_query.order_by(desc(ScrapeJob.completed_at)).first()

        # Calculate freshness
        freshness = 0.0
        if last_job and last_job.completed_at:
            days_old = (datetime.now(timezone.utc) - last_job.completed_at).days
            if days_old <= 1:
                freshness = 100.0
            elif days_old <= 7:
                freshness = 80.0 - (days_old * 5)
            elif days_old <= 30:
                freshness = 50.0 - (days_old - 7)
            else:
                freshness = max(0, 20 - (days_old - 30) * 0.5)
        elif count > 0:
            freshness = 30.0

        return DataFreshnessResponse(
            state=state,
            county=county,
            last_scrape=last_job.completed_at.isoformat() if last_job and last_job.completed_at else None,
            last_scrape_status=last_job.status if last_job else None,
            properties_count=count,
            oldest_property=oldest.created_at.isoformat() if oldest and oldest.created_at else None,
            newest_property=newest.created_at.isoformat() if newest and newest.created_at else None,
            freshness_score=freshness
        )

    except Exception as e:
        logger.error(f"Failed to get state freshness: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve freshness")


@router.delete("/jobs/{job_id}")
@limiter.limit("10/minute")
def cancel_scrape_job(
    request: Request,
    job_id: str,
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Cancel a pending or running scrape job.
    """
    try:
        job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()

        if not job:
            raise HTTPException(status_code=404, detail="Scrape job not found")

        if job.status not in ['pending', 'running']:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel job with status: {job.status}"
            )

        job.status = 'cancelled'
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"Cancelled scrape job {job_id}")

        return {"message": "Job cancelled", "job_id": job_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to cancel job")


@router.get("/states")
@limiter.limit("60/minute")
async def get_available_states(request: Request):
    """
    Get list of states available for scraping.
    """
    states = []
    for code, config in STATE_CONFIGS.items():
        states.append({
            "state_code": code,
            "state_name": config.state_name,
            "is_active": config.is_active,
            "sale_type": config.sale_type,
            "scraper_module": config.scraper_module
        })

    return {"states": states}
