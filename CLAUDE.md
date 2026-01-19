- no emojis

## Scraper Architecture

### Execution Patterns
- **Arkansas (in-process)**: Uses aiohttp, runs directly in FastAPI's event loop
- **Alabama/Texas/Florida (subprocess)**: Uses Playwright, runs in subprocess to avoid asyncio conflicts on Windows

### Exit Code System
Subprocess scrapers communicate via exit codes (see `core/scrapers/EXIT_CODES.md`):
- 0: Success
- 1: Transient error (retry with backoff)
- 2: Permanent error (no retry)
- 3: Rate limited (60s cooldown)

### Known Issues Fixed
- 2026-01-06: Fixed Alabama acreage parsing - `extract_acreage_with_lineage()` returns `AcreageResult` dataclass, not dict. Use attribute access (`.acreage`) not `.get('acreage')`
- 2026-01-07: Fixed subprocess import error - Changed `.utils` to `core.scrapers.utils` in alabama_dor.py and texas_counties.py to support both module and script execution
- 2026-01-07: Fixed .gitignore `lib/` pattern that was accidentally ignoring `frontend/src/lib/`. Changed to `/lib/` to only match root-level Python dist folder
- 2026-01-07: Fixed useUrlState infinite loop - Added ref to track programmatic URL updates
- 2026-01-07: Fixed sequential bulk watchlist operations - Now uses Promise.allSettled() for parallel execution
- 2026-01-07: Fixed Math.random in LoadingSkeleton render - Moved to useMemo to prevent layout thrashing
- 2026-01-07: Fixed PropertiesTable toggleWatch race condition - Changed `togglingWatch` from `string | null` to `Set<string>` to allow concurrent toggles on different properties
- 2026-01-07: Fixed Watchlist optimistic update rollback - Added proper rollback on failure for `updateRating` and `saveNotes`
- 2026-01-07: Added accessibility labels - Star rating buttons, state filter select now have proper aria-labels
- 2026-01-07: Fixed El Paso County acreage parsing - "(0371 AC)" format now correctly parsed as 0.0371 acres instead of 371.0
- 2026-01-09: Fixed jwt.JWTError exception - Changed to PyJWTError import in backend_api/auth.py for PyJWT compatibility
- 2026-01-09: Added API connection retry with exponential backoff - Frontend now retries failed requests 3x with 1s/2s/4s delays
- 2026-01-09: Added ConnectionManager for auto-reconnection - Monitors connection, schedules reconnect attempts up to 10x
- 2026-01-09: Added ConnectionStatus UI component - Shows banner when offline, auto-hides when reconnected
- 2026-01-09: Fixed PropertiesTable scroll - Added flex container and overflow-auto for vertical scrolling with sticky header
- 2026-01-10: Added MyFirstDeal enhancements - Deal pipeline tracking, property comparison, external resource links
- 2026-01-10: Added Portfolio Analytics Dashboard - Visualizes backend Portfolio API with summary cards, charts, and risk analysis
- 2026-01-17: Fixed Parcels page infinite loop - Competing URL state management between Parcels.tsx and useUrlState caused re-render loop. Root cause: `setSearchParams({...})` overwrites ALL params. Fix: use functional form `setSearchParams(prev => ...)` to preserve existing params, and useUrlState now preserves unmanaged params.
- 2026-01-19: Fixed CachingMiddleware Content-Length bug - Re-enabled server-side response caching. Root causes: (1) body bytes corrupted by JSON serialization, (2) ASGI body chunks not accumulated. Fix: base64-encode body for storage, accumulate all body chunks before caching, recalculate Content-Length on retrieval. Adds `X-Cache: HIT/MISS` headers.
- 2026-01-19: Added CSV Import Feature - Bulk property import via TopBar Actions menu. Backend endpoints at `/api/v1/import/csv/preview` and `/api/v1/import/csv`. Frontend modal with drag-and-drop, column mapping, preview, and import progress. Auto-detects common CSV header variations.

### URL State Management Guidelines
When using `useSearchParams` alongside `useUrlState`, follow these rules to prevent infinite loops:

1. **Never use object literal form** - `setSearchParams({ key: value })` replaces ALL params
2. **Always use functional form** to preserve existing params:
   ```typescript
   setSearchParams(prev => {
     const newParams = new URLSearchParams(prev)
     newParams.set('key', value)
     return newParams
   }, { replace: true })
   ```
3. **useUrlState owns these params**: sort, order, page, per_page, q, state, county, minPrice, maxPrice, minAcreage, maxAcreage, minScore, minCountyScore, minGeoScore, waterOnly, excludeDelta, minYear, period
4. **Other params** (like `selected` in Parcels) are safe to use without conflict

### Portfolio Analytics Dashboard
The Portfolio page (`/portfolio`) displays aggregate analytics for watched properties:
- **Summary Cards**: Total properties, portfolio value, avg investment score, capital utilization
- **Geographic Charts**: State distribution pie chart, top counties bar chart
- **Score Distribution**: Investment score histogram with color-coded buckets
- **Activity Timeline**: Weekly additions line chart
- **Risk Analysis**: Diversification score, concentration metrics, risk flags
- **Performance Metrics**: Recent additions, star rating breakdown, first deal status

Frontend components:
- `frontend/src/pages/Portfolio.tsx` - Main page
- `frontend/src/components/portfolio/` - Summary cards, charts, risk section
- `frontend/src/lib/hooks.ts` - usePortfolioSummary, usePortfolioGeographic, etc.
- `frontend/src/lib/api.ts` - portfolioApi object

Backend endpoints used (already implemented):
- `GET /portfolio/summary` - Aggregate metrics
- `GET /portfolio/geographic` - State/county breakdown
- `GET /portfolio/scores` - Score distribution buckets
- `GET /portfolio/risk` - Risk analysis
- `GET /portfolio/performance` - Activity tracking

### MyFirstDeal Feature
The My First Deal page (`/my-first-deal`) now includes:
- **Deal Pipeline Tracking**: Assign a property as your "first deal" and track it through stages (Research -> Bid -> Won -> Quiet Title -> Done). Backend-synced via PropertyInteraction model.
- **Property Comparison**: Compare up to 3 recommended properties side-by-side using existing PropertyCompareContext.
- **External Resource Links**: Steps 2, 6, and 7 now include helpful links (FEMA flood maps, state bar attorney referrals, land selling platforms).

Backend endpoints added:
- `GET /watchlist/first-deal` - Get current first deal
- `POST /watchlist/property/{id}/set-first-deal` - Assign property as first deal
- `PUT /watchlist/first-deal/stage` - Update pipeline stage
- `DELETE /watchlist/first-deal` - Remove first deal assignment

Database migration needed: PropertyInteraction model has new columns (`is_first_deal`, `first_deal_stage`, `first_deal_assigned_at`, `first_deal_updated_at`).

### CSV Import Feature
The CSV Import feature (`Actions > Import CSV` in TopBar) allows bulk property import:

**Backend Endpoints:**
- `POST /api/v1/import/csv/preview` - Upload CSV, get headers, sample rows, suggested mapping, duplicate count
- `POST /api/v1/import/csv` - Import properties with column mapping via query params
- `GET /api/v1/import/columns` - Get importable fields and their aliases

**Frontend Components:**
- `frontend/src/components/CSVImportModal.tsx` - Modal with drag-and-drop, column mapping, preview
- `frontend/src/lib/api.ts` - importApi with previewCSV, importCSV, getColumns

**Required CSV Fields:** `parcel_id`, `amount`
**Optional Fields:** `acreage`, `county`, `state`, `description`, `owner_name`, `year_sold`, `assessed_value`, `sale_type`, `redemption_period_days`, `auction_date`, `auction_platform`, `data_source`, `estimated_market_value`

**Column Auto-Detection:** Common header variations are auto-mapped (e.g., "parcel", "parcel_number", "pid" all map to `parcel_id`)

### Known Data Quality Issues
- Harris County listings: Empty during non-auction periods (next sale date shown on page). Not a bug.
- Florida counties: May have empty listings between auction dates. Check auction calendar on RealTaxDeed site.

### Testing
- Factory retry tests: `pytest tests/unit/test_factory_retry.py -v`
- Arkansas tests: `pytest tests/unit/test_arkansas_cosl.py -v`
- Alabama tests: `pytest tests/unit/test_alabama_dor.py -v`
- Texas tests: `pytest tests/unit/test_texas_counties.py -v`
- Florida tests: `pytest tests/unit/test_florida_counties.py -v`
- All scraper tests: `pytest tests/unit/test_factory_retry.py tests/unit/test_arkansas_cosl.py tests/unit/test_alabama_dor.py tests/unit/test_texas_counties.py tests/unit/test_florida_counties.py -v`