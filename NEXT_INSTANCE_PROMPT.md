# Prompt for Next Instance - Alabama Auction Watcher

## Session Objective

Your next session should focus on **investment analysis and user experience improvements**. The scraper is proven, reliable, and has successfully added 1,138 properties. Now it's time to help identify the best water properties for investment.

---

## Starting Status

- **Database:** 3,943 properties across 39 Alabama counties
- **Scraper:** HTTP-based, working perfectly (no JavaScript/Playwright needed)
- **Data Quality:** Good baseline, needs improvement on acreage inference
- **Priority:** Investment analysis with water property detection

---

## Your Top 3 Tasks (Do These First)

### Task 1: Water Property Detection & Tagging
Identify all properties with water features:

1. Search all 3,943 property descriptions for water keywords:
   - "lake", "river", "creek", "pond", "water", "waterfront", "canal", "bayou", "inlet", "beach"

2. Create a water_features column in the database (boolean)

3. Tag all existing properties and generate a report:
   - Total water properties found
   - Count by county
   - Average price per acre for water vs non-water

4. Expected output: CSV with top 100 water properties sorted by investment potential

### Task 2: Fix Acreage Data Quality (65% Currently Invalid)
Currently 65% of properties have acreage < 0.01 acres (clearly wrong):

1. Review `scripts/parser.py` - look at:
   - `normalize_data()` function (acreage processing)
   - `calculate_metrics()` function (price_per_acre calculation)

2. Improve acreage extraction from property descriptions:
   - Many descriptions likely contain "X acres" or "X acre parcel"
   - Current regex is too simple
   - Test with 20-30 sample descriptions to see what patterns exist

3. Re-process all 3,943 properties with improved acreage inference

4. Target: Get valid acreage (>0.01 acres) for 80%+ of properties

5. Measure improvement: Before/after report

### Task 3: Create Investment Ranking & Reports
Build an investment scoring algorithm:

1. **Scoring formula:**
   - Base: price_per_acre (lower is better)
   - Bonus: +20% investment_score if water features detected
   - Acreage preference: 1-20 acres (good for individual investors)
   - Optional: County weighting if known

2. **Generate reports:**
   - Top 50-100 water properties by investment score
   - Export CSV with: parcel_id, county, acreage, price/acre, water_features, investment_score, owner, description
   - "Best Deals" list: properties under $500/acre with water features
   - County breakdown: count of water properties, avg price/acre

3. **Dashboard integration:**
   - Add filter: "Water Features Only"
   - Add filter: "Price Per Acre Range" (e.g., $100-$500)
   - Sort by investment_score
   - Show water feature badge/indicator

---

## Secondary Tasks (Do If Time Allows)

4. **Scrape remaining 28 counties** for complete Alabama coverage (currently 39/67)
   - Use proven script pattern from `scripts/scrape_remaining_14_counties.py`
   - Expected: 2,000-5,000+ additional properties
   - Runtime: 1-2 hours

5. **Database optimization:**
   - Add indexes on: county, price_per_acre, investment_score, water_features
   - Run VACUUM to reclaim space

6. **Fix remaining tests** (currently 35 failing)
   - Add tests for water feature detection
   - Add tests for investment ranking algorithm
   - Target: 90%+ passing

---

## Key Files to Reference

- `scripts/parser.py` - Acreage extraction logic (line 410+)
- `scripts/utils.py` - Data normalization
- `alabama_auction_watcher.db` - SQLite database with 3,943 properties
- `data/processed/watchlist.csv` - Latest full dataset
- `direct_import.py` - Import CSV to database
- `NEXT_INSTANCE_NOTES.md` - Technical details from previous session

---

## How to Start

```bash
cd c:/auction

# 1. Check current database
python -c "import sqlite3; conn = sqlite3.connect('alabama_auction_watcher.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*), COUNT(DISTINCT county) FROM properties'); count, counties = cursor.fetchone(); print(f'Properties: {count:,}, Counties: {counties}')"

# 2. Sample some property descriptions to understand acreage patterns
python -c "
import sqlite3
conn = sqlite3.connect('alabama_auction_watcher.db')
cursor = conn.cursor()
cursor.execute('SELECT description FROM properties WHERE acreage < 0.01 LIMIT 20')
for row in cursor.fetchall():
    print(row[0][:100])
"

# 3. Start implementing water feature detection in parser.py
# 4. Re-process properties with improved acreage logic
# 5. Generate investment reports
```

---

## Success Criteria

By the end of your next session:

- [ ] Water properties detected and tagged (200-500 expected)
- [ ] Acreage quality improved: 80%+ of properties have valid (>0.01) acreage
- [ ] Top 100 water properties report generated and saved
- [ ] Dashboard shows water property filters and sorting
- [ ] Investment ranking algorithm implemented and tested
- [ ] User has CSV export with best water properties for personal review
- [ ] (Optional) 28 additional counties scraped for complete coverage

---

## The Big Picture

You're building a property investment discovery tool. After this session:
- Users will be able to find the best water properties in Alabama by investment potential
- The app will rank properties by price per acre, water features, and size
- Data quality will be good enough to make real investment decisions
- Eventually: complete all 67 Alabama counties with 6,000-9,000+ properties

Good luck!
