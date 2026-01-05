"""
Recalculate Multi-State Scores for All Properties

This script updates buy_hold_score, wholesale_score, effective_cost,
and time_penalty_factor for all properties in the database using
the new multi-state scoring engine.

Usage:
    python scripts/recalculate_scores.py
    python scripts/recalculate_scores.py --state AR
    python scripts/recalculate_scores.py --dry-run
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend_api.database.connection import SessionLocal
from backend_api.database.models import Property
from core.scoring import ScoringEngine, PropertyScoreInput
from config.logging_config import get_logger

logger = get_logger(__name__)


def recalculate_all_scores(
    state_filter: str = None,
    dry_run: bool = False,
    capital_limit: float = 10000.0
):
    """
    Recalculate scores for all properties.

    Args:
        state_filter: Optional state code to filter (e.g., 'AR')
        dry_run: If True, don't commit changes
        capital_limit: Maximum investment budget
    """
    db = SessionLocal()
    engine = ScoringEngine(capital_limit=capital_limit)

    try:
        # Build query
        query = db.query(Property)
        if state_filter:
            query = query.filter(Property.state == state_filter.upper())

        properties = query.all()
        total = len(properties)
        logger.info(f"Processing {total} properties...")

        updated = 0
        skipped = 0

        for i, prop in enumerate(properties):
            # Skip properties without required data
            if not prop.amount or prop.amount <= 0:
                skipped += 1
                continue
            if not prop.acreage or prop.acreage <= 0:
                skipped += 1
                continue

            # Create scoring input
            input_data = PropertyScoreInput(
                state=prop.state or 'AL',
                sale_type=prop.sale_type or 'tax_lien',
                amount=prop.amount,
                acreage=prop.acreage,
                water_score=prop.water_score or 0.0,
                assessed_value=prop.assessed_value,
                estimated_market_value=prop.estimated_market_value,
                year_sold=prop.year_sold,  # For market reject penalty
                county=prop.county  # For Delta region penalty
            )

            # Calculate scores
            result = engine.calculate_scores(input_data)

            # Update property
            prop.buy_hold_score = result.buy_hold_score
            prop.wholesale_score = result.wholesale_score
            prop.effective_cost = result.effective_cost
            prop.time_penalty_factor = result.time_penalty_factor

            # Update market reject and Delta region flags
            prop.is_market_reject = result.is_market_reject
            prop.is_delta_region = result.is_delta_region
            prop.delta_penalty_factor = result.delta_penalty_factor

            # Also update wholesale_spread if market value available
            if result.wholesale_spread is not None:
                prop.wholesale_spread = result.wholesale_spread

            updated += 1

            # Progress logging
            if (i + 1) % 500 == 0:
                logger.info(f"Processed {i + 1}/{total} properties...")

        if dry_run:
            logger.info(f"DRY RUN: Would update {updated} properties, skip {skipped}")
            db.rollback()
        else:
            db.commit()
            logger.info(f"Updated {updated} properties, skipped {skipped}")

        # Print summary statistics
        print_score_summary(db, state_filter)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to recalculate scores: {e}")
        raise
    finally:
        db.close()


def print_score_summary(db, state_filter: str = None):
    """Print summary statistics of scores by state."""
    from sqlalchemy import func

    print("\n" + "=" * 60)
    print("SCORE SUMMARY BY STATE")
    print("=" * 60)

    query = db.query(
        Property.state,
        func.count(Property.id).label('count'),
        func.avg(Property.buy_hold_score).label('avg_bh'),
        func.avg(Property.wholesale_score).label('avg_ws'),
        func.avg(Property.effective_cost).label('avg_cost'),
        func.avg(Property.time_penalty_factor).label('avg_time')
    ).group_by(Property.state)

    if state_filter:
        query = query.filter(Property.state == state_filter.upper())

    results = query.all()

    print(f"{'State':<8} {'Count':>8} {'Avg BH':>10} {'Avg WS':>10} {'Avg Cost':>12} {'Time Mult':>10}")
    print("-" * 60)

    for row in results:
        state = row.state or 'N/A'
        count = row.count
        avg_bh = row.avg_bh or 0
        avg_ws = row.avg_ws or 0
        avg_cost = row.avg_cost or 0
        avg_time = row.avg_time or 0
        print(f"{state:<8} {count:>8} {avg_bh:>10.1f} {avg_ws:>10.1f} ${avg_cost:>11,.0f} {avg_time:>10.3f}")

    # Top properties by buy-hold score
    print("\n" + "=" * 60)
    print("TOP 10 PROPERTIES BY BUY-HOLD SCORE")
    print("=" * 60)

    top_query = db.query(Property).filter(
        Property.buy_hold_score.isnot(None)
    )

    if state_filter:
        top_query = top_query.filter(Property.state == state_filter.upper())

    top_props = top_query.order_by(Property.buy_hold_score.desc()).limit(10).all()

    print(f"{'State':<5} {'County':<15} {'Amount':>10} {'Acres':>8} {'BH Score':>10} {'Eff Cost':>12}")
    print("-" * 60)

    for prop in top_props:
        print(f"{prop.state or 'N/A':<5} {(prop.county or 'N/A')[:15]:<15} "
              f"${prop.amount:>9,.0f} {prop.acreage or 0:>8.2f} "
              f"{prop.buy_hold_score or 0:>10.1f} ${prop.effective_cost or 0:>11,.0f}")


def main():
    parser = argparse.ArgumentParser(
        description="Recalculate multi-state scores for all properties"
    )
    parser.add_argument(
        "--state",
        help="Filter by state code (e.g., 'AR', 'AL')"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without committing"
    )
    parser.add_argument(
        "--capital-limit",
        type=float,
        default=10000.0,
        help="Maximum investment budget (default: $10,000)"
    )

    args = parser.parse_args()

    logger.info("Starting score recalculation...")
    logger.info(f"Capital limit: ${args.capital_limit:,.0f}")

    if args.state:
        logger.info(f"Filtering by state: {args.state}")

    if args.dry_run:
        logger.info("DRY RUN MODE - no changes will be committed")

    recalculate_all_scores(
        state_filter=args.state,
        dry_run=args.dry_run,
        capital_limit=args.capital_limit
    )


if __name__ == "__main__":
    main()
