# County Scraping Task - Alabama Auction Watcher

## Objective
Scrape property data from all remaining Alabama counties that are not yet in the database.

## Current Database Status
- **18 counties** already scraped with data
- **49 counties** remaining to scrape
- **Total**: 67 Alabama counties

## Counties Already in Database (DO NOT RE-SCRAPE)
1. Autauga (1232 properties)
2. Cherokee (325 properties)
3. Barbour (172 properties)
4. Mobile (126 properties)
5. Baldwin (89 properties)
6. Madison (42 properties)
7. Morgan (21 properties)
8. Jefferson (16 properties)
9. DeKalb (8 properties)
10. Cullman (4 properties)
11. Coosa (3 properties)
12. Randolph (3 properties)
13. Tuscaloosa (3 properties)
14. Blount (2 properties)
15. Calhoun (2 properties)
16. Shelby (2 properties)
17. Walker (2 properties)
18. Butler (1 properties)

## Counties to Scrape (49 remaining)
Bibb, Bullock, Chambers, Chilton, Choctaw, Clarke, Clay, Cleburne, Coffee, Colbert, Conecuh, Covington, Crenshaw, Dale, Dallas, Elmore, Escambia, Etowah, Fayette, Franklin, Geneva, Greene, Hale, Henry, Houston, Jackson, Lamar, Lauderdale, Lawrence, Lee, Limestone, Lowndes, Macon, Marengo, Marion, Marshall, Monroe, Montgomery, Perry, Pickens, Pike, Russell, Saint Clair, Sumter, Talladega, Tallapoosa, Washington, Wilcox, Winston

## Scraping Command
```bash
python c:/auction/scripts/parser.py --scrape-county "<COUNTY_NAME>" --max-pages 10 --infer-acres
```

## Execution Strategy

### Option A: Sequential (Safe, Slower)
Run one county at a time:
```bash
python c:/auction/scripts/parser.py --scrape-county Bibb --max-pages 10 --infer-acres
python c:/auction/scripts/parser.py --scrape-county Bullock --max-pages 10 --infer-acres
# ... continue for each county
```

### Option B: Batch Script
Create and run a batch script:
```bash
# Create scrape_all.py
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

import subprocess
import time

for county in counties:
    print(f"\n{'='*60}")
    print(f"Scraping {county} County...")
    print('='*60)

    result = subprocess.run([
        "python", "c:/auction/scripts/parser.py",
        "--scrape-county", county,
        "--max-pages", "10",
        "--infer-acres"
    ], capture_output=False)

    # Rate limiting - be respectful to the server
    time.sleep(5)

print("\nScraping complete!")
```

## Important Notes

1. **Rate Limiting**: Add 5 second delays between counties to avoid overwhelming the server
2. **Max Pages**: Use `--max-pages 10` for initial scrape (can adjust if needed)
3. **Infer Acres**: Always use `--infer-acres` to extract acreage from descriptions
4. **Error Handling**: Some counties may have no data - this is normal
5. **Database**: Data automatically saves to `alabama_auction_watcher.db`

## Verification After Scraping
```bash
python c:/auction/quick_validate.py
```

## Expected Output Per County
```
Scraping data for <County> County (code: XX)...
Successfully scraped N records
Mapping columns to standard field names...
Normalizing data...
Applying filters...
Final filtered dataset: N records
Calculating investment metrics...
Exporting results to: data/processed/watchlist.csv
```

## Working Directory
```
c:\auction
```

## Files Modified by Scraping
- `alabama_auction_watcher.db` - SQLite database with all properties
- `data/raw/scraped_<county>_<timestamp>.csv` - Raw scraped data
- `data/processed/watchlist.csv` - Latest processed watchlist
