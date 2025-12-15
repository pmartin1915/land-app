"""
Database Migration Script for Enhanced Scoring Fields
Alabama Auction Watcher - Phase 1 Enhancement

This script adds new enhanced description intelligence and county intelligence
fields to the existing properties table.

Author: Claude Code AI Assistant
Date: 2025-09-19
"""

import sqlite3
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def migrate_database(db_path: str = "alabama_auction_watcher.db"):
    """
    Migrate the database to add enhanced scoring fields.

    Args:
        db_path: Path to the SQLite database file
    """

    print(f"=== Database Migration: Enhanced Scoring Fields ===")
    print(f"Database: {db_path}")

    # Check if database exists
    if not os.path.exists(db_path):
        print(f"ERROR: Database file not found: {db_path}")
        return False

    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check current schema
        cursor.execute("PRAGMA table_info(properties)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        print(f"Existing columns: {len(existing_columns)}")

        # Define new columns to add
        new_columns = [
            # Enhanced Description Intelligence Fields
            ("lot_dimensions_score", "REAL DEFAULT 0.0"),
            ("shape_efficiency_score", "REAL DEFAULT 0.0"),
            ("corner_lot_bonus", "REAL DEFAULT 0.0"),
            ("irregular_shape_penalty", "REAL DEFAULT 0.0"),
            ("subdivision_quality_score", "REAL DEFAULT 0.0"),
            ("road_access_score", "REAL DEFAULT 0.0"),
            ("location_type_score", "REAL DEFAULT 0.0"),
            ("title_complexity_score", "REAL DEFAULT 0.0"),
            ("survey_requirement_score", "REAL DEFAULT 0.0"),
            ("premium_water_access_score", "REAL DEFAULT 0.0"),
            ("total_description_score", "REAL DEFAULT 0.0"),

            # County Intelligence Fields (for future use)
            ("county_market_score", "REAL DEFAULT 0.0"),
            ("geographic_score", "REAL DEFAULT 0.0"),
            ("market_timing_score", "REAL DEFAULT 0.0")
        ]

        # Add columns that don't already exist
        columns_added = 0
        for column_name, column_definition in new_columns:
            if column_name not in existing_columns:
                try:
                    sql = f"ALTER TABLE properties ADD COLUMN {column_name} {column_definition}"
                    cursor.execute(sql)
                    print(f"[SUCCESS] Added column: {column_name}")
                    columns_added += 1
                except sqlite3.Error as e:
                    print(f"[ERROR] Failed to add column {column_name}: {e}")
            else:
                print(f"[SKIP] Column already exists: {column_name}")

        # Commit changes
        conn.commit()

        # Verify the migration
        cursor.execute("PRAGMA table_info(properties)")
        final_columns = [column[1] for column in cursor.fetchall()]
        print(f"\nMigration Summary:")
        print(f"  Columns before: {len(existing_columns)}")
        print(f"  Columns added: {columns_added}")
        print(f"  Columns after: {len(final_columns)}")

        # Test the new schema
        cursor.execute("SELECT COUNT(*) FROM properties")
        property_count = cursor.fetchone()[0]
        print(f"  Properties in database: {property_count}")

        # Close connection
        cursor.close()
        conn.close()

        print(f"\n[SUCCESS] Migration completed successfully!")
        return True

    except sqlite3.Error as e:
        print(f"[ERROR] Database migration failed: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error during migration: {e}")
        return False


def rollback_migration(db_path: str = "alabama_auction_watcher.db"):
    """
    Rollback the migration by removing the enhanced scoring columns.

    Note: SQLite doesn't support dropping columns directly, so this would
    require creating a new table and copying data.

    Args:
        db_path: Path to the SQLite database file
    """
    print("[WARNING] Rollback not implemented for SQLite.")
    print("If rollback is needed, restore from backup or recreate database.")


def main():
    """Main migration function."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate database for enhanced scoring")
    parser.add_argument("--db", default="alabama_auction_watcher.db",
                       help="Database file path")
    parser.add_argument("--rollback", action="store_true",
                       help="Rollback the migration")

    args = parser.parse_args()

    if args.rollback:
        rollback_migration(args.db)
    else:
        success = migrate_database(args.db)
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()