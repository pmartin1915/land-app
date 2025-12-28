# Playwright MCP Integration for Alabama Auction Watcher

This folder contains tools for AI-driven UI testing using Playwright.

## Quick Start

### Option 1: Standalone Control Server (Works Now)

Start the server that Claude/Gemini can control via HTTP:

```bash
cd c:\auction\tools\playwright-mcp
node server.js
```

The server runs on `http://localhost:3333` and provides endpoints:
- `POST /navigate` - Navigate to a URL
- `POST /screenshot` - Take screenshots
- `POST /click` - Click elements
- `POST /type` - Type into inputs
- `GET /accessibility` - Get page structure for LLM parsing

### Option 2: Claude Desktop MCP Integration

1. Install [Claude Desktop](https://claude.ai/download)
2. Copy `claude_desktop_config.json` contents to:
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`
3. Restart Claude Desktop

Then you can tell Claude: "Use playwright to open http://localhost:1420"

### Option 3: Quick UI Test

Run the automated test script:

```bash
node test-ui.js
```

This navigates through Dashboard, Map, and Triage views, taking screenshots.

## Using with Claude Code

Once the control server is running, you can ask Claude to:

1. Navigate: "Fetch http://localhost:3333/navigate with body {url: 'http://localhost:1420/dashboard'}"
2. Screenshot: "Take a screenshot by posting to http://localhost:3333/screenshot"
3. Interact: "Click the Triage button by posting to http://localhost:3333/click with {text: 'Triage'}"

## Screenshots

All screenshots are saved to `tools/playwright-mcp/screenshots/`
