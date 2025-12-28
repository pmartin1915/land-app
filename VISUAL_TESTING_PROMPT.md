# Visual Testing Prompt for Alabama Auction Watcher

Use this prompt with **Google Antigravity** or **Claude Code + Playwright MCP** to enable AI-driven visual testing of the Alabama Auction Watcher application.

---

## Project Context

**Alabama Auction Watcher** is a property research and investment analysis tool for Alabama tax lien auctions. It scrapes property data from the Alabama Department of Revenue, calculates investment scores, and provides a research workflow for triaging properties.

**Tech Stack:**
- Frontend: React + TypeScript + Vite (port 5173)
- Desktop: Tauri 2
- Backend: FastAPI (port 8001)
- Database: SQLite with 3,943+ properties
- Maps: Mapbox with FEMA flood zone overlays

**Key Features:**
- Dashboard with Research Pipeline workflow stats
- Interactive property map with investment score clustering
- Triage view for AI-assisted property review
- Parcel browser with filters
- Scrape job management

---

## Prompt for Google Antigravity

Copy this into Antigravity's agent interface:

```
PROJECT: Alabama Auction Watcher - Tax Lien Property Research Tool
LOCATION: C:\auction

OBJECTIVE: Perform visual testing and UI validation of the Alabama Auction Watcher application across all major views.

STARTUP COMMANDS:
- Backend API: cd C:\auction && python -m uvicorn backend_api.main:app --port 8001 --reload
- Frontend: cd C:\auction\frontend && npm run dev
- Frontend URL: http://localhost:5173

TESTING SCENARIOS:

1. DASHBOARD VIEW
   - Navigate to http://localhost:5173/dashboard
   - Screenshot the full dashboard layout
   - Verify these sections are visible:
     - Research Pipeline (workflow status breakdown)
     - Counties Active card
     - Water Access card
     - Avg Price/Acre card
     - Analytics & Insights section
   - Check sidebar navigation shows: Dashboard, Parcels, Map, Triage, Scrape Jobs, Watchlist, Reports, Settings
   - Verify "Backend: Connected" status in footer

2. RESEARCH PIPELINE WORKFLOW
   - On Dashboard, locate the Research Pipeline section
   - Screenshot the status breakdown (New, Reviewing, Bid Ready, Rejected, Purchased)
   - Verify counts display correctly (should show ~3,943 total properties)
   - Click on each status card and verify it navigates/filters appropriately

3. PROPERTY MAP VIEW
   - Navigate to Map view via sidebar
   - Screenshot initial map state (should show Alabama)
   - Verify Investment Score legend is visible:
     - Elite (85+) - Green
     - Good (70-84) - Blue
     - Moderate (50-69) - Yellow
     - Low (<50) - Red
   - Toggle FEMA Flood Zones checkbox
   - Screenshot with flood zones visible
   - Click on a property cluster and verify popup/detail appears
   - Test Min Score dropdown filter (Moderate 50+)

4. TRIAGE / AI SUGGESTIONS VIEW
   - Navigate to Triage view
   - Screenshot the property list layout
   - Select a property and verify detail panel appears
   - Test status change workflow:
     - Click a property
     - Change status from "New" to "Reviewing"
     - Add triage notes
     - Verify the change persists
   - Screenshot before/after status change

5. PARCELS BROWSER
   - Navigate to Parcels view
   - Screenshot the data table
   - Test filtering:
     - Filter by county
     - Filter by price range
     - Filter by acreage
   - Test sorting columns
   - Click a property row to view details
   - Screenshot the property detail modal/panel

6. RESPONSIVE TESTING
   - Test at these viewport sizes:
     - Mobile: 375x667
     - Tablet: 768x1024
     - Desktop: 1280x800
   - Screenshot Dashboard at each size
   - Verify sidebar collapses on mobile
   - Verify map is usable on mobile

7. DARK MODE / THEME
   - Locate theme toggle (sun/moon icon in header)
   - Screenshot current theme
   - Toggle theme
   - Screenshot after toggle
   - Verify all components adapt properly (no white backgrounds in dark mode)

8. ERROR STATES
   - Stop the backend API
   - Refresh frontend and screenshot the error state
   - Verify "Backend: Disconnected" or error message appears
   - Restart backend and verify reconnection

9. SEARCH FUNCTIONALITY
   - Use the search bar in header
   - Search for "parcels" or a property owner name
   - Screenshot search results
   - Verify search filters work correctly

10. KEYBOARD NAVIGATION
    - Test Cmd+1 through Cmd+5 keyboard shortcuts
    - Verify they navigate to correct views
    - Test Tab navigation through forms
    - Verify focus indicators are visible

ARTIFACT REQUIREMENTS:
- Save all screenshots to: C:\auction\tools\playwright-mcp\screenshots\
- Name format: {view}-{scenario}-{timestamp}.png
- Generate summary report: C:\auction\tools\playwright-mcp\screenshots\VISUAL_TEST_REPORT.md

VALIDATION CRITERIA:
- All data loads without console errors
- Map renders with property markers
- Research Pipeline stats match API response
- Status updates persist correctly
- Responsive layouts work at all breakpoints
- Theme toggle works completely
```

---

## Prompt for Claude Code + Playwright MCP

Use this when working with Claude Code and the Playwright control server:

```
I need to perform visual testing on the Alabama Auction Watcher application.

PROJECT LOCATION: C:\auction
FRONTEND URL: http://localhost:5173 (run `cd frontend && npm run dev`)
BACKEND URL: http://localhost:8001 (run `python -m uvicorn backend_api.main:app --port 8001`)
PLAYWRIGHT TOOLS: C:\auction\tools\playwright-mcp\

Please perform the following visual tests using Playwright:

TASK 1: Dashboard Baseline
- Navigate to http://localhost:5173/dashboard
- Wait for data to load (check for "Backend: Connected" in footer)
- Take full-page screenshot: dashboard-baseline.png
- Verify Research Pipeline section shows property counts
- Get accessibility tree and report any issues

TASK 2: Map View Testing
- Navigate to Map view
- Wait for properties to load on map
- Take screenshot: map-default.png
- Enable FEMA Flood Zones toggle
- Take screenshot: map-with-flood-zones.png
- Change Min Score filter to "Elite (85+)"
- Take screenshot: map-elite-only.png

TASK 3: Workflow Status Testing
- Navigate to Triage view
- Take screenshot of initial state
- Click first property in list
- Take screenshot showing property details
- If possible, test status change (New -> Reviewing)

TASK 4: Responsive Screenshots
- Set viewport to mobile (375x667)
- Navigate to Dashboard, take screenshot: dashboard-mobile.png
- Navigate to Map, take screenshot: map-mobile.png
- Set viewport to tablet (768x1024)
- Navigate to Dashboard, take screenshot: dashboard-tablet.png

TASK 5: Theme Testing
- Find and click theme toggle button
- Take screenshot after toggle: dashboard-dark.png or dashboard-light.png
- Verify no visual artifacts (white boxes in dark mode, etc.)

After testing, provide:
1. Summary of each view's visual state
2. Any loading issues or errors observed
3. Accessibility concerns from the tree analysis
4. UI/UX improvement suggestions
```

---

## Quick Start Commands

```bash
# Terminal 1: Backend API
cd c:\auction
python -m uvicorn backend_api.main:app --port 8001 --reload

# Terminal 2: Frontend
cd c:\auction\frontend
npm run dev

# Terminal 3: Playwright Control Server
cd c:\auction\tools\playwright-mcp
node server.js
```

---

## Playwright Control Server API (port 3333)

### Core Endpoints
| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| POST | /navigate | `{ url: "..." }` | Navigate to URL |
| POST | /screenshot | `{ filename?, selector?, fullPage? }` | Capture screenshot (returns base64) |
| POST | /click | `{ selector? or text? }` | Click element |
| POST | /type | `{ selector, text, clear? }` | Type into input |
| GET | /status | - | Current URL and title |
| GET | /text | - | All visible text on page |
| POST | /evaluate | `{ script: "..." }` | Execute JavaScript |
| POST | /close | - | Close browser and reset state |

### AI Integration Endpoints
| Method | Endpoint | Body/Query | Description |
|--------|----------|------------|-------------|
| POST | /configure | `{ headers?, viewport? }` | Set auth headers (X-Device-ID, X-API-Key) |
| POST | /viewport | `{ width, height }` | Set viewport for responsive testing |
| GET | /accessibility | - | Page accessibility tree |
| GET | /observe | - | Combined status + accessibility + errors |
| GET | /console-logs | `?clear=true&type=error` | Browser console logs |
| GET | /network-activity | `?status=4xx&clear=true` | Track API calls and failures |

### Example: Configure Auth Headers
```bash
curl -X POST http://localhost:3333/configure \
  -H "Content-Type: application/json" \
  -d '{"headers": {"X-Device-ID": "test-agent", "X-API-Key": "your-key"}}'
```

### Example: Responsive Testing
```bash
# Mobile viewport
curl -X POST http://localhost:3333/viewport \
  -H "Content-Type: application/json" \
  -d '{"width": 375, "height": 667}'

# Navigate and screenshot
curl -X POST http://localhost:3333/navigate \
  -H "Content-Type: application/json" \
  -d '{"url": "http://localhost:5173/dashboard"}'

curl -X POST http://localhost:3333/screenshot \
  -H "Content-Type: application/json" \
  -d '{"filename": "dashboard-mobile.png"}'
```

---

## Best Practices for AI Visual Testing

### 1. Use Reliable Selectors
Prioritize selectors in this order:
1. `data-testid` attributes: `[data-testid="nav-triage-link"]`
2. ARIA roles: `[role="button"][name="Save"]`
3. Semantic HTML: `nav a`, `button`, `input[type="submit"]`
4. Text content (fallback): `text="Triage"`

### 2. Handle Network Errors
After each action, check `/network-activity`:
- **Critical 404s**: Fail the test if essential endpoints fail
- **Expected 404s**: Ignore known missing endpoints
- **5xx errors**: Always flag for investigation

### 3. Wait for Stability
Before taking screenshots or interacting:
1. Call `/navigate` with `waitUntil: 'networkidle'`
2. Wait for critical elements to be visible
3. Check `/observe` for any errors

### 4. Use Combined /observe Endpoint
Call `GET /observe` at key test points to get:
- Current URL and title
- Accessibility tree
- Recent console errors
- Failed network requests

---

## Key Views Reference

| View | URL Path | Key Elements |
|------|----------|--------------|
| Dashboard | `/dashboard` | Pipeline stats, metric cards, analytics |
| Parcels | `/parcels` | Data table, filters, property details |
| Map | `/map` | Mapbox, markers, flood zones, legend |
| Triage | `/triage` | Property list, status workflow, AI suggestions |
| Scrape Jobs | `/scrape-jobs` | Job history, run controls |
| Watchlist | `/watchlist` | Saved properties |
| Reports | `/reports` | Export options |
| Settings | `/settings` | App configuration |

---

## Expected Visual States

### Dashboard Cards
- **Counties Active:** Number with building icon
- **Water Access:** Count with heart icon
- **Avg Price/Acre:** Dollar amount with currency icon
- Cards should have subtle borders, dark backgrounds

### Research Pipeline
- Progress bar showing workflow distribution
- Status cards: New (blue), Reviewing (yellow), Bid Ready (green), Rejected (red), Purchased (purple)
- Total count prominently displayed

### Map Investment Score Legend
| Score | Color | Label |
|-------|-------|-------|
| 85+ | Green | Elite |
| 70-84 | Blue | Good |
| 50-69 | Yellow/Orange | Moderate |
| <50 | Red | Low |

### Sidebar Navigation
- Active item: Blue background highlight
- Keyboard shortcuts shown (Cmd+1, Cmd+2, etc.)
- Collapse/expand on mobile
- Badge numbers on Triage (pending count) and Watchlist (saved count)

---

## API Endpoints for Verification

When testing, these endpoints can verify data:

```bash
# Workflow stats (should match dashboard)
curl http://localhost:8001/api/v1/properties/workflow/stats

# Property count
curl http://localhost:8001/api/v1/properties?limit=1

# Health check
curl http://localhost:8001/api/v1/health
```

---

## Known Issues to Watch For

1. **Loading overlay on Map:** A semi-transparent overlay appears while properties load - may block clicks
2. **Authentication:** Some endpoints require auth headers (X-Device-ID, X-API-Key)
3. **Mapbox token:** Ensure VITE_MAPBOX_TOKEN is set in frontend/.env
4. **Large dataset:** 3,943 properties may cause initial load delay

---

## Using with Google Antigravity

When using Antigravity's Manager view for parallel testing:

**Agent 1: Dashboard & Workflow**
- Focus on Dashboard view
- Test Research Pipeline interactions
- Verify metric cards load

**Agent 2: Map & Spatial**
- Focus on Map view
- Test property clustering
- Verify FEMA flood zone overlay

**Agent 3: Triage & Status**
- Focus on Triage view
- Test status change workflow
- Verify property detail panels

This parallel approach lets you test all major features simultaneously and compare results.

---

## Artifacts Directory Structure

```
tools/playwright-mcp/
├── screenshots/
│   ├── 01-dashboard.png
│   ├── 02-map.png
│   ├── 03-triage.png
│   ├── dashboard-mobile.png
│   ├── dashboard-tablet.png
│   ├── map-with-flood-zones.png
│   └── accessibility.json
├── server.js          # HTTP control server
├── test-ui.js         # Quick test script
└── README.md
```
