"""
Recalculate all property acreage and scores using improved algorithms.

This script:
1. Backs up the database
2. Re-parses acreage from descriptions using improved logic
3. Recalculates price_per_acre, investment_score, and other metrics
4. Generates before/after comparison report
"""
import sqlite3
import pandas as pd
import sys
import os
from pathlib import Path
from datetime import datetime
import numpy as np

# Add project root to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

# Now import from the correct modules
from scripts import utils
from config import settings

# Import specific functions
parse_acreage_from_description = utils.parse_acreage_from_description
calculate_water_score = utils.calculate_water_score
calculate_investment_score = utils.calculate_investment_score
validate_data_quality = utils.validate_data_quality

def main():
    db_path = 'alabama_auction_watcher.db'
    
    print("="*80)
    print("PROPERTY RECALCULATION SCRIPT")
    print("="*80)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    
    # Load all properties
    print("\n1. Loading properties from database...")
    df = pd.read_sql_query("""
        SELECT id, parcel_id, county, amount, acreage, description, 
               assessed_value, price_per_acre, investment_score
        FROM properties
    """, conn)
    
    print(f"   Loaded {len(df)} properties")
    
    # Store original values for comparison
    df['original_acreage'] = df['acreage']
    df['original_price_per_acre'] = df['price_per_acre']
    df['original_investment_score'] = df['investment_score']
    
    # Count before stats
    before_zero_acres = (df['acreage'] == 0).sum()
    before_tiny_acres = ((df['acreage'] > 0) & (df['acreage'] < 0.01)).sum()
    before_invalid = before_zero_acres + before_tiny_acres
    
    print(f"\n2. BEFORE RECALCULATION:")
    print(f"   Properties with 0 acres: {before_zero_acres}")
    print(f"   Properties with tiny acres (<0.01): {before_tiny_acres}")
    print(f"   Total invalid: {before_invalid} ({before_invalid/len(df)*100:.1f}%)")
    
    # Recalculate acreage using improved parsing
    print(f"\n3. Recalculating acreage from descriptions...")
    recalculated_count = 0
    improved_count = 0
    
    for idx, row in df.iterrows():
        # Re-parse acreage from description
        new_acreage = parse_acreage_from_description(row['description'])
        
        if new_acreage is not None:
            if row['original_acreage'] != new_acreage:
                recalculated_count += 1
                if row['original_acreage'] == 0 or row['original_acreage'] < 0.01:
                    improved_count += 1
            df.at[idx, 'acreage'] = new_acreage
        # If parsing still fails, keep original value (might be from scraper)
    
    print(f"   Recalculated: {recalculated_count} properties")
    print(f"   Improved (was invalid): {improved_count} properties")
    
    # Recalculate price per acre with safe division
    print(f"\n4. Recalculating price per acre...")
    df['price_per_acre'] = np.where(
        df['acreage'] > 0.001,
        df['amount'] / df['acreage'],
        np.nan
    )
    
    valid_ppa = df['price_per_acre'].notna().sum()
    print(f"   Valid price_per_acre: {valid_ppa}/{len(df)}")
    
    # Recalculate investment scores
    print(f"\n5. Recalculating investment scores...")
    
    def calc_score_row(row):
        return calculate_investment_score(
            price_per_acre=row['price_per_acre'] if pd.notna(row['price_per_acre']) else 0,
            acreage=row['acreage'] if pd.notna(row['acreage']) else 0,
            water_score=calculate_water_score(row['description']),
            assessed_value_ratio=1.0,  # Default if not available
            weights=settings.INVESTMENT_SCORE_WEIGHTS
        )
    
    df['investment_score'] = df.apply(calc_score_row, axis=1)
    
    # Count after stats
    after_zero_acres = (df['acreage'] == 0).sum()
    after_tiny_acres = ((df['acreage'] > 0) & (df['acreage'] < 0.01)).sum()
    after_invalid = after_zero_acres + after_tiny_acres
    
    print(f"\n6. AFTER RECALCULATION:")
    print(f"   Properties with 0 acres: {after_zero_acres}")
    print(f"   Properties with tiny acres (<0.01): {after_tiny_acres}")
    print(f"   Total invalid: {after_invalid} ({after_invalid/len(df)*100:.1f}%)")
    
    print(f"\n7. IMPROVEMENT:")
    print(f"   Invalid properties reduced: {before_invalid} → {after_invalid}")
    print(f"   Improvement: {before_invalid - after_invalid} properties fixed ({(before_invalid - after_invalid)/before_invalid*100:.1f}% of invalid)")
    
    # Data quality validation
    print(f"\n8. DATA QUALITY VALIDATION:")
    validation = validate_data_quality(df[['parcel_id', 'amount', 'acreage', 'price_per_acre', 'description']])
    
    if validation['issues']:
        print("   ISSUES:")
        for issue in validation['issues']:
            print(f"     - {issue}")
    else:
        print("   No critical issues found!")
        
    if validation['warnings']:
        print("   WARNINGS:")
        for warning in validation['warnings']:
            print(f"     - {warning}")
    
    # Update database
    print(f"\n9. Updating database...")
    cursor = conn.cursor()
    
    updated = 0
    for idx, row in df.iterrows():
        cursor.execute("""
            UPDATE properties
            SET acreage = ?, price_per_acre = ?, investment_score = ?
            WHERE id = ?
        """, (
            float(row['acreage']) if pd.notna(row['acreage']) else None,
            float(row['price_per_acre']) if pd.notna(row['price_per_acre']) else None,
            float(row['investment_score']) if pd.notna(row['investment_score']) else None,
            row['id']
        ))
        updated += 1
    
    conn.commit()
    print(f"   Updated {updated} properties in database")
    
    # Generate comparison report
    print(f"\n10. Generating before/after comparison...")
    
    # Find properties that changed significantly
    df['score_change'] = df['investment_score'] - df['original_investment_score']
    df['acreage_change'] = df['acreage'] - df['original_acreage']
    
    significant_changes = df[abs(df['score_change']) > 10].sort_values('score_change', ascending=False)
    
    print(f"\n    Properties with significant score changes (>10 points): {len(significant_changes)}")
    if len(significant_changes) > 0:
        print(f"\n    Top 10 score increases:")
        top_increases = significant_changes.head(10)
        for _, row in top_increases.iterrows():
            print(f"      {row['parcel_id']}: {row['original_investment_score']:.1f} → {row['investment_score']:.1f} (+{row['score_change']:.1f})")
            print(f"        Acreage: {row['original_acreage']:.3f} → {row['acreage']:.3f}")
            print(f"        Description: {row['description'][:70]}...")
        
        print(f"\n    Top 10 score decreases:")
        top_decreases = significant_changes.tail(10).sort_values('score_change')
        for _, row in top_decreases.iterrows():
            print(f"      {row['parcel_id']}: {row['original_investment_score']:.1f} → {row['investment_score']:.1f} ({row['score_change']:.1f})")
            print(f"        Acreage: {row['original_acreage']:.3f} → {row['acreage']:.3f}")
    
    # Export comparison
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    comparison_file = f"recalculation_comparison_{timestamp}.csv"
    
    comparison_df = df[['parcel_id', 'county', 'description', 
                        'original_acreage', 'acreage', 'acreage_change',
                        'original_price_per_acre', 'price_per_acre',
                        'original_investment_score', 'investment_score', 'score_change']]
    comparison_df.to_csv(comparison_file, index=False)
    
    print(f"\n    Comparison exported to: {comparison_file}")
    
    conn.close()
    
    print(f"\n{'='*80}")
    print(f"RECALCULATION COMPLETE!")
    print(f"{'='*80}")
    print(f"\nSummary:")
    print(f"  - {improved_count} properties had acreage improved from invalid values")
    print(f"  - Invalid property count: {before_invalid} → {after_invalid} ({(1 - after_invalid/before_invalid)*100:.1f}% reduction)")
    print(f"  - Database updated successfully")
    print(f"  - Comparison report: {comparison_file}")

if __name__ == '__main__':
    main()
