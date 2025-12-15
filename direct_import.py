#!/usr/bin/env python3
"""
Direct database import script to bypass validation issues
"""
import pandas as pd
import sqlite3
import sys
from pathlib import Path
import uuid
from datetime import datetime

def main():
    """Import CSV data directly into SQLite database."""

    print("[INFO] Starting direct database import...")

    # Read the CSV file
    try:
        df = pd.read_csv('data/processed/watchlist.csv', dtype={'year_sold': str, 'parcel_id': str})
        print(f"[OK] Loaded {len(df)} records from CSV")
    except Exception as e:
        print(f"[ERROR] Failed to read CSV: {e}")
        return False

    # Connect to SQLite database
    try:
        conn = sqlite3.connect('alabama_auction_watcher.db')
        cursor = conn.cursor()
        print("[OK] Connected to database")
    except Exception as e:
        print(f"[ERROR] Failed to connect to database: {e}")
        return False

    # Check current count
    try:
        cursor.execute("SELECT COUNT(*) FROM properties")
        current_count = cursor.fetchone()[0]
        print(f"[OK] Current database has {current_count} properties")
    except Exception as e:
        print(f"[WARNING] Could not get current count: {e}")
        current_count = 0

    try:
        # Process each row for import
        imported_count = 0
        duplicate_count = 0

        for idx, row in df.iterrows():
            # Check if parcel_id already exists
            cursor.execute("SELECT id FROM properties WHERE parcel_id = ?", (row['parcel_id'],))
            if cursor.fetchone() is not None:
                duplicate_count += 1
                continue

            # Generate UUID for new property
            property_id = str(uuid.uuid4())
            current_time = datetime.utcnow()

            # Insert new property
            cursor.execute("""
                INSERT INTO properties (
                    id, parcel_id, amount, acreage, price_per_acre, water_score,
                    investment_score, estimated_all_in_cost, assessed_value,
                    description, county, owner_name, year_sold, created_at,
                    updated_at, device_id, sync_timestamp, is_deleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                property_id,
                row['parcel_id'],
                row['amount'],
                row.get('acreage', 0.0),
                row.get('price_per_acre', 0.0),
                row.get('water_score', 0.0),
                row.get('investment_score', 0.0),
                row.get('estimated_all_in_cost', 0.0),
                row.get('assessed_value', 0.0),
                row.get('description', ''),
                row.get('county', ''),
                row.get('owner_name', ''),
                row.get('year_sold', ''),
                current_time,
                current_time,
                'data_importer_v2',
                current_time,
                False
            ))

            imported_count += 1

            if imported_count % 100 == 0:
                print(f"[PROGRESS] Imported {imported_count} properties...")

        # Commit the transaction
        conn.commit()

        # Final count check
        cursor.execute("SELECT COUNT(*) FROM properties")
        final_count = cursor.fetchone()[0]

        print(f"\n[SUCCESS] Import completed!")
        print(f"[INFO] Records processed: {len(df)}")
        print(f"[INFO] Records imported: {imported_count}")
        print(f"[INFO] Duplicates skipped: {duplicate_count}")
        print(f"[INFO] Database count: {current_count} -> {final_count}")

        return True

    except Exception as e:
        print(f"[ERROR] Import failed: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)