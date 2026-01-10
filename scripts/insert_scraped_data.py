#!/usr/bin/env python3
"""
Insert Scraped Data - Process scraped JSON results and insert into database

Usage:
    python scripts/insert_scraped_data.py --state AR  # Scrape and insert Arkansas
    python scripts/insert_scraped_data.py --state FL  # Scrape and insert Florida
    python scripts/insert_scraped_data.py --all       # Scrape and insert all states (AR, AL, TX, FL)
"""

import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import get_logger
from config.states import ALABAMA_MISSING_COUNTIES, TEXAS_COUNTIES, FLORIDA_COUNTIES
from core.scrapers.factory import ScraperFactory

# Database imports
sys.path.insert(0, str(project_root / 'backend_api'))
from backend_api.database.connection import SessionLocal
from backend_api.database.models import Property

logger = get_logger(__name__)


def _apply_scores(prop, scoring_engine, PropertyScoreInput):
    """Apply investment scores to a Property model instance.

    Args:
        prop: Property model instance with state, sale_type, amount, acreage, etc.
        scoring_engine: ScoringEngine instance for score calculation
        PropertyScoreInput: PropertyScoreInput class for building input
    """
    if not (prop.amount and prop.amount > 0 and prop.acreage and prop.acreage > 0):
        return

    score_input = PropertyScoreInput(
        state=prop.state or 'AR',
        sale_type=prop.sale_type or 'tax_deed',
        amount=prop.amount,
        acreage=prop.acreage,
        water_score=prop.water_score or 0.0,
        year_sold=prop.year_sold,
        county=prop.county
    )
    result = scoring_engine.calculate_scores(score_input)
    prop.buy_hold_score = result.buy_hold_score
    prop.wholesale_score = result.wholesale_score
    prop.effective_cost = result.effective_cost
    prop.time_penalty_factor = result.time_penalty_factor
    prop.is_market_reject = result.is_market_reject
    prop.is_delta_region = result.is_delta_region
    prop.delta_penalty_factor = result.delta_penalty_factor


def insert_properties(properties: list, state: str) -> tuple:
    """Insert or update properties in database."""
    from core.scoring import ScoringEngine, PropertyScoreInput, DELTA_REGION_COUNTIES, DELTA_REGION_PENALTY

    db = SessionLocal()
    scoring_engine = ScoringEngine(capital_limit=10000.0)
    scrape_timestamp = datetime.now(timezone.utc)

    items_added = 0
    items_updated = 0
    items_skipped = 0

    try:
        for prop_dict in properties:
            parcel_id = prop_dict.get('parcel_id')
            prop_state = prop_dict.get('state', state)

            if not parcel_id:
                items_skipped += 1
                continue

            # Check if exists
            existing = db.query(Property).filter(
                Property.parcel_id == parcel_id,
                Property.state == prop_state
            ).first()

            if existing:
                # Update existing
                existing.amount = prop_dict.get('amount', existing.amount)
                existing.owner_name = prop_dict.get('owner_name', existing.owner_name)
                existing.description = prop_dict.get('description', existing.description)
                existing.updated_at = scrape_timestamp

                # Update acreage if we have new data
                new_acreage = prop_dict.get('acreage')
                if new_acreage and new_acreage > 0:
                    if not existing.acreage or existing.acreage <= 0:
                        existing.acreage = new_acreage
                        existing.acreage_source = prop_dict.get('acreage_source')
                        existing.acreage_confidence = prop_dict.get('acreage_confidence')
                        existing.acreage_raw_text = prop_dict.get('acreage_raw_text')

                # Re-score if needed
                if existing.buy_hold_score is None:
                    _apply_scores(existing, scoring_engine, PropertyScoreInput)

                items_updated += 1
            else:
                # Create new property
                county = prop_dict.get('county', '').upper()
                is_delta = county in DELTA_REGION_COUNTIES

                new_prop = Property(
                    parcel_id=prop_dict['parcel_id'],
                    county=prop_dict.get('county'),
                    owner_name=prop_dict.get('owner_name'),
                    acreage=prop_dict.get('acreage'),
                    amount=prop_dict.get('amount'),
                    description=prop_dict.get('description'),
                    state=prop_dict.get('state', state),
                    sale_type=prop_dict.get('sale_type'),
                    redemption_period_days=prop_dict.get('redemption_period_days'),
                    time_to_ownership_days=prop_dict.get('time_to_ownership_days'),
                    data_source=prop_dict.get('data_source'),
                    auction_platform=prop_dict.get('auction_platform'),
                    year_sold=prop_dict.get('year_sold'),
                    status='new',
                    updated_at=scrape_timestamp,
                    acreage_source=prop_dict.get('acreage_source'),
                    acreage_confidence=prop_dict.get('acreage_confidence'),
                    acreage_raw_text=prop_dict.get('acreage_raw_text'),
                    is_delta_region=is_delta,
                    delta_penalty_factor=DELTA_REGION_PENALTY if is_delta else 1.0,
                )

                # Score if possible
                _apply_scores(new_prop, scoring_engine, PropertyScoreInput)

                db.add(new_prop)
                items_added += 1

            # Batch commit every 100 properties
            if (items_added + items_updated) % 100 == 0:
                db.commit()
                logger.info(f"Progress: {items_added} added, {items_updated} updated")

        # Final commit
        db.commit()

    except Exception as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

    return items_added, items_updated, items_skipped


async def scrape_and_insert(state: str, counties: list = None) -> dict:
    """Scrape a state and insert directly into database."""
    all_properties = []
    results = {'state': state, 'counties_processed': 0, 'total_properties': 0}

    if state == 'AR':
        logger.info("Scraping Arkansas...")
        result = await ScraperFactory.scrape(state='AR')
        if not result.error_message:
            all_properties.extend(result.properties)
            results['counties_processed'] = 1
            results['total_properties'] = len(result.properties)

    elif state == 'AL':
        counties_to_scrape = counties or ALABAMA_MISSING_COUNTIES
        for county in counties_to_scrape:
            logger.info(f"Scraping Alabama - {county}...")
            result = await ScraperFactory.scrape(state='AL', county=county)
            if not result.error_message:
                all_properties.extend(result.properties)
                results['counties_processed'] += 1
                results['total_properties'] += len(result.properties)
            await asyncio.sleep(2)

    elif state == 'TX':
        counties_to_scrape = counties or TEXAS_COUNTIES
        for county in counties_to_scrape:
            logger.info(f"Scraping Texas - {county}...")
            result = await ScraperFactory.scrape(state='TX', county=county)
            if not result.error_message:
                all_properties.extend(result.properties)
                results['counties_processed'] += 1
                results['total_properties'] += len(result.properties)
            await asyncio.sleep(2)

    elif state == 'FL':
        counties_to_scrape = counties or FLORIDA_COUNTIES
        for county in counties_to_scrape:
            logger.info(f"Scraping Florida - {county}...")
            result = await ScraperFactory.scrape(state='FL', county=county)
            if not result.error_message:
                all_properties.extend(result.properties)
                results['counties_processed'] += 1
                results['total_properties'] += len(result.properties)
            await asyncio.sleep(2)

    # Insert into database
    if all_properties:
        logger.info(f"Inserting {len(all_properties)} properties into database...")
        added, updated, skipped = insert_properties(all_properties, state)
        results['items_added'] = added
        results['items_updated'] = updated
        results['items_skipped'] = skipped
        logger.info(f"Database: {added} added, {updated} updated, {skipped} skipped")

    return results


async def process_all_states(states: list) -> dict:
    """Process multiple states with single event loop."""
    total_results = {
        'started_at': datetime.now().isoformat(),
        'states': {},
        'total_added': 0,
        'total_updated': 0
    }

    for state in states:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing {state}...")
        logger.info(f"{'='*60}")

        result = await scrape_and_insert(state)
        total_results['states'][state] = result
        total_results['total_added'] += result.get('items_added', 0)
        total_results['total_updated'] += result.get('items_updated', 0)

    total_results['completed_at'] = datetime.now().isoformat()
    return total_results


def main():
    parser = argparse.ArgumentParser(description='Insert scraped data into database')
    parser.add_argument('--state', type=str, help='Scrape and insert state (AR, AL, TX, FL)')
    parser.add_argument('--all', action='store_true', help='Scrape and insert all states')

    args = parser.parse_args()

    if args.all:
        states = ['AR', 'AL', 'TX', 'FL']
    elif args.state:
        states = [args.state.upper()]
    else:
        print("Usage: python insert_scraped_data.py --state AR|AL|TX|FL OR --all")
        return 1

    # Single event loop for all states
    total_results = asyncio.run(process_all_states(states))

    # Print summary
    print("\n" + "="*60)
    print("SCRAPING AND DATABASE INSERT COMPLETE")
    print("="*60)

    for state, result in total_results['states'].items():
        print(f"\n{state}:")
        print(f"  Counties processed: {result.get('counties_processed', 0)}")
        print(f"  Properties scraped: {result.get('total_properties', 0)}")
        print(f"  DB Added: {result.get('items_added', 0)}")
        print(f"  DB Updated: {result.get('items_updated', 0)}")

    print(f"\nTotal Added: {total_results['total_added']}")
    print(f"Total Updated: {total_results['total_updated']}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
