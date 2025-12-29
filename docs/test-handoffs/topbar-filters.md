# Test Handoff: TopBar Filter Popover

**Date:** 2025-12-29
**Branch:** main
**Claude Tests:** 15 passing (TopBar.test.tsx)

## Summary

The TopBar component includes a global search, advanced filter popover, quick actions dropdown, theme toggle, and period selector. Claude has written 15 unit tests covering rendering, search functionality, filter popover interactions, and actions dropdown.

## Files

- `frontend/src/components/TopBar.tsx` - Main component
- `frontend/src/components/TopBar.test.tsx` - Unit tests (15 tests)

## Prerequisites

- [ ] Backend API running on port 8001 (for counties list and search)
- [ ] Frontend dev server running on port 5173
- [ ] Some properties in database for search results

---

## Test Scenarios for Gemini

### Scenario 1: Search Bar Functionality

**Precondition:** On Dashboard page

**Steps:**
1. Click in the search bar
2. Type "Mobile" slowly
3. Wait for search results dropdown

**Expected Visual Outcomes:**
- [ ] Search icon visible on left of input
- [ ] Placeholder text "Search properties, owners, parcels..." visible
- [ ] Loading spinner appears while searching (if backend connected)
- [ ] Results dropdown appears below search bar
- [ ] Each result shows parcel ID, description snippet, county, and investment score

**Expected Functional Outcomes:**
- [ ] Clicking a result navigates to that property

---

### Scenario 2: Filter Popover - Open/Close

**Precondition:** On any page with TopBar

**Steps:**
1. Click "Filters" button
2. Verify popover appears
3. Click outside the popover
4. Verify it closes
5. Open popover again
6. Press Escape key

**Expected Visual Outcomes:**
- [ ] Popover appears below Filters button with smooth animation
- [ ] Semi-transparent backdrop appears behind popover
- [ ] "Advanced Filters" heading visible
- [ ] X button in top-right corner
- [ ] Popover closes when clicking outside
- [ ] Popover closes on Escape key

---

### Scenario 3: Filter Popover - Apply Filters

**Precondition:** Filter popover is open

**Steps:**
1. Enter "1000" in Min price field
2. Enter "25000" in Max price field
3. Enter "1" in Min acreage field
4. Enter "50" in Max acreage field
5. Select a county from dropdown (if available)
6. Check "Water access only" checkbox
7. Click "Apply Filters"

**Expected Visual Outcomes:**
- [ ] All inputs accept values correctly
- [ ] County dropdown shows available counties
- [ ] Checkbox changes to checked state
- [ ] Popover closes after Apply
- [ ] Filters button now shows a badge with count (e.g., "4")
- [ ] Filters button background changes to blue/accent color

---

### Scenario 4: Filter Popover - Reset Filters

**Precondition:** Filters are applied (badge visible on button)

**Steps:**
1. Open filter popover
2. Note that previous values are still shown
3. Click "Reset" button

**Expected Visual Outcomes:**
- [ ] All input fields clear to empty/default
- [ ] Checkbox becomes unchecked
- [ ] County dropdown resets to "All Counties"
- [ ] Popover closes
- [ ] Badge disappears from Filters button
- [ ] Filters button returns to default gray style

---

### Scenario 5: Quick Actions Dropdown

**Precondition:** On any page with TopBar

**Steps:**
1. Click "Actions" button
2. Verify dropdown menu appears
3. Hover over each menu item

**Expected Visual Outcomes:**
- [ ] Dropdown appears below button
- [ ] Menu items: Export Data, Import CSV, New Scrape, Settings
- [ ] Each item has an icon on the left
- [ ] Hover state shows background color change
- [ ] Settings item has a separator line above it

**Expected Functional Outcomes:**
- [ ] Clicking "Export Data" navigates to /reports
- [ ] Clicking "New Scrape" navigates to /scrape-jobs
- [ ] Clicking "Settings" navigates to /settings

---

### Scenario 6: Theme Toggle

**Precondition:** App is in dark mode

**Steps:**
1. Locate theme toggle button (sun/moon icon)
2. Click to toggle to light mode
3. Verify theme changes
4. Click again to return to dark mode

**Expected Visual Outcomes:**
- [ ] Icon changes from moon to sun (or vice versa)
- [ ] Entire app theme changes (background, text colors)
- [ ] All TopBar elements remain readable
- [ ] Theme persists after page refresh

---

### Scenario 7: Period Selector

**Precondition:** On any page with TopBar

**Steps:**
1. Click the period dropdown (shows "Last 7 Days" by default)
2. Select "Last 30 Days"

**Expected Visual Outcomes:**
- [ ] Dropdown shows all options: 24 Hours, 7 Days, 30 Days, Quarter, Year, All Time
- [ ] Selected option updates in the dropdown display

---

## Visual Regression Points

| Element | Dark Mode | Light Mode |
|---------|-----------|------------|
| Search bar | Dark background, light text | Light background, dark text |
| Filters button (inactive) | Gray border, neutral text | Same |
| Filters button (active) | Blue background, white text, badge | Same |
| Popover | Card background color, proper shadows | Same |
| Input fields | Surface color background | Same |

---

## Accessibility Checks

- [ ] Tab through all interactive elements in order
- [ ] Focus ring visible on all focusable elements
- [ ] Search input has proper placeholder
- [ ] Filter popover can be closed with Escape
- [ ] All buttons have clear purposes from visual appearance

---

## Known Limitations

- Search results require backend API to be running
- County dropdown requires backend API for data
- "Import CSV" action not yet fully implemented (TODO in code)
- Period selector UI only - not connected to data filtering yet

---

## Claude Test Coverage

The following scenarios are covered by unit tests in `TopBar.test.tsx`:

| Test | Status |
|------|--------|
| Renders title | PASS |
| Renders search input | PASS |
| Renders Filters button | PASS |
| Renders Actions button | PASS |
| Renders period selector | PASS |
| Search input updates on type | PASS |
| Calls onSearchChange callback | PASS |
| Opens filter popover on click | PASS |
| Shows county dropdown in popover | PASS |
| Closes popover on Apply | PASS |
| Calls onFiltersChange on apply | PASS |
| Resets filters on Reset click | PASS |
| Opens actions dropdown | PASS |
| Period selector has correct default | PASS |
| Period selector has all options | PASS |

---

## Gemini Report

_To be filled in after testing:_

**Pass/Fail Summary:** _ of 7 scenarios passed

**Issues Found:**
1.

**Screenshots:**
-

**Observations:**
-
