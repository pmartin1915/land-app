# Scraper Exit Code System

Subprocess-based scrapers (Alabama, Texas) use exit codes to communicate
status to the factory's retry logic.

## Exit Codes

| Code | Constant | Meaning | Factory Behavior |
|------|----------|---------|------------------|
| 0 | EXIT_SUCCESS | Scrape completed successfully | Return results |
| 1 | EXIT_TRANSIENT | Network error, timeout, selector not found | Retry with exponential backoff |
| 2 | EXIT_PERMANENT | Auth failure, major layout change | Fail immediately (no retry) |
| 3 | EXIT_RATE_LIMIT | HTTP 429 or access denied | Retry after 60s cooldown |

## Retry Configuration

- **MAX_RETRIES**: 3 attempts
- **BASE_DELAY**: 2 seconds (exponential: 2s, 4s, 8s)
- **MAX_DELAY**: 30 seconds cap
- **RATE_LIMIT_DELAY**: 60 seconds cooldown

## Why Subprocess?

Alabama and Texas scrapers use Playwright for browser automation. Playwright's
asyncio implementation conflicts with FastAPI's event loop on Windows. Running
scrapers in a subprocess isolates the event loops and prevents deadlocks.

Arkansas uses aiohttp (pure async HTTP client) which works correctly in-process
with FastAPI's event loop.

## Architecture

```
FastAPI (main event loop)
    |
    +-- Arkansas: Direct async call (aiohttp)
    |
    +-- Alabama/Texas: subprocess.Popen + JSON file output
            |
            +-- Exit code signals retry behavior
            +-- JSON file contains property data
            +-- Graceful termination: terminate() then kill()
```

## Debug Snapshots

All scrapers save HTML/JSON snapshots to `debug_failures/` when:
- Parsing fails
- No properties are found (potential layout change)
- Unexpected errors occur

Filename format: `{STATE}_{COUNTY}_{TIMESTAMP}.{html|json}`

Example: `AL_Baldwin_20260105_143022.html`
