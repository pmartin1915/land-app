"""
Fix Zero-Acreage Properties

This script specifically targets properties in the database with zero or null
acreage and attempts to parse a valid acreage from their legal descriptions.
It then recalculates their scores and updates the database.
"""
import sqlite3
import pandas as pd
import sys
import os
from pathlib import Path
import numpy as np

# Add project root to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

# Import necessary functions
from scripts.utils import parse_acreage_from_description, calculate_water_score
from scripts.utils import calculate_investment_score
from config import settings

def main():
    db_path = 'alabama_auction_watcher.db'
    
    print("="*80)
    print("FIX ZERO-ACREAGE PROPERTIES SCRIPT")
    print("="*80)
    
    # Connect to database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return

    # 1. Load only properties with invalid acreage
    print("\n1. Loading properties with zero or null acreage from database...")
    df = pd.read_sql_query("""
        SELECT id, parcel_id, county, amount, acreage, description, assessed_value
        FROM properties
        WHERE acreage IS NULL OR acreage < 0.01
    """, conn)
    
    if df.empty:
        print("   No properties with zero or null acreage found. Nothing to do.")
        conn.close()
        return

    print(f"   Found {len(df)} properties to fix.")

    # 2. Attempt to parse acreage from description
    print("\n2. Parsing descriptions for dimension data...")
    fixed_count = 0
    df['new_acreage'] = None

    for idx, row in df.iterrows():
        parsed_acreage = parse_acreage_from_description(row['description'])
        if parsed_acreage is not None and parsed_acreage > 0:
            df.at[idx, 'new_acreage'] = parsed_acreage
            fixed_count += 1
    
    print(f"   Successfully parsed acreage for {fixed_count} properties.")

    if fixed_count == 0:
        print("   No properties could be fixed. Exiting.")
        conn.close()
        return

    # 3. Recalculate metrics for fixed properties
    print("\n3. Recalculating scores for fixed properties...")
    df_fixed = df[df['new_acreage'].notna()].copy()
    
    # Recalculate price_per_acre
    df_fixed['price_per_acre'] = np.where(
        df_fixed['new_acreage'] > 0.001,
        df_fixed['amount'] / df_fixed['new_acreage'],
        np.nan
    )

    # Recalculate investment_score
    def calc_score_row(row):
        # A simple default for assessed_value_ratio if not available
        ratio = row['amount'] / row['assessed_value'] if row['assessed_value'] and row['assessed_value'] > 0 else 1.0
        return calculate_investment_score(
            price_per_acre=row['price_per_acre'] if pd.notna(row['price_per_acre']) else 0,
            acreage=row['new_acreage'],
            water_score=calculate_water_score(row['description']),
            assessed_value_ratio=ratio,
            weights=settings.INVESTMENT_SCORE_WEIGHTS
        )

    df_fixed['investment_score'] = df_fixed.apply(calc_score_row, axis=1)
    print(f"   Scores recalculated.")

    # 4. Update database
    print("\n4. Updating database...")
    for _, row in df_fixed.iterrows():
        cursor.execute("""
            UPDATE properties
            SET acreage = ?, price_per_acre = ?, investment_score = ?
            WHERE id = ?
        """, (row['new_acreage'], row['price_per_acre'], row['investment_score'], row['id']))
    
    conn.commit()
    conn.close()
    
    print(f"   Updated {len(df_fixed)} properties in the database.")
    print(f"\n{'='*80}\nFIX COMPLETE!\n{'='*80}")

if __name__ == '__main__':
    main()