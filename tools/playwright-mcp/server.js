/**
 * Playwright Control Server for AI-driven UI Testing
 *
 * This server allows Claude/Gemini to control a browser and test the UI.
 *
 * Usage:
 *   node server.js
 *
 * Then the AI can make HTTP requests to control the browser:
 *   POST /navigate - Navigate to a URL
 *   POST /screenshot - Take a screenshot
 *   POST /click - Click an element
 *   POST /type - Type into an input
 *   GET /status - Get current page info
 *   GET /accessibility - Get accessibility tree (for LLM-friendly parsing)
 */

const express = require('express');
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 3333;

app.use(express.json());

let browser;
let context;
let page;
let consoleLogs = [];
let networkRequests = [];
let customHeaders = {};

// Ensure screenshots directory exists
const screenshotsDir = path.join(__dirname, 'screenshots');
if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir, { recursive: true });
}

async function ensurePage() {
    if (!browser) {
        console.log('Launching browser (visible mode)...');
        browser = await chromium.launch({
            headless: false,  // Visible browser so you can see what AI is doing
            slowMo: 100       // Slow down actions for visibility
        });
    }
    if (!context) {
        console.log('Creating browser context...');
        context = await browser.newContext();
        if (Object.keys(customHeaders).length > 0) {
            await context.setExtraHTTPHeaders(customHeaders);
        }
    }
    if (!page || page.isClosed()) {
        console.log('Creating new page...');
        page = await context.newPage();
        await page.setViewportSize({ width: 1280, height: 800 });

        // Set up console log capture
        page.on('console', msg => {
            consoleLogs.push({
                type: msg.type(),
                text: msg.text(),
                timestamp: new Date().toISOString()
            });
            // Keep only last 100 logs
            if (consoleLogs.length > 100) consoleLogs.shift();
        });

        page.on('pageerror', error => {
            consoleLogs.push({
                type: 'error',
                text: error.message,
                timestamp: new Date().toISOString()
            });
        });

        // Set up network request capture
        page.on('response', response => {
            networkRequests.push({
                url: response.url(),
                status: response.status(),
                method: response.request().method(),
                timestamp: new Date().toISOString()
            });
            // Keep only last 50 requests
            if (networkRequests.length > 50) networkRequests.shift();
        });
    }
    return page;
}

// Navigate to URL
app.post('/navigate', async (req, res) => {
    const { url } = req.body;
    if (!url) {
        return res.status(400).json({ error: 'URL is required' });
    }
    try {
        const currentPage = await ensurePage();
        console.log(`Navigating to: ${url}`);
        await currentPage.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
        res.json({
            success: true,
            currentUrl: currentPage.url(),
            title: await currentPage.title()
        });
    } catch (error) {
        console.error('Navigation error:', error.message);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Take screenshot
app.post('/screenshot', async (req, res) => {
    const { filename, selector, fullPage } = req.body;
    const outputPath = path.join(screenshotsDir, filename || `screenshot-${Date.now()}.png`);
    try {
        const currentPage = await ensurePage();
        console.log(`Taking screenshot: ${outputPath}`);

        if (selector) {
            const element = await currentPage.$(selector);
            if (element) {
                await element.screenshot({ path: outputPath });
            } else {
                return res.status(404).json({ error: `Element "${selector}" not found` });
            }
        } else {
            await currentPage.screenshot({ path: outputPath, fullPage: fullPage !== false });
        }

        // Return base64 for AI to analyze
        const imageBuffer = fs.readFileSync(outputPath);
        const base64 = imageBuffer.toString('base64');

        res.json({
            success: true,
            path: outputPath,
            base64: base64,
            size: imageBuffer.length
        });
    } catch (error) {
        console.error('Screenshot error:', error.message);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Click element
app.post('/click', async (req, res) => {
    const { selector, text } = req.body;
    try {
        const currentPage = await ensurePage();

        if (text) {
            // Click by text content
            console.log(`Clicking element with text: "${text}"`);
            await currentPage.click(`text="${text}"`);
        } else if (selector) {
            console.log(`Clicking selector: ${selector}`);
            await currentPage.click(selector);
        } else {
            return res.status(400).json({ error: 'Selector or text is required' });
        }

        // Wait for any navigation or state changes
        await currentPage.waitForTimeout(500);

        res.json({ success: true, currentUrl: currentPage.url() });
    } catch (error) {
        console.error('Click error:', error.message);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Type into element
app.post('/type', async (req, res) => {
    const { selector, text, clear } = req.body;
    if (!selector || text === undefined) {
        return res.status(400).json({ error: 'Selector and text are required' });
    }
    try {
        const currentPage = await ensurePage();
        console.log(`Typing "${text}" into: ${selector}`);

        if (clear) {
            await currentPage.fill(selector, text);
        } else {
            await currentPage.type(selector, text);
        }

        res.json({ success: true });
    } catch (error) {
        console.error('Type error:', error.message);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Get page status
app.get('/status', async (req, res) => {
    try {
        const currentPage = await ensurePage();
        res.json({
            success: true,
            currentUrl: currentPage.url(),
            title: await currentPage.title()
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Get accessibility tree (LLM-friendly page structure)
app.get('/accessibility', async (req, res) => {
    try {
        const currentPage = await ensurePage();
        const snapshot = await currentPage.accessibility.snapshot();
        res.json({
            success: true,
            tree: snapshot,
            url: currentPage.url()
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Get all visible text on page
app.get('/text', async (req, res) => {
    try {
        const currentPage = await ensurePage();
        const text = await currentPage.evaluate(() => document.body.innerText);
        res.json({
            success: true,
            text: text,
            url: currentPage.url()
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Execute JavaScript on page
app.post('/evaluate', async (req, res) => {
    const { script } = req.body;
    if (!script) {
        return res.status(400).json({ error: 'Script is required' });
    }
    try {
        const currentPage = await ensurePage();
        console.log(`Evaluating script...`);
        const result = await currentPage.evaluate(script);
        res.json({ success: true, result });
    } catch (error) {
        console.error('Evaluate error:', error.message);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Configure session (auth headers, viewport)
app.post('/configure', async (req, res) => {
    const { headers, viewport } = req.body;
    try {
        // Store custom headers for future contexts
        if (headers) {
            customHeaders = { ...customHeaders, ...headers };
            console.log('Custom headers configured:', Object.keys(headers));

            // If context exists, update it
            if (context) {
                await context.setExtraHTTPHeaders(customHeaders);
            }
        }

        // Update viewport if provided
        if (viewport && page) {
            await page.setViewportSize(viewport);
            console.log(`Viewport set to: ${viewport.width}x${viewport.height}`);
        }

        res.json({
            success: true,
            headers: Object.keys(customHeaders),
            viewport: viewport || { width: 1280, height: 800 }
        });
    } catch (error) {
        console.error('Configure error:', error.message);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Set viewport size (for responsive testing)
app.post('/viewport', async (req, res) => {
    const { width, height } = req.body;
    if (!width || !height) {
        return res.status(400).json({ error: 'Width and height are required' });
    }
    try {
        const currentPage = await ensurePage();
        await currentPage.setViewportSize({ width, height });
        console.log(`Viewport changed to: ${width}x${height}`);
        res.json({ success: true, viewport: { width, height } });
    } catch (error) {
        console.error('Viewport error:', error.message);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Get console logs (for debugging)
app.get('/console-logs', async (req, res) => {
    const { clear, type } = req.query;
    try {
        let logs = [...consoleLogs];

        // Filter by type if specified
        if (type) {
            logs = logs.filter(log => log.type === type);
        }

        // Clear logs if requested
        if (clear === 'true') {
            consoleLogs = [];
        }

        res.json({
            success: true,
            count: logs.length,
            logs: logs
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Get network activity (for detecting failed API calls)
app.get('/network-activity', async (req, res) => {
    const { clear, status } = req.query;
    try {
        let requests = [...networkRequests];

        // Filter by status code if specified (e.g., "4xx" or "401")
        if (status) {
            if (status.endsWith('xx')) {
                const prefix = parseInt(status[0]);
                requests = requests.filter(r => Math.floor(r.status / 100) === prefix);
            } else {
                requests = requests.filter(r => r.status === parseInt(status));
            }
        }

        // Clear if requested
        if (clear === 'true') {
            networkRequests = [];
        }

        res.json({
            success: true,
            count: requests.length,
            requests: requests
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Get combined status with accessibility tree (AI-friendly)
app.get('/observe', async (req, res) => {
    try {
        const currentPage = await ensurePage();
        let snapshot = null;
        try {
            snapshot = await currentPage.accessibility.snapshot();
        } catch (e) {
            console.log('Accessibility snapshot not available:', e.message);
        }

        // Get recent errors
        const recentErrors = consoleLogs.filter(l => l.type === 'error').slice(-5);
        const failedRequests = networkRequests.filter(r => r.status >= 400).slice(-5);

        res.json({
            success: true,
            url: currentPage.url(),
            title: await currentPage.title(),
            accessibility: snapshot,
            recentErrors: recentErrors,
            failedRequests: failedRequests
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Shutdown
app.post('/close', async (req, res) => {
    try {
        if (browser) {
            await browser.close();
            browser = null;
            context = null;
            page = null;
        }
        // Reset state
        consoleLogs = [];
        networkRequests = [];
        customHeaders = {};
        res.json({ success: true, message: 'Browser closed and state reset' });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.listen(PORT, async () => {
    console.log(`\n========================================`);
    console.log(`  Playwright Control Server (AI-Enhanced)`);
    console.log(`  Running on http://localhost:${PORT}`);
    console.log(`========================================\n`);
    console.log(`Core Endpoints:`);
    console.log(`  POST /navigate     - { url: "..." }`);
    console.log(`  POST /screenshot   - { filename?, selector?, fullPage? }`);
    console.log(`  POST /click        - { selector? or text? }`);
    console.log(`  POST /type         - { selector, text, clear? }`);
    console.log(`  GET  /status       - Current page info`);
    console.log(`  GET  /text         - All visible text`);
    console.log(`  POST /evaluate     - { script: "..." }`);
    console.log(`  POST /close        - Close browser\n`);
    console.log(`AI Integration Endpoints:`);
    console.log(`  POST /configure    - { headers?, viewport? } - Set auth headers`);
    console.log(`  POST /viewport     - { width, height } - Responsive testing`);
    console.log(`  GET  /accessibility - Page accessibility tree`);
    console.log(`  GET  /observe      - Combined status + accessibility + errors`);
    console.log(`  GET  /console-logs - Browser console logs (?clear=true&type=error)`);
    console.log(`  GET  /network-activity - API calls (?status=4xx)\n`);

    // Pre-launch browser
    await ensurePage();
    console.log('Browser ready!\n');
});

process.on('SIGINT', async () => {
    console.log('\nShutting down...');
    if (browser) await browser.close();
    process.exit(0);
});
