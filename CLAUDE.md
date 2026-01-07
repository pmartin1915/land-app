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

### Testing
- Factory retry tests: `pytest tests/unit/test_factory_retry.py -v`
- Arkansas tests: `pytest tests/unit/test_arkansas_cosl.py -v`
- Alabama tests: `pytest tests/unit/test_alabama_dor.py -v`
- Texas tests: `pytest tests/unit/test_texas_counties.py -v`
- All scraper tests: `pytest tests/unit/test_factory_retry.py tests/unit/test_arkansas_cosl.py tests/unit/test_alabama_dor.py tests/unit/test_texas_counties.py -v`