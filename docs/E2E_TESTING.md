# E2E Testing Guide

End-to-end testing infrastructure for Alabama Auction Watcher using Playwright.

## Overview

The E2E test suite verifies the application works correctly as an integrated system:
- Frontend (React + Vite) on port 5173
- Backend API (FastAPI) on port 8001
- Desktop app (Tauri) for production

## Quick Start

```bash
cd frontend

# Run all E2E tests (auto-starts backend + frontend)
npm run test:e2e

# Run with browser visible
npm run test:e2e:headed

# Run with Playwright UI (interactive debugging)
npm run test:e2e:ui

# Debug a specific test
npm run test:e2e:debug

# View test report
npm run test:e2e:report
```

## Test Architecture

```
frontend/
  e2e/
    smoke.spec.ts       # Critical path tests (always run first)
    properties.spec.ts  # Properties table & filtering tests
    utils/
      start-backend.js  # Robust backend lifecycle manager
      tauri-driver.js   # Tauri WebDriver integration
  playwright.config.ts       # Main config (web testing)
  playwright.tauri.config.ts # Desktop app testing config
```

## Backend Lifecycle Manager

The test setup automatically manages the backend API:

1. **Health Check**: Verifies if backend is already running
2. **Port Cleanup**: Kills zombie processes on port 8001
3. **Auto-Start**: Spawns uvicorn if needed
4. **Retry Logic**: Exponential backoff for health checks
5. **Graceful Shutdown**: Clean termination after tests

### Manual Backend Start (optional)

If you prefer to manage the backend manually:

```bash
# Terminal 1: Start backend
cd backend_api
uvicorn main:app --reload --port 8001

# Terminal 2: Run tests (will reuse existing backend)
cd frontend
npm run test:e2e
```

## Test Categories

### Smoke Tests (`smoke.spec.ts`)

Critical path verification - these must always pass:
- Dashboard loads without errors
- No console errors on startup
- Navigation between pages works
- Backend API is reachable
- Theme is applied correctly
- Responsive layout works

### Properties Tests (`properties.spec.ts`)

Main workhorse functionality:
- Table renders with data
- Sorting by columns
- Pagination controls
- Row selection
- Property detail slide-over
- Search and filtering
- Export functionality

## Configuration

### Web Testing (`playwright.config.ts`)

```typescript
// Key settings
baseURL: 'http://localhost:5173'
timeout: 30000  // 30 second test timeout
webServer: [
  { command: 'node e2e/utils/start-backend.js', url: 'http://localhost:8001/health' },
  { command: 'npm run dev', url: 'http://localhost:5173' }
]
```

### Tauri Testing (`playwright.tauri.config.ts`)

For testing the built desktop app:

```bash
# Build the app first
npm run tauri:build

# Then run Tauri tests
npm run test:e2e:tauri
```

**Prerequisites for Tauri testing:**
1. Rust toolchain installed
2. `cargo install tauri-driver`
3. Built Tauri app in `src-tauri/target/release/`

## Writing New Tests

### Basic Test Structure

```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/page-path');
  });

  test('should do something', async ({ page }) => {
    // Arrange
    await expect(page.getByRole('heading', { name: 'Title' })).toBeVisible();

    // Act
    await page.getByRole('button', { name: 'Click Me' }).click();

    // Assert
    await expect(page.locator('.result')).toContainText('Success');
  });
});
```

### Waiting for API Responses

```typescript
// Wait for specific API call
await page.waitForResponse(
  (response) => response.url().includes('/api/v1/properties') && response.status() === 200
);

// Or wait for network idle
await page.waitForLoadState('networkidle');
```

### Mocking API Responses

```typescript
await page.route('**/api/v1/properties**', (route) => {
  route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ properties: [], total: 0 }),
  });
});
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install backend dependencies
        run: pip install -r requirements.txt

      - name: Install frontend dependencies
        run: cd frontend && npm ci

      - name: Install Playwright browsers
        run: cd frontend && npx playwright install --with-deps chromium

      - name: Run E2E tests
        run: cd frontend && npm run test:e2e

      - name: Upload test report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: frontend/playwright-report/
```

## Debugging Failed Tests

### 1. Run in headed mode
```bash
npm run test:e2e:headed
```

### 2. Use Playwright UI
```bash
npm run test:e2e:ui
```

### 3. Enable trace
Tests automatically capture traces on first retry. View them:
```bash
npx playwright show-trace test-results/trace.zip
```

### 4. Check backend logs
The backend lifecycle manager logs to stdout:
```
[Backend] Starting backend lifecycle manager...
[Backend] Health check passed (attempt 1/30)
[Backend] Server is healthy and ready for tests!
```

### 5. View screenshots and videos
Failed tests save artifacts to `test-results/`:
- `screenshot.png` - Screenshot at failure point
- `video.webm` - Video of test execution
- `trace.zip` - Full execution trace

## Troubleshooting

### Port 8001 already in use

The backend manager auto-cleans zombie processes, but if issues persist:

```bash
# Windows
netstat -ano | findstr :8001
taskkill /F /PID <pid>

# Unix
lsof -ti :8001 | xargs kill -9
```

### Tests timeout waiting for backend

1. Check backend logs for errors
2. Verify database exists: `data/alabama_auction_watcher.db`
3. Try starting backend manually first

### Frontend fails to start

1. Check Vite dev server logs
2. Ensure node_modules is installed: `npm install`
3. Verify no port conflicts on 5173

### Tauri tests fail

1. Ensure app is built: `npm run tauri:build`
2. Verify tauri-driver installed: `cargo install tauri-driver`
3. Check for missing system dependencies

## Test Coverage Goals

| Category | Coverage Target | Status |
|----------|-----------------|--------|
| Smoke tests | 100% | Done |
| Navigation | 100% | Done |
| Properties table | 80% | Done |
| Filtering | 70% | Done |
| Property detail | 60% | Done |
| Map | 40% | TODO |
| Settings | 30% | TODO |

## Related Documentation

- [Vitest Unit Tests](../frontend/README.md) - Component unit tests
- [Testing Handoff Template](./TESTING_HANDOFF_TEMPLATE.md) - Claude/Gemini workflow
- [Backend API](../backend_api/README.md) - API documentation
