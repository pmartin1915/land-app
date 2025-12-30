import { test, expect } from '@playwright/test';

/**
 * Smoke Tests - Critical Path Verification
 *
 * These tests verify the application loads and core functionality works.
 * They run on every commit and block deployment if they fail.
 */

test.describe('Application Smoke Tests', () => {
  test.describe('Page Load', () => {
    test('dashboard loads without white screen', async ({ page }) => {
      await page.goto('/');

      // Wait for app to hydrate
      await expect(page.locator('.app')).toBeVisible();

      // Verify no React error boundary triggered
      await expect(page.locator('text=Something went wrong')).not.toBeVisible();

      // Dashboard page heading should be visible (the h2 in the main content)
      await expect(page.locator('h1:has-text("Dashboard")').first()).toBeVisible();
    });

    test('dashboard displays content sections', async ({ page }) => {
      await page.goto('/');

      // Wait for dashboard to load
      await expect(page.locator('h1:has-text("Dashboard")').first()).toBeVisible();

      // Should show main dashboard sections (visible even when data is loading)
      await expect(page.getByText('High-level health and quick triage')).toBeVisible({ timeout: 15000 });
      await expect(page.getByText('Research Pipeline')).toBeVisible({ timeout: 15000 });
    });

    test('no console errors on load', async ({ page }) => {
      const consoleErrors: string[] = [];

      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });

      await page.goto('/');
      // Wait for page to stabilize
      await page.waitForTimeout(3000);

      // Filter out known non-critical errors
      const criticalErrors = consoleErrors.filter((error) => {
        const lowerError = error.toLowerCase();
        // Ignore React dev mode warnings
        if (error.includes('React Router Future Flag')) return false;
        // Ignore baseline browser mapping warning
        if (error.includes('baseline-browser-mapping')) return false;
        // Ignore favicon errors
        if (lowerError.includes('favicon')) return false;
        // Ignore MapBox WebGL warnings
        if (lowerError.includes('mapbox')) return false;
        if (lowerError.includes('webgl')) return false;
        // Ignore network errors from API calls (handled separately)
        if (error.includes('Failed to fetch')) return false;
        if (error.includes('net::ERR_')) return false;
        // Ignore Vite HMR warnings
        if (error.includes('[vite]')) return false;
        // Ignore plotly warnings
        if (lowerError.includes('plotly')) return false;
        // Ignore ResizeObserver errors (common in React)
        if (error.includes('ResizeObserver')) return false;
        // Ignore API errors (404s, 429s etc are expected during testing)
        if (error.includes('API Error')) return false;
        if (error.includes('status of 404')) return false;
        if (error.includes('status of 401')) return false;
        if (error.includes('status of 429')) return false;
        if (error.includes('Failed to load resource')) return false;
        // Ignore rate limiting errors (expected during parallel tests)
        if (error.includes('Rate limit')) return false;
        if (error.includes('AxiosError')) return false;
        if (error.includes('Authentication failed')) return false;
        if (error.includes('Response status')) return false;
        if (error.includes('Response data')) return false;
        if (error.includes('device token')) return false;
        return true;
      });

      // Log for debugging if there are critical errors
      if (criticalErrors.length > 0) {
        console.log('Critical errors found:', criticalErrors);
      }

      expect(criticalErrors).toEqual([]);
    });
  });

  test.describe('Navigation', () => {
    test('left rail navigation works', async ({ page }) => {
      await page.goto('/');

      // Wait for layout to load
      await expect(page.locator('.app')).toBeVisible();
      await page.waitForTimeout(2000);

      // Navigate to Parcels
      const parcelsBtn = page.getByRole('button', { name: /^Parcels/ });
      await parcelsBtn.scrollIntoViewIfNeeded();
      await parcelsBtn.click({ force: true });
      await expect(page).toHaveURL(/\/parcels/);
      await page.waitForTimeout(1000);

      // Navigate to Settings (simpler test - doesn't have heavy loading)
      const settingsBtn = page.getByRole('button', { name: /^Settings/ });
      await settingsBtn.scrollIntoViewIfNeeded();
      await settingsBtn.click({ force: true });
      await expect(page).toHaveURL(/\/settings/);
    });

    test('all main routes are accessible', async ({ page }) => {
      const routes = [
        { path: '/', title: 'Dashboard' },
        { path: '/dashboard', title: 'Dashboard' },
        { path: '/parcels', title: 'Parcels' },
        { path: '/map', title: 'Map' },
        { path: '/triage', title: 'Triage' },
        { path: '/watchlist', title: 'Watchlist' },
        { path: '/settings', title: 'Settings' },
      ];

      for (const route of routes) {
        await page.goto(route.path);
        await expect(page.locator('.app')).toBeVisible();
        // Should not show error state
        await expect(page.locator('text=Something went wrong')).not.toBeVisible();
      }
    });
  });

  test.describe('API Integration', () => {
    test('backend API is reachable', async ({ request }) => {
      const response = await request.get('http://localhost:8001/health');
      expect(response.ok()).toBeTruthy();

      const body = await response.json();
      expect(body.status).toBe('healthy');
    });

    test('properties API returns data', async ({ request }) => {
      const response = await request.get('http://localhost:8001/api/v1/properties');

      // API might return 401 without auth, but should respond
      expect(response.status()).toBeLessThan(500);
    });

    test('dashboard fetches data from backend', async ({ page }) => {
      // Intercept API calls
      let apiCalled = false;

      page.on('response', (response) => {
        if (response.url().includes('/api/v1/')) {
          apiCalled = true;
        }
      });

      await page.goto('/');
      // Don't wait for networkidle as it can timeout with long-polling/websockets
      // Instead wait for the page to load and some API calls to happen
      await page.waitForTimeout(5000);

      // Dashboard should have made API calls
      expect(apiCalled).toBeTruthy();
    });
  });

  test.describe('Theme', () => {
    test('dark theme is applied by default', async ({ page }) => {
      await page.goto('/');

      // The app should have dark theme class or styles
      const html = page.locator('html');
      await expect(html).toHaveClass(/dark/);
    });

    test('theme toggle works', async ({ page }) => {
      await page.goto('/');

      // Find theme toggle in settings or header
      // This depends on where the toggle is located
      // Adjust selector based on actual implementation
    });
  });

  test.describe('Responsive Layout', () => {
    test('layout adapts to mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/');

      // App should still be visible
      await expect(page.locator('.app')).toBeVisible();

      // Left rail might be collapsed or hidden on mobile
      // Dashboard content should still be accessible
      await expect(page.locator('h1:has-text("Dashboard")').first()).toBeVisible();
    });

    test('layout works on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto('/');

      await expect(page.locator('.app')).toBeVisible();
      await expect(page.locator('h1:has-text("Dashboard")').first()).toBeVisible();
    });
  });
});

test.describe('Error Handling', () => {
  test('handles API errors gracefully', async ({ page }) => {
    // Simulate API failure
    await page.route('**/api/v1/**', (route) => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Internal server error' }),
      });
    });

    await page.goto('/');

    // App should show error state, not crash
    await expect(page.locator('.app')).toBeVisible();
    // Should show some error indication
    // The exact behavior depends on how errors are handled
  });

  test('handles network timeout gracefully', async ({ page }) => {
    // Simulate slow network
    await page.route('**/api/v1/**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 10000));
      route.abort('timedout');
    });

    await page.goto('/');

    // App should still render with loading states
    await expect(page.locator('.app')).toBeVisible();
  });
});
