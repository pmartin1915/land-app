"""
Shared utilities for scraper implementations.

Provides common functionality used across multiple state scrapers:
- Exit codes for subprocess communication
- Debug snapshot saving for failure diagnosis
"""

from pathlib import Path
from datetime import datetime
from typing import Optional
import logging

project_root = Path(__file__).parent.parent.parent
DEBUG_SNAPSHOT_DIR = project_root / 'debug_failures'

# Exit codes for subprocess communication with factory.py
# These must match the constants in factory.py
EXIT_SUCCESS = 0
EXIT_TRANSIENT = 1   # Network error, timeout, selector not found - RETRY
EXIT_PERMANENT = 2   # Auth failure, major layout change - NO RETRY
EXIT_RATE_LIMIT = 3  # HTTP 429 or access denied - LONG BACKOFF


def save_debug_snapshot(
    content: str,
    state: str,
    county: str,
    error: str,
    extension: str = 'html',
    logger: Optional[logging.Logger] = None
) -> Optional[Path]:
    """
    Save content snapshot when parsing fails for debugging.

    Enables diagnosing site layout changes or parse failures without
    re-running the scraper.

    Args:
        content: HTML/JSON content to save
        state: Two-letter state code (AL, AR, TX)
        county: County name for filename
        error: Error description for logging
        extension: File extension (html, json)
        logger: Optional logger instance for status messages

    Returns:
        Path to saved file, or None if save failed
    """
    try:
        DEBUG_SNAPSHOT_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # Sanitize county name for filename
        safe_county = county.replace(' ', '_').replace('/', '_')
        filename = f"{state}_{safe_county}_{timestamp}.{extension}"
        filepath = DEBUG_SNAPSHOT_DIR / filename

        filepath.write_text(content, encoding='utf-8')

        if logger:
            logger.info(f"Saved debug snapshot: {filepath}")

        return filepath
    except Exception as e:
        if logger:
            logger.warning(f"Failed to save debug snapshot: {e}")
        return None
