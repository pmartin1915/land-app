"""
Scraper Factory for dispatching scrape jobs to appropriate state scrapers.

Provides a unified interface for running scrapers across different states,
returning standardized results regardless of the underlying scraper implementation.

Features:
- Subprocess isolation for Playwright scrapers (Windows asyncio compatibility)
- Exponential backoff retry logic with semantic exit codes
- Configurable timeouts per scraper type
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import subprocess
import json
import tempfile
import os
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.states import get_state_config
from config.logging_config import get_logger

logger = get_logger(__name__)

# Retry configuration
MAX_RETRIES = 3
BASE_DELAY = 2.0  # seconds
MAX_DELAY = 30.0  # seconds
RATE_LIMIT_DELAY = 60.0  # seconds - cooldown for rate limiting

# Import exit codes from shared utils module
from .utils import EXIT_SUCCESS, EXIT_TRANSIENT, EXIT_PERMANENT, EXIT_RATE_LIMIT


@dataclass
class ScrapeResult:
    """Standardized result from any scraper."""
    properties: List[Dict[str, Any]]
    items_found: int
    error_message: Optional[str] = None


async def _run_subprocess_with_retry(
    script_path: Path,
    args: List[str],
    timeout: int,
    state_name: str
) -> ScrapeResult:
    """
    Run a scraper subprocess with exponential backoff retry.

    Args:
        script_path: Path to the scraper Python script
        args: Command line arguments for the scraper
        timeout: Timeout in seconds for each attempt
        state_name: State name for logging (e.g., 'Alabama', 'Texas')

    Returns:
        ScrapeResult with properties or error message
    """
    last_error = "Unknown error"

    for attempt in range(MAX_RETRIES):
        # Create temp file for JSON output
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = f.name

        process = None
        try:
            # Build command with JSON output
            cmd = ['python', str(script_path)] + args + ['--json-output', output_file]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(project_root)
            )

            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                logger.warning(f"{state_name} scraper timed out on attempt {attempt + 1}/{MAX_RETRIES}")
                # Graceful termination: try SIGTERM first, then SIGKILL
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

                if attempt < MAX_RETRIES - 1:
                    delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                    logger.info(f"Retrying {state_name} in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    return ScrapeResult(
                        properties=[],
                        items_found=0,
                        error_message=f"{state_name} scraper timed out after {MAX_RETRIES} attempts"
                    )

            # Log stderr for debugging (even on success)
            if stderr and stderr.strip():
                logger.debug(f"{state_name} stderr: {stderr.strip()}")

            # Handle exit codes
            if process.returncode == EXIT_SUCCESS:
                # Success - read results
                if os.path.exists(output_file):
                    with open(output_file, 'r') as f:
                        prop_dicts = json.load(f)
                else:
                    prop_dicts = []

                logger.info(f"{state_name} scrape complete: {len(prop_dicts)} properties")
                return ScrapeResult(
                    properties=prop_dicts,
                    items_found=len(prop_dicts)
                )

            elif process.returncode == EXIT_TRANSIENT:
                # Transient error - retry with backoff
                last_error = stderr.strip() if stderr else "Transient error"
                logger.warning(f"{state_name} transient error on attempt {attempt + 1}/{MAX_RETRIES}: {last_error}")

                if attempt < MAX_RETRIES - 1:
                    delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                    logger.info(f"Retrying {state_name} in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    continue

            elif process.returncode == EXIT_RATE_LIMIT:
                # Rate limited - longer backoff
                last_error = stderr.strip() if stderr else "Rate limited"
                logger.warning(f"{state_name} rate limited on attempt {attempt + 1}/{MAX_RETRIES}")

                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Rate limit cooldown: waiting {RATE_LIMIT_DELAY}s...")
                    await asyncio.sleep(RATE_LIMIT_DELAY)
                    continue

            elif process.returncode == EXIT_PERMANENT:
                # Permanent error - don't retry
                last_error = stderr.strip() if stderr else "Permanent error"
                logger.error(f"{state_name} permanent error: {last_error}")
                return ScrapeResult(
                    properties=[],
                    items_found=0,
                    error_message=f"{state_name} scraper failed: {last_error}"
                )

            else:
                # Unknown exit code - treat as transient
                last_error = stderr.strip() if stderr else f"Unknown exit code: {process.returncode}"
                logger.warning(f"{state_name} unknown exit code {process.returncode}: {last_error}")

                if attempt < MAX_RETRIES - 1:
                    delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                    await asyncio.sleep(delay)
                    continue

        except Exception as e:
            last_error = str(e)
            logger.error(f"{state_name} scraper exception on attempt {attempt + 1}: {e}")

            # Ensure subprocess is terminated (graceful then force)
            if process and process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                except Exception:
                    pass

            if attempt < MAX_RETRIES - 1:
                delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                await asyncio.sleep(delay)
                continue

        finally:
            # Always clean up temp file
            if os.path.exists(output_file):
                try:
                    os.unlink(output_file)
                except OSError:
                    pass

    # All retries exhausted
    return ScrapeResult(
        properties=[],
        items_found=0,
        error_message=f"{state_name} scraper failed after {MAX_RETRIES} attempts: {last_error}"
    )


class ScraperFactory:
    """
    Factory for creating and running state-specific scrapers.

    Usage:
        result = await ScraperFactory.scrape(state='AR', county='Pulaski')
        if result.error_message:
            print(f"Error: {result.error_message}")
        else:
            print(f"Found {result.items_found} properties")
    """

    @staticmethod
    async def scrape(state: str, county: Optional[str] = None) -> ScrapeResult:
        """
        Run the appropriate scraper for a state.

        Args:
            state: Two-letter state code (e.g., 'AR', 'AL')
            county: Optional county filter

        Returns:
            ScrapeResult with properties list and counts
        """
        state = state.upper()
        config = get_state_config(state)

        if not config:
            return ScrapeResult(
                properties=[],
                items_found=0,
                error_message=f"Unknown state: {state}"
            )

        if not config.is_active:
            return ScrapeResult(
                properties=[],
                items_found=0,
                error_message=f"Scraper for {state} ({config.state_name}) is not yet active"
            )

        try:
            if state == 'AR':
                return await ScraperFactory._scrape_arkansas(county)
            elif state == 'AL':
                return await ScraperFactory._scrape_alabama(county)
            elif state == 'TX':
                return await ScraperFactory._scrape_texas(county)
            else:
                return ScrapeResult(
                    properties=[],
                    items_found=0,
                    error_message=f"Scraper not implemented for state: {state}"
                )
        except Exception as e:
            logger.error(f"Scraper error for {state}: {e}")
            return ScrapeResult(
                properties=[],
                items_found=0,
                error_message=str(e)
            )

    @staticmethod
    async def _scrape_arkansas(county: Optional[str]) -> ScrapeResult:
        """Run Arkansas COSL scraper."""
        from .arkansas_cosl import ArkansasCOSLScraper

        logger.info(f"Starting Arkansas COSL scrape" + (f" for county: {county}" if county else ""))

        async with ArkansasCOSLScraper() as scraper:
            properties = await scraper.scrape_all_properties(county_filter=county)

        # Convert to dicts for consistent interface
        prop_dicts = [prop.to_dict() for prop in properties]

        logger.info(f"Arkansas scrape complete: {len(prop_dicts)} properties")

        return ScrapeResult(
            properties=prop_dicts,
            items_found=len(prop_dicts)
        )

    @staticmethod
    async def _scrape_alabama(county: Optional[str]) -> ScrapeResult:
        """
        Run Alabama ADOR scraper via subprocess with retry logic.

        Note: Alabama requires a county parameter (county-based system).
        Uses subprocess to avoid Playwright/asyncio conflicts in FastAPI on Windows.
        """
        if not county:
            return ScrapeResult(
                properties=[],
                items_found=0,
                error_message="County is required for Alabama scraping. Alabama uses a county-based system."
            )

        logger.info(f"Starting Alabama ADOR scrape for county: {county} (via subprocess with retry)")

        script_path = Path(__file__).parent / 'alabama_dor.py'
        return await _run_subprocess_with_retry(
            script_path=script_path,
            args=[county],
            timeout=180,  # 3 minutes per attempt
            state_name='Alabama'
        )

    @staticmethod
    async def _scrape_texas(county: Optional[str]) -> ScrapeResult:
        """
        Run Texas RealAuction scraper via subprocess with retry logic.

        Note: Texas uses county-specific RealAuction sites ([county].realforeclose.com).
        Uses subprocess to avoid Playwright/asyncio conflicts in FastAPI on Windows.

        Supported counties: Harris, Dallas, Tarrant, Travis, Collin, Denton, El Paso, Fort Bend
        """
        if not county:
            return ScrapeResult(
                properties=[],
                items_found=0,
                error_message=(
                    "County is required for Texas scraping. "
                    "Supported counties: Harris, Dallas, Tarrant, Travis, Collin, Denton, El Paso, Fort Bend"
                )
            )

        logger.info(f"Starting Texas RealAuction scrape for county: {county} (via subprocess with retry)")

        script_path = Path(__file__).parent / 'texas_counties.py'
        return await _run_subprocess_with_retry(
            script_path=script_path,
            args=[county],
            timeout=300,  # 5 minutes per attempt
            state_name='Texas'
        )
