"""
Playwright configuration for the Alabama Auction Watcher project.

This configuration file defines settings for the Playwright test runner.
For pytest-playwright, most configuration is handled via pytest.ini and fixtures.

This file provides:
- Project-wide constants (ports, URLs, directories)
- Configuration class for reference
- Documentation of settings

Usage:
- Run UI tests: pytest tests/ui -v
- Update visual snapshots: pytest tests/ui --update-snapshots
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

# Project root directory
ROOT_DIR = Path(__file__).parent

# Default port for Streamlit app
STREAMLIT_PORT = 8501

# Playwright Test configuration class
class PlaywrightConfig:
    """
    Configuration settings for Playwright UI tests.

    Note: pytest-playwright uses pytest.ini and fixtures for actual configuration.
    This class serves as a reference for all configurable settings.
    """
    browser: str = "chromium"
    headless: bool = not os.getenv("HEADED", "false").lower() == "true"
    base_url: str = f"http://localhost:{STREAMLIT_PORT}"
    viewport: Dict[str, int] = {"width": 1920, "height": 1080}
    screenshot_dir: str = "test-results/screenshots"
    trace: str = "on-first-retry"
    video: str = "retain-on-failure"

    # Visual testing configuration
    snapshot_dir: str = "tests/ui/visual"
    update_snapshots: bool = os.getenv("UPDATE_SNAPSHOTS", "false").lower() == "true"

    # Timeout settings
    timeout: int = 30000  # 30 seconds default
    navigation_timeout: int = 30000
