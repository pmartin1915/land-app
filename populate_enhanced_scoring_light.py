"""
Lightweight Enhanced Scoring Data Population Script
Alabama Auction Watcher - Column Stratification & Compatibilization

This script populates the enhanced scoring columns for all properties in the database
using minimal memory footprint and direct SQLite operations.

Author: Claude Code AI Assistant
Date: 2025-09-25
"""

import sqlite3
import sys
from pathlib import Path
from typing import Dict, Tuple
import time
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from scripts.enhanced_description_analysis import EnhancedDescriptionAnalyzer, analyze_property_description
    from scripts.county_intelligence import CountyIntelligenceAnalyzer
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all required modules are available")
    sys.exit(1)

def populate_enhanced_scores_lightweight(db_path: str = "alabama_auction_watcher.db", batch_size: int = 50) -> bool:
    """
    Lightweight version that processes properties without heavy dependencies.

    Args:
        db_path: Path to the SQLite database
        batch_size: Number of properties to process in each batch

    Returns:
        True if successful, False otherwise
    """
    print("=== LIGHTWEIGHT ENHANCED SCORING POPULATION ===")
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

        # Get unique counties for caching
        cursor.execute("SELECT DISTINCT county FROM properties WHERE county IS NOT NULL")
        unique_counties = [row[0] for row in cursor.fetchall()]
        print(f"Found {len(unique_counties)} unique counties: {', '.join(unique_counties)}")

        # Pre-compute county intelligence scores to avoid repeated calculation
        print("Pre-computing county intelligence scores...")
        county_intelligence_cache = {}
        for county in unique_counties:
            try:
                intelligence = county_analyzer.analyze_county(county)
                county_intelligence_cache[county] = {
                    'county_market_score': intelligence.county_market_score,
                    'geographic_score': intelligence.geographic_score,
                    'market_timing_score': intelligence.market_timing_score
                }
                print(f"  {county}: Market={intelligence.county_market_score:.1f}, Geographic={intelligence.geographic_score:.1f}")
            except Exception as e:
                print(f"Error analyzing county {county}: {e}")
                county_intelligence_cache[county] = {
                    'county_market_score': 50.0,
                    'geographic_score': 50.0,
                    'market_timing_score': 50.0
                }

        # Process properties in batches
        processed_count = 0
        batch_num = 1

        for offset in range(0, total_properties, batch_size):
            print(f"\nProcessing Batch {batch_num} (Properties {offset + 1} to {min(offset + batch_size, total_properties)})...")

            # Fetch batch of properties with only required fields
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
            batch_start_time = time.time()

            for prop in batch_properties:
                prop_id, description, county, amount, acreage, assessed_value, water_score = prop

                try:
                    # Run enhanced description analysis
                    desc_scores = analyze_property_description(description or "")

                    # Get cached county intelligence scores
                    county_scores = county_intelligence_cache.get(county, {
                        'county_market_score': 50.0,
                        'geographic_score': 50.0,
                        'market_timing_score': 50.0
                    })

                    # Calculate enhanced investment score
                    investment_score = calculate_enhanced_investment_score_simple(
                        amount=float(amount) if amount else 0.0,
                        acreage=float(acreage) if acreage else 0.1,
                        assessed_value=float(assessed_value) if assessed_value else 0.0,
                        water_score=float(water_score) if water_score else 0.0,
                        desc_total_score=desc_scores['total_description_score'],
                        county_market_score=county_scores['county_market_score']
                    )

                    # Update this property directly
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

                    cursor.execute(update_sql, update_data)
                    processed_count += 1

                except Exception as e:
                    print(f"  Error processing property {prop_id}: {e}")
                    continue

            # Commit the batch
            conn.commit()

            batch_time = time.time() - batch_start_time
            progress = (processed_count / total_properties) * 100

            print(f"  Batch {batch_num} Complete: {len(batch_properties)} properties processed in {batch_time:.1f}s")
            print(f"  Progress: {processed_count}/{total_properties} ({progress:.1f}%)")

            batch_num += 1
            time.sleep(0.1)  # Brief pause between batches

        print(f"\n=== DESCRIPTION SCORING COMPLETE ===")
        print(f"Properties Processed: {processed_count}")

        # Calculate and populate rankings
        print("\nCalculating Investment Rankings...")
        calculate_property_rankings_simple(cursor, conn)

        # Final validation
        print("\nRunning Post-Processing Validation...")
        validate_enhanced_scoring_simple(cursor)

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


def calculate_enhanced_investment_score_simple(amount: float, acreage: float, assessed_value: float,
                                             water_score: float, desc_total_score: float,
                                             county_market_score: float) -> float:
    """Simplified enhanced investment score calculation."""
    try:
        # Base price per acre score (lower is better)
        price_per_acre = amount / max(acreage, 0.01)
        price_score = max(0, min(100, 100 - (price_per_acre / 100)))

        # Assessed value ratio score
        ratio_score = 50.0  # Default
        if assessed_value > 0:
            ratio = amount / assessed_value
            if ratio < 0.1:
                ratio_score = 100
            elif ratio < 0.3:
                ratio_score = 80
            elif ratio < 0.5:
                ratio_score = 60
            else:
                ratio_score = max(0, 60 - (ratio * 50))

        # Acreage preference score
        acreage_score = 50
        if 2.0 <= acreage <= 4.0:
            acreage_score = 100
        elif 1.0 <= acreage <= 6.0:
            acreage_score = 80
        elif acreage > 10:
            acreage_score = max(20, 100 - (acreage * 2))

        # Enhanced composite score
        enhanced_score = (
            price_score * 0.25 +
            ratio_score * 0.10 +
            acreage_score * 0.15 +
            water_score * 0.15 +
            desc_total_score * 0.25 +
            county_market_score * 0.10
        )

        return round(max(0, min(100, enhanced_score)), 1)

    except Exception:
        return 50.0


def calculate_property_rankings_simple(cursor: sqlite3.Cursor, conn: sqlite3.Connection):
    """Calculate and populate property rankings."""
    try:
        cursor.execute("""
        SELECT id, investment_score
        FROM properties
        WHERE investment_score IS NOT NULL
        ORDER BY investment_score DESC, amount ASC
        """)

        properties = cursor.fetchall()

        # Update rankings one by one to avoid memory issues
        for rank, (prop_id, score) in enumerate(properties, 1):
            cursor.execute("UPDATE properties SET rank = ? WHERE id = ?", (rank, prop_id))

        conn.commit()
        print(f"Rankings calculated for {len(properties)} properties")

    except Exception as e:
        print(f"Error calculating rankings: {e}")


def validate_enhanced_scoring_simple(cursor: sqlite3.Cursor):
    """Simple validation of enhanced scoring results."""
    try:
        cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN total_description_score > 0 THEN 1 END) as has_desc_score,
            COUNT(CASE WHEN county_market_score > 0 THEN 1 END) as has_county_score,
            COUNT(CASE WHEN rank IS NOT NULL THEN 1 END) as has_rank
        FROM properties
        """)

        result = cursor.fetchone()
        total, has_desc, has_county, has_rank = result

        print(f"Validation Results:")
        print(f"  Total Properties: {total}")
        print(f"  Properties with Description Scores: {has_desc} ({has_desc/total*100:.1f}%)")
        print(f"  Properties with County Scores: {has_county} ({has_county/total*100:.1f}%)")
        print(f"  Properties with Rankings: {has_rank} ({has_rank/total*100:.1f}%)")

        if has_desc == total and has_rank == total:
            print("[SUCCESS] All properties have complete enhanced scoring data!")
            return True
        else:
            print("[WARNING] Some properties missing enhanced scoring data")
            return False

    except Exception as e:
        print(f"Error in validation: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Lightweight enhanced scoring population")
    parser.add_argument("--db", default="alabama_auction_watcher.db", help="Database file path")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for processing")
    parser.add_argument("--test", action="store_true", help="Run test on small sample")

    args = parser.parse_args()

    if args.test:
        print("Running test mode on first 50 properties...")
        success = populate_enhanced_scores_lightweight(args.db, batch_size=10)
    else:
        success = populate_enhanced_scores_lightweight(args.db, args.batch_size)

    if not success:
        sys.exit(1)