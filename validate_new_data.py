#!/usr/bin/env python3
"""
Validate the new CSV data before import
"""
import pandas as pd
import sys

def main():
    # Read the CSV file
    try:
        df = pd.read_csv('data/processed/watchlist.csv', dtype={'year_sold': str, 'parcel_id': str})
        print(f'[OK] CSV loaded successfully: {len(df)} records')

        # Check columns
        expected_cols = ['rank', 'parcel_id', 'county', 'amount', 'acreage', 'price_per_acre',
                        'estimated_all_in_cost', 'water_score', 'investment_score', 'assessed_value',
                        'description', 'owner_name', 'year_sold']

        missing_cols = [col for col in expected_cols if col not in df.columns]
        if missing_cols:
            print(f'[ERROR] Missing columns: {missing_cols}')
            return False
        else:
            print('[OK] All expected columns present')

        # Check data quality
        print(f'[OK] Counties: {df["county"].nunique()} unique counties')
        print(f'[OK] Investment scores: min={df["investment_score"].min()}, max={df["investment_score"].max()}')
        print(f'[OK] Price range: ${df["amount"].min():.2f} - ${df["amount"].max():.2f}')

        # Check for duplicates
        duplicates = df['parcel_id'].duplicated().sum()
        print(f'[OK] Duplicate parcel IDs: {duplicates}')

        # Sample of counties
        counties_sample = list(df["county"].unique()[:5])
        print(f'[OK] Sample counties: {counties_sample}')

        print('')
        print('[SUCCESS] Data validation passed! Ready for import.')
        return True

    except Exception as e:
        print(f'[ERROR] Error validating CSV: {e}')
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)