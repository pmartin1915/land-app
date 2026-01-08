- no emojis

## Scraper Architecture

### Execution Patterns
- **Arkansas (in-process)**: Uses aiohttp, runs directly in FastAPI's event loop
- **Alabama/Texas (subprocess)**: Uses Playwright, runs in subprocess to avoid asyncio conflicts on Windows

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

### Known Data Quality Issues
- Harris County listings: Empty during non-auction periods (next sale date shown on page). Not a bug.

### Testing
- Factory retry tests: `pytest tests/unit/test_factory_retry.py -v`
- Arkansas tests: `pytest tests/unit/test_arkansas_cosl.py -v`
- Alabama tests: `pytest tests/unit/test_alabama_dor.py -v`
- Texas tests: `pytest tests/unit/test_texas_counties.py -v`
- All scraper tests: `pytest tests/unit/test_factory_retry.py tests/unit/test_arkansas_cosl.py tests/unit/test_alabama_dor.py tests/unit/test_texas_counties.py -v`