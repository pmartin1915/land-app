import subprocess
import time
import sys
from datetime import datetime

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

successful = []
failed = []

for i, county in enumerate(counties, 1):
    print(f"\n[{i}/{len(counties)}] Scraping {county} County...")
    print("-" * 70)

    try:
        result = subprocess.run([
            "python", "c:/auction/scripts/parser.py",
            "--scrape-county", county,
            "--max-pages", "10",
            "--infer-acres"
        ], capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            print(f"[OK] Successfully scraped {county}")
            successful.append(county)
        else:
            print(f"[FAIL] Failed to scrape {county}")
            print(f"Error: {result.stderr}")
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
print(f"Failed: {len(failed)}/{len(counties)}")
end_time = datetime.now()
duration = end_time - start_time
print(f"Total time: {duration}")

if failed:
    print(f"\nFailed counties: {', '.join(failed)}")

print("\nRunning validation...")
subprocess.run(["python", "c:/auction/quick_validate.py"])
