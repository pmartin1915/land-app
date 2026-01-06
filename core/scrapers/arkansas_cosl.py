"""
Arkansas Commissioner of State Lands (COSL) Scraper

Scrapes tax-forfeited properties from the Arkansas COSL auction platform.
Properties have NO redemption period - buyer gets immediate ownership via warranty deed.

Key differences from Alabama:
- State-level centralized system (not county-by-county)
- Tax DEED sale (not lien sale)
- Minimum bid = back taxes + costs
- Quiet title required (~$1,500) despite warranty deed - title insurance companies require it
- Properties available via post-auction sales after failed auction

Data source: https://auction.cosl.org/
API endpoint: /auctions/grid_read (Kendo UI grid)

Usage:
    from core.scrapers.arkansas_cosl import ArkansasCOSLScraper

    scraper = ArkansasCOSLScraper()
    properties = await scraper.scrape_all_properties()
"""

import asyncio
import aiohttp
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import json
import sys

# Add project root for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import get_logger
from scripts.acreage_processor import extract_acreage_with_lineage

logger = get_logger(__name__)


# Arkansas County FIPS codes (75 counties)
ARKANSAS_COUNTIES = {
    '001': 'Arkansas', '003': 'Ashley', '005': 'Baxter', '007': 'Benton', '009': 'Boone',
    '011': 'Bradley', '013': 'Calhoun', '015': 'Carroll', '017': 'Chicot', '019': 'Clark',
    '021': 'Clay', '023': 'Cleburne', '025': 'Cleveland', '027': 'Columbia', '029': 'Conway',
    '031': 'Craighead', '033': 'Crawford', '035': 'Crittenden', '037': 'Cross', '039': 'Dallas',
    '041': 'Desha', '043': 'Drew', '045': 'Faulkner', '047': 'Franklin', '049': 'Fulton',
    '051': 'Garland', '053': 'Grant', '055': 'Greene', '057': 'Hempstead', '059': 'Hot Spring',
    '061': 'Howard', '063': 'Independence', '065': 'Izard', '067': 'Jackson', '069': 'Jefferson',
    '071': 'Johnson', '073': 'Lafayette', '075': 'Lawrence', '077': 'Lee', '079': 'Lincoln',
    '081': 'Little River', '083': 'Logan', '085': 'Lonoke', '087': 'Madison', '089': 'Marion',
    '091': 'Miller', '093': 'Mississippi', '095': 'Monroe', '097': 'Montgomery', '099': 'Nevada',
    '101': 'Newton', '103': 'Ouachita', '105': 'Perry', '107': 'Phillips', '109': 'Pike',
    '111': 'Poinsett', '113': 'Polk', '115': 'Pope', '117': 'Prairie', '119': 'Pulaski',
    '121': 'Randolph', '123': 'St. Francis', '125': 'Saline', '127': 'Scott', '129': 'Searcy',
    '131': 'Sebastian', '133': 'Sevier', '135': 'Sharp', '137': 'Stone', '139': 'Union',
    '141': 'Van Buren', '143': 'Washington', '145': 'White', '147': 'Woodruff', '149': 'Yell'
}

# Reverse mapping
COUNTY_NAME_TO_CODE = {v.upper(): k for k, v in ARKANSAS_COUNTIES.items()}


@dataclass
class COSLProperty:
    """Data class for Arkansas COSL property listing."""
    listing_token: str
    parcel_number: str
    county: str
    owner: str
    acres: float
    section: Optional[str]
    township: Optional[str]
    range: Optional[str]
    starting_bid: float
    current_bid: float
    added_on: Optional[datetime]
    gis_id: Optional[str]

    # Additional fields for database compatibility
    legal_description: Optional[str] = None

    # Acreage lineage tracking (for parsed acreage)
    acreage_source: Optional[str] = None  # 'api', 'parsed_explicit', 'parsed_plss', 'parsed_dimensions'
    acreage_confidence: Optional[str] = None  # 'high', 'medium', 'low'
    acreage_raw_text: Optional[str] = None  # The text that was parsed

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            'parcel_id': self.parcel_number,
            'county': self.county,
            'owner_name': self.owner,
            'acreage': self.acres,
            'amount': self.current_bid if self.current_bid > 0 else self.starting_bid,
            'description': self.legal_description or self._build_legal_description(),
            'state': 'AR',
            'sale_type': 'tax_deed',
            'redemption_period_days': 0,
            'time_to_ownership_days': 1,
            'data_source': 'arkansas_cosl',
            'auction_platform': 'COSL Website',
            'year_sold': str(datetime.now().year),
            # Acreage data lineage (set in _parse_property)
            'acreage_source': self.acreage_source,
            'acreage_confidence': self.acreage_confidence,
            'acreage_raw_text': self.acreage_raw_text,
        }

    def _build_legal_description(self) -> str:
        """Build legal description from section/township/range."""
        parts = []
        if self.section:
            parts.append(f"SEC {self.section}")
        if self.township:
            parts.append(f"TWP {self.township}")
        if self.range:
            parts.append(f"RNG {self.range}")
        if self.acres:
            parts.append(f"{self.acres:.2f} ACRES")
        return " ".join(parts) if parts else f"Parcel {self.parcel_number}"


class ArkansasCOSLScraper:
    """
    Scraper for Arkansas Commissioner of State Lands auction platform.

    The COSL platform uses Kendo UI grids with AJAX data loading.
    Properties are loaded via POST requests to /auctions/grid_read.
    """

    BASE_URL = "https://auction.cosl.org"
    GRID_ENDPOINT = "/auctions/grid_read"
    ONGOING_ENDPOINT = "/auctions/ongoing-auctions_grid_read"

    # Default page size for grid requests
    DEFAULT_PAGE_SIZE = 500

    # Retry configuration
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BASE_DELAY = 1.0  # seconds
    MAX_DELAY = 30.0  # cap for exponential backoff

    def __init__(self, session: Optional[aiohttp.ClientSession] = None,
                 max_retries: int = DEFAULT_MAX_RETRIES,
                 base_delay: float = DEFAULT_BASE_DELAY):
        """Initialize scraper with optional session and retry configuration.

        Args:
            session: Optional aiohttp session to reuse
            max_retries: Number of retry attempts on transient failures (default: 3)
            base_delay: Base delay in seconds for exponential backoff (default: 1.0)
        """
        self._session = session
        self._owns_session = session is None
        self._max_retries = max_retries
        self._base_delay = base_delay

    async def __aenter__(self):
        """Async context manager entry."""
        if self._owns_session:
            self._session = aiohttp.ClientSession(
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Origin': self.BASE_URL,
                    'Referer': f'{self.BASE_URL}/Auctions/ListingsView',
                }
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._owns_session and self._session:
            await self._session.close()

    def _build_kendo_request(self, page: int = 1, page_size: int = None,
                              county_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Build Kendo UI grid request payload.

        The Kendo grid expects a specific format for pagination and filtering.
        """
        page_size = page_size or self.DEFAULT_PAGE_SIZE

        payload = {
            'take': page_size,
            'skip': (page - 1) * page_size,
            'page': page,
            'pageSize': page_size,
            'sort': '',
        }

        # Add county filter if specified
        if county_filter:
            payload['filter[filters][0][field]'] = 'County'
            payload['filter[filters][0][operator]'] = 'contains'
            payload['filter[filters][0][value]'] = county_filter
            payload['filter[logic]'] = 'and'

        return payload

    async def _fetch_grid_page(self, endpoint: str, page: int = 1,
                                page_size: int = None,
                                county_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch a single page of grid data with exponential backoff retry.

        Retries on transient failures (network errors, timeouts, HTTP 5xx).
        Does NOT retry on client errors (4xx) or JSON decode errors.

        Returns:
            Dict with 'Data' (list of properties) and 'Total' (total count)
        """
        for attempt in range(self._max_retries):
            try:
                return await self._fetch_grid_page_inner(endpoint, page, page_size, county_filter)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == self._max_retries - 1:
                    logger.error(f"Failed after {self._max_retries} attempts: {e}")
                    return {'Data': [], 'Total': 0}
                delay = min(self._base_delay * (2 ** attempt), self.MAX_DELAY)
                logger.warning(f"Retry {attempt + 1}/{self._max_retries} after {delay:.1f}s: {e}")
                await asyncio.sleep(delay)

        return {'Data': [], 'Total': 0}

    async def _fetch_grid_page_inner(self, endpoint: str, page: int = 1,
                                      page_size: int = None,
                                      county_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Internal method to fetch a single page of grid data.

        Raises exceptions on transient failures to trigger retry logic.

        Returns:
            Dict with 'Data' (list of properties) and 'Total' (total count)

        Raises:
            aiohttp.ClientError: On network errors or HTTP 5xx responses
            asyncio.TimeoutError: On request timeout
        """
        if not self._session:
            raise RuntimeError("Session not initialized. Use async with context manager.")

        url = f"{self.BASE_URL}{endpoint}"
        payload = self._build_kendo_request(page, page_size, county_filter)

        async with self._session.post(url, data=payload) as response:
            # Retry on server errors (5xx)
            if response.status >= 500:
                raise aiohttp.ClientError(f"Server error: HTTP {response.status}")

            # Don't retry on client errors (4xx) - these are not transient
            if response.status >= 400:
                logger.error(f"COSL API client error: HTTP {response.status}")
                return {'Data': [], 'Total': 0}

            try:
                data = await response.json()
                return data
            except json.JSONDecodeError as e:
                # Don't retry JSON errors - likely a data issue, not transient
                logger.error(f"JSON decode error from COSL: {e}")
                return {'Data': [], 'Total': 0}

    def _parse_property(self, raw_data: Dict[str, Any]) -> COSLProperty:
        """
        Parse raw API response into COSLProperty object.

        Actual API fields (discovered from live API):
        - ListingToken: unique identifier
        - CoSLParcelNumber: parcel ID
        - CoSLCountyName: county name
        - Owner: owner name
        - Acreage: float
        - Section, Township, Range: legal description parts
        - StartingBid: minimum bid
        - CurrentBid: current highest bid
        - Added: timestamp (ISO format)
        - GisId: GIS identifier for mapping
        - SaleType: sale type code (S4, etc.)
        - Start, End: auction start/end times
        - NumberOfBids: bid count
        """
        # Parse date if present
        added_on = None
        date_str = raw_data.get('Added') or raw_data.get('AddedOn')
        if date_str:
            try:
                # Handle .NET JSON date format: /Date(1234567890000)/
                if '/Date(' in str(date_str):
                    timestamp = int(str(date_str).replace('/Date(', '').replace(')/', '')) / 1000
                    added_on = datetime.fromtimestamp(timestamp)
                else:
                    # Handle ISO format: 2025-12-20T06:05:26.6002548
                    added_on = datetime.fromisoformat(str(date_str).split('.')[0])
            except (ValueError, TypeError) as e:
                logger.debug(f"Date parse error: {e}")

        # Get API acreage first
        api_acreage = float(raw_data.get('Acreage') or raw_data.get('Acres', 0) or 0)

        # Extract section/township/range for legal description
        section = raw_data.get('Section')
        township = raw_data.get('Township')
        range_val = raw_data.get('Range')
        parcel_number = raw_data.get('CoSLParcelNumber') or raw_data.get('ParcelNumber', '')

        # Initialize lineage tracking
        acreage_source = None
        acreage_confidence = None
        acreage_raw_text = None
        final_acres = api_acreage

        if api_acreage > 0:
            # API provided acreage
            acreage_source = 'api'
            acreage_confidence = 'high'
        else:
            # Try to parse acreage from legal description components
            desc_parts = []
            if section:
                desc_parts.append(f"SEC {section}")
            if township:
                desc_parts.append(f"TWP {township}")
            if range_val:
                desc_parts.append(f"RNG {range_val}")
            temp_desc = " ".join(desc_parts) if desc_parts else f"Parcel {parcel_number}"

            parsed_result = extract_acreage_with_lineage(temp_desc)
            if parsed_result:
                final_acres = parsed_result.acreage
                acreage_source = parsed_result.source
                acreage_confidence = parsed_result.confidence
                acreage_raw_text = parsed_result.raw_text
                logger.debug(f"Parsed acreage for {parcel_number}: {final_acres} ({acreage_source})")

        return COSLProperty(
            listing_token=raw_data.get('ListingToken', ''),
            parcel_number=parcel_number,
            county=raw_data.get('CoSLCountyName') or raw_data.get('County', ''),
            owner=raw_data.get('Owner', ''),
            acres=final_acres,
            section=section,
            township=township,
            range=range_val,
            starting_bid=float(raw_data.get('StartingBid', 0) or 0),
            current_bid=float(raw_data.get('CurrentBid', 0) or 0),
            added_on=added_on,
            gis_id=str(raw_data.get('GisId', '')) if raw_data.get('GisId') else None,
            acreage_source=acreage_source,
            acreage_confidence=acreage_confidence,
            acreage_raw_text=acreage_raw_text,
        )

    async def scrape_all_properties(self, county_filter: Optional[str] = None,
                                     max_pages: int = 100,
                                     include_ongoing: bool = True) -> List[COSLProperty]:
        """
        Scrape all available properties from COSL.

        Args:
            county_filter: Optional county name to filter by
            max_pages: Maximum pages to fetch (safety limit)
            include_ongoing: Include ongoing auction properties

        Returns:
            List of COSLProperty objects
        """
        all_properties = []

        # Fetch post-auction properties (main inventory)
        logger.info("Fetching COSL post-auction properties...")
        page = 1
        total_fetched = 0

        while page <= max_pages:
            data = await self._fetch_grid_page(
                self.GRID_ENDPOINT,
                page=page,
                county_filter=county_filter
            )

            properties = data.get('Data', [])
            total = data.get('Total', 0)

            if not properties:
                break

            for raw_prop in properties:
                try:
                    prop = self._parse_property(raw_prop)
                    all_properties.append(prop)
                except Exception as e:
                    logger.warning(f"Failed to parse property: {e}")

            total_fetched += len(properties)
            logger.info(f"Page {page}: fetched {len(properties)} properties ({total_fetched}/{total} total)")

            if total_fetched >= total:
                break

            page += 1
            await asyncio.sleep(0.5)  # Rate limiting

        # Optionally fetch ongoing auctions
        if include_ongoing:
            logger.info("Fetching COSL ongoing auction properties...")
            ongoing_data = await self._fetch_grid_page(self.ONGOING_ENDPOINT)

            for raw_prop in ongoing_data.get('Data', []):
                try:
                    prop = self._parse_property(raw_prop)
                    all_properties.append(prop)
                except Exception as e:
                    logger.warning(f"Failed to parse ongoing property: {e}")

        logger.info(f"Total properties scraped: {len(all_properties)}")
        return all_properties

    async def scrape_county(self, county_name: str) -> List[COSLProperty]:
        """
        Scrape properties for a specific Arkansas county.

        Args:
            county_name: County name (e.g., "Pulaski", "Washington")

        Returns:
            List of COSLProperty objects for that county
        """
        return await self.scrape_all_properties(county_filter=county_name)

    def to_dataframe(self, properties: List[COSLProperty]) -> pd.DataFrame:
        """
        Convert list of properties to pandas DataFrame.

        Returns DataFrame with columns matching database schema.
        """
        if not properties:
            return pd.DataFrame()

        records = [prop.to_dict() for prop in properties]
        df = pd.DataFrame(records)

        # Calculate price per acre
        df['price_per_acre'] = df.apply(
            lambda row: row['amount'] / row['acreage'] if row['acreage'] > 0 else None,
            axis=1
        )

        return df

    async def scrape_to_dataframe(self, county_filter: Optional[str] = None,
                                   save_raw: bool = True) -> pd.DataFrame:
        """
        Convenience method to scrape and return DataFrame directly.

        Args:
            county_filter: Optional county name filter
            save_raw: Whether to save raw CSV to data/raw/

        Returns:
            pandas DataFrame with scraped properties
        """
        properties = await self.scrape_all_properties(county_filter=county_filter)
        df = self.to_dataframe(properties)

        if save_raw and not df.empty:
            raw_dir = Path("data/raw")
            raw_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            county_suffix = f"_{county_filter.lower().replace(' ', '_')}" if county_filter else ""
            filename = f"arkansas_cosl{county_suffix}_{timestamp}.csv"
            filepath = raw_dir / filename
            df.to_csv(filepath, index=False)
            logger.info(f"Saved raw data to: {filepath}")

        return df


# Convenience function for CLI usage
async def scrape_arkansas_properties(county: Optional[str] = None,
                                      save_raw: bool = True) -> pd.DataFrame:
    """
    Scrape Arkansas COSL properties.

    Args:
        county: Optional county name to filter
        save_raw: Whether to save raw CSV

    Returns:
        pandas DataFrame with property data
    """
    async with ArkansasCOSLScraper() as scraper:
        return await scraper.scrape_to_dataframe(county_filter=county, save_raw=save_raw)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape Arkansas COSL tax deed properties")
    parser.add_argument("--county", help="Filter by county name (e.g., 'Pulaski')")
    parser.add_argument("--output", help="Output CSV file path")
    parser.add_argument("--no-save-raw", action="store_true", help="Don't save raw CSV")

    args = parser.parse_args()

    async def main():
        df = await scrape_arkansas_properties(
            county=args.county,
            save_raw=not args.no_save_raw
        )

        if args.output:
            df.to_csv(args.output, index=False)
            print(f"Saved {len(df)} properties to: {args.output}")
        else:
            print(f"Scraped {len(df)} Arkansas properties")
            if not df.empty:
                print(f"\nCounty distribution:")
                print(df['county'].value_counts().head(10))
                print(f"\nPrice range: ${df['amount'].min():.2f} - ${df['amount'].max():.2f}")
                print(f"Acreage range: {df['acreage'].min():.2f} - {df['acreage'].max():.2f}")

    asyncio.run(main())
