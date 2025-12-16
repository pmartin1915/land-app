"""
Create Final Dataset

This script connects to the database, filters out properties with invalid
acreage (less than 0.01 acres), and exports the resulting clean dataset
to a CSV file for final analysis.
"""
import sqlite3
import pandas as pd
from pathlib import Path

def main():
    """
    Main function to filter and export the final dataset.
    """
    db_path = 'alabama_auction_watcher.db'
    output_csv_path = Path('final_property_dataset.csv')
    
    print("="*80)
    print("CREATE FINAL DATASET SCRIPT")
    print("="*80)
    
    # Connect to database
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return

    # 1. Load only properties with valid acreage
    print(f"\n1. Loading valid properties from '{db_path}'...")
    query = """
        SELECT *
        FROM properties
        WHERE acreage IS NOT NULL AND acreage >= 0.01
        ORDER BY investment_score DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    print(f"   Found {len(df)} valid properties.")

    # 2. Export to CSV
    print(f"\n2. Exporting clean dataset to '{output_csv_path}'...")
    df.to_csv(output_csv_path, index=False)
    
    print(f"   Export complete.")
    print(f"\n{'='*80}\nFINAL DATASET CREATED SUCCESSFULLY!\n{'='*80}")

if __name__ == '__main__':
    main()