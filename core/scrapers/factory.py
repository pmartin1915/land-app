"""
Scraper Factory for dispatching scrape jobs to appropriate state scrapers.

Provides a unified interface for running scrapers across different states,
returning standardized results regardless of the underlying scraper implementation.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.states import get_state_config
from config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ScrapeResult:
    """Standardized result from any scraper."""
    properties: List[Dict[str, Any]]
    items_found: int
    error_message: Optional[str] = None


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
        Run Alabama ADOR scraper.

        Note: Alabama requires a county parameter (county-based system).
        """
        from .alabama_dor import AlabamaDORScraper, CountyValidationError

        if not county:
            return ScrapeResult(
                properties=[],
                items_found=0,
                error_message="County is required for Alabama scraping. Alabama uses a county-based system."
            )

        logger.info(f"Starting Alabama ADOR scrape for county: {county}")

        try:
            async with AlabamaDORScraper() as scraper:
                properties = await scraper.scrape_county(county)

            prop_dicts = [prop.to_dict() for prop in properties]

            logger.info(f"Alabama scrape complete: {len(prop_dicts)} properties")

            return ScrapeResult(
                properties=prop_dicts,
                items_found=len(prop_dicts)
            )

        except CountyValidationError as e:
            return ScrapeResult(
                properties=[],
                items_found=0,
                error_message=f"Invalid county: {e}"
            )
