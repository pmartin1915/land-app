"""
Scrape the remaining 14 Alabama counties with confirmed available data.

This script uses the proven direct Python import approach (not subprocess)
to scrape counties that timed out or were not completed in the previous batch.

Counties: Hale, Lamar, Lawrence, Limestone, Lowndes, Macon, Marengo, Perry,
          Pike, Russell, Saint Clair, Sumter, Talladega, Tallapoosa
"""

import sys
sys.path.insert(0, 'c:/auction')

from scripts.scraper import scrape_county_data
from scripts.parser import AuctionParser
import time
import sqlite3
from datetime import datetime

# Exactly 14 remaining counties with confirmed available data
counties_to_scrape = [
    'Hale',
    'Lamar',
    'Lawrence',
    'Limestone',
    'Lowndes',
    'Macon',
    'Marengo',
    'Perry',
    'Pike',
    'Russell',
    'Saint Clair',
    'Sumter',
    'Talladega',
    'Tallapoosa'
]

def get_db_status(label):
    """Get current database property count."""
    try:
        conn = sqlite3.connect('c:/auction/alabama_auction_watcher.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM properties')
        count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(DISTINCT county) FROM properties')
        county_count = cursor.fetchone()[0]
        conn.close()
        return count, county_count
    except Exception as e:
        print(f"  [WARNING] Could not query database: {e}")
        return None, None

def main():
    """Main scraping loop for 14 remaining counties."""

    print(f"\n{'='*70}")
    print(f"ALABAMA AUCTION WATCHER - SCRAPING REMAINING 14 COUNTIES")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('='*70)

    # Check initial database state
    initial_count, initial_counties = get_db_status("Initial")
    if initial_count is not None:
        print(f"\nDatabase Status BEFORE scraping:")
        print(f"  Properties: {initial_count:,}")
        print(f"  Counties: {initial_counties}")
    else:
        print(f"\nWarning: Could not verify initial database state")
        initial_count = 0

    print(f"\nCounties to scrape: {len(counties_to_scrape)}")
    print(f"  {', '.join(counties_to_scrape[:7])}")
    print(f"  {', '.join(counties_to_scrape[7:])}")

    # Initialize parser
    parser = AuctionParser(infer_acres=True)

    # Track results
    results = {
        'success': [],
        'no_data': [],
        'error': []
    }

    # Scrape each county
    print(f"\n{'='*70}")
    print("SCRAPING IN PROGRESS")
    print('='*70)

    for i, county in enumerate(counties_to_scrape, 1):
        print(f"\n[{i:2d}/{len(counties_to_scrape)}] {county.upper():20s} ", end='', flush=True)

        try:
            # Scrape raw data
            df = scrape_county_data(county, max_pages=10, save_raw=True)

            if df.empty:
                print("NO DATA")
                results['no_data'].append((county, 0))
                continue

            raw_count = len(df)

            # Process through parser pipeline
            processed_df = parser.map_columns(df, county_name=county)
            processed_df = parser.normalize_data(processed_df)
            processed_df = parser.calculate_metrics(processed_df)

            # Save to CSV
            output_path = f'data/processed/{county.lower()}_watchlist.csv'
            parser.export_results(processed_df, output_path)

            final_count = len(processed_df)
            pct_retained = (final_count / raw_count * 100) if raw_count > 0 else 0

            print(f"OK ({raw_count:4d} raw → {final_count:4d} final, {pct_retained:5.1f}%)")
            results['success'].append((county, raw_count, final_count))

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)[:50]}"
            print(f"ERROR - {error_msg}")
            results['error'].append((county, error_msg))
            # Continue to next county instead of crashing

        # Rate limiting between counties (conservative 3 seconds)
        if i < len(counties_to_scrape):
            time.sleep(3)

    # Final summary
    print(f"\n{'='*70}")
    print("SCRAPING COMPLETE - SUMMARY")
    print('='*70)

    print(f"\nResults by Category:")
    print(f"  ✓ Successful: {len(results['success']):2d} counties")
    print(f"  ✗ No data:   {len(results['no_data']):2d} counties")
    print(f"  ✗ Failed:    {len(results['error']):2d} counties")

    # Detailed results
    if results['success']:
        print(f"\n✓ Successfully Scraped ({len(results['success'])} counties):")
        total_raw = 0
        total_final = 0
        for county, raw, final in results['success']:
            print(f"    {county:18s} {raw:5d} raw → {final:5d} final")
            total_raw += raw
            total_final += final
        print(f"    {'─'*40}")
        print(f"    {'Total':18s} {total_raw:5d} raw → {total_final:5d} final")

    if results['no_data']:
        print(f"\n✗ No Data Available ({len(results['no_data'])} counties):")
        for county, _ in results['no_data']:
            print(f"    {county}")

    if results['error']:
        print(f"\n✗ Failed ({len(results['error'])} counties):")
        for county, error in results['error']:
            print(f"    {county}: {error}")

    # Check final database state
    print(f"\n{'='*70}")
    print("DATABASE STATUS")
    print('='*70)

    final_count, final_counties = get_db_status("Final")
    if final_count is not None and initial_count is not None:
        added = final_count - initial_count
        print(f"\nBefore: {initial_count:,} properties ({initial_counties} counties)")
        print(f"After:  {final_count:,} properties ({final_counties} counties)")
        print(f"Added:  {added:,} properties ({final_counties - initial_counties} counties)")

        if added > 0:
            print(f"\n✓ Import successful! Data is now in the database.")
        else:
            print(f"\n⚠ Warning: No properties were added to database.")
            print(f"  Check data/raw/ and data/processed/ directories for scraped files.")
    else:
        print(f"Could not verify final database state")

    # Files created
    print(f"\nFiles Created:")
    print(f"  Raw data:     data/raw/scraped_*_county_*.csv")
    print(f"  Processed:    data/processed/*_watchlist.csv")

    print(f"\n{'='*70}")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('='*70 + "\n")

    return len(results['error']) == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
