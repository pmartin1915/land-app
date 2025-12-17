# investment_reporter.py

import sqlite3
import pandas as pd
import os
from typing import Optional

# --- Configuration ---
DATABASE_FILE = 'alabama_auction_watcher.db'
REPORTS_DIR = 'reports'

# --- Scoring Logic ---

def calculate_investment_boost(water_score: Optional[float]) -> float:
    """
    Calculates an investment score multiplier based on the water score.
    Maps water_score (2-15) to a boost multiplier (1.15-1.25).
    """
    if not water_score or water_score <= 0:
        return 1.0

    min_score, max_score_cap = 2.0, 15.0
    min_boost, max_boost = 0.15, 0.25

    if water_score >= max_score_cap:
        normalized_score = 1.0
    elif water_score < min_score:
        normalized_score = 0.0
    else:
        normalized_score = (water_score - min_score) / (max_score_cap - min_score)

    boost = min_boost + normalized_score * (max_boost - min_boost)
    return 1.0 + boost

def get_acreage_modifier(acreage: Optional[float]) -> float:
    """Returns a modifier based on acreage, rewarding the 1-20 acre range."""
    if not acreage or acreage <= 0:
        return 0.1  # Heavy penalty for invalid/missing acreage
    if 1 <= acreage <= 20:
        return 1.0  # Ideal range
    if acreage < 1:
        return 0.75 + (0.25 * acreage)
    return max(0.5, 1.0 - (acreage - 20) / 100)

def get_base_score(price_per_acre: Optional[float]) -> float:
    """Returns a base score inversely proportional to price_per_acre."""
    if not price_per_acre or price_per_acre <= 0:
        return 0.0
    return min(100.0, 25000 / price_per_acre)

def calculate_investment_score(row: pd.Series) -> float:
    """Calculates the final investment score for a property given as a pandas Series."""
    base_score = get_base_score(row.get('price_per_acre'))
    acreage_mod = get_acreage_modifier(row.get('acreage'))
    water_mod = calculate_investment_boost(row.get('water_score'))
    investment_score = base_score * acreage_mod * water_mod
    return round(investment_score, 2)

# --- Data Fetching and Processing ---

def get_water_properties_data(db_path: str) -> Optional[pd.DataFrame]:
    """Fetches all properties with water features and their details."""
    print("Connecting to database to fetch water properties...")
    try:
        conn = sqlite3.connect(db_path)
        query = """
        SELECT
            p.parcel_id,
            p.county,
            p.amount,
            p.acreage,
            p.price_per_acre,
            p.water_score,
            SUBSTR(p.description, 1, 100) AS description,
            GROUP_CONCAT(wf.feature_name, ', ') AS water_features
        FROM
            properties p
        LEFT JOIN
            property_water_features wf ON p.id = wf.property_id
        WHERE
            p.water_score IS NOT NULL AND p.water_score > 0
        GROUP BY
            p.id
        ORDER BY
            p.water_score DESC;
        """
        df = pd.read_sql_query(query, conn)
        print(f"Successfully fetched {len(df)} properties with water features.")
        return df
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        if conn:
            conn.close()

def generate_reports(df: pd.DataFrame, output_dir: str):
    """Generates and saves all required CSV reports."""
    if df.empty:
        print("No data to generate reports from.")
        return

    os.makedirs(output_dir, exist_ok=True)

    # --- 1. Top 100 Overall Investment Report ---
    df_top_100 = df.sort_values(by='investment_score', ascending=False).head(100)
    df_top_100_ranked = df_top_100.copy()
    df_top_100_ranked.insert(0, 'rank', range(1, len(df_top_100_ranked) + 1))
    df_top_100_ranked.to_csv(f'{output_dir}/top_100_water_properties.csv', index=False)
    print(f"Generated '{output_dir}/top_100_water_properties.csv'")

    # --- 2. Best Deals Report (< $500/acre) ---
    df_deals = df[df['price_per_acre'] < 500].sort_values('price_per_acre')
    if not df_deals.empty:
        df_deals_ranked = df_deals.copy()
        df_deals_ranked.insert(0, 'rank', range(1, len(df_deals_ranked) + 1))
        df_deals_ranked.to_csv(f'{output_dir}/best_deals_under_500_per_acre.csv', index=False)
        print(f"Generated '{output_dir}/best_deals_under_500_per_acre.csv'")
    else:
        print("No properties found under $500/acre to generate 'best deals' report.")

    # --- 3. Premium Water Properties Report (Score >= 10) ---
    df_premium = df[df['water_score'] >= 10].sort_values('investment_score', ascending=False)
    if not df_premium.empty:
        df_premium_ranked = df_premium.copy()
        df_premium_ranked.insert(0, 'rank', range(1, len(df_premium_ranked) + 1))
        df_premium_ranked.to_csv(f'{output_dir}/premium_water_properties.csv', index=False)
        print(f"Generated '{output_dir}/premium_water_properties.csv'")
    else:
        print("No premium (score >= 10) properties found.")

    # --- 4. County-by-County Breakdown Report ---
    county_summary = df.groupby('county').agg(
        property_count=('parcel_id', 'count'),
        avg_water_score=('water_score', 'mean'),
        avg_investment_score=('investment_score', 'mean'),
        min_price=('amount', 'min'),
        max_price=('amount', 'max')
    ).round(2).sort_values('property_count', ascending=False)
    county_summary.to_csv(f'{output_dir}/county_breakdown.csv')
    print(f"Generated '{output_dir}/county_breakdown.csv'")


if __name__ == '__main__':
    print("=== Alabama Auction Watcher - Investment Report Generator ===\n")

    # Fetch the base data
    water_properties_df = get_water_properties_data(DATABASE_FILE)

    if water_properties_df is not None and not water_properties_df.empty:
        # Calculate the investment score for all fetched properties
        print("\nCalculating investment scores...")
        water_properties_df['investment_score'] = water_properties_df.apply(calculate_investment_score, axis=1)

        # Generate all reports
        print("\nGenerating reports...")
        generate_reports(water_properties_df, REPORTS_DIR)

        print("\n--- Top 10 Properties by Investment Score ---")
        top_10 = water_properties_df.sort_values('investment_score', ascending=False).head(10)
        print(top_10[['parcel_id', 'county', 'amount', 'acreage', 'price_per_acre', 'water_score', 'water_features', 'investment_score']].to_string(index=False))

        print("\n=== Reporting process complete ===")
        print(f"\nReports saved to: {os.path.abspath(REPORTS_DIR)}/")
    else:
        print("No water properties found or database error occurred.")
