"""
Texas RealAuction Scraper for County Tax Deed Sales

Scrapes tax deed properties from RealAuction platform ([county].realforeclose.com).
8 of top 10 Texas counties use this platform:
- Harris, Dallas, Tarrant, Travis, Collin, Denton, El Paso, Fort Bend

Key characteristics:
- Tax DEED state (redeemable deed): 6-month redemption for non-homestead, 2 years for homestead
- 25% penalty if owner redeems within redemption period
- "First Tuesday" of the month auction schedule
- Playwright required (ASP.NET postback-heavy UI)

Data source: https://[county].realforeclose.com
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import sys
import re

# Add project root for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright, Browser, Page, Playwright, TimeoutError as PlaywrightTimeoutError
from config.logging_config import get_logger
from .utils import EXIT_SUCCESS, EXIT_TRANSIENT, EXIT_PERMANENT, EXIT_RATE_LIMIT, save_debug_snapshot

logger = get_logger(__name__)


# Texas counties with their tax sale listing URLs
# Texas doesn't have a centralized auction system - each county has their own
TEXAS_COUNTIES: Dict[str, Dict[str, Any]] = {
    'harris': {
        'name': 'Harris',
        'fips': '201',
        'seat': 'Houston',
        'listing_url': 'https://www.hctax.net/Property/listings/taxsalelisting',
        'info_url': 'https://www.hctax.net/Property/TaxSales',
        'format': 'hctax',  # Harris County Tax format - WORKING
    },
    'dallas': {
        'name': 'Dallas',
        'fips': '113',
        'seat': 'Dallas',
        'listing_url': 'https://dallas.texas.sheriffsaleauctions.com',
        'info_url': 'https://www.dallascounty.org/departments/tax/sheriff-sales.php',
        'format': 'realauction_sheriff',  # RealAuction platform - requires Playwright
    },
    'tarrant': {
        'name': 'Tarrant',
        'fips': '439',
        'seat': 'Fort Worth',
        'listing_url': 'https://www.tarrantcountytx.gov/en/constables/constable-3/delinquent-tax-sales/monthly-tax-sales-listings.html',
        'info_url': 'https://www.tarrantcountytx.gov/en/constables/constable-3/delinquent-tax-sales.html',
        'format': 'tarrant_html',  # Nested HTML pages with date links
    },
    'travis': {
        'name': 'Travis',
        'fips': '453',
        'seat': 'Austin',
        'listing_url': 'https://travis.texas.realforeclose.com/index.cfm?zaction=USER&zmethod=CALENDAR',
        'info_url': 'https://tax-office.traviscountytx.gov/properties/foreclosed/upcoming-sales',
        'format': 'realauction',  # RealAuction platform - requires Playwright
    },
    'collin': {
        'name': 'Collin',
        'fips': '085',
        'seat': 'McKinney',
        'listing_url': 'https://www.collincountytx.gov/Courts/Constables/constable-sales',
        'info_url': 'https://www.collincountytx.gov/Tax-Assessor/properties-for-sale',
        'format': 'sharepoint',  # SharePoint AJAX - complex
    },
    'denton': {
        'name': 'Denton',
        'fips': '121',
        'seat': 'Denton',
        'listing_url': 'https://www.govease.com',
        'info_url': 'https://www.dentoncounty.gov/867/Delinquent-Tax-Sales',
        'format': 'govease',  # GovEase platform - requires registration
    },
    'el_paso': {
        'name': 'El Paso',
        'fips': '141',
        'seat': 'El Paso',
        'listing_url': 'https://www.epcounty.com/sheriff/cp_sales.htm',
        'info_url': 'https://www.epcounty.com/sheriff/cp_sales.htm',
        'format': 'el_paso_html',  # Simple HTML tables
    },
    'fort_bend': {
        'name': 'Fort Bend',
        'fips': '157',
        'seat': 'Richmond',
        'listing_url': 'https://www.fortbendcountytx.gov/government/departments/constables/constable-precinct-4/tax-and-property-sales',
        'info_url': 'https://www.fortbendcountytx.gov/government/departments/constables/constable-precinct-4/tax-and-property-sales',
        'format': 'fort_bend_html',  # Dynamic content
    },
}

# Reverse mapping (various formats to county key)
COUNTY_NAME_TO_KEY: Dict[str, str] = {}
for key, config in TEXAS_COUNTIES.items():
    COUNTY_NAME_TO_KEY[key.upper()] = key
    COUNTY_NAME_TO_KEY[config['name'].upper()] = key
    # Handle variations like "EL PASO" vs "ELPASO" vs "EL_PASO"
    COUNTY_NAME_TO_KEY[key.replace('_', '').upper()] = key
    COUNTY_NAME_TO_KEY[key.replace('_', ' ').upper()] = key


class CountyValidationError(Exception):
    """Raised when an invalid county code/name is provided."""
    pass


@dataclass
class TexasProperty:
    """Data class for Texas RealAuction property listing."""
    parcel_id: str
    amount: float  # Starting bid / minimum bid
    county: str
    description: str
    acreage: Optional[float] = None
    owner_name: Optional[str] = None
    auction_date: Optional[datetime] = None
    property_address: Optional[str] = None
    cause_number: Optional[str] = None  # Texas court case number
    assessed_value: Optional[float] = None
    property_type: Optional[str] = None  # Homestead status affects redemption
    scraped_at: datetime = field(default_factory=datetime.utcnow)

    # Acreage lineage tracking
    acreage_source: Optional[str] = None
    acreage_confidence: Optional[str] = None
    acreage_raw_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            'parcel_id': self.parcel_id,
            'county': self.county,
            'owner_name': self.owner_name,
            'amount': self.amount,
            'description': self.description,
            'acreage': self.acreage,
            'state': 'TX',
            'sale_type': 'redeemable_deed',
            'redemption_period_days': 180,  # 6 months standard (2 years for homestead)
            'time_to_ownership_days': 180,
            'data_source': 'texas_realauction',
            'auction_platform': 'RealAuction',
            'auction_date': self.auction_date.isoformat() if self.auction_date else None,
            'year_sold': str(datetime.now().year),
            'acreage_source': self.acreage_source,
            'acreage_confidence': self.acreage_confidence,
            'acreage_raw_text': self.acreage_raw_text,
            # Additional Texas-specific fields
            'property_address': self.property_address,
            'cause_number': self.cause_number,
            'assessed_value': self.assessed_value,
        }


class TexasRealAuctionScraper:
    """
    Scraper for Texas county tax deed auctions on RealAuction platform.
    Uses Playwright to handle ASP.NET postbacks and JavaScript-heavy UI.

    Usage:
        async with TexasRealAuctionScraper() as scraper:
            properties = await scraper.scrape_county('harris')
    """

    BASE_URL_TEMPLATE = "https://{subdomain}.realforeclose.com"
    DEFAULT_TIMEOUT = 60000  # milliseconds
    RATE_LIMIT_DELAY = 2.0  # seconds between requests (be conservative)

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context = None

    async def __aenter__(self):
        """Start Playwright browser with realistic browser context."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        # Create context with realistic user agent to avoid 403 blocks
        self._context = await self._browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            java_script_enabled=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup Playwright resources."""
        if hasattr(self, '_context') and self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    def _normalize_county(self, county_input: str) -> str:
        """
        Normalize county input to internal key format.

        Args:
            county_input: County name in various formats (e.g., 'Harris', 'harris', 'HARRIS')

        Returns:
            Internal county key (e.g., 'harris')

        Raises:
            CountyValidationError: If county not found in supported list
        """
        if not county_input:
            raise CountyValidationError("County is required for Texas RealAuction search")

        county_input = str(county_input).strip()
        normalized = county_input.upper().replace('-', '_').replace(' ', '_')

        # Try direct lookup
        if normalized in COUNTY_NAME_TO_KEY:
            return COUNTY_NAME_TO_KEY[normalized]

        # Try without underscores/spaces
        simplified = normalized.replace('_', '')
        if simplified in COUNTY_NAME_TO_KEY:
            return COUNTY_NAME_TO_KEY[simplified]

        # Try partial match
        for key in TEXAS_COUNTIES:
            if normalized.startswith(key.upper()) or key.upper().startswith(normalized):
                return key

        supported = ', '.join(sorted(c['name'] for c in TEXAS_COUNTIES.values()))
        raise CountyValidationError(
            f"Invalid Texas RealAuction county: {county_input}. "
            f"Supported counties: {supported}"
        )

    def _get_county_config(self, county_key: str) -> Dict[str, str]:
        """Get county configuration by internal key."""
        return TEXAS_COUNTIES[county_key]

    def _parse_amount(self, amount_str: str) -> float:
        """Parse amount string to float."""
        if not amount_str:
            return 0.0
        # Remove currency symbols and commas
        cleaned = re.sub(r'[^\d.]', '', str(amount_str))
        try:
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0

    def _parse_acreage(self, text: str) -> tuple[Optional[float], Optional[str], Optional[str]]:
        """
        Extract acreage from text description.

        Returns:
            Tuple of (acreage, source, confidence)
        """
        if not text:
            return None, None, None

        text_lower = text.lower()

        # Pattern: "X.XX acres" or "X.XX ac"
        acre_match = re.search(r'(\d+\.?\d*)\s*(?:acres?|ac\.?)\b', text_lower)
        if acre_match:
            try:
                acreage = float(acre_match.group(1))
                return acreage, 'parsed_explicit', 'high'
            except ValueError:
                pass

        # Pattern: "X sq ft" or "X square feet" - convert to acres
        sqft_match = re.search(r'(\d+[,\d]*\.?\d*)\s*(?:sq\.?\s*ft\.?|square\s*feet?)', text_lower)
        if sqft_match:
            try:
                sqft = float(sqft_match.group(1).replace(',', ''))
                acreage = sqft / 43560  # Convert sq ft to acres
                return round(acreage, 4), 'parsed_sqft', 'medium'
            except ValueError:
                pass

        return None, None, None

    async def scrape_county(self, county_input: str, max_pages: int = 50) -> List[TexasProperty]:
        """
        Scrape tax deed properties for a specific Texas county.

        Args:
            county_input: County name (e.g., 'Harris', 'harris')
            max_pages: Maximum pages to scrape (safety limit)

        Returns:
            List of TexasProperty objects
        """
        if not self._browser or not hasattr(self, '_context'):
            raise RuntimeError("Scraper not started. Use 'async with' context manager.")

        county_key = self._normalize_county(county_input)
        config = self._get_county_config(county_key)
        county_name = config['name']
        listing_url = config['listing_url']
        county_format = config.get('format', 'generic')

        logger.info(f"Starting Texas tax sale scrape for {county_name} County at {listing_url}")

        # Use context for realistic browser fingerprint
        page = await self._context.new_page()
        page.set_default_timeout(self.DEFAULT_TIMEOUT)

        properties: List[TexasProperty] = []

        try:
            # Navigate to county tax sale listing page
            await page.goto(listing_url)
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(self.RATE_LIMIT_DELAY)

            # Dispatch to format-specific parser
            if county_format == 'hctax':
                properties = await self._parse_harris_county(page, county_name)
            elif county_format == 'el_paso_html':
                properties = await self._parse_el_paso_county(page, county_name)
            elif county_format == 'tarrant_html':
                properties = await self._parse_tarrant_county(page, county_name)
            elif county_format == 'govease':
                # GovEase requires user registration - cannot scrape automatically
                logger.warning(f"{county_name} County uses GovEase platform which requires registration. Visit govease.com to view listings.")
                properties = []
            elif county_format in ('realauction', 'realauction_sheriff'):
                # RealAuction platforms - not yet implemented
                logger.warning(f"{county_name} County uses RealAuction platform - parser not yet implemented")
                properties = await self._parse_generic_county(page, county_name)
            elif county_format in ('sharepoint', 'fort_bend_html'):
                # Complex formats - not yet implemented
                logger.warning(f"{county_name} County format '{county_format}' not yet implemented - trying generic parser")
                properties = await self._parse_generic_county(page, county_name)
            else:
                # Generic fallback - try to find any property data
                properties = await self._parse_generic_county(page, county_name)

            # Save debug snapshot if no properties found (potential parsing issue)
            if not properties:
                logger.warning(f"No properties found for {county_name} - saving debug snapshot")
                try:
                    content = await page.content()
                    save_debug_snapshot(content, 'TX', county_name, "no_properties_found", logger=logger)
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Error scraping {county_name}: {e}")
            # Save debug snapshot on error
            try:
                content = await page.content()
                save_debug_snapshot(content, 'TX', county_name, str(e), logger=logger)
            except Exception:
                pass  # Don't fail on snapshot error
            raise
        finally:
            await page.close()

        logger.info(f"Scraped {len(properties)} properties from {county_name} County")
        return properties

    async def _parse_harris_county(self, page, county_name: str) -> List[TexasProperty]:
        """
        Parse Harris County Tax Office listing format.
        Properties are displayed in individual card/table structures.
        """
        properties = []

        # Get all tables - Harris County uses multiple tables per property
        tables = await page.query_selector_all('table')
        logger.debug(f"Found {len(tables)} tables on Harris County page")

        current_prop_data: Dict[str, Any] = {}

        for table in tables:
            rows = await table.query_selector_all('tr')

            for row in rows:
                cells = await row.query_selector_all('td, th')
                cell_texts = [(await c.text_content() or '').strip() for c in cells]

                # Look for key-value pairs (format: "Key:" "Value")
                if len(cell_texts) >= 2:
                    key = cell_texts[0].replace(':', '').strip()
                    value = cell_texts[1].strip()

                    if key and value:
                        current_prop_data[key.lower().replace(' ', '_')] = value

                elif len(cell_texts) == 1:
                    text = cell_texts[0]
                    # "Adjudged Value: $X" marks start of new property
                    if 'Adjudged Value' in text:
                        # Save previous property if we have data
                        if current_prop_data.get('cause#') or current_prop_data.get('sale#'):
                            prop = self._create_property_from_harris_data(current_prop_data, county_name)
                            if prop:
                                properties.append(prop)

                        # Start new property
                        current_prop_data = {}
                        # Extract adjudged value
                        match = re.search(r'\$[\d,]+(?:\.\d{2})?', text)
                        if match:
                            current_prop_data['adjudged_value'] = match.group()

        # Don't forget last property
        if current_prop_data.get('cause#') or current_prop_data.get('sale#'):
            prop = self._create_property_from_harris_data(current_prop_data, county_name)
            if prop:
                properties.append(prop)

        return properties

    def _create_property_from_harris_data(self, data: Dict[str, Any], county: str) -> Optional[TexasProperty]:
        """Create TexasProperty from Harris County parsed data."""
        try:
            # Extract cause number as primary ID
            cause_number = data.get('cause#', '')

            if not cause_number:
                return None

            # Parse minimum bid
            min_bid_str = data.get('minimum_bid', '0')
            amount = self._parse_amount(min_bid_str)

            # Parse adjudged value
            adjudged_str = data.get('adjudged_value', '0')
            assessed_value = self._parse_amount(adjudged_str)

            # Build parcel ID from cause number
            parcel_id = f"TX-HARRIS-{cause_number}"

            # Build description from available data
            desc_parts = []
            if data.get('type'):
                desc_parts.append(f"Type: {data['type']}")
            if data.get('tax_years_in_judgement'):
                desc_parts.append(f"Tax Years: {data['tax_years_in_judgement']}")
            if data.get('precinct'):
                desc_parts.append(data['precinct'])
            description = '; '.join(desc_parts) if desc_parts else f"Cause #{cause_number}"

            return TexasProperty(
                parcel_id=parcel_id,
                amount=amount,
                county=county,
                description=description,
                cause_number=cause_number,
                assessed_value=assessed_value,
                acreage=None,  # Not provided in Harris format
                owner_name=None,  # Not directly provided
            )
        except Exception as e:
            logger.debug(f"Failed to create property from Harris data: {e}")
            return None

    async def _parse_generic_county(self, page, county_name: str) -> List[TexasProperty]:
        """
        Generic parser for counties without specific format handlers.
        Attempts to find property data in tables or structured elements.
        """
        properties = []

        # Try to find tables with property data
        tables = await page.query_selector_all('table')

        for table in tables:
            rows = await table.query_selector_all('tr')

            # Skip tables with less than 2 rows (header + data)
            if len(rows) < 2:
                continue

            # Try to identify header row
            header_row = rows[0]
            header_cells = await header_row.query_selector_all('th, td')
            headers = [(await h.text_content() or '').strip().lower() for h in header_cells]

            # Skip if this doesn't look like a property table
            property_keywords = ['parcel', 'account', 'address', 'bid', 'amount', 'value', 'cause']
            if not any(kw in ' '.join(headers) for kw in property_keywords):
                continue

            # Parse data rows
            for row in rows[1:]:
                cells = await row.query_selector_all('td')
                cell_texts = [(await c.text_content() or '').strip() for c in cells]

                if not any(cell_texts):
                    continue

                try:
                    prop = await self._parse_property_element(row, county_name)
                    if prop:
                        properties.append(prop)
                except Exception as e:
                    logger.debug(f"Failed to parse row: {e}")

        # If no tables found, check for card-style layouts
        if not properties:
            cards = await page.query_selector_all('.card, .property, [class*="listing"], [class*="item"]')
            for card in cards:
                try:
                    prop = await self._parse_property_element(card, county_name)
                    if prop:
                        properties.append(prop)
                except Exception:
                    continue

        return properties

    async def _parse_property_element(self, element, county: str) -> Optional[TexasProperty]:
        """
        Parse a property from a page element (table row or card).

        Args:
            element: Playwright element handle
            county: County name

        Returns:
            TexasProperty or None if parsing fails
        """
        try:
            # Get all text content from element
            text_content = await element.text_content() or ''

            # Try to extract data from common patterns
            # RealAuction typically shows: Cause#, Address, Min Bid, Assessed Value, etc.

            # Look for cause number (Texas specific - format like "2023-12345")
            cause_match = re.search(r'(?:cause\s*#?:?\s*)?(\d{4}[-/]\d+)', text_content, re.I)
            cause_number = cause_match.group(1) if cause_match else None

            # Look for parcel/property ID
            parcel_match = re.search(
                r'(?:parcel|prop(?:erty)?|id)\s*(?:#|:)?\s*([A-Z0-9\-]+)',
                text_content, re.I
            )
            parcel_id = parcel_match.group(1) if parcel_match else None

            # If no parcel, use cause number as identifier
            if not parcel_id and cause_number:
                parcel_id = f"TX-{county.upper()}-{cause_number}"
            elif not parcel_id:
                # Generate a placeholder - will be deduplicated later
                parcel_id = f"TX-{county.upper()}-{hash(text_content) % 100000:05d}"

            # Look for amount/bid
            # Patterns: "$1,234", "Min Bid: $1,234", "Opening Bid $1,234"
            amount_match = re.search(
                r'(?:min(?:imum)?\s*bid|opening\s*bid|bid|amount)\s*:?\s*\$?([\d,]+(?:\.\d{2})?)',
                text_content, re.I
            )
            if not amount_match:
                # Try generic dollar amount
                amount_match = re.search(r'\$([\d,]+(?:\.\d{2})?)', text_content)

            amount = self._parse_amount(amount_match.group(1)) if amount_match else 0.0

            # Look for address (multi-line pattern)
            # Texas addresses typically: "123 Main St" or full address
            address_match = re.search(
                r'(\d+\s+[A-Za-z0-9\s,\.]+(?:St|Ave|Rd|Dr|Blvd|Ln|Way|Ct|Pl|Circle|Cir)\.?)',
                text_content, re.I
            )
            address = address_match.group(1).strip() if address_match else None

            # Look for defendant/owner name
            owner_match = re.search(
                r'(?:defendant|owner|name)\s*:?\s*([A-Za-z\s,\.]+?)(?:\d|$|\n)',
                text_content, re.I
            )
            owner = owner_match.group(1).strip() if owner_match else None

            # Look for assessed value
            assessed_match = re.search(
                r'(?:assessed|appraised|value)\s*:?\s*\$?([\d,]+)',
                text_content, re.I
            )
            assessed_value = self._parse_amount(assessed_match.group(1)) if assessed_match else None

            # Parse acreage from description
            acreage, acreage_source, acreage_confidence = self._parse_acreage(text_content)

            # Build description from available text (cleaned)
            description = re.sub(r'\s+', ' ', text_content).strip()[:500]  # Limit length

            return TexasProperty(
                parcel_id=parcel_id,
                amount=amount,
                county=county,
                description=description,
                acreage=acreage,
                owner_name=owner,
                property_address=address,
                cause_number=cause_number,
                assessed_value=assessed_value,
                acreage_source=acreage_source,
                acreage_confidence=acreage_confidence,
                acreage_raw_text=text_content[:200] if acreage else None,
            )

        except Exception as e:
            logger.debug(f"Failed to parse property: {e}")
            return None

    async def _parse_el_paso_county(self, page, county_name: str) -> List[TexasProperty]:
        """
        Parse El Paso County Sheriff's Office real property sale notices.

        The page has a "Real Property Sale Notices (Judgment Sales)" section
        with a table containing: Sale Date, Time, Location, Property Description.
        The Description column may contain multiple properties for one sale date.
        Note: Minimum bid amounts are not shown - posted on lgbs.com monthly.
        """
        properties = []
        seen_parcels = set()  # Track duplicates

        # Find all tables on the page
        tables = await page.query_selector_all('table')
        logger.debug(f"Found {len(tables)} tables on El Paso page")

        current_sale_date = None
        current_location = None

        for table in tables:
            rows = await table.query_selector_all('tr')

            for row in rows:
                cells = await row.query_selector_all('td')
                if len(cells) < 3:
                    continue

                cell_texts = [(await c.text_content() or '').strip() for c in cells]

                # Skip header rows
                first_cell_lower = cell_texts[0].lower() if cell_texts else ''
                if first_cell_lower in ('sale date', 'date', '') or 'sale date' in first_cell_lower:
                    continue

                # Check if this row has a date (starts new sale event)
                date_text = cell_texts[0]
                date_match = re.search(
                    r'((?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4})',
                    date_text, re.I
                )

                if date_match:
                    # New sale date found
                    try:
                        for fmt in ['%B %d, %Y', '%B %d %Y']:
                            try:
                                current_sale_date = datetime.strptime(date_match.group(1).replace(',', ''), fmt.replace(',', ''))
                                break
                            except ValueError:
                                continue
                    except Exception:
                        current_sale_date = None

                    # Get location (usually column 3)
                    if len(cell_texts) >= 3:
                        current_location = cell_texts[2]

                # Get the description column (last column with substantial content)
                description = ''
                for text in reversed(cell_texts):
                    if text and len(text) > 20:  # Skip short cells like dates/times
                        description = text
                        break

                if not description:
                    continue

                # The description may contain multiple properties separated by patterns
                # Split on "STREET ADDR" or similar markers, or process as single property
                property_blocks = re.split(r'(?=STREET\s*ADDR)', description, flags=re.I)

                for block in property_blocks:
                    block = block.strip()
                    if not block or len(block) < 10:
                        continue

                    try:
                        # Extract street address
                        address_match = re.search(
                            r'(?:STREET\s*ADDR[:\s]*)?(\d+\s+[A-Za-z0-9\s]+(?:RD|ST|AVE|DR|BLVD|LN|WAY|CT|PL|CIR)\.?)',
                            block, re.I
                        )
                        address = address_match.group(1).strip() if address_match else None

                        # Extract tax account number (format like C30199902507700)
                        account_match = re.search(r'(?:TAX\s*)?(?:ACCT|ACCOUNT|ACCT\s*NO)[\s\(\):\.#]*([A-Z]?\d{8,})', block, re.I)
                        account_number = account_match.group(1) if account_match else None

                        # Extract lot/block info
                        lot_match = re.search(r'LOT\s+(\d+)', block, re.I)
                        block_match = re.search(r'BLOCK\s+(\d+)', block, re.I)

                        # Generate unique parcel ID
                        if account_number:
                            parcel_id = f"TX-ELPASO-{account_number}"
                        elif lot_match and block_match:
                            parcel_id = f"TX-ELPASO-L{lot_match.group(1)}-B{block_match.group(1)}"
                        elif address:
                            addr_hash = abs(hash(address)) % 100000
                            parcel_id = f"TX-ELPASO-{addr_hash:05d}"
                        else:
                            desc_hash = abs(hash(block)) % 100000
                            parcel_id = f"TX-ELPASO-{desc_hash:05d}"

                        # Skip duplicates
                        if parcel_id in seen_parcels:
                            continue
                        seen_parcels.add(parcel_id)

                        # Parse acreage if present
                        acreage, acreage_source, acreage_confidence = self._parse_acreage(block)

                        # Clean up description
                        clean_desc = re.sub(r'\s+', ' ', block).strip()[:400]
                        if current_location:
                            clean_desc = f"{clean_desc}; Sale Location: {current_location}"

                        prop = TexasProperty(
                            parcel_id=parcel_id,
                            amount=0.0,  # El Paso doesn't show minimum bid on county site
                            county=county_name,
                            description=clean_desc,
                            property_address=address,
                            auction_date=current_sale_date,
                            acreage=acreage,
                            acreage_source=acreage_source,
                            acreage_confidence=acreage_confidence,
                            acreage_raw_text=block[:200] if acreage else None,
                        )
                        properties.append(prop)

                    except Exception as e:
                        logger.debug(f"Failed to parse El Paso property block: {e}")
                        continue

        logger.info(f"Parsed {len(properties)} properties from El Paso County")
        return properties

    async def _parse_tarrant_county(self, page, county_name: str) -> List[TexasProperty]:
        """
        Parse Tarrant County monthly tax sales listings.

        The main page lists upcoming sale dates as links.
        Each date link leads to a page with a table of properties:
        Cause Number | Account Number | Status (For Sale/Withdrawn)

        Note: Minimum bid amounts not shown on county site.
        """
        properties = []
        base_url = 'https://www.tarrantcountytx.gov'

        # Find all links to monthly sale pages
        links = await page.query_selector_all('a')
        sale_page_urls = []

        for link in links:
            href = await link.get_attribute('href')
            text = await link.text_content() or ''

            # Look for date links (e.g., "October 7, 2025" or links containing sale info)
            if href and re.search(r'\d{4}|january|february|march|april|may|june|july|august|september|october|november|december', text.lower()):
                # Skip if it's just an anchor or external link
                if href.startswith('#') or 'tarrantcountytx.gov' not in href and not href.startswith('/'):
                    continue

                full_url = href if href.startswith('http') else f"{base_url}{href}"

                # Avoid duplicates
                if full_url not in sale_page_urls:
                    sale_page_urls.append(full_url)

        logger.debug(f"Found {len(sale_page_urls)} potential sale date pages")

        # Visit each sale page (limit to next 3 to avoid overloading)
        for url in sale_page_urls[:3]:
            try:
                logger.debug(f"Visiting Tarrant sale page: {url}")
                await page.goto(url)
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(self.RATE_LIMIT_DELAY)

                # Extract sale date from page title or URL
                page_title = await page.title()
                sale_date = None
                date_match = re.search(
                    r'((?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4})',
                    page_title.lower()
                )
                if date_match:
                    try:
                        for fmt in ['%B %d, %Y', '%B %d %Y']:
                            try:
                                sale_date = datetime.strptime(date_match.group(1).title(), fmt)
                                break
                            except ValueError:
                                continue
                    except Exception:
                        pass

                # Find property table
                tables = await page.query_selector_all('table')

                for table in tables:
                    rows = await table.query_selector_all('tr')

                    # Skip small tables
                    if len(rows) < 2:
                        continue

                    # Check if this looks like a property table
                    header_row = rows[0]
                    header_text = (await header_row.text_content() or '').lower()

                    if 'cause' not in header_text and 'account' not in header_text:
                        continue

                    # Parse data rows
                    for row in rows[1:]:
                        cells = await row.query_selector_all('td')
                        if len(cells) < 2:
                            continue

                        cell_texts = [(await c.text_content() or '').strip() for c in cells]

                        # Skip empty rows
                        if not any(cell_texts):
                            continue

                        try:
                            # Expected: Cause Number | Account Number | Status
                            cause_number = cell_texts[0] if len(cell_texts) > 0 else ''
                            account_number = cell_texts[1] if len(cell_texts) > 1 else ''
                            status = cell_texts[2] if len(cell_texts) > 2 else 'For Sale'

                            # Skip withdrawn/voided/sold properties
                            if any(s in status.lower() for s in ('withdrawn', 'sold', 'voided', 'cancelled')):
                                continue

                            # Skip if no valid cause/account number
                            if not cause_number or cause_number.lower() in ('cause', 'cause number', 'cause #'):
                                continue

                            # Generate parcel ID
                            if account_number and account_number.lower() not in ('account', 'account number', 'account #'):
                                parcel_id = f"TX-TARRANT-{account_number}"
                            else:
                                parcel_id = f"TX-TARRANT-{cause_number}"

                            prop = TexasProperty(
                                parcel_id=parcel_id,
                                amount=0.0,  # Not provided on county site
                                county=county_name,
                                description=f"Cause: {cause_number}; Account: {account_number}; Status: {status}",
                                cause_number=cause_number,
                                auction_date=sale_date,
                            )
                            properties.append(prop)

                        except Exception as e:
                            logger.debug(f"Failed to parse Tarrant row: {e}")
                            continue

            except Exception as e:
                logger.warning(f"Failed to process Tarrant sale page {url}: {e}")
                continue

        logger.info(f"Parsed {len(properties)} properties from Tarrant County")
        return properties


def get_supported_counties() -> List[str]:
    """Get list of supported Texas counties."""
    return sorted(c['name'] for c in TEXAS_COUNTIES.values())


# Convenience function for CLI usage
async def scrape_texas_county(county: str, max_pages: int = 50) -> List[TexasProperty]:
    """
    Scrape Texas RealAuction properties for a county.

    Args:
        county: County name
        max_pages: Maximum pages to scrape

    Returns:
        List of TexasProperty objects
    """
    async with TexasRealAuctionScraper() as scraper:
        return await scraper.scrape_county(county, max_pages=max_pages)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Scrape Texas RealAuction tax deed properties")
    parser.add_argument(
        "county",
        nargs='?',  # Make county optional to allow --list-counties
        help=f"County name. Supported: {', '.join(get_supported_counties())}"
    )
    parser.add_argument("--max-pages", type=int, default=50, help="Maximum pages to scrape")
    parser.add_argument("--output", help="Output CSV file path")
    parser.add_argument("--json-output", help="Output JSON file path (for API integration)")
    parser.add_argument("--list-counties", action="store_true", help="List supported counties and exit")

    args = parser.parse_args()

    if args.list_counties:
        print("Supported Texas counties:")
        for county in get_supported_counties():
            config = TEXAS_COUNTIES[county.lower().replace(' ', '_')]
            print(f"  - {county} ({config['seat']}) - {config['listing_url']}")
        sys.exit(EXIT_SUCCESS)

    if not args.county:
        parser.error("county is required (or use --list-counties)")
        sys.exit(EXIT_PERMANENT)

    async def main():
        try:
            properties = await scrape_texas_county(args.county, max_pages=args.max_pages)

            if args.json_output:
                # JSON output for API subprocess integration
                prop_dicts = [p.to_dict() for p in properties]
                with open(args.json_output, 'w') as f:
                    json.dump(prop_dicts, f, indent=2, default=str)
                # Silent success for subprocess
                sys.exit(EXIT_SUCCESS)
            elif args.output:
                import pandas as pd
                df = pd.DataFrame([p.to_dict() for p in properties])
                df.to_csv(args.output, index=False)
                print(f"Saved {len(properties)} properties to: {args.output}")
                sys.exit(EXIT_SUCCESS)
            else:
                print(f"Scraped {len(properties)} properties from {args.county} County")
                for prop in properties[:5]:
                    print(f"  - {prop.parcel_id}: ${prop.amount:.2f}")
                    if prop.property_address:
                        print(f"    Address: {prop.property_address}")
                    if prop.cause_number:
                        print(f"    Cause #: {prop.cause_number}")
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
