# Claude Code Quick Start Prompt
## Land-App Pivot: Tax Deed States + Wholesaling

**Copy and paste this into your Claude Code session to get started:**

---

## Context Prompt

```
I'm working on pivoting my land-app (https://github.com/pmartin1915/land-app) from Alabama tax liens to tax deed states and land wholesaling.

**My situation:**
- 27 y/o junior developer, pediatric nurse, NP student
- $10,000 investment capital (firm limit)
- Located in Alabama
- Using Claude Code + MCP PAL (Gemini subagents) + Google Antigravity IDE

**The problem:**
Alabama tax liens require 4-year hold + $3-6k quiet title costs = not viable for my budget.

**The pivot:**
1. Add tax DEED states (immediate ownership): Arkansas, Texas, Florida
2. Add wholesale scoring (find deals, assign contracts, never buy)

**Current app capabilities:**
- Scrapes Alabama DOR for 2,053 properties
- Parses acreage from descriptions
- Calculates investment_score (price_per_acre based)
- Streamlit dashboard + FastAPI backend
- SQLite database (alabama_auction_watcher.db)

**Immediate priorities:**
1. Update database schema for multi-state support
2. Build Arkansas COSL scraper (https://www.cosl.org/) - tax deed, no redemption
3. Update scoring algorithm for state-aware weighting
4. Add wholesale_spread calculation

**Read the full roadmap:** See PIVOT_ROADMAP_2025.md in the repo root

**Key files to examine:**
- CLAUDE.md (project instructions)
- core/ (business logic, scrapers)
- streamlit_app/ (dashboard)
- scripts/create_final_dataset.py (output format)
- config/ (configuration patterns)

What would you like to work on first?
```

---

## Alternate: Minimal Context (for quick sessions)

```
Resume work on land-app pivot. Current state:
- Pivoting from Alabama tax liens → tax deed states + wholesaling
- Need: multi-state DB schema, Arkansas scraper, updated scoring
- See PIVOT_ROADMAP_2025.md for full details
- Start by reading core/ and streamlit_app/ structure
```

---

## Task-Specific Prompts

### For Database Work:
```
Update the land-app database schema to support multi-state properties. 

Add fields:
- state, sale_type, redemption_period_days, time_to_ownership_days
- estimated_market_value, wholesale_spread, owner_type
- data_source, auction_date, auction_platform

Add new tables:
- state_configs (state settings and scraper mappings)
- wholesale_pipeline (deal tracking)

Use Alembic for migrations. See PIVOT_ROADMAP_2025.md for full schema.
```

### For Arkansas Scraper:
```
Build a scraper for Arkansas Commissioner of State Lands (https://www.cosl.org/).

Key facts:
- Tax DEED state (not lien) - immediate ownership
- NO redemption period
- State-level centralized system
- Properties listed by county with minimum bids

Create: core/scrapers/arkansas_cosl.py
Follow patterns from existing Alabama scraper.
```

### For Scoring Updates:
```
Update the investment scoring algorithm to be state-aware.

Requirements:
- Penalize tax lien states for time-to-ownership (4+ years = -20 points)
- Bonus tax deed states with no redemption (+15 points)
- Add wholesale_score calculation: (market_value - asking) / market_value
- Factor in quiet_title_cost from state_configs

See PIVOT_ROADMAP_2025.md Milestone 3 for implementation details.
```

### For Streamlit Dashboard:
```
Add a state comparison view to the Streamlit dashboard.

Features needed:
- Dropdown to filter by state
- Side-by-side metrics (avg price, time to ownership, typical ROI)
- Table showing top 20 properties per state
- Color-coding: green for tax deed, yellow for redeemable, red for tax lien

Use existing streamlit_app/ patterns.
```

---

## Useful Commands

```bash
# Inspect current database schema
sqlite3 alabama_auction_watcher.db ".schema"

# Run existing scraper
python full_scrape.py

# Launch Streamlit dashboard
streamlit run streamlit_app/app.py

# Run tests
pytest tests/

# Check data quality
python quick_validate.py
```

---

## Key URLs for Scraping

| State | URL | Type |
|-------|-----|------|
| Alabama | revenue.alabama.gov/property-tax/delinquent-search/ | Tax Lien |
| Arkansas | cosl.org | Tax Deed |
| Texas | varies by county | Redeemable Deed |
| Florida | tax-sale.info | Hybrid |

---

## Remember

1. **Don't delete Alabama code** - it's still useful for future when capital grows
2. **Arkansas first** - simplest to implement, immediate ownership
3. **Wholesale scoring is the money feature** - enables zero-capital deals
4. **Test with real data** - scrape a small batch before full implementation
