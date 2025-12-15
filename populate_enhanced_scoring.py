"""
Enhanced Scoring Data Population Script
Alabama Auction Watcher - Column Stratification & Compatibilization

This script populates the enhanced scoring columns for all properties in the database
by running the sophisticated property intelligence analysis.

Author: Claude Code AI Assistant
Date: 2025-09-25
"""

import sqlite3
import sys
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
import time
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scripts.enhanced_description_analysis import EnhancedDescriptionAnalyzer, analyze_property_description
from scripts.county_intelligence import CountyIntelligenceAnalyzer
from config.settings import INVESTMENT_SCORE_WEIGHTS

def batch_process_properties(db_path: str = "alabama_auction_watcher.db", batch_size: int = 100) -> bool:
    """
    Process all properties in batches to populate enhanced scoring data.

    Args:
        db_path: Path to the SQLite database
        batch_size: Number of properties to process in each batch

    Returns:
        True if successful, False otherwise
    """
    print("=== ENHANCED PROPERTY SCORING POPULATION ===")
    print(f"Database: {db_path}")
    print(f"Batch Size: {batch_size}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get total property count
        cursor.execute("SELECT COUNT(*) FROM properties")
        total_properties = cursor.fetchone()[0]
        print(f"Total Properties to Process: {total_properties}")

        if total_properties == 0:
            print("No properties found in database!")
            return False

        # Initialize analyzers
        print("Initializing Enhanced Description Analyzer...")
        desc_analyzer = EnhancedDescriptionAnalyzer()

        print("Initializing County Intelligence Analyzer...")
        county_analyzer = CountyIntelligenceAnalyzer()

        # Process properties in batches
        processed_count = 0
        batch_num = 1

        for offset in range(0, total_properties, batch_size):
            print(f"\nProcessing Batch {batch_num} (Properties {offset + 1} to {min(offset + batch_size, total_properties)})...")

            # Fetch batch of properties
            query = """
            SELECT id, description, county, amount, acreage, assessed_value, water_score
            FROM properties
            ORDER BY id
            LIMIT ? OFFSET ?
            """

            cursor.execute(query, (batch_size, offset))
            batch_properties = cursor.fetchall()

            if not batch_properties:
                break

            # Process each property in the batch
            batch_updates = []

            for prop in batch_properties:
                prop_id, description, county, amount, acreage, assessed_value, water_score = prop

                try:
                    # Run enhanced description analysis
                    desc_scores = analyze_property_description(description or "")

                    # Run county intelligence analysis
                    county_intelligence = county_analyzer.analyze_county(county)
                    county_scores = {
                        'county_market_score': county_intelligence.county_market_score,
                        'geographic_score': county_intelligence.geographic_score,
                        'market_timing_score': county_intelligence.market_timing_score
                    }

                    # Calculate enhanced investment score
                    investment_score = calculate_enhanced_investment_score(
                        amount=amount,
                        acreage=acreage,
                        assessed_value=assessed_value,
                        water_score=water_score,
                        desc_total_score=desc_scores['total_description_score'],
                        county_market_score=county_scores['county_market_score']
                    )

                    # Prepare update data
                    update_data = (
                        desc_scores['lot_dimensions_score'],
                        desc_scores['shape_efficiency_score'],
                        desc_scores['corner_lot_bonus'],
                        desc_scores['irregular_shape_penalty'],
                        desc_scores['subdivision_quality_score'],
                        desc_scores['road_access_score'],
                        desc_scores['location_type_score'],
                        desc_scores['title_complexity_score'],
                        desc_scores['survey_requirement_score'],
                        desc_scores['premium_water_access_score'],
                        desc_scores['total_description_score'],
                        county_scores['county_market_score'],
                        county_scores['geographic_score'],
                        county_scores['market_timing_score'],
                        investment_score,
                        prop_id
                    )

                    batch_updates.append(update_data)

                except Exception as e:
                    print(f"Error processing property {prop_id}: {e}")
                    continue

            # Execute batch update
            if batch_updates:
                update_sql = """
                UPDATE properties SET
                    lot_dimensions_score = ?,
                    shape_efficiency_score = ?,
                    corner_lot_bonus = ?,
                    irregular_shape_penalty = ?,
                    subdivision_quality_score = ?,
                    road_access_score = ?,
                    location_type_score = ?,
                    title_complexity_score = ?,
                    survey_requirement_score = ?,
                    premium_water_access_score = ?,
                    total_description_score = ?,
                    county_market_score = ?,
                    geographic_score = ?,
                    market_timing_score = ?,
                    investment_score = ?
                WHERE id = ?
                """

                cursor.executemany(update_sql, batch_updates)
                conn.commit()

                processed_count += len(batch_updates)
                progress = (processed_count / total_properties) * 100

                print(f"  Batch {batch_num} Complete: {len(batch_updates)} properties updated")
                print(f"  Progress: {processed_count}/{total_properties} ({progress:.1f}%)")

            batch_num += 1
            time.sleep(0.1)  # Brief pause between batches

        print(f"\n=== DESCRIPTION SCORING COMPLETE ===")
        print(f"Properties Processed: {processed_count}")

        # Calculate and populate rankings
        print("\nCalculating Investment Rankings...")
        calculate_property_rankings(cursor, conn)

        # Final validation
        print("\nRunning Post-Processing Validation...")
        validate_enhanced_scoring(cursor)

        cursor.close()
        conn.close()

        print(f"\n[SUCCESS] Enhanced scoring population completed!")
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return True

    except Exception as e:
        print(f"[ERROR] Enhanced scoring population failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False


def calculate_enhanced_investment_score(amount: float, acreage: float, assessed_value: float,
                                      water_score: float, desc_total_score: float,
                                      county_market_score: float) -> float:
    """
    Calculate enhanced investment score incorporating all intelligence factors.

    Args:
        amount: Property bid amount
        acreage: Property acreage
        assessed_value: Assessed property value
        water_score: Water feature score
        desc_total_score: Total description intelligence score
        county_market_score: County market intelligence score

    Returns:
        Enhanced investment score (0-100)
    """
    try:
        # Base price per acre score (lower is better)
        price_per_acre = amount / max(acreage, 0.01)
        price_score = max(0, min(100, 100 - (price_per_acre / 100)))

        # Assessed value ratio score
        ratio_score = 0
        if assessed_value > 0:
            ratio = amount / assessed_value
            if ratio < 0.1:  # Great deal
                ratio_score = 100
            elif ratio < 0.3:  # Good deal
                ratio_score = 80
            elif ratio < 0.5:  # Fair deal
                ratio_score = 60
            else:  # Expensive
                ratio_score = max(0, 100 - (ratio * 100))

        # Acreage preference score
        acreage_score = 50  # Base score
        if 2.0 <= acreage <= 4.0:  # Preferred range
            acreage_score = 100
        elif 1.0 <= acreage <= 6.0:  # Acceptable range
            acreage_score = 80
        elif acreage > 10:  # Large parcels
            acreage_score = max(20, 100 - (acreage * 2))

        # Enhanced composite score with new intelligence factors
        enhanced_score = (
            price_score * 0.25 +                    # Price per acre weight
            ratio_score * 0.10 +                    # Assessed value ratio weight
            acreage_score * 0.15 +                  # Acreage preference weight
            water_score * 0.15 +                    # Water features weight
            desc_total_score * 0.25 +               # Description intelligence weight
            county_market_score * 0.10              # County market intelligence weight
        )

        return round(max(0, min(100, enhanced_score)), 1)

    except Exception:
        return 50.0  # Default score if calculation fails


def calculate_property_rankings(cursor: sqlite3.Cursor, conn: sqlite3.Connection):
    """Calculate and populate property rankings based on enhanced investment scores."""

    try:
        # Get all properties with their enhanced investment scores
        cursor.execute("""
        SELECT id, investment_score
        FROM properties
        WHERE investment_score IS NOT NULL
        ORDER BY investment_score DESC, amount ASC
        """)

        properties = cursor.fetchall()

        # Calculate rankings
        rankings = []
        for rank, (prop_id, score) in enumerate(properties, 1):
            rankings.append((rank, prop_id))

        # Update rankings in batches
        cursor.executemany("UPDATE properties SET rank = ? WHERE id = ?", rankings)
        conn.commit()

        print(f"Rankings calculated for {len(rankings)} properties")

    except Exception as e:
        print(f"Error calculating rankings: {e}")


def validate_enhanced_scoring(cursor: sqlite3.Cursor):
    """Validate the enhanced scoring results."""

    try:
        # Check completion rates
        cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN lot_dimensions_score > 0 THEN 1 END) as has_lot_score,
            COUNT(CASE WHEN total_description_score > 0 THEN 1 END) as has_desc_score,
            COUNT(CASE WHEN county_market_score > 0 THEN 1 END) as has_county_score,
            COUNT(CASE WHEN rank IS NOT NULL THEN 1 END) as has_rank,
            AVG(total_description_score) as avg_desc_score,
            AVG(investment_score) as avg_investment_score
        FROM properties
        """)

        result = cursor.fetchone()
        total, has_lot, has_desc, has_county, has_rank, avg_desc, avg_inv = result

        print(f"Validation Results:")
        print(f"  Total Properties: {total}")
        print(f"  Properties with Lot Scores: {has_lot} ({has_lot/total*100:.1f}%)")
        print(f"  Properties with Description Scores: {has_desc} ({has_desc/total*100:.1f}%)")
        print(f"  Properties with County Scores: {has_county} ({has_county/total*100:.1f}%)")
        print(f"  Properties with Rankings: {has_rank} ({has_rank/total*100:.1f}%)")
        print(f"  Average Description Score: {avg_desc:.1f}")
        print(f"  Average Investment Score: {avg_inv:.1f}")

        if has_desc == total and has_rank == total:
            print("[SUCCESS] All properties have complete enhanced scoring data!")
        else:
            print("[WARNING] Some properties missing enhanced scoring data")

    except Exception as e:
        print(f"Error in validation: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Populate enhanced scoring data for all properties")
    parser.add_argument("--db", default="alabama_auction_watcher.db", help="Database file path")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for processing")
    parser.add_argument("--test", action="store_true", help="Run test on small sample")

    args = parser.parse_args()

    if args.test:
        print("Running test mode on first 10 properties...")
        success = batch_process_properties(args.db, batch_size=10)
    else:
        success = batch_process_properties(args.db, args.batch_size)

    if not success:
        sys.exit(1)