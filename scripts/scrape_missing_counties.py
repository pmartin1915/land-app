import sys
sys.path.insert(0, 'c:/auction')
from scripts.scraper import scrape_county_data
from scripts.parser import AuctionParser
import time
import sqlite3

# 21 counties with confirmed available data
counties_to_scrape = [
    'Clarke', 'Conecuh', 'Covington', 'Elmore', 'Escambia', 'Fayette',
    'Franklin', 'Hale', 'Lamar', 'Lawrence', 'Limestone', 'Lowndes',
    'Macon', 'Marengo', 'Perry', 'Pike', 'Russell', 'Saint Clair',
    'Sumter', 'Talladega', 'Tallapoosa'
]

# Check initial database count
conn = sqlite3.connect('c:/auction/alabama_auction_watcher.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM properties')
initial_count = cursor.fetchone()[0]
print(f"Initial database count: {initial_count} properties\n")
conn.close()

# Scrape each county
results = []
parser = AuctionParser(infer_acres=True)

for i, county in enumerate(counties_to_scrape, 1):
    print(f"\n{'='*60}")
    print(f"[{i}/{len(counties_to_scrape)}] Scraping {county} County...")
    print('='*60)

    try:
        # Scrape raw data
        df = scrape_county_data(county, max_pages=10, save_raw=True)

        if df.empty:
            print(f"  No data available for {county}")
            results.append((county, 0, "No data"))
            continue

        raw_count = len(df)
        print(f"  Scraped {raw_count} raw records")

        # Process through parser pipeline (without filters initially)
        processed_df = parser.map_columns(df, county_name=county)
        processed_df = parser.normalize_data(processed_df)
        # Skip filters - just save raw data
        processed_df = parser.calculate_metrics(processed_df)

        # Save to CSV
        output_path = f'data/processed/{county.lower()}_watchlist.csv'
        parser.export_results(processed_df, output_path)

        filtered_count = len(processed_df)
        print(f"  [OK] Success: {raw_count} raw -> {filtered_count} final properties")
        results.append((county, raw_count, "Success"))

    except Exception as e:
        print(f"  [ERROR] {e}")
        results.append((county, 0, f"Error: {str(e)}"))

    # Rate limiting between counties
    if i < len(counties_to_scrape):
        time.sleep(2)

# Final summary
print(f"\n{'='*60}")
print("SCRAPING COMPLETE - SUMMARY")
print('='*60)

successful = [r for r in results if r[2] == "Success"]
failed = [r for r in results if "Error" in r[2]]
no_data = [r for r in results if r[2] == "No data"]

print(f"Successful: {len(successful)} counties")
print(f"No data: {len(no_data)} counties")
print(f"Failed: {len(failed)} counties")
print(f"Total properties scraped: {sum(r[1] for r in results)}")

if successful:
    print(f"\nSuccessful counties:")
    for county, count, _ in successful:
        print(f"  - {county}: {count} properties")

if no_data:
    print(f"\nCounties with no data:")
    for county, _, _ in no_data:
        print(f"  - {county}")

if failed:
    print(f"\nFailed counties:")
    for county, _, msg in failed:
        print(f"  - {county}: {msg}")

# Check final database count
conn = sqlite3.connect('c:/auction/alabama_auction_watcher.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM properties')
final_count = cursor.fetchone()[0]
cursor.execute('SELECT county, COUNT(*) FROM properties GROUP BY county ORDER BY county')
print(f"\n{'='*60}")
print("DATABASE STATUS")
print('='*60)
print(f"Before: {initial_count} properties")
print(f"After: {final_count} properties")
print(f"Added: {final_count - initial_count} properties")
print(f"\nCounties in database: {cursor.execute('SELECT COUNT(DISTINCT county) FROM properties').fetchone()[0]}")
conn.close()
