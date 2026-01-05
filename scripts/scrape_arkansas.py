"""
Arkansas COSL Scraper Script

Scrapes tax deed properties from Arkansas Commissioner of State Lands
and optionally imports them into the database.

Usage:
    # Scrape and save to CSV only
    python scripts/scrape_arkansas.py

    # Scrape and import to database
    python scripts/scrape_arkansas.py --import-db

    # Scrape specific county
    python scripts/scrape_arkansas.py --county Pulaski

    # Limit number of properties
    python scripts/scrape_arkansas.py --limit 100
"""

import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.scrapers.arkansas_cosl import ArkansasCOSLScraper, scrape_arkansas_properties
from config.logging_config import get_logger

logger = get_logger(__name__)


async def import_to_database(properties_df, dry_run: bool = False):
    """
    Import scraped properties to the database.

    Args:
        properties_df: DataFrame with property data
        dry_run: If True, don't actually insert, just report what would happen
    """
    if properties_df.empty:
        logger.warning("No properties to import")
        return 0

    from backend_api.database.connection import SessionLocal
    from backend_api.database.models import Property
    import uuid

    db = SessionLocal()
    imported = 0
    skipped = 0

    try:
        for _, row in properties_df.iterrows():
            # Check if property already exists (by parcel_id + state)
            existing = db.query(Property).filter(
                Property.parcel_id == row['parcel_id'],
                Property.state == 'AR'
            ).first()

            if existing:
                skipped += 1
                continue

            if dry_run:
                logger.info(f"Would import: {row['parcel_id']} - {row['county']} - ${row['amount']:.2f}")
                imported += 1
                continue

            # Create new property
            prop = Property(
                id=str(uuid.uuid4()),
                parcel_id=row['parcel_id'],
                county=row['county'],
                owner_name=row.get('owner_name'),
                acreage=row.get('acreage'),
                amount=row['amount'],
                description=row.get('description'),
                price_per_acre=row.get('price_per_acre'),
                state='AR',
                sale_type='tax_deed',
                redemption_period_days=0,
                time_to_ownership_days=1,
                data_source='arkansas_cosl',
                auction_platform='COSL Website',
                year_sold=str(datetime.now().year),
                status='new',
            )

            db.add(prop)
            imported += 1

            # Commit in batches
            if imported % 100 == 0:
                db.commit()
                logger.info(f"Imported {imported} properties...")

        db.commit()
        logger.info(f"Import complete: {imported} imported, {skipped} skipped (already exist)")

    except Exception as e:
        db.rollback()
        logger.error(f"Database import failed: {e}")
        raise
    finally:
        db.close()

    return imported


async def main():
    parser = argparse.ArgumentParser(description="Scrape Arkansas COSL tax deed properties")
    parser.add_argument("--county", help="Filter by county name (e.g., 'Pulaski')")
    parser.add_argument("--output", help="Output CSV file path")
    parser.add_argument("--limit", type=int, help="Limit number of properties to scrape")
    parser.add_argument("--import-db", action="store_true", help="Import to database")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be imported without actually importing")
    parser.add_argument("--no-save-raw", action="store_true", help="Don't save raw CSV")

    args = parser.parse_args()

    logger.info("Starting Arkansas COSL scraper...")

    # Calculate max pages based on limit
    max_pages = 100
    if args.limit:
        # Each page has 500 properties
        max_pages = (args.limit // 500) + 1

    async with ArkansasCOSLScraper() as scraper:
        df = await scraper.scrape_to_dataframe(
            county_filter=args.county,
            save_raw=not args.no_save_raw
        )

    if args.limit and len(df) > args.limit:
        df = df.head(args.limit)

    if df.empty:
        logger.warning("No properties found")
        return

    # Print summary
    print(f"\n{'='*60}")
    print(f"Arkansas COSL Scrape Results")
    print(f"{'='*60}")
    print(f"Total properties: {len(df)}")
    print(f"\nCounty distribution (top 10):")
    print(df['county'].value_counts().head(10).to_string())
    print(f"\nPrice statistics:")
    print(f"  Min: ${df['amount'].min():.2f}")
    print(f"  Max: ${df['amount'].max():.2f}")
    print(f"  Mean: ${df['amount'].mean():.2f}")
    print(f"  Median: ${df['amount'].median():.2f}")
    print(f"\nAcreage statistics:")
    print(f"  Min: {df['acreage'].min():.2f}")
    print(f"  Max: {df['acreage'].max():.2f}")
    print(f"  Mean: {df['acreage'].mean():.2f}")

    # Save to custom output if specified
    if args.output:
        df.to_csv(args.output, index=False)
        print(f"\nSaved to: {args.output}")

    # Import to database if requested
    if args.import_db or args.dry_run:
        print(f"\n{'='*60}")
        print("Database Import")
        print(f"{'='*60}")
        imported = await import_to_database(df, dry_run=args.dry_run)
        if args.dry_run:
            print(f"Dry run: would import {imported} properties")
        else:
            print(f"Imported {imported} properties to database")


if __name__ == "__main__":
    asyncio.run(main())
