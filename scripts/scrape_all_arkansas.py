"""
Comprehensive Arkansas COSL Property Scraper

This script scrapes ALL available properties from the Arkansas
Commissioner of State Lands auction platform and imports them
into the database with proper scoring.

Usage:
    python scripts/scrape_all_arkansas.py
    python scripts/scrape_all_arkansas.py --dry-run
    python scripts/scrape_all_arkansas.py --min-delinquency-year 2015

Created: 2025-01-04
Purpose: Expand Arkansas property inventory for investment analysis
"""

import argparse
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import get_logger
from backend_api.database.connection import SessionLocal
from backend_api.database.models import Property
from core.scrapers.arkansas_cosl import ArkansasCOSLScraper
from core.scoring import ScoringEngine, PropertyScoreInput

logger = get_logger(__name__)

# Counties to prioritize (safer markets)
PRIORITY_COUNTIES = [
    'WASHINGTON', 'BENTON', 'PULASKI', 'SALINE', 'FAULKNER',
    'CLEBURNE', 'BAXTER', 'GARLAND', 'SEBASTIAN', 'WHITE'
]

# Counties to avoid (Delta region, economic distress)
AVOID_COUNTIES = [
    'PHILLIPS', 'LEE', 'CHICOT', 'MISSISSIPPI', 'CRITTENDEN',
    'ST. FRANCIS', 'MONROE', 'DESHA', 'ARKANSAS'
]


async def scrape_and_import(
    dry_run: bool = False,
    min_delinquency_year: int = 2015,
    capital_limit: float = 10000.0,
    skip_avoid_counties: bool = True
):
    """
    Scrape all Arkansas COSL properties and import to database.

    Args:
        dry_run: If True, don't commit to database
        min_delinquency_year: Skip properties delinquent before this year
        capital_limit: Maximum budget for scoring
        skip_avoid_counties: If True, skip high-risk Delta counties
    """
    logger.info("=" * 60)
    logger.info("ARKANSAS COSL COMPREHENSIVE SCRAPER")
    logger.info("=" * 60)

    engine = ScoringEngine(capital_limit=capital_limit)

    # Scrape all properties using async context manager
    logger.info("Fetching all properties from COSL...")
    try:
        async with ArkansasCOSLScraper() as scraper:
            properties = await scraper.scrape_all_properties()
        logger.info(f"Found {len(properties)} total properties")
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        return

    # Process and filter
    db = SessionLocal()
    imported = 0
    skipped_county = 0
    skipped_exists = 0
    skipped_delinquency = 0
    updated = 0

    try:
        for prop in properties:
            prop_dict = prop.to_dict()
            county = prop_dict.get('county', '').upper()
            parcel_id = prop_dict.get('parcel_id')

            # Skip avoid counties if configured
            if skip_avoid_counties and county in AVOID_COUNTIES:
                logger.debug(f"Skipping {parcel_id} - avoid county: {county}")
                skipped_county += 1
                continue

            # TODO: Add delinquency year check when available from scraper
            # For now, use added_on date as proxy
            # if delinquency_year < min_delinquency_year:
            #     skipped_delinquency += 1
            #     continue

            # Check if exists
            existing = db.query(Property).filter(
                Property.parcel_id == parcel_id,
                Property.state == 'AR'
            ).first()

            if existing:
                # Update if bid changed
                if existing.amount != prop_dict.get('amount'):
                    existing.amount = prop_dict.get('amount')
                    updated += 1
                else:
                    skipped_exists += 1
                continue

            # Create new property
            new_prop = Property(
                parcel_id=prop_dict['parcel_id'],
                county=prop_dict['county'],
                owner_name=prop_dict.get('owner_name'),
                acreage=prop_dict.get('acreage'),
                amount=prop_dict.get('amount'),
                description=prop_dict.get('description'),
                state='AR',
                sale_type='tax_deed',
                redemption_period_days=0,
                data_source='arkansas_cosl',
                auction_platform='COSL Website'
            )

            # Calculate scores
            if new_prop.amount and new_prop.amount > 0 and new_prop.acreage and new_prop.acreage > 0:
                score_input = PropertyScoreInput(
                    state='AR',
                    sale_type='tax_deed',
                    amount=new_prop.amount,
                    acreage=new_prop.acreage,
                    water_score=0.0  # Would need description analysis
                )
                result = engine.calculate_scores(score_input)
                new_prop.buy_hold_score = result.buy_hold_score
                new_prop.wholesale_score = result.wholesale_score
                new_prop.effective_cost = result.effective_cost
                new_prop.time_penalty_factor = result.time_penalty_factor

            db.add(new_prop)
            imported += 1

            if imported % 100 == 0:
                logger.info(f"Imported {imported} properties...")

        # Summary
        logger.info("")
        logger.info("=" * 60)
        logger.info("IMPORT SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total scraped:     {len(properties)}")
        logger.info(f"New imported:      {imported}")
        logger.info(f"Updated bids:      {updated}")
        logger.info(f"Skipped (exists):  {skipped_exists}")
        logger.info(f"Skipped (county):  {skipped_county}")
        logger.info(f"Skipped (old):     {skipped_delinquency}")

        if dry_run:
            logger.info("")
            logger.info("DRY RUN - No changes committed")
            db.rollback()
        else:
            db.commit()
            logger.info("")
            logger.info("Changes committed to database")

        # Show county breakdown
        print_county_summary(db)

    except Exception as e:
        db.rollback()
        logger.error(f"Import failed: {e}")
        raise
    finally:
        db.close()


def print_county_summary(db):
    """Print summary of properties by county."""
    from sqlalchemy import func

    print("\n" + "=" * 60)
    print("ARKANSAS PROPERTIES BY COUNTY")
    print("=" * 60)

    results = db.query(
        Property.county,
        func.count(Property.id).label('count'),
        func.avg(Property.buy_hold_score).label('avg_score'),
        func.min(Property.amount).label('min_bid')
    ).filter(
        Property.state == 'AR'
    ).group_by(Property.county).order_by(func.count(Property.id).desc()).all()

    print(f"{'County':<20} {'Count':>8} {'Avg Score':>10} {'Min Bid':>12} {'Status':<10}")
    print("-" * 60)

    for row in results:
        county = row.county or 'Unknown'
        status = "AVOID" if county.upper() in AVOID_COUNTIES else ""
        if county.upper() in PRIORITY_COUNTIES:
            status = "PRIORITY"
        print(f"{county:<20} {row.count:>8} {row.avg_score or 0:>10.1f} ${row.min_bid or 0:>11,.0f} {status:<10}")

    # Top properties by score
    print("\n" + "=" * 60)
    print("TOP 10 PROPERTIES BY BUY-HOLD SCORE")
    print("=" * 60)

    top_props = db.query(Property).filter(
        Property.state == 'AR',
        Property.buy_hold_score.isnot(None)
    ).order_by(Property.buy_hold_score.desc()).limit(10).all()

    print(f"{'County':<15} {'Parcel':<20} {'Acres':>8} {'Bid':>10} {'Score':>8}")
    print("-" * 60)

    for prop in top_props:
        county = (prop.county or 'N/A')[:15]
        parcel = (prop.parcel_id or 'N/A')[:20]
        print(f"{county:<15} {parcel:<20} {prop.acreage or 0:>8.2f} ${prop.amount or 0:>9,.0f} {prop.buy_hold_score or 0:>8.1f}")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape all Arkansas COSL properties"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without committing"
    )
    parser.add_argument(
        "--min-delinquency-year",
        type=int,
        default=2015,
        help="Skip properties delinquent before this year (default: 2015)"
    )
    parser.add_argument(
        "--capital-limit",
        type=float,
        default=10000.0,
        help="Maximum investment budget (default: $10,000)"
    )
    parser.add_argument(
        "--include-avoid-counties",
        action="store_true",
        help="Include high-risk Delta counties (Phillips, Lee, etc.)"
    )

    args = parser.parse_args()

    asyncio.run(scrape_and_import(
        dry_run=args.dry_run,
        min_delinquency_year=args.min_delinquency_year,
        capital_limit=args.capital_limit,
        skip_avoid_counties=not args.include_avoid_counties
    ))


if __name__ == "__main__":
    main()
