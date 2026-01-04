# Session Handoff: Arkansas Property Expansion

## Date: January 4, 2025

## Session Summary

This session completed Milestone 3 (multi-state scoring algorithm) and performed detailed due diligence on Arkansas investment opportunities. The key outcome: **the top-scoring property was identified as a trap** (80-year delinquency, flood zone, no market) and should be passed.

---

## Gemini Strategy Input (January 4, 2025)

### Scraping Strategy
- **Use the API directly** - Kendo UI grids are powered by backend JSON APIs
- **Scrape county-by-county** for resilience, logging, and rate limiting
- Look for XHR requests to endpoints like `/Read` or `/GetData` in browser DevTools

### Data Enrichment Priority
**Tier 1 - Essential (Automate):**
- FEMA Flood Zone via API (reject Zone A, AE)
- Federal/State Wetlands check
- Road access via reverse geocoding

**Tier 2 - For Shortlisted Properties:**
- County GIS verification
- Proximity to utilities
- County economic health (Census data)

### Delinquency Filtering (Tiered Approach)
| Flag | Delinquency Age | Action |
|------|-----------------|--------|
| RED | 15+ years old | Auto-reject |
| YELLOW | 5-15 years old | Manual review required |
| GREEN | < 5 years old | Standard due diligence |

### Arkansas-Specific Legal Issues (VERIFIED via web research)
1. **30-day post-sale redemption** - Owner can reclaim within 30 days
2. **Quiet Title IS required** - Budget $1,500-$2,000 per property for marketable title
   - COSL issues a "Limited Warranty Deed" - NOT insurable without quiet title
   - Alternative: Hold property and pay taxes for 15 years = marketable title
3. **Notice defects** - Can void sale years later
4. **Surviving liens** - IRS liens and state DFA liens survive the sale

**CONFIG UPDATED**: `config/states.py` now reflects:
- `quiet_title_cost_estimate=1500.0` (was 0.0)
- `redemption_period_days=30` (was 0)
- `time_to_ownership_days=180` (was 1)

---

## Current System State

### Database Status
- **Alabama**: 3,943 properties (tax liens, 4-year redemption)
- **Arkansas**: 100 properties (tax deeds, immediate ownership)
- **Total**: 4,043 properties

### Arkansas Counties Currently Scraped (9 of 75)
| County | Properties | Notes |
|--------|------------|-------|
| Phillips | 65 | Mississippi Delta, HIGH RISK - see below |
| Van Buren | 16 | Ozarks foothills |
| Union | 7 | Southern AR |
| Faulkner | 4 | Near Little Rock |
| Cleburne | 2 | Greers Ferry area |
| Columbia | 2 | Southern AR |
| Lee | 2 | Delta region |
| Calhoun | 1 | |
| Monroe | 1 | |

### Scoring Engine Status (UPDATED with correct quiet title)
- Multi-state scoring engine: `core/scoring.py` - **WORKING**
- Scores recalculated with $1,500 quiet title + 6-month wait
- AR average: 5.2 (was 12.1 before correction)
- AR time penalty: 0.843 (6-month quiet title process)
- AR effective cost range: $1,698 - $6,059

---

## Critical Learning: Phillips County is a Trap

The top-scoring property (001-03667-000) revealed serious red flags:

1. **Delinquency Year: 1944** - 80 years delinquent means the market has rejected this property for decades
2. **Flood Zone**: Mississippi Delta floodplain, 1927 Great Flood area
3. **Economic Distress**: 34.5% poverty rate, declining population
4. **No Local Market**: Properties cannot be verified for access remotely

**Recommendation**: Filter out properties with delinquency years before 2015 (10+ years).

---

## Next Session Goals

### Priority 1: Comprehensive Arkansas Scraping

Scrape ALL 75 Arkansas counties from COSL website. The scraper exists at:
- `core/scrapers/arkansas_cosl.py`

Current limitation: Only scraped ~100 properties. Need to:
1. Run full scrape of all available properties
2. Capture the `added_on` date (correlates to delinquency age)
3. Identify which counties have the most properties

### Priority 2: Add Risk Indicators

Add these fields to scraping/analysis:
- **Delinquency Year**: Extract from COSL listing (critical filter)
- **County Health Score**: Population trend, poverty rate, median income
- **Flood Zone Flag**: FEMA flood zone check
- **Road Access Flag**: Properties near roads vs landlocked

### Priority 3: Safer County Targeting

Based on research, prioritize these Arkansas counties for investment:

**Tier 1 - Safest (Growing/Stable)**:
- Washington County (Fayetteville area)
- Benton County (NW Arkansas boom)
- Pulaski County (Little Rock)
- Saline County (suburban growth)
- Faulkner County (Conway area)

**Tier 2 - Moderate**:
- Cleburne County (Greers Ferry Lake)
- Baxter County (Mountain Home)
- Garland County (Hot Springs)
- Sebastian County (Fort Smith)

**Avoid** (Tier 3 - High Risk):
- Phillips County (Delta, economic distress)
- Lee County (Delta)
- Chicot County (Delta)
- Mississippi County (Delta)
- Any property with delinquency before 2015

---

## Investment Context

- **Budget**: $8,000 available capital
- **Investor Profile**: First-time, conservative
- **Strategy**: Buy and hold for appreciation, NOT wholesale flipping
- **Target Properties**:
  - 2-10 acres (sweet spot)
  - Effective cost < $3,000 (leaves buffer for fees)
  - Recent delinquency (2020+)
  - Near roads/towns
  - Not in flood zone

---

## Code Locations

### Scraper
```
core/scrapers/arkansas_cosl.py
```
Key methods:
- `scrape_all_properties()` - Main scraping method
- `_fetch_grid_data()` - Hits COSL Kendo UI API
- `to_dict()` - Converts to database format

### Scoring Engine
```
core/scoring.py
```
Key classes:
- `ScoringEngine` - Main scoring class
- `PropertyScoreInput` - Input data structure
- `ScoreResult` - Output with buy_hold_score, wholesale_score

### Score Recalculation
```
scripts/recalculate_scores.py
```
Run after importing new properties:
```bash
python scripts/recalculate_scores.py --state AR
```

### Database Models
```
backend_api/database/models.py - Property model
backend_api/models/property.py - API Pydantic models
```

New fields added:
- `buy_hold_score` (Float)
- `wholesale_score` (Float)
- `effective_cost` (Float)
- `time_penalty_factor` (Float)

---

## Recommended Session Flow

### Step 1: Full Arkansas Scrape
```python
# Run comprehensive scrape
from core.scrapers.arkansas_cosl import ArkansasCOSLScraper
scraper = ArkansasCOSLScraper()
properties = await scraper.scrape_all_properties()
# Import to database
```

### Step 2: Add Delinquency Filter
Modify scraper to capture delinquency year and add filter:
```python
# Skip properties delinquent before 2015
if delinquency_year < 2015:
    logger.warning(f"Skipping ancient delinquency: {parcel_id} ({delinquency_year})")
    continue
```

### Step 3: Recalculate Scores
```bash
python scripts/recalculate_scores.py --state AR
```

### Step 4: Analyze by County
Query top properties grouped by county, avoiding Delta region.

### Step 5: Due Diligence on Top 5
For each top property:
1. Check COSL listing for delinquency year
2. Verify road access on Google Maps
3. Check FEMA flood zone
4. Look up county assessor for assessed value

---

## Prompt for Next Session

```
Continue Arkansas property analysis for tax deed investment. Current state:
- 100 AR properties in database (need 500+)
- Scoring engine working
- Top property was a trap (80-year delinquency)

Tasks:
1. Run full Arkansas COSL scrape (all counties)
2. Add delinquency year filtering (skip pre-2015)
3. Focus on safe counties: Washington, Benton, Pulaski, Saline, Faulkner
4. Find properties: 2-10 acres, <$3k effective cost, 2020+ delinquency
5. Perform due diligence on top 5 candidates

Investment context: $8k budget, first-time buyer, conservative approach.
Avoid: Phillips County, Delta region, any 10+ year delinquent properties.

Use MCP PAL tools for Gemini assistance on research tasks.
```

---

## Files Modified This Session

1. `streamlit_app/app.py` - Added multi-state dashboard features
2. `backend_api/models/property.py` - Added scoring fields to API
3. `config/states.py` - **CORRECTED** Arkansas quiet title cost ($0 -> $1,500)
4. Scores recalculated for all properties with correct costs

## Files Created This Session

1. `docs/SESSION_HANDOFF_2025-01-04.md` - This file
2. `scripts/scrape_all_arkansas.py` - Ready-to-run comprehensive scraper

---

## Key Insight

Arkansas tax deeds are still better than Alabama tax liens, but not as dramatically as initially thought:

| Factor | Arkansas | Alabama |
|--------|----------|---------|
| Redemption | 30 days | 4 years |
| Quiet Title | ~$1,500 | ~$4,000 |
| Time to Marketable Title | ~6 months | ~5.5 years |
| Total Effective Cost Adder | ~$1,650 | ~$4,400 |

**Arkansas Advantage**: Still ~$2,750 cheaper and 5 years faster than Alabama.

**Critical Warning**: Many COSL properties are "perpetual inventory" that have been rejected by the market for decades. The delinquency year is the critical filter to avoid these traps.

## Sources

- [Arkansas COSL Buyer Information](https://www.cosl.org/Home/Buyers)
- [Tax Title Services - Arkansas Quiet Title](https://www.taxtitleservices.com/quiet-title-action-arkansas)
- [Gramling Law Firm - COSL Purchases](https://www.gramlinglawfirm.com/blog/2025/06/when-a-bargain-isnt-a-bargain-buying-property-from-the-commissioner-of-state-lands/)
