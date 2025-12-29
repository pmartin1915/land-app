# Claude-to-Gemini Test Handoff Template

This template standardizes how Claude communicates testing requirements to Gemini for interactive UI testing in Antigravity.

---

## Template Structure

```markdown
## Feature: [Feature Name]

**Date:** [YYYY-MM-DD]
**Commit/Branch:** [git ref]
**Claude Session:** [session identifier if applicable]

### Summary
[1-2 sentence description of what was implemented]

### Files Changed
- `path/to/file1.tsx` - [brief description]
- `path/to/file2.ts` - [brief description]

### Prerequisites
- [ ] Backend API running on port 8001
- [ ] Frontend dev server running on port 5173
- [ ] [Any test data requirements]
- [ ] [User state requirements - logged in, specific role, etc.]

---

### Test Scenarios

#### Scenario 1: [Happy Path Name]

**Precondition:** [Starting state - e.g., "Logged in as test@example.com, on Dashboard page"]

**Steps:**
1. [Action 1 - e.g., "Click the 'Add to Watchlist' button (star icon)"]
2. [Action 2]
3. [Action 3]

**Expected Visual Outcomes:**
- [ ] [Visual check 1 - e.g., "Star icon changes from outline to solid yellow"]
- [ ] [Visual check 2 - e.g., "Toast notification 'Added to Watchlist' appears top-right"]
- [ ] [Visual check 3 - e.g., "Toast disappears after 3 seconds"]

**Expected Functional Outcomes:**
- [ ] [Functional check - e.g., "Item appears in Watchlist page"]

---

#### Scenario 2: [Edge Case / Error State]

**Precondition:** [Starting state]

**Steps:**
1. [Action that triggers edge case]

**Expected Outcomes:**
- [ ] [What should happen]
- [ ] [Error message if applicable]

---

#### Scenario 3: [Accessibility Check]

**Check these accessibility items:**
- [ ] All interactive elements are keyboard navigable (Tab key)
- [ ] Focus indicators are visible
- [ ] Color contrast is sufficient for readability
- [ ] Screen reader announcements are appropriate (if applicable)

---

### Visual Regression Points

**Verify these UI elements are correctly styled:**
- [ ] [Component 1] - [expected appearance]
- [ ] [Component 2] - [expected appearance]
- [ ] Dark mode: [any theme-specific checks]
- [ ] Light mode: [any theme-specific checks]

---

### Known Limitations / Out of Scope
- [Things Gemini should NOT test or expect to work]
- [Backend features not yet implemented]

---

### Gemini Report Template

After testing, Gemini should report back with:

1. **Pass/Fail Summary:** X of Y scenarios passed
2. **Screenshots:** Attach for any failures
3. **Issues Found:** List with severity (Critical/High/Medium/Low)
4. **Observations:** Any UX concerns or suggestions
```

---

## Example: Filter Popover Feature

```markdown
## Feature: Advanced Filter Popover

**Date:** 2025-12-29
**Commit:** 1f7c8c6
**Branch:** main

### Summary
Implemented an advanced filter popover in the TopBar component allowing users to filter properties by price range, acreage, county, water access, and various scores.

### Files Changed
- `frontend/src/components/TopBar.tsx` - Added FilterPopover component
- `frontend/src/lib/hooks.ts` - useCounties hook for dropdown

### Prerequisites
- [ ] Backend API running (for counties list)
- [ ] Frontend dev server running
- [ ] At least 3 counties in database

---

### Test Scenarios

#### Scenario 1: Open and Close Filter Popover

**Precondition:** On any page with TopBar visible

**Steps:**
1. Click the "Filters" button in the TopBar
2. Verify popover opens
3. Press Escape key

**Expected Visual Outcomes:**
- [ ] Popover slides in below the Filters button
- [ ] "Advanced Filters" heading is visible
- [ ] X close button is in top-right of popover
- [ ] Popover closes on Escape key press

---

#### Scenario 2: Apply Price Range Filter

**Precondition:** Filter popover is open

**Steps:**
1. Enter "5000" in the Min price field
2. Enter "50000" in the Max price field
3. Click "Apply Filters"

**Expected Visual Outcomes:**
- [ ] Popover closes
- [ ] Filters button shows badge with "1" (indicating 1 active filter)
- [ ] Filters button background changes to accent color (blue)

---

#### Scenario 3: Reset All Filters

**Precondition:** At least one filter is applied (badge showing)

**Steps:**
1. Open filter popover
2. Click "Reset" button

**Expected Visual Outcomes:**
- [ ] All input fields clear
- [ ] Popover closes
- [ ] Filter badge disappears
- [ ] Filters button returns to default gray styling

---

#### Scenario 4: County Dropdown Population

**Precondition:** Filter popover is open, backend running

**Steps:**
1. Click the County dropdown

**Expected Visual Outcomes:**
- [ ] "All Counties" is first option
- [ ] Counties from database appear in list
- [ ] Selecting a county populates the field

---

#### Scenario 5: Water Access Toggle

**Precondition:** Filter popover is open

**Steps:**
1. Click the "Water access only" checkbox

**Expected Visual Outcomes:**
- [ ] Checkbox becomes checked with accent color
- [ ] Label remains readable

---

### Visual Regression Points

- [ ] Popover has correct border radius (rounded-lg)
- [ ] Input fields have consistent styling
- [ ] Buttons have proper hover states
- [ ] Dark mode: popover background is card color, text is readable
- [ ] Light mode: same checks

### Known Limitations
- Filters are client-side only until Apply is clicked
- Score filters (Investment, County Market, Geographic) not yet connected to backend filtering
```

---

## Workflow Integration

### When Claude completes a feature:

1. Claude writes unit/component tests (Vitest + RTL)
2. Claude creates a handoff document using this template
3. Claude saves it to `docs/test-handoffs/[feature-name].md`
4. User can pass the handoff to Gemini for interactive testing

### When Gemini completes testing:

1. Gemini adds results to the handoff document
2. Reports any failures with screenshots
3. Claude addresses issues based on Gemini's findings

---

## Quick Reference: Visual Check Categories

| Category | Example Checks |
|----------|---------------|
| **Layout** | Elements aligned, spacing correct, responsive |
| **Colors** | Brand colors, contrast, theme consistency |
| **Typography** | Font sizes, weights, readability |
| **States** | Hover, focus, active, disabled, loading |
| **Animations** | Transitions smooth, timing appropriate |
| **Responsiveness** | Works at different window sizes |
| **Accessibility** | Keyboard nav, focus visible, color contrast |
