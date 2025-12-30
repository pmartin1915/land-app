import { defineConfig } from '@playwright/test';

/**
 * Playwright configuration for Tauri Desktop E2E Tests
 *
 * This configuration is specifically for testing the built Tauri desktop app.
 * It uses WebDriver protocol via tauri-driver to interact with the native window.
 *
 * Prerequisites:
 * 1. Build the Tauri app: npm run tauri:build
 * 2. Install tauri-driver: cargo install tauri-driver
 *
 * Usage:
 *   npm run test:e2e:tauri
 */
export default defineConfig({
  testDir: './e2e',
  testMatch: ['**/*.tauri.spec.ts', '**/smoke.spec.ts'],

  // Tauri tests must run serially
  fullyParallel: false,
  workers: 1,

  // More retries for desktop tests (can be flaky)
  retries: 2,

  // Longer timeout for desktop app startup
  timeout: 60000,

  expect: {
    timeout: 15000,
  },

  reporter: [
    ['html', { outputFolder: 'playwright-report-tauri' }],
    ['list'],
  ],

  use: {
    // For Tauri, we connect via WebDriver
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
  },

  projects: [
    {
      name: 'tauri-desktop',
      use: {
        // Note: Actual Tauri testing requires webdriver-style connection
        // This is a placeholder - full Tauri testing requires additional setup
        // See: https://tauri.app/v1/guides/testing/webdriver
      },
    },
  ],

  // Backend still needs to run for Tauri tests
  webServer: [
    {
      command: 'node e2e/utils/start-backend.js',
      url: 'http://localhost:8001/health',
      timeout: 60000,
      reuseExistingServer: true,
      stdout: 'pipe',
      stderr: 'pipe',
    },
  ],

  outputDir: 'test-results-tauri',
});
