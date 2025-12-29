"""
Alabama ADOR Web Scraper

This module provides functionality to scrape delinquent property data
directly from the Alabama Department of Revenue website, eliminating
the need for manual CSV downloads.

Usage:
    from scripts.scraper import scrape_county_data
    df = scrape_county_data('05')  # Baldwin County
"""

import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import time
import re
from typing import Optional, Dict, Tuple
from urllib.parse import urljoin
import random

# Import structured logging
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import get_logger, log_scraping_metrics, log_error_with_context
from config.enhanced_error_handling import smart_retry, get_user_friendly_error_message
from scripts.exceptions import CountyValidationError, NetworkError, ParseError, ScrapingError

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

# Base ADOR URL
ADOR_BASE_URL = "https://www.revenue.alabama.gov/property-tax/delinquent-search/"

# Request settings
DEFAULT_TIMEOUT = 60000  # milliseconds for Playwright
RATE_LIMIT_DELAY = 2.0  # Seconds between requests
MAX_RETRIES = 3


def validate_county_code(county_input: str) -> str:
    """Validate and normalize county code input."""
    county_input = str(county_input).strip()

    # Reject empty input
    if not county_input:
        raise CountyValidationError("empty string")

    # Check if it's a numeric code
    if county_input.isdigit() and len(county_input) <= 2:
        county_code = county_input.zfill(2)
        if county_code in ALABAMA_COUNTY_CODES:
            return county_code

    # Check exact name match
    county_name = county_input.upper()
    if county_name in COUNTY_NAME_TO_CODE:
        return COUNTY_NAME_TO_CODE[county_name]

    # Check partial name match (prefix or substring)
    for name, code in COUNTY_NAME_TO_CODE.items():
        if county_name in name or name.startswith(county_name):
            return code

    raise CountyValidationError(county_input)


def get_county_name(county_code: str) -> str:
    """Get county name from code."""
    return ALABAMA_COUNTY_CODES.get(county_code, f"County {county_code}")

async def scrape_county_data(county_input: str,
                           max_pages: int = 10,
                           save_raw: bool = True) -> pd.DataFrame:
    """
    Scrape all delinquent property data for a county using Playwright.
    """
    county_code = validate_county_code(county_input)
    county_name = get_county_name(county_code)
    start_time = time.time()

    logger.info(f"Starting Playwright scrape for {county_name} County (code: {county_code})")

    all_data = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)

        try:
            await page.goto(ADOR_BASE_URL)
            
            # Select county and submit form
            await page.select_option('select[name="ador-delinquent-county"]', county_code)
            await page.click('input[name="_ador-delinquent-county-submit"]')
            
            await page.wait_for_selector('table.table-striped', state='visible')

            page_count = 0
            while page_count < max_pages:
                page_count += 1
                logger.info(f"Scraping page {page_count} for {county_name}")

                table_html = await page.inner_html('table.table-striped')
                
                if not table_html or "No matching records found" in table_html:
                    if page_count == 1:
                        logger.info(f"No delinquent properties found for {county_name}.")
                    else:
                        logger.info(f"No more data found for {county_name}.")
                    break

                df = pd.read_html(table_html)[0]
                all_data.append(df)
                
                # Check for "Next" link and navigate
                next_button = await page.query_selector('a:has-text("Next")')
                if next_button:
                    await next_button.click()
                    await page.wait_for_load_state('networkidle')
                    await asyncio.sleep(RATE_LIMIT_DELAY) # Rate limit
                else:
                    logger.info(f"Last page reached for {county_name}.")
                    break
        
        except Exception as e:
            logger.error(f"An error occurred during Playwright scraping for {county_name}: {e}")
            raise ScrapingError(f"Failed to scrape {county_name}: {e}")
        
        finally:
            await browser.close()

    if not all_data:
        return pd.DataFrame()

    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df['County'] = county_name
    combined_df['County Code'] = county_code
    
    duration = time.time() - start_time
    log_scraping_metrics(logger, county_name, page_count, len(combined_df), duration, errors=0)

    if save_raw:
        raw_dir = Path("data/raw")
        raw_dir.mkdir(parents=True, exist_ok=True)
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        filename = f"scraped_{county_name.lower().replace(' ', '_')}_county_{timestamp}.csv"
        filepath = raw_dir / filename
        combined_df.to_csv(filepath, index=False)
        logger.info(f"Saved raw scraped data to: {filepath}")

    return combined_df

def list_available_counties() -> Dict[str, str]:
    """Return dictionary of available counties."""
    return ALABAMA_COUNTY_CODES.copy()


def search_counties(query: str) -> Dict[str, str]:
    """Search for counties by partial name."""
    query = query.upper().strip()
    matches = {}
    for code, name in ALABAMA_COUNTY_CODES.items():
        if query in name.upper():
            matches[code] = name
    return matches


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape Alabama ADOR delinquent property data with Playwright")
    parser.add_argument("county", help="County code (e.g., '05') or name (e.g., 'Baldwin')")
    parser.add_argument("--max-pages", type=int, default=10, help="Maximum pages to scrape")
    parser.add_argument("--output", help="Output CSV file path")

    args = parser.parse_args()

    async def main():
        try:
            df = await scrape_county_data(args.county, max_pages=args.max_pages)
            if args.output:
                df.to_csv(args.output, index=False)
                print(f"Data saved to: {args.output}")
            else:
                print(f"Scraped {len(df)} records:")
                print(df.head())
        except Exception as e:
            print(f"Error: {e}")
            exit(1)

    asyncio.run(main())
