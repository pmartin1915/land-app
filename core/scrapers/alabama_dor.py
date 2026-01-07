"""
Alabama Department of Revenue (ADOR) Scraper

Scrapes delinquent property data directly from the Alabama Department of Revenue website.
Wraps Playwright automation in a class structure compatible with the project's ScraperFactory.

Key characteristics:
- County-based search (requires county code/name)
- Playwright used for form submission and pagination (JavaScript-heavy site)
- Returns standardized AlabamaProperty objects
- Tax LIEN state: 4-year redemption period, 12% interest

Data source: https://www.revenue.alabama.gov/property-tax/delinquent-search/
"""

import asyncio
import pandas as pd
from io import StringIO
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import sys

# Add project root for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright, Browser, Page, Playwright, TimeoutError as PlaywrightTimeoutError
from config.logging_config import get_logger
from scripts.acreage_processor import extract_acreage_with_lineage
from core.scrapers.utils import EXIT_SUCCESS, EXIT_TRANSIENT, EXIT_PERMANENT, EXIT_RATE_LIMIT, save_debug_snapshot

logger = get_logger(__name__)


# Alabama County Codes Mapping - ADOR System (Alphabetical Order, Not FIPS)
# Note: ADOR uses alphabetical ordering, not standard FIPS county codes
ALABAMA_COUNTY_CODES = {
    '04': 'Autauga', '05': 'Baldwin', '06': 'Barbour', '07': 'Bibb', '08': 'Blount',
    '09': 'Bullock', '10': 'Butler', '11': 'Calhoun', '12': 'Chambers', '13': 'Cherokee',
    '14': 'Chilton', '15': 'Choctaw', '16': 'Clarke', '17': 'Clay', '18': 'Cleburne',
    '19': 'Coffee', '20': 'Colbert', '21': 'Conecuh', '22': 'Coosa', '23': 'Covington',
    '24': 'Crenshaw', '25': 'Cullman', '26': 'Dale', '27': 'Dallas', '28': 'DeKalb',
    '29': 'Elmore', '30': 'Escambia', '31': 'Etowah', '32': 'Fayette', '33': 'Franklin',
    '34': 'Geneva', '35': 'Greene', '36': 'Hale', '37': 'Henry', '38': 'Houston',
    '39': 'Jackson', '68': 'Jefferson-Bess', '01': 'Jefferson-Bham', '40': 'Lamar',
    '41': 'Lauderdale', '42': 'Lawrence', '43': 'Lee', '44': 'Limestone', '45': 'Lowndes',
    '46': 'Macon', '47': 'Madison', '48': 'Marengo', '49': 'Marion', '50': 'Marshall',
    '02': 'Mobile', '51': 'Monroe', '03': 'Montgomery', '52': 'Morgan', '53': 'Perry',
    '54': 'Pickens', '55': 'Pike', '56': 'Randolph', '57': 'Russell', '58': 'Shelby',
    '59': 'St_Clair', '60': 'Sumter', '61': 'Talladega', '62': 'Tallapoosa',
    '63': 'Tuscaloosa', '64': 'Walker', '65': 'Washington', '66': 'Wilcox', '67': 'Winston'
}

# Reverse mapping (county name to code)
COUNTY_NAME_TO_CODE = {v.upper(): k for k, v in ALABAMA_COUNTY_CODES.items()}


class CountyValidationError(Exception):
    """Raised when an invalid county code/name is provided."""
    pass


@dataclass
class AlabamaProperty:
    """Data class for Alabama ADOR property listing."""
    parcel_number: str
    owner: str
    description: str
    year: str
    balance: float
    county: str
    county_code: str
    scraped_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        # Parse acreage from description if available
        acreage = None
        acreage_source = None
        acreage_confidence = None
        acreage_raw_text = None

        if self.description:
            result = extract_acreage_with_lineage(self.description)
            if result and result.acreage:
                acreage = result.acreage
                acreage_source = result.source
                acreage_confidence = result.confidence
                acreage_raw_text = result.raw_text

        return {
            'parcel_id': self.parcel_number,
            'county': self.county,
            'owner_name': self.owner,
            'amount': self.balance,
            'description': self.description,
            'year_sold': self.year,
            'state': 'AL',
            'sale_type': 'tax_lien',
            'redemption_period_days': 1460,  # 4 years
            'time_to_ownership_days': 2000,  # ~5.5 years total
            'data_source': 'alabama_dor',
            'auction_platform': 'ADOR Search',
            'acreage': acreage,
            'acreage_source': acreage_source,
            'acreage_confidence': acreage_confidence,
            'acreage_raw_text': acreage_raw_text,
        }


class AlabamaDORScraper:
    """
    Scraper for Alabama Department of Revenue delinquent property search.
    Uses Playwright to handle the JavaScript-heavy search interface.

    Usage:
        async with AlabamaDORScraper() as scraper:
            properties = await scraper.scrape_county('Baldwin')
    """

    BASE_URL = "https://www.revenue.alabama.gov/property-tax/delinquent-search/"
    DEFAULT_TIMEOUT = 60000  # milliseconds
    RATE_LIMIT_DELAY = 1.5  # seconds between page loads

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    async def __aenter__(self):
        """Start Playwright browser."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup Playwright resources."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    def _validate_county(self, county_input: str) -> str:
        """
        Normalize county input to 2-digit ADOR code.

        Args:
            county_input: County code (e.g., '05') or name (e.g., 'Baldwin')

        Returns:
            2-digit county code

        Raises:
            CountyValidationError: If county not found
        """
        if not county_input:
            raise CountyValidationError("County is required for Alabama search")

        county_input = str(county_input).strip()

        if not county_input:
            raise CountyValidationError("County is required for Alabama search")

        # Check if it's a numeric code
        if county_input.isdigit() and len(county_input) <= 2:
            county_code = county_input.zfill(2)
            if county_code in ALABAMA_COUNTY_CODES:
                return county_code

        # Check exact name match (case-insensitive)
        county_name = county_input.upper()
        if county_name in COUNTY_NAME_TO_CODE:
            return COUNTY_NAME_TO_CODE[county_name]

        # Check partial name match (prefix or substring)
        for name, code in COUNTY_NAME_TO_CODE.items():
            if county_name in name or name.startswith(county_name):
                return code

        raise CountyValidationError(f"Invalid Alabama county: {county_input}")

    def _parse_row(self, row: pd.Series, county_code: str) -> Optional[AlabamaProperty]:
        """
        Convert a DataFrame row to an AlabamaProperty object.

        Args:
            row: pandas Series from HTML table
            county_code: 2-digit ADOR county code

        Returns:
            AlabamaProperty or None if parsing fails
        """
        try:
            # Actual ADOR column names (as of 2026):
            # 'CS Number', 'County Code', 'Document Number', 'Parcel ID',
            # 'Year Sold', 'Assessed Value', 'Amount Bid at Tax Sale', 'Name', 'Description'

            # Get amount (bid at tax sale)
            amount_str = str(row.get('Amount Bid at Tax Sale', row.get('Amount', '0')))
            amount_str = amount_str.replace('$', '').replace(',', '').strip()
            try:
                amount = float(amount_str) if amount_str else 0.0
            except ValueError:
                amount = 0.0

            # Get parcel ID
            parcel = str(row.get('Parcel ID', row.get('Parcel Number', '')))
            if not parcel or parcel == 'nan' or parcel == '':
                return None

            # Get year sold
            year = str(row.get('Year Sold', row.get('Year', '')))

            return AlabamaProperty(
                parcel_number=parcel,
                owner=str(row.get('Name', '')),
                description=str(row.get('Description', '')),
                year=year,
                balance=amount,
                county=ALABAMA_COUNTY_CODES.get(county_code, 'Unknown'),
                county_code=county_code,
                scraped_at=datetime.utcnow()
            )
        except Exception as e:
            logger.warning(f"Failed to parse row: {e}")
            return None

    async def scrape_county(self, county_input: str, max_pages: int = 50) -> List[AlabamaProperty]:
        """
        Scrape delinquent properties for a specific Alabama county.

        Args:
            county_input: County name or code
            max_pages: Safety limit for pagination

        Returns:
            List of AlabamaProperty objects
        """
        if not self._browser:
            raise RuntimeError("Scraper not started. Use 'async with' context manager.")

        county_code = self._validate_county(county_input)
        county_name = ALABAMA_COUNTY_CODES[county_code]

        logger.info(f"Starting Alabama ADOR scrape for {county_name} (code: {county_code})")

        page = await self._browser.new_page()
        page.set_default_timeout(self.DEFAULT_TIMEOUT)

        properties: List[AlabamaProperty] = []

        try:
            # Navigate to ADOR search page
            await page.goto(self.BASE_URL)
            await page.wait_for_load_state('networkidle')

            # Select county from dropdown and submit
            # Note: ADOR site uses <button> elements with truncated id (missing 't')
            await page.select_option('select[name="ador-delinquent-county"]', county_code)
            await page.click('button#ador-delinquent-county-submi')

            # Wait for results table or "no records" message
            try:
                await page.wait_for_selector(
                    'table.table-striped, div.alert-warning, .no-results',
                    state='visible',
                    timeout=15000
                )
            except Exception:
                logger.warning(f"Timeout waiting for results for {county_name}")
                return []

            page_count = 0
            while page_count < max_pages:
                page_count += 1

                # Check if table exists
                table = await page.query_selector('table.table-striped')
                if not table:
                    # Check for "No matching records" message
                    content = await page.content()
                    if "No matching records" in content or "no records found" in content.lower():
                        logger.info(f"No delinquent properties found for {county_name}")
                    break

                # Extract table HTML and parse with pandas
                table_html = await table.inner_html()

                # Wrap in table tags for pandas
                full_table = f"<table>{table_html}</table>"

                try:
                    dfs = pd.read_html(StringIO(full_table))
                    if dfs:
                        df = dfs[0]
                        for _, row in df.iterrows():
                            prop = self._parse_row(row, county_code)
                            if prop:
                                properties.append(prop)
                except Exception as e:
                    logger.warning(f"Failed to parse table on page {page_count}: {e}")

                # Check for "Next" pagination link
                next_button = await page.query_selector('a:has-text("Next"), .pagination .next a')
                if next_button:
                    is_disabled = await next_button.get_attribute('class')
                    if is_disabled and 'disabled' in str(is_disabled):
                        break

                    await next_button.click()
                    await page.wait_for_load_state('networkidle')
                    await asyncio.sleep(self.RATE_LIMIT_DELAY)
                else:
                    # No more pages
                    break

            # Save debug snapshot if no properties found (potential parsing issue)
            if not properties:
                logger.warning(f"No properties found for {county_name} - saving debug snapshot")
                try:
                    content = await page.content()
                    save_debug_snapshot(content, 'AL', county_name, "no_properties_found", logger=logger)
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Playwright error scraping {county_name}: {e}")
            # Save debug snapshot on error
            try:
                content = await page.content()
                save_debug_snapshot(content, 'AL', county_name, str(e), logger=logger)
            except Exception:
                pass  # Don't fail on snapshot error
            raise
        finally:
            await page.close()

        logger.info(f"Scraped {len(properties)} properties from {county_name}")
        return properties


# Convenience function for CLI usage
async def scrape_alabama_county(county: str, max_pages: int = 50) -> List[AlabamaProperty]:
    """
    Scrape Alabama ADOR delinquent properties for a county.

    Args:
        county: County name or code
        max_pages: Maximum pages to scrape

    Returns:
        List of AlabamaProperty objects
    """
    async with AlabamaDORScraper() as scraper:
        return await scraper.scrape_county(county, max_pages=max_pages)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Scrape Alabama ADOR delinquent properties")
    parser.add_argument("county", help="County code (e.g., '05') or name (e.g., 'Baldwin')")
    parser.add_argument("--max-pages", type=int, default=50, help="Maximum pages to scrape")
    parser.add_argument("--output", help="Output CSV file path")
    parser.add_argument("--json-output", help="Output JSON file path (for API integration)")

    args = parser.parse_args()

    async def main():
        try:
            properties = await scrape_alabama_county(args.county, max_pages=args.max_pages)

            if args.json_output:
                # JSON output for API subprocess integration
                prop_dicts = [p.to_dict() for p in properties]
                with open(args.json_output, 'w') as f:
                    json.dump(prop_dicts, f)
                # Silent success for subprocess
                sys.exit(EXIT_SUCCESS)
            elif args.output:
                df = pd.DataFrame([p.to_dict() for p in properties])
                df.to_csv(args.output, index=False)
                print(f"Saved {len(properties)} properties to: {args.output}")
                sys.exit(EXIT_SUCCESS)
            else:
                print(f"Scraped {len(properties)} properties")
                for prop in properties[:5]:
                    print(f"  - {prop.parcel_number}: ${prop.balance:.2f} ({prop.owner})")
                if len(properties) > 5:
                    print(f"  ... and {len(properties) - 5} more")
                sys.exit(EXIT_SUCCESS)

        except CountyValidationError as e:
            # Invalid county - permanent error, don't retry
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(EXIT_PERMANENT)
        except PlaywrightTimeoutError as e:
            # Timeout - transient error, retry
            print(f"Timeout error: {e}", file=sys.stderr)
            sys.exit(EXIT_TRANSIENT)
        except ConnectionError as e:
            # Network error - transient, retry
            print(f"Connection error: {e}", file=sys.stderr)
            sys.exit(EXIT_TRANSIENT)
        except Exception as e:
            error_msg = str(e).lower()
            # Check for rate limiting indicators
            if 'rate limit' in error_msg or '429' in error_msg or 'too many requests' in error_msg:
                print(f"Rate limited: {e}", file=sys.stderr)
                sys.exit(EXIT_RATE_LIMIT)
            # Check for access denied (may indicate rate limiting)
            if 'access denied' in error_msg or '403' in error_msg:
                print(f"Access denied (possible rate limit): {e}", file=sys.stderr)
                sys.exit(EXIT_RATE_LIMIT)
            # Default to transient for unknown errors (allow retry)
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(EXIT_TRANSIENT)

    asyncio.run(main())
