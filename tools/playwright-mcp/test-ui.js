/**
 * Quick UI Test Script
 *
 * This script tests the Alabama Auction Watcher frontend UI.
 * Run it to verify Playwright is working correctly.
 *
 * Usage: node test-ui.js
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const FRONTEND_URL = 'http://localhost:5173';
const SCREENSHOTS_DIR = path.join(__dirname, 'screenshots');

async function testUI() {
    console.log('Starting UI test...\n');

    // Ensure screenshots directory
    if (!fs.existsSync(SCREENSHOTS_DIR)) {
        fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
    }

    const browser = await chromium.launch({
        headless: false,
        slowMo: 200
    });

    const page = await browser.newPage();
    await page.setViewportSize({ width: 1280, height: 800 });

    try {
        // Test 1: Navigate to Dashboard
        console.log('1. Navigating to Dashboard...');
        await page.goto(`${FRONTEND_URL}/dashboard`, { waitUntil: 'networkidle' });
        await page.screenshot({
            path: path.join(SCREENSHOTS_DIR, '01-dashboard.png'),
            fullPage: true
        });
        console.log('   Dashboard loaded successfully');

        // Test 2: Check for Research Pipeline section
        console.log('2. Looking for Research Pipeline...');
        const pipeline = await page.$('text=Research Pipeline');
        if (pipeline) {
            console.log('   Research Pipeline section found');
        } else {
            console.log('   WARNING: Research Pipeline section not found');
        }

        // Test 3: Navigate to Map
        console.log('3. Navigating to Map view...');
        await page.click('text=Map');
        await page.waitForTimeout(1000);
        await page.screenshot({
            path: path.join(SCREENSHOTS_DIR, '02-map.png'),
            fullPage: true
        });
        console.log('   Map view loaded');

        // Test 4: Navigate to Triage
        console.log('4. Navigating to Triage view...');
        await page.click('text=Triage');
        await page.waitForTimeout(1000);
        await page.screenshot({
            path: path.join(SCREENSHOTS_DIR, '03-triage.png'),
            fullPage: true
        });
        console.log('   Triage view loaded');

        // Test 5: Get accessibility tree
        console.log('5. Getting accessibility snapshot...');
        const accessibility = await page.accessibility.snapshot();
        fs.writeFileSync(
            path.join(SCREENSHOTS_DIR, 'accessibility.json'),
            JSON.stringify(accessibility, null, 2)
        );
        console.log('   Accessibility tree saved');

        console.log('\n========================================');
        console.log('  UI Test Complete');
        console.log(`  Screenshots saved to: ${SCREENSHOTS_DIR}`);
        console.log('========================================\n');

    } catch (error) {
        console.error('Test failed:', error.message);
        await page.screenshot({
            path: path.join(SCREENSHOTS_DIR, 'error.png'),
            fullPage: true
        });
    } finally {
        await browser.close();
    }
}

testUI().catch(console.error);
