"""
Florida RealTaxDeed Scraper for County Tax Deed Sales

Scrapes tax deed properties from RealTaxDeed platform ([county].realtaxdeed.com).
Major Florida counties use this platform for tax deed auctions.

Key characteristics:
- HYBRID state: Tax lien first (18% interest), then tax deed auction
- No redemption after tax deed sale - buyer gets immediate ownership
- ~2-year holding period before lien holder can force deed auction
- Playwright required (ASP.NET postback-heavy UI)

Data source: https://[county].realtaxdeed.com
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
from core.scrapers.utils import EXIT_SUCCESS, EXIT_TRANSIENT, EXIT_PERMANENT, EXIT_RATE_LIMIT, save_debug_snapshot

logger = get_logger(__name__)


# Florida counties with their tax deed listing URLs
# Florida uses county-specific RealTaxDeed sites for tax deed auctions
FLORIDA_COUNTIES: Dict[str, Dict[str, Any]] = {
    'orange': {
        'name': 'Orange',
        'fips': '095',
        'seat': 'Orlando',
        'listing_url': 'https://orange.realtaxdeed.com/index.cfm?zaction=USER&zmethod=CALENDAR',
        'format': 'realtaxdeed',
    },
    'miami_dade': {
        'name': 'Miami-Dade',
        'fips': '086',
        'seat': 'Miami',
        'listing_url': 'https://www.miamidade.realforeclose.com/index.cfm?zaction=USER&zmethod=CALENDAR',
        'format': 'realtaxdeed',
    },
    'hillsborough': {
        'name': 'Hillsborough',
        'fips': '057',
        'seat': 'Tampa',
        'listing_url': 'https://hillsborough.realtaxdeed.com/index.cfm?zaction=USER&zmethod=CALENDAR',
        'format': 'realtaxdeed',
    },
    'duval': {
        'name': 'Duval',
        'fips': '031',
        'seat': 'Jacksonville',
        'listing_url': 'https://duval.realtaxdeed.com/index.cfm?zaction=USER&zmethod=CALENDAR',
        'format': 'realtaxdeed',
    },
}

# Reverse mapping (various formats to county key)
COUNTY_NAME_TO_KEY: Dict[str, str] = {}
for key, config in FLORIDA_COUNTIES.items():
    COUNTY_NAME_TO_KEY[key.upper()] = key
    COUNTY_NAME_TO_KEY[config['name'].upper()] = key
    # Handle variations like "MIAMI DADE" vs "MIAMIDADE" vs "MIAMI_DADE" vs "MIAMI-DADE"
    COUNTY_NAME_TO_KEY[key.replace('_', '').upper()] = key
    COUNTY_NAME_TO_KEY[key.replace('_', ' ').upper()] = key
    COUNTY_NAME_TO_KEY[key.replace('_', '-').upper()] = key


class CountyValidationError(Exception):
    """Raised when an invalid county code/name is provided."""
    pass


@dataclass
class FloridaProperty:
    """Data class for Florida RealTaxDeed property listing."""
    parcel_id: str
    amount: float  # Opening bid / minimum bid
    county: str
    description: str

    # Florida-specific fields
    certificate_number: Optional[str] = None  # Tax certificate number
    assessed_value: Optional[float] = None
    property_address: Optional[str] = None
    auction_date: Optional[datetime] = None
    certificate_year: Optional[int] = None  # Year tax certificate was issued

    # Common fields
    acreage: Optional[float] = None
    owner_name: Optional[str] = None
    property_type: Optional[str] = None
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
            'state': 'FL',
            'sale_type': 'tax_deed',  # At deed auction phase
            'redemption_period_days': 0,  # No redemption after deed sale
            'time_to_ownership_days': 0,  # Immediate ownership at deed auction
            'data_source': 'florida_realtaxdeed',
            'auction_platform': 'RealTaxDeed',
            'auction_date': self.auction_date.isoformat() if self.auction_date else None,
            'year_sold': str(self.auction_date.year) if self.auction_date else str(datetime.now().year),
            'acreage_source': self.acreage_source,
            'acreage_confidence': self.acreage_confidence,
            'acreage_raw_text': self.acreage_raw_text,
            # Florida-specific fields
            'certificate_number': self.certificate_number,
            'assessed_value': self.assessed_value,
            'property_address': self.property_address,
        }


class FloridaRealTaxDeedScraper:
    """
    Scraper for Florida county tax deed auctions on RealTaxDeed platform.
    Uses Playwright to handle ASP.NET postbacks and JavaScript-heavy UI.

    Usage:
        async with FloridaRealTaxDeedScraper() as scraper:
            properties = await scraper.scrape_county('orange')
    """

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
            county_input: County name in various formats (e.g., 'Orange', 'orange', 'MIAMI-DADE')

        Returns:
            Internal county key (e.g., 'orange', 'miami_dade')

        Raises:
            CountyValidationError: If county not found in supported list
        """
        if not county_input:
            raise CountyValidationError("County is required for Florida RealTaxDeed search")

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
        for key in FLORIDA_COUNTIES:
            if normalized.startswith(key.upper()) or key.upper().startswith(normalized):
                return key

        supported = ', '.join(sorted(c['name'] for c in FLORIDA_COUNTIES.values()))
        raise CountyValidationError(
            f"Invalid Florida RealTaxDeed county: {county_input}. "
            f"Supported counties: {supported}"
        )

    def _get_county_config(self, county_key: str) -> Dict[str, str]:
        """Get county configuration by internal key."""
        return FLORIDA_COUNTIES[county_key]

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

        # Standard pattern: "X.XX acres" or "X.XX ac"
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

    async def scrape_county(self, county_input: str, max_pages: int = 50) -> List[FloridaProperty]:
        """
        Scrape tax deed properties for a specific Florida county.

        Args:
            county_input: County name (e.g., 'Orange', 'Miami-Dade')
            max_pages: Maximum pages to scrape (safety limit)

        Returns:
            List of FloridaProperty objects
        """
        if not self._browser or not hasattr(self, '_context'):
            raise RuntimeError("Scraper not started. Use 'async with' context manager.")

        county_key = self._normalize_county(county_input)
        config = self._get_county_config(county_key)
        county_name = config['name']
        listing_url = config['listing_url']
        county_format = config.get('format', 'realtaxdeed')

        logger.info(f"Starting Florida tax deed scrape for {county_name} County at {listing_url}")

        # Use context for realistic browser fingerprint
        page = await self._context.new_page()
        page.set_default_timeout(self.DEFAULT_TIMEOUT)

        properties: List[FloridaProperty] = []

        try:
            # Navigate to county tax deed calendar page
            await page.goto(listing_url)
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(self.RATE_LIMIT_DELAY)

            # Dispatch to format-specific parser
            if county_format == 'realtaxdeed':
                properties = await self._parse_realtaxdeed_county(page, county_name, max_pages)
            else:
                # Generic fallback
                properties = await self._parse_generic_county(page, county_name)

            # Save debug snapshot if no properties found (potential parsing issue)
            if not properties:
                logger.warning(f"No properties found for {county_name} - saving debug snapshot")
                try:
                    content = await page.content()
                    save_debug_snapshot(content, 'FL', county_name, "no_properties_found", logger=logger)
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Error scraping {county_name}: {e}")
            # Save debug snapshot on error
            try:
                content = await page.content()
                save_debug_snapshot(content, 'FL', county_name, str(e), logger=logger)
            except Exception:
                pass  # Don't fail on snapshot error
            raise
        finally:
            await page.close()

        logger.info(f"Scraped {len(properties)} properties from {county_name} County")
        return properties

    async def _parse_realtaxdeed_county(self, page: Page, county_name: str, max_pages: int = 50) -> List[FloridaProperty]:
        """
        Parse RealTaxDeed format (standard for most Florida counties).

        RealTaxDeed/RealAuction sites have a calendar view with clickable sale dates.
        Each sale date shows a list of property auctions.
        """
        properties = []
        seen_parcels = set()  # Track duplicates

        # Look for calendar days with auction counts
        # Calendar structure: table with CALMONTH header, CALDAY cells
        # Active sale days have links or auction counts

        # First, try to find any upcoming sale dates on the calendar
        calendar_days = await page.query_selector_all('.CALDAY, [class*="calendar"] a, [class*="Calendar"] a')
        sale_date_links = []

        for day in calendar_days:
            try:
                text = await day.text_content() or ''
                href = await day.get_attribute('href')

                # Look for days with auction counts (e.g., "15 (5 auctions)")
                if re.search(r'\d+\s*(?:auction|sale|item)', text, re.I) or href:
                    if href and not href.startswith('#'):
                        sale_date_links.append(href)
            except Exception:
                continue

        logger.debug(f"Found {len(sale_date_links)} potential sale date links")

        # If no calendar links found, try to find auction items directly on the page
        if not sale_date_links:
            logger.debug("No calendar links found, checking for auction items on current page")
            properties = await self._parse_auction_items_on_page(page, county_name, seen_parcels)

            # Also check for "View All" or "Search" functionality
            if not properties:
                # Try clicking on search/view all buttons
                view_all = await page.query_selector('a:has-text("View All"), a:has-text("Search"), button:has-text("Search")')
                if view_all:
                    try:
                        await view_all.click()
                        await page.wait_for_load_state('networkidle')
                        await asyncio.sleep(self.RATE_LIMIT_DELAY)
                        properties = await self._parse_auction_items_on_page(page, county_name, seen_parcels)
                    except Exception as e:
                        logger.debug(f"Failed to click view all: {e}")
        else:
            # Visit each sale date page (limit to avoid overloading)
            pages_visited = 0
            for link in sale_date_links[:max_pages]:
                if pages_visited >= max_pages:
                    break

                try:
                    # Build full URL if needed
                    if not link.startswith('http'):
                        current_url = page.url
                        base_url = '/'.join(current_url.split('/')[:3])
                        link = f"{base_url}{link}" if link.startswith('/') else f"{current_url.rsplit('/', 1)[0]}/{link}"

                    logger.debug(f"Visiting sale date page: {link}")
                    await page.goto(link)
                    await page.wait_for_load_state('networkidle')
                    await asyncio.sleep(self.RATE_LIMIT_DELAY)

                    page_properties = await self._parse_auction_items_on_page(page, county_name, seen_parcels)
                    properties.extend(page_properties)
                    pages_visited += 1

                except Exception as e:
                    logger.warning(f"Failed to process sale date page {link}: {e}")
                    continue

        return properties

    async def _parse_auction_items_on_page(self, page: Page, county_name: str, seen_parcels: set) -> List[FloridaProperty]:
        """
        Parse auction items from the current page.

        RealTaxDeed auction items typically have:
        - Parcel/Property ID
        - Opening bid amount
        - Property address
        - Legal description
        - Assessed value
        - Certificate number
        """
        properties = []

        # Try multiple selectors for auction items
        # RealTaxDeed uses various class names: AUCTION_ITEM, AuctionItem, etc.
        item_selectors = [
            '.AUCTION_ITEM',
            '.AuctionItem',
            '[class*="auction-item"]',
            '[class*="AuctionItem"]',
            'tr[class*="Item"]',
            '.property-card',
            'table tr:has(td)',
        ]

        items = []
        for selector in item_selectors:
            items = await page.query_selector_all(selector)
            if items:
                logger.debug(f"Found {len(items)} items with selector: {selector}")
                break

        # If no specific items found, try parsing tables
        if not items:
            tables = await page.query_selector_all('table')
            for table in tables:
                rows = await table.query_selector_all('tr')
                if len(rows) > 1:  # Has header + data
                    items.extend(rows[1:])  # Skip header row

        for item in items:
            try:
                prop = await self._parse_auction_item(item, county_name)
                if prop and prop.parcel_id not in seen_parcels:
                    seen_parcels.add(prop.parcel_id)
                    properties.append(prop)
            except Exception as e:
                logger.debug(f"Failed to parse auction item: {e}")
                continue

        return properties

    async def _parse_auction_item(self, element, county_name: str) -> Optional[FloridaProperty]:
        """
        Parse a single auction item element.

        Args:
            element: Playwright element handle
            county_name: County name

        Returns:
            FloridaProperty or None if parsing fails
        """
        try:
            # Get all text content from element
            text_content = await element.text_content() or ''

            if len(text_content.strip()) < 10:
                return None

            # Try to find specific fields using common RealTaxDeed patterns

            # Parcel/Property ID (various formats)
            parcel_match = re.search(
                r'(?:parcel|property|tax)\s*(?:#|id|no\.?)?:?\s*([A-Z0-9\-]+)',
                text_content, re.I
            )
            parcel_id = parcel_match.group(1) if parcel_match else None

            # Certificate number (Florida specific)
            cert_match = re.search(
                r'(?:cert(?:ificate)?)\s*(?:#|no\.?)?:?\s*(\d+[-/]?\d*)',
                text_content, re.I
            )
            certificate_number = cert_match.group(1) if cert_match else None

            # If no parcel ID, try certificate number as identifier
            if not parcel_id and certificate_number:
                parcel_id = f"FL-{county_name.upper()}-CERT-{certificate_number}"
            elif not parcel_id:
                # Generate hash-based ID as fallback
                text_hash = abs(hash(text_content)) % 1000000
                parcel_id = f"FL-{county_name.upper()}-{text_hash:06d}"

            # Opening bid / minimum bid
            bid_match = re.search(
                r'(?:opening|min(?:imum)?|starting)\s*bid:?\s*\$?([\d,]+(?:\.\d{2})?)',
                text_content, re.I
            )
            if not bid_match:
                # Try generic dollar amount
                bid_match = re.search(r'\$([\d,]+(?:\.\d{2})?)', text_content)

            amount = self._parse_amount(bid_match.group(1)) if bid_match else 0.0

            # Property address
            address_match = re.search(
                r'(\d+\s+[A-Za-z0-9\s,\.]+(?:St|Ave|Rd|Dr|Blvd|Ln|Way|Ct|Pl|Circle|Cir)\.?)',
                text_content, re.I
            )
            property_address = address_match.group(1).strip() if address_match else None

            # Assessed value
            assessed_match = re.search(
                r'(?:assessed|appraised|just)\s*(?:value)?:?\s*\$?([\d,]+)',
                text_content, re.I
            )
            assessed_value = self._parse_amount(assessed_match.group(1)) if assessed_match else None

            # Owner/defendant name
            owner_match = re.search(
                r'(?:owner|defendant|name):?\s*([A-Za-z\s,\.]+?)(?:\d|$|\n|parcel|cert)',
                text_content, re.I
            )
            owner_name = owner_match.group(1).strip() if owner_match else None

            # Auction date
            date_match = re.search(
                r'(?:sale|auction)\s*date:?\s*([\d/\-]+)',
                text_content, re.I
            )
            auction_date = None
            if date_match:
                for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%m-%d-%Y']:
                    try:
                        auction_date = datetime.strptime(date_match.group(1), fmt)
                        break
                    except ValueError:
                        continue

            # Parse acreage from description
            acreage, acreage_source, acreage_confidence = self._parse_acreage(text_content)

            # Build description (cleaned)
            description = re.sub(r'\s+', ' ', text_content).strip()[:500]

            return FloridaProperty(
                parcel_id=parcel_id,
                amount=amount,
                county=county_name,
                description=description,
                certificate_number=certificate_number,
                assessed_value=assessed_value,
                property_address=property_address,
                auction_date=auction_date,
                acreage=acreage,
                owner_name=owner_name,
                acreage_source=acreage_source,
                acreage_confidence=acreage_confidence,
                acreage_raw_text=text_content[:200] if acreage else None,
            )

        except Exception as e:
            logger.debug(f"Failed to parse auction item: {e}")
            return None

    async def _parse_generic_county(self, page: Page, county_name: str) -> List[FloridaProperty]:
        """
        Generic parser for counties without specific format handlers.
        Attempts to find property data in tables or structured elements.
        """
        properties = []
        seen_parcels = set()

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
            property_keywords = ['parcel', 'property', 'address', 'bid', 'amount', 'value', 'cert']
            if not any(kw in ' '.join(headers) for kw in property_keywords):
                continue

            # Parse data rows
            for row in rows[1:]:
                cells = await row.query_selector_all('td')
                cell_texts = [(await c.text_content() or '').strip() for c in cells]

                if not any(cell_texts):
                    continue

                try:
                    prop = await self._parse_auction_item(row, county_name)
                    if prop and prop.parcel_id not in seen_parcels:
                        seen_parcels.add(prop.parcel_id)
                        properties.append(prop)
                except Exception as e:
                    logger.debug(f"Failed to parse row: {e}")

        return properties


def get_supported_counties() -> List[str]:
    """Get list of supported Florida counties."""
    return sorted(c['name'] for c in FLORIDA_COUNTIES.values())


# Convenience function for CLI usage
async def scrape_florida_county(county: str, max_pages: int = 50) -> List[FloridaProperty]:
    """
    Scrape Florida RealTaxDeed properties for a county.

    Args:
        county: County name
        max_pages: Maximum pages to scrape

    Returns:
        List of FloridaProperty objects
    """
    async with FloridaRealTaxDeedScraper() as scraper:
        return await scraper.scrape_county(county, max_pages=max_pages)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Scrape Florida RealTaxDeed tax deed properties")
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
        print("Supported Florida counties:")
        for county in get_supported_counties():
            key = county.lower().replace('-', '_').replace(' ', '_')
            if key in FLORIDA_COUNTIES:
                config = FLORIDA_COUNTIES[key]
                print(f"  - {county} ({config['seat']}) - {config['listing_url']}")
        sys.exit(EXIT_SUCCESS)

    if not args.county:
        parser.error("county is required (or use --list-counties)")
        sys.exit(EXIT_PERMANENT)

    async def main():
        try:
            properties = await scrape_florida_county(args.county, max_pages=args.max_pages)

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
                    if prop.certificate_number:
                        print(f"    Cert #: {prop.certificate_number}")
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
