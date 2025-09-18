"""
Alabama ADOR Web Scraper

This module provides functionality to scrape delinquent property data
directly from the Alabama Department of Revenue website, eliminating
the need for manual CSV downloads.

Usage:
    from scripts.scraper import scrape_county_data
    df = scrape_county_data('05')  # Baldwin County
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import logging
import re
from typing import Optional, List, Dict, Tuple
from urllib.parse import urljoin, urlparse, parse_qs
import random
from io import StringIO

# Import structured logging
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import get_logger, log_performance, log_scraping_metrics, log_error_with_context
from scripts.exceptions import CountyValidationError, NetworkError, ParseError, ScrapingError

logger = get_logger(__name__)

# Alabama County Codes Mapping - ADOR System (Alphabetical Order, Not FIPS)
# Note: ADOR uses alphabetical ordering, not standard FIPS county codes
ALABAMA_COUNTY_CODES = {
    # Verified through web scraping tests:
    '01': 'Autauga',      # ✅ Tested - 200 records
    '02': 'Mobile',       # ✅ Tested - 100+ records (was incorrectly mapped as Baldwin)
    '03': 'Barbour',      # ✅ Tested - 999+ records
    '04': 'Bibb',         # ✅ Tested - No data available
    '05': 'Baldwin',      # ✅ Tested - 29 records (was incorrectly mapped as Blount)
    '06': 'Blount',
    '07': 'Bullock',
    '08': 'Butler',
    '09': 'Calhoun',
    '10': 'Chambers',
    '11': 'Cherokee',
    '12': 'Chilton',
    '13': 'Choctaw',
    '14': 'Clarke',
    '15': 'Clay',
    '16': 'Cleburne',
    '17': 'Coffee',
    '18': 'Colbert',
    '19': 'Conecuh',
    '20': 'Coosa',
    '21': 'Covington',
    '22': 'Crenshaw',
    '23': 'Cullman',
    '24': 'Dale',
    '25': 'Dallas',
    '26': 'DeKalb',
    '27': 'Elmore',
    '28': 'Escambia',
    '29': 'Etowah',
    '30': 'Fayette',
    '31': 'Franklin',
    '32': 'Geneva',
    '33': 'Greene',
    '34': 'Hale',
    '35': 'Henry',
    '36': 'Houston',
    '37': 'Jackson',
    '38': 'Jefferson',  # Note: May be split into JEFFERSON-BESS and JEFFERSON-BHAM
    '39': 'Lamar',
    '40': 'Lauderdale',
    '41': 'Lawrence',
    '42': 'Lee',
    '43': 'Limestone',
    '44': 'Lowndes',
    '45': 'Macon',
    '46': 'Madison',
    '47': 'Marengo',
    '48': 'Marion',
    '49': 'Marshall',
    '50': 'Monroe',
    '51': 'Montgomery',
    '52': 'Morgan',
    '53': 'Perry',
    '54': 'Pickens',
    '55': 'Pike',
    '56': 'Randolph',
    '57': 'Russell',
    '58': 'Saint Clair',
    '59': 'Shelby',
    '60': 'Sumter',
    '61': 'Talladega',
    '62': 'Tallapoosa',
    '63': 'Tuscaloosa',
    '64': 'Walker',
    '65': 'Washington',
    '66': 'Wilcox',
    '67': 'Winston'
}

# Reverse mapping (county name to code)
COUNTY_NAME_TO_CODE = {v.upper(): k for k, v in ALABAMA_COUNTY_CODES.items()}

# Base ADOR URL
ADOR_BASE_URL = "https://www.revenue.alabama.gov/property-tax/delinquent-search/"

# Request settings
DEFAULT_TIMEOUT = 30
RATE_LIMIT_DELAY = 2.0  # Seconds between requests
MAX_RETRIES = 3


# Using custom exceptions from scripts.exceptions module


def validate_county_code(county_input: str) -> str:
    """
    Validate and normalize county code input.

    Args:
        county_input: County code (e.g., '05') or name (e.g., 'Baldwin')

    Returns:
        Validated county code (2-digit string)

    Raises:
        ValueError: If county is not found
    """
    county_input = str(county_input).strip()

    # If it's already a 2-digit code
    if county_input.isdigit() and len(county_input) <= 2:
        county_code = county_input.zfill(2)  # Pad with leading zero if needed
        if county_code in ALABAMA_COUNTY_CODES:
            return county_code

    # Try to find by county name
    county_name = county_input.upper()
    if county_name in COUNTY_NAME_TO_CODE:
        return COUNTY_NAME_TO_CODE[county_name]

    # Try partial matching
    for name, code in COUNTY_NAME_TO_CODE.items():
        if county_name in name or name.startswith(county_name):
            return code

    raise CountyValidationError(county_input)


def get_county_name(county_code: str) -> str:
    """Get county name from code."""
    return ALABAMA_COUNTY_CODES.get(county_code, f"County {county_code}")


def create_session() -> requests.Session:
    """
    Create a requests session with appropriate headers.

    Returns:
        Configured requests session
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })
    return session


def extract_pagination_info(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str], int]:
    """
    Extract pagination information from the ADOR page.

    Args:
        soup: BeautifulSoup parsed HTML

    Returns:
        Tuple of (previous_url, next_url, current_page_num)
    """
    prev_url = None
    next_url = None
    current_page = 1

    # Look for pagination links
    pagination_links = soup.find_all('a', href=True)

    for link in pagination_links:
        href = link.get('href', '')
        text = link.get_text(strip=True).lower()

        if 'previous' in text:
            prev_url = href
        elif 'next' in text:
            next_url = href

        # Try to extract current page number from URL or context
        if 'offset' in href:
            try:
                offset = int(re.search(r'offset=(\d+)', href).group(1))
                current_page = (offset // 50) + 1  # Assuming 50 records per page
            except (AttributeError, ValueError):
                pass

    return prev_url, next_url, current_page


def parse_property_table(soup: BeautifulSoup) -> pd.DataFrame:
    """
    Extract property data from the HTML table.

    Args:
        soup: BeautifulSoup parsed HTML

    Returns:
        DataFrame with property data
    """
    try:
        # Try pandas.read_html first (simplest approach)
        tables = pd.read_html(StringIO(str(soup)), attrs={'id': 'ador-delinquent-search-results'})
        if tables:
            df = tables[0]
            logger.info(f"Extracted table with {len(df)} rows using pandas.read_html")
            return df
    except Exception as e:
        logger.warning(f"pandas.read_html failed: {e}, trying BeautifulSoup parsing")

    # Fallback to manual BeautifulSoup parsing
    table = soup.find('table')
    if not table:
        logger.warning("No table found in HTML")
        return pd.DataFrame()

    # Extract headers
    headers = []
    header_row = table.find('tr')
    if header_row:
        for th in header_row.find_all(['th', 'td']):
            headers.append(th.get_text(strip=True))

    if not headers:
        logger.warning("No table headers found")
        return pd.DataFrame()

    # Extract data rows
    data_rows = []
    rows = table.find_all('tr')[1:]  # Skip header row

    for row in rows:
        cells = row.find_all(['td', 'th'])
        row_data = []
        for cell in cells:
            # Clean cell text
            text = cell.get_text(strip=True)
            text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
            row_data.append(text)

        if len(row_data) == len(headers):
            data_rows.append(row_data)

    if not data_rows:
        logger.warning("No data rows found")
        return pd.DataFrame()

    df = pd.DataFrame(data_rows, columns=headers)
    logger.info(f"Extracted table with {len(df)} rows using BeautifulSoup parsing")

    return df


def scrape_single_page(session: requests.Session, url: str, params: Dict = None) -> Tuple[pd.DataFrame, Dict]:
    """
    Scrape a single page of ADOR data.

    Args:
        session: Requests session
        url: URL to scrape
        params: URL parameters

    Returns:
        Tuple of (DataFrame, pagination_info)
    """
    try:
        logger.info(f"Scraping: {url}")
        response = session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'lxml')

        # Extract table data
        df = parse_property_table(soup)

        # Extract pagination info
        prev_url, next_url, current_page = extract_pagination_info(soup)
        pagination_info = {
            'prev_url': prev_url,
            'next_url': next_url,
            'current_page': current_page,
            'has_more': next_url is not None
        }

        return df, pagination_info

    except requests.RequestException as e:
        raise NetworkError(f"HTTP request failed: {e}", url=url)
    except Exception as e:
        content_length = len(response.content) if 'response' in locals() else None
        raise ParseError(f"Failed to parse page: {e}", page_content_length=content_length)


def scrape_county_data(county_input: str,
                      max_pages: int = 10,
                      save_raw: bool = True) -> pd.DataFrame:
    """
    Scrape all delinquent property data for a county.

    Args:
        county_input: County code ('05') or name ('Baldwin')
        max_pages: Maximum number of pages to scrape (safety limit)
        save_raw: Whether to save raw scraped data to CSV

    Returns:
        DataFrame with all scraped property data

    Raises:
        ValueError: Invalid county
        AdorScrapingError: Scraping failed
    """
    # Validate county
    county_code = validate_county_code(county_input)
    county_name = get_county_name(county_code)

    # Start timing for performance metrics
    import time
    start_time = time.time()

    logger.info(f"Starting scrape for {county_name} County (code: {county_code}) - Max pages: {max_pages}")

    # Create session
    session = create_session()

    # Initial request parameters
    params = {
        'ador-delinquent-county': county_code,
        '_ador-delinquent-county-submit': 'submit'
    }

    all_data = []
    current_url = ADOR_BASE_URL
    page_count = 0

    try:
        while page_count < max_pages:
            page_count += 1

            # Add rate limiting
            if page_count > 1:
                delay = RATE_LIMIT_DELAY + random.uniform(0, 1)  # Add some jitter
                logger.info(f"Rate limiting: waiting {delay:.1f} seconds...")
                time.sleep(delay)

            # Scrape current page
            df, pagination_info = scrape_single_page(session, current_url, params)

            if df.empty:
                logger.warning(f"Page {page_count} returned no data")
                break

            logger.info(f"Page {page_count}: extracted {len(df)} records")
            all_data.append(df)

            # Check for next page
            if not pagination_info['has_more']:
                logger.info("No more pages available")
                break

            # Update URL for next page
            next_url = pagination_info['next_url']
            if next_url:
                # Handle relative URLs
                current_url = urljoin(ADOR_BASE_URL, next_url)
                params = None  # Parameters should be in the URL now
            else:
                break

        if page_count >= max_pages:
            logger.warning(f"Reached maximum page limit ({max_pages})")

        # Combine all data
        if not all_data:
            logger.error(f"No data found for {county_name} County")
            return pd.DataFrame()

        combined_df = pd.concat(all_data, ignore_index=True)

        # Remove duplicates (in case of overlapping pages)
        if 'Parcel ID' in combined_df.columns:
            combined_df = combined_df.drop_duplicates(subset=['Parcel ID'], keep='first')
        elif 'CS Number' in combined_df.columns:
            combined_df = combined_df.drop_duplicates(subset=['CS Number'], keep='first')

        # Add county information
        combined_df['County'] = county_name
        combined_df['County Code'] = county_code

        # Calculate performance metrics
        duration = time.time() - start_time
        log_scraping_metrics(logger, county_name, page_count, len(combined_df), duration, errors=0)

        # Save raw data if requested
        if save_raw:
            from pathlib import Path
            raw_dir = Path("data/raw")
            raw_dir.mkdir(parents=True, exist_ok=True)

            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scraped_{county_name.lower().replace(' ', '_')}_county_{timestamp}.csv"
            filepath = raw_dir / filename

            combined_df.to_csv(filepath, index=False)
            logger.info(f"Saved raw scraped data to: {filepath}")

        return combined_df

    except Exception as e:
        duration = time.time() - start_time
        log_error_with_context(logger, e, "County data scraping failed",
                             county=county_name, county_code=county_code,
                             max_pages=max_pages, duration=duration)
        raise ScrapingError(f"Failed to scrape {county_name} County: {e}")

    finally:
        session.close()


def list_available_counties() -> Dict[str, str]:
    """
    Return dictionary of available counties.

    Returns:
        Dictionary mapping county codes to names
    """
    return ALABAMA_COUNTY_CODES.copy()


def search_counties(query: str) -> Dict[str, str]:
    """
    Search for counties by partial name.

    Args:
        query: Search query (partial county name)

    Returns:
        Dictionary of matching counties (code -> name)
    """
    query = query.upper().strip()
    matches = {}

    for code, name in ALABAMA_COUNTY_CODES.items():
        if query in name.upper():
            matches[code] = name

    return matches


if __name__ == "__main__":
    # Simple CLI for testing
    import argparse

    parser = argparse.ArgumentParser(description="Scrape Alabama ADOR delinquent property data")
    parser.add_argument("county", help="County code (e.g., '05') or name (e.g., 'Baldwin')")
    parser.add_argument("--max-pages", type=int, default=10, help="Maximum pages to scrape")
    parser.add_argument("--output", help="Output CSV file path")

    args = parser.parse_args()

    try:
        df = scrape_county_data(args.county, max_pages=args.max_pages)

        if args.output:
            df.to_csv(args.output, index=False)
            print(f"Data saved to: {args.output}")
        else:
            print(f"Scraped {len(df)} records:")
            print(df.head())

    except Exception as e:
        print(f"Error: {e}")
        exit(1)