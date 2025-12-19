import subprocess
import time
import sys
from datetime import datetime
import os

counties = [
    "Bibb", "Bullock", "Chambers", "Chilton", "Choctaw", "Clarke", "Clay",
    "Cleburne", "Coffee", "Colbert", "Conecuh", "Covington", "Crenshaw",
    "Dale", "Dallas", "Elmore", "Escambia", "Etowah", "Fayette", "Franklin",
    "Geneva", "Greene", "Hale", "Henry", "Houston", "Jackson", "Lamar",
    "Lauderdale", "Lawrence", "Lee", "Limestone", "Lowndes", "Macon",
    "Marengo", "Marion", "Marshall", "Monroe", "Montgomery", "Perry",
    "Pickens", "Pike", "Russell", "Saint Clair", "Sumter", "Talladega",
    "Tallapoosa", "Washington", "Wilcox", "Winston"
]

start_time = datetime.now()
print(f"Starting scraping task at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Total counties to scrape: {len(counties)}")
print("=" * 70)

# Ensure data/processed directory exists
os.makedirs("data/processed", exist_ok=True)

successful = []
failed = []
no_data_counties = []

for i, county in enumerate(counties, 1):
    print(f"\n[{i}/{len(counties)}] Scraping {county} County...")
    print("-" * 70)

    # Construct unique output path for processed data
    output_file_path = f"data/processed/{county.lower()}_watchlist.csv"

    try:
        result = subprocess.run([
            "python", "c:/auction/scripts/parser.py",
            "--scrape-county", county,
            "--infer-acres",
            "--output", output_file_path # Pass the unique output path
        ], capture_output=True, text=True, timeout=600)

        # Check for "No data found" message in stdout, which now indicates a non-failure
        if "No data found for" in result.stdout and "Skipping processing" in result.stdout:
            print(f"[NO DATA] No delinquent properties found for {county}")
            no_data_counties.append(county)
        elif result.returncode == 0:
            print(f"[OK] Successfully scraped {county}")
            successful.append(county)
        else:
            print(f"[FAIL] Failed to scrape {county}")
            print(f"Stderr: {result.stderr}")
            print(f"Stdout: {result.stdout}")
            failed.append(county)

    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] Timeout scraping {county}")
        failed.append(county)
    except Exception as e:
        print(f"[ERROR] Error scraping {county}: {str(e)}")
        failed.append(county)

    # Rate limiting
    if i < len(counties):
        time.sleep(5)

# Final summary
print("\n" + "=" * 70)
print("SCRAPING SUMMARY")
print("=" * 70)
print(f"Successful: {len(successful)}/{len(counties)}")
print(f"No Data: {len(no_data_counties)}/{len(counties)}")
print(f"Failed: {len(failed)}/{len(counties)}")
end_time = datetime.now()
duration = end_time - start_time
print(f"Total time: {duration}")

if no_data_counties:
    print(f"\nNo Data counties: {', '.join(no_data_counties)}")
if failed:
    print(f"\nFailed counties: {', '.join(failed)}")