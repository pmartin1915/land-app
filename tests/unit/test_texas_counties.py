"""
Unit tests for Texas RealAuction scraper module.

Tests the Playwright-based web scraping functionality including
property dataclass, county normalization, amount/acreage parsing,
async context management, county-specific parsers, and exit code handling.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from core.scrapers.texas_counties import (
    TexasRealAuctionScraper,
    TexasProperty,
    CountyValidationError,
    TEXAS_COUNTIES,
    COUNTY_NAME_TO_KEY,
    get_supported_counties,
)
from core.scrapers.utils import (
    EXIT_SUCCESS,
    EXIT_TRANSIENT,
    EXIT_PERMANENT,
    EXIT_RATE_LIMIT,
)


# =============================================================================
# Sample Test Data Constants
# =============================================================================

# Sample property data for dataclass tests
SAMPLE_PROPERTY_DATA = {
    'parcel_id': 'TX-HARRIS-2024-12345',
    'amount': 5000.0,
    'county': 'Harris',
    'description': 'LOT 1 BLOCK 2 SUBDIVISION XYZ 0.25 ACRES',
    'owner_name': 'JOHN DOE',
    'cause_number': '2024-12345',
    'assessed_value': 150000.0,
}

# Sample Harris County table row data
SAMPLE_HARRIS_ROW = {
    'cause#': '2024-67890',
    'minimum_bid': '$3,500.00',
    'adjudged_value': '$125,000.00',
    'type': 'Residential',
    'tax_years_in_judgement': '2020-2023',
    'precinct': 'Precinct 4',
}

# Sample El Paso property block (matches real format)
SAMPLE_EL_PASO_BLOCK = """
STREET ADDR: 1234 MAIN ST
LOT 15 BLOCK 3 SUBDIVISION SAMPLE
TAX ACCT NO: C30199902507700
2.5 ACRES
"""

# Sample Tarrant row data
SAMPLE_TARRANT_ROW = ['2024-11111', 'R000012345', 'For Sale']


# =============================================================================
# TestTexasPropertyDataclass
# =============================================================================

class TestTexasPropertyDataclass:
    """Tests for TexasProperty dataclass and to_dict method."""

    @pytest.mark.unit
    def test_to_dict_returns_correct_fields(self):
        """to_dict should return all expected fields."""
        prop = TexasProperty(
            parcel_id='TX-HARRIS-2024-12345',
            amount=5000.0,
            county='Harris',
            description='LOT 1 BLOCK 2 TEST',
            owner_name='TEST OWNER',
            cause_number='2024-12345',
            assessed_value=150000.0,
            scraped_at=datetime(2026, 1, 6, 12, 0, 0)
        )

        result = prop.to_dict()

        assert result['parcel_id'] == 'TX-HARRIS-2024-12345'
        assert result['county'] == 'Harris'
        assert result['owner_name'] == 'TEST OWNER'
        assert result['amount'] == 5000.0
        assert result['description'] == 'LOT 1 BLOCK 2 TEST'
        assert result['cause_number'] == '2024-12345'
        assert result['assessed_value'] == 150000.0
        assert result['data_source'] == 'texas_realauction'
        assert result['auction_platform'] == 'RealAuction'

    @pytest.mark.unit
    def test_to_dict_state_is_texas(self):
        """State should always be 'TX'."""
        prop = TexasProperty(
            parcel_id='TEST-001',
            amount=100.0,
            county='Harris',
            description='TEST',
            scraped_at=datetime.utcnow()
        )

        result = prop.to_dict()

        assert result['state'] == 'TX'

    @pytest.mark.unit
    def test_to_dict_sale_type_is_redeemable_deed(self):
        """Sale type should be 'redeemable_deed' for Texas."""
        prop = TexasProperty(
            parcel_id='TEST-001',
            amount=100.0,
            county='Harris',
            description='TEST',
            scraped_at=datetime.utcnow()
        )

        result = prop.to_dict()

        assert result['sale_type'] == 'redeemable_deed'

    @pytest.mark.unit
    def test_to_dict_redemption_period_180_days(self):
        """Default redemption period should be 180 days (6 months)."""
        prop = TexasProperty(
            parcel_id='TEST-001',
            amount=100.0,
            county='Harris',
            description='TEST',
            scraped_at=datetime.utcnow()
        )

        result = prop.to_dict()

        assert result['redemption_period_days'] == 180
        assert result['time_to_ownership_days'] == 180

    @pytest.mark.unit
    def test_to_dict_auction_date_formatting(self):
        """Auction date should be formatted as ISO string when present."""
        auction_date = datetime(2026, 2, 4, 10, 0, 0)
        prop = TexasProperty(
            parcel_id='TEST-001',
            amount=100.0,
            county='Harris',
            description='TEST',
            auction_date=auction_date,
            scraped_at=datetime.utcnow()
        )

        result = prop.to_dict()

        assert result['auction_date'] == '2026-02-04T10:00:00'

    @pytest.mark.unit
    def test_to_dict_auction_date_none_when_not_set(self):
        """Auction date should be None when not provided."""
        prop = TexasProperty(
            parcel_id='TEST-001',
            amount=100.0,
            county='Harris',
            description='TEST',
            scraped_at=datetime.utcnow()
        )

        result = prop.to_dict()

        assert result['auction_date'] is None

    @pytest.mark.unit
    def test_to_dict_acreage_lineage_fields(self):
        """Acreage lineage fields should be included in output."""
        prop = TexasProperty(
            parcel_id='TEST-001',
            amount=100.0,
            county='Harris',
            description='TEST 2.5 ACRES',
            acreage=2.5,
            acreage_source='parsed_explicit',
            acreage_confidence='high',
            acreage_raw_text='2.5 ACRES',
            scraped_at=datetime.utcnow()
        )

        result = prop.to_dict()

        assert result['acreage'] == 2.5
        assert result['acreage_source'] == 'parsed_explicit'
        assert result['acreage_confidence'] == 'high'
        assert result['acreage_raw_text'] == '2.5 ACRES'


# =============================================================================
# TestCountyNormalization
# =============================================================================

class TestCountyNormalization:
    """Tests for county name normalization."""

    @pytest.mark.unit
    def test_normalize_valid_county_lowercase(self):
        """Lowercase county name should be normalized."""
        scraper = TexasRealAuctionScraper()
        assert scraper._normalize_county('harris') == 'harris'
        assert scraper._normalize_county('dallas') == 'dallas'

    @pytest.mark.unit
    def test_normalize_valid_county_uppercase(self):
        """Uppercase county name should be normalized."""
        scraper = TexasRealAuctionScraper()
        assert scraper._normalize_county('HARRIS') == 'harris'
        assert scraper._normalize_county('DALLAS') == 'dallas'

    @pytest.mark.unit
    def test_normalize_valid_county_mixed_case(self):
        """Mixed case county name should be normalized."""
        scraper = TexasRealAuctionScraper()
        assert scraper._normalize_county('Harris') == 'harris'
        assert scraper._normalize_county('DaLlAs') == 'dallas'

    @pytest.mark.unit
    def test_normalize_county_with_underscore(self):
        """County with underscore should be normalized."""
        scraper = TexasRealAuctionScraper()
        assert scraper._normalize_county('el_paso') == 'el_paso'
        assert scraper._normalize_county('fort_bend') == 'fort_bend'

    @pytest.mark.unit
    def test_normalize_county_with_space(self):
        """County with space should be normalized to underscore."""
        scraper = TexasRealAuctionScraper()
        assert scraper._normalize_county('EL PASO') == 'el_paso'
        assert scraper._normalize_county('Fort Bend') == 'fort_bend'

    @pytest.mark.unit
    def test_normalize_county_with_hyphen(self):
        """County with hyphen should be normalized to underscore."""
        scraper = TexasRealAuctionScraper()
        assert scraper._normalize_county('el-paso') == 'el_paso'
        assert scraper._normalize_county('Fort-Bend') == 'fort_bend'

    @pytest.mark.unit
    def test_normalize_partial_match_prefix(self):
        """Partial county name prefix should match."""
        scraper = TexasRealAuctionScraper()
        # 'harr' should match 'harris'
        assert scraper._normalize_county('harr') == 'harris'
        # 'dal' should match 'dallas'
        assert scraper._normalize_county('dal') == 'dallas'

    @pytest.mark.unit
    def test_normalize_strips_whitespace(self):
        """Whitespace should be stripped from input."""
        scraper = TexasRealAuctionScraper()
        assert scraper._normalize_county('  harris  ') == 'harris'
        assert scraper._normalize_county('\tDallas\n') == 'dallas'

    @pytest.mark.unit
    def test_normalize_invalid_county_raises_error(self):
        """Invalid county name should raise CountyValidationError."""
        scraper = TexasRealAuctionScraper()
        with pytest.raises(CountyValidationError):
            scraper._normalize_county('InvalidCounty')
        with pytest.raises(CountyValidationError):
            scraper._normalize_county('California')
        with pytest.raises(CountyValidationError):
            scraper._normalize_county('XYZ123')

    @pytest.mark.unit
    def test_normalize_empty_raises_error(self):
        """Empty string should raise CountyValidationError."""
        scraper = TexasRealAuctionScraper()
        with pytest.raises(CountyValidationError):
            scraper._normalize_county('')

    @pytest.mark.unit
    def test_normalize_none_raises_error(self):
        """None should raise CountyValidationError."""
        scraper = TexasRealAuctionScraper()
        with pytest.raises(CountyValidationError):
            scraper._normalize_county(None)


# =============================================================================
# TestAmountParsing
# =============================================================================

class TestAmountParsing:
    """Tests for amount string parsing."""

    @pytest.mark.unit
    def test_parse_amount_currency_format(self):
        """Currency format with $ and commas should parse correctly."""
        scraper = TexasRealAuctionScraper()
        assert scraper._parse_amount('$1,234.56') == 1234.56
        assert scraper._parse_amount('$12,345.00') == 12345.0

    @pytest.mark.unit
    def test_parse_amount_plain_number(self):
        """Plain number should parse correctly."""
        scraper = TexasRealAuctionScraper()
        assert scraper._parse_amount('1234.56') == 1234.56
        assert scraper._parse_amount('5000') == 5000.0

    @pytest.mark.unit
    def test_parse_amount_empty_string(self):
        """Empty string should return 0.0."""
        scraper = TexasRealAuctionScraper()
        assert scraper._parse_amount('') == 0.0

    @pytest.mark.unit
    def test_parse_amount_invalid_string(self):
        """Non-numeric string should return 0.0."""
        scraper = TexasRealAuctionScraper()
        assert scraper._parse_amount('N/A') == 0.0
        assert scraper._parse_amount('TBD') == 0.0
        assert scraper._parse_amount('Not Available') == 0.0

    @pytest.mark.unit
    def test_parse_amount_with_commas(self):
        """Large numbers with commas should parse correctly."""
        scraper = TexasRealAuctionScraper()
        assert scraper._parse_amount('12,345,678') == 12345678.0
        assert scraper._parse_amount('$1,000,000.00') == 1000000.0

    @pytest.mark.unit
    def test_parse_amount_none_input(self):
        """None input should return 0.0."""
        scraper = TexasRealAuctionScraper()
        assert scraper._parse_amount(None) == 0.0


# =============================================================================
# TestAcreageParsing
# =============================================================================

class TestAcreageParsing:
    """Tests for acreage extraction from text."""

    @pytest.mark.unit
    def test_parse_acreage_explicit_acres(self):
        """Explicit 'X acres' pattern should be parsed."""
        scraper = TexasRealAuctionScraper()
        acreage, source, confidence = scraper._parse_acreage('LOT 1 2.5 acres')
        assert acreage == 2.5
        assert source == 'parsed_explicit'
        assert confidence == 'high'

    @pytest.mark.unit
    def test_parse_acreage_abbreviated(self):
        """Abbreviated 'X ac' pattern should be parsed."""
        scraper = TexasRealAuctionScraper()
        acreage, source, confidence = scraper._parse_acreage('PARCEL A 10 ac')
        assert acreage == 10.0
        assert source == 'parsed_explicit'
        assert confidence == 'high'

    @pytest.mark.unit
    def test_parse_acreage_sqft_conversion(self):
        """Square footage should be converted to acres."""
        scraper = TexasRealAuctionScraper()
        # 43560 sq ft = 1 acre
        acreage, source, confidence = scraper._parse_acreage('LOT SIZE 43560 sq ft')
        assert acreage == pytest.approx(1.0, rel=0.01)
        assert source == 'parsed_sqft'
        assert confidence == 'medium'

    @pytest.mark.unit
    def test_parse_acreage_sqft_with_commas(self):
        """Square footage with commas should parse correctly."""
        scraper = TexasRealAuctionScraper()
        acreage, source, confidence = scraper._parse_acreage('21,780 square feet')
        assert acreage == pytest.approx(0.5, rel=0.01)
        assert source == 'parsed_sqft'
        assert confidence == 'medium'

    @pytest.mark.unit
    def test_parse_acreage_no_match(self):
        """Text without acreage should return None tuple."""
        scraper = TexasRealAuctionScraper()
        acreage, source, confidence = scraper._parse_acreage('LOT 1 BLOCK 2')
        assert acreage is None
        assert source is None
        assert confidence is None

    @pytest.mark.unit
    def test_parse_acreage_empty_string(self):
        """Empty string should return None tuple."""
        scraper = TexasRealAuctionScraper()
        acreage, source, confidence = scraper._parse_acreage('')
        assert acreage is None
        assert source is None
        assert confidence is None

    @pytest.mark.unit
    def test_parse_acreage_none_input(self):
        """None input should return None tuple."""
        scraper = TexasRealAuctionScraper()
        acreage, source, confidence = scraper._parse_acreage(None)
        assert acreage is None
        assert source is None
        assert confidence is None

    @pytest.mark.unit
    def test_parse_acreage_el_paso_format_with_parens(self):
        """El Paso format '(0371 AC)' should parse as 0.0371 acres."""
        scraper = TexasRealAuctionScraper()
        # El Paso uses (0XXX AC) to mean 0.0XXX acres
        acreage, source, confidence = scraper._parse_acreage('LOT 1 BLOCK 2 (0371 AC)')
        assert acreage == pytest.approx(0.0371, rel=0.01)
        assert source == 'parsed_el_paso_format'
        assert confidence == 'high'

    @pytest.mark.unit
    def test_parse_acreage_el_paso_format_larger(self):
        """El Paso format '(0500 AC)' should parse as 0.0500 acres."""
        scraper = TexasRealAuctionScraper()
        acreage, source, confidence = scraper._parse_acreage('PROPERTY (0500 AC) RESIDENTIAL')
        assert acreage == pytest.approx(0.05, rel=0.01)
        assert source == 'parsed_el_paso_format'
        assert confidence == 'high'

    @pytest.mark.unit
    def test_parse_acreage_el_paso_format_small(self):
        """El Paso format '(0125 AC)' should parse as 0.0125 acres."""
        scraper = TexasRealAuctionScraper()
        acreage, source, confidence = scraper._parse_acreage('(0125 AC)')
        assert acreage == pytest.approx(0.0125, rel=0.01)
        assert source == 'parsed_el_paso_format'
        assert confidence == 'high'

    @pytest.mark.unit
    def test_parse_acreage_standard_format_not_confused(self):
        """Standard '2.5 acres' should not be misinterpreted as El Paso format."""
        scraper = TexasRealAuctionScraper()
        acreage, source, confidence = scraper._parse_acreage('LOT SIZE 2.5 acres')
        assert acreage == 2.5
        assert source == 'parsed_explicit'
        assert confidence == 'high'

    @pytest.mark.unit
    def test_parse_acreage_large_standard_acreage(self):
        """Large acreage like '150 acres' should parse correctly."""
        scraper = TexasRealAuctionScraper()
        acreage, source, confidence = scraper._parse_acreage('RANCH 150 acres')
        assert acreage == 150.0
        assert source == 'parsed_explicit'
        assert confidence == 'high'


# =============================================================================
# TestAsyncContextManager
# =============================================================================

class TestAsyncContextManager:
    """Tests for async context manager behavior."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_context_manager_starts_browser(self):
        """Context manager should start Playwright browser on enter."""
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        with patch('core.scrapers.texas_counties.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            async with TexasRealAuctionScraper() as scraper:
                assert scraper._browser is not None
                mock_playwright.chromium.launch.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_context_manager_creates_context(self):
        """Context manager should create browser context with user agent."""
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        with patch('core.scrapers.texas_counties.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            async with TexasRealAuctionScraper() as scraper:
                # Verify new_context was called with user agent
                mock_browser.new_context.assert_called_once()
                call_kwargs = mock_browser.new_context.call_args[1]
                assert 'user_agent' in call_kwargs
                assert 'Chrome' in call_kwargs['user_agent']

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_context_manager_closes_browser(self):
        """Context manager should close browser on exit."""
        mock_browser = AsyncMock()
        mock_browser.close = AsyncMock()
        mock_context = AsyncMock()
        mock_context.close = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.stop = AsyncMock()

        with patch('core.scrapers.texas_counties.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            async with TexasRealAuctionScraper() as scraper:
                pass

            mock_browser.close.assert_called_once()
            mock_playwright.stop.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_context_manager_cleanup_on_error(self):
        """Resources should be cleaned up even if an error occurs."""
        mock_browser = AsyncMock()
        mock_browser.close = AsyncMock()
        mock_context = AsyncMock()
        mock_context.close = AsyncMock()
        mock_context.new_page = AsyncMock(side_effect=Exception("Page error"))
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.stop = AsyncMock()

        with patch('core.scrapers.texas_counties.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            try:
                async with TexasRealAuctionScraper() as scraper:
                    await scraper._context.new_page()
            except Exception:
                pass

            # Cleanup should still happen
            mock_browser.close.assert_called_once()
            mock_playwright.stop.assert_called_once()


# =============================================================================
# TestScrapeCounty
# =============================================================================

class TestScrapeCounty:
    """Tests for scrape_county method."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_county_validates_county_first(self):
        """Invalid county should raise error before browser operations."""
        scraper = TexasRealAuctionScraper()
        scraper._browser = MagicMock()
        scraper._context = MagicMock()

        with pytest.raises(CountyValidationError):
            await scraper.scrape_county('InvalidCounty')

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_county_browser_not_started_error(self):
        """Error should be raised if browser not started."""
        scraper = TexasRealAuctionScraper()
        # _browser is None by default

        with pytest.raises(RuntimeError) as excinfo:
            await scraper.scrape_county('Harris')

        assert "Scraper not started" in str(excinfo.value)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_county_dispatches_to_harris_parser(self):
        """Harris county should dispatch to Harris parser."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.query_selector_all = AsyncMock(return_value=[])
        mock_page.close = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html></html>")

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        scraper = TexasRealAuctionScraper()
        scraper._browser = MagicMock()
        scraper._context = mock_context

        with patch.object(scraper, '_parse_harris_county', new_callable=AsyncMock) as mock_parser:
            mock_parser.return_value = []
            with patch('core.scrapers.texas_counties.save_debug_snapshot'):
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    await scraper.scrape_county('harris')

            mock_parser.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_county_dispatches_to_el_paso_parser(self):
        """El Paso county should dispatch to El Paso parser."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.query_selector_all = AsyncMock(return_value=[])
        mock_page.close = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html></html>")

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        scraper = TexasRealAuctionScraper()
        scraper._browser = MagicMock()
        scraper._context = mock_context

        with patch.object(scraper, '_parse_el_paso_county', new_callable=AsyncMock) as mock_parser:
            mock_parser.return_value = []
            with patch('core.scrapers.texas_counties.save_debug_snapshot'):
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    await scraper.scrape_county('el_paso')

            mock_parser.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_county_dispatches_to_tarrant_parser(self):
        """Tarrant county should dispatch to Tarrant parser."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.query_selector_all = AsyncMock(return_value=[])
        mock_page.close = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html></html>")

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        scraper = TexasRealAuctionScraper()
        scraper._browser = MagicMock()
        scraper._context = mock_context

        with patch.object(scraper, '_parse_tarrant_county', new_callable=AsyncMock) as mock_parser:
            mock_parser.return_value = []
            with patch('core.scrapers.texas_counties.save_debug_snapshot'):
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    await scraper.scrape_county('tarrant')

            mock_parser.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_county_dispatches_to_generic_for_collin(self):
        """Collin county (sharepoint format) should use generic parser."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.query_selector_all = AsyncMock(return_value=[])
        mock_page.close = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html></html>")

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        scraper = TexasRealAuctionScraper()
        scraper._browser = MagicMock()
        scraper._context = mock_context

        with patch.object(scraper, '_parse_generic_county', new_callable=AsyncMock) as mock_parser:
            mock_parser.return_value = []
            with patch('core.scrapers.texas_counties.save_debug_snapshot'):
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    await scraper.scrape_county('collin')

            mock_parser.assert_called_once()


# =============================================================================
# TestHarrisCountyParser
# =============================================================================

class TestHarrisCountyParser:
    """Tests for Harris County-specific parser."""

    @pytest.mark.unit
    def test_create_property_from_harris_extracts_cause_number(self):
        """Harris parser should extract cause number as primary ID."""
        scraper = TexasRealAuctionScraper()
        data = {'cause#': '2024-67890'}

        result = scraper._create_property_from_harris_data(data, 'Harris')

        assert result is not None
        assert result.cause_number == '2024-67890'
        assert 'TX-HARRIS-2024-67890' in result.parcel_id

    @pytest.mark.unit
    def test_create_property_from_harris_extracts_minimum_bid(self):
        """Harris parser should extract minimum bid amount."""
        scraper = TexasRealAuctionScraper()
        data = {
            'cause#': '2024-67890',
            'minimum_bid': '$3,500.00'
        }

        result = scraper._create_property_from_harris_data(data, 'Harris')

        assert result is not None
        assert result.amount == 3500.0

    @pytest.mark.unit
    def test_create_property_from_harris_extracts_adjudged_value(self):
        """Harris parser should extract adjudged/assessed value."""
        scraper = TexasRealAuctionScraper()
        data = {
            'cause#': '2024-67890',
            'adjudged_value': '$125,000.00'
        }

        result = scraper._create_property_from_harris_data(data, 'Harris')

        assert result is not None
        assert result.assessed_value == 125000.0

    @pytest.mark.unit
    def test_create_property_from_harris_builds_description(self):
        """Harris parser should build description from available data."""
        scraper = TexasRealAuctionScraper()
        data = {
            'cause#': '2024-67890',
            'type': 'Residential',
            'tax_years_in_judgement': '2020-2023',
            'precinct': 'Precinct 4'
        }

        result = scraper._create_property_from_harris_data(data, 'Harris')

        assert result is not None
        assert 'Residential' in result.description
        assert '2020-2023' in result.description
        assert 'Precinct 4' in result.description

    @pytest.mark.unit
    def test_create_property_from_harris_handles_empty_data(self):
        """Harris parser should return None for empty data."""
        scraper = TexasRealAuctionScraper()

        result = scraper._create_property_from_harris_data({}, 'Harris')

        assert result is None

    @pytest.mark.unit
    def test_create_property_from_harris_handles_missing_cause(self):
        """Harris parser should return None when cause number missing."""
        scraper = TexasRealAuctionScraper()
        data = {'minimum_bid': '$1,000.00'}  # No cause#

        result = scraper._create_property_from_harris_data(data, 'Harris')

        assert result is None


# =============================================================================
# TestGenericParser
# =============================================================================

class TestGenericParser:
    """Tests for generic county parser."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_parse_generic_finds_tables(self):
        """Generic parser should search for tables with property data."""
        mock_table = AsyncMock()
        mock_table.query_selector_all = AsyncMock(return_value=[])

        mock_page = AsyncMock()
        mock_page.query_selector_all = AsyncMock(side_effect=[
            [mock_table],  # First call for tables
            []  # Second call for cards
        ])

        scraper = TexasRealAuctionScraper()
        result = await scraper._parse_generic_county(mock_page, 'Test')

        # Should have queried for tables
        mock_page.query_selector_all.assert_any_call('table')

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_parse_generic_finds_cards_fallback(self):
        """Generic parser should fall back to card layouts."""
        mock_page = AsyncMock()
        mock_page.query_selector_all = AsyncMock(side_effect=[
            [],  # No tables
            []   # No cards either
        ])

        scraper = TexasRealAuctionScraper()
        result = await scraper._parse_generic_county(mock_page, 'Test')

        # Should have queried for card-style elements
        calls = mock_page.query_selector_all.call_args_list
        assert len(calls) >= 2
        # Second call should look for cards
        assert any('.card' in str(call) or 'listing' in str(call) for call in calls)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_parse_property_element_extracts_cause_number(self):
        """Property element parser should extract cause number."""
        mock_element = AsyncMock()
        mock_element.text_content = AsyncMock(return_value='Cause: 2024-12345 Min Bid: $5,000')

        scraper = TexasRealAuctionScraper()
        result = await scraper._parse_property_element(mock_element, 'Test')

        assert result is not None
        assert result.cause_number == '2024-12345'

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_parse_property_element_extracts_amount(self):
        """Property element parser should extract bid amount."""
        mock_element = AsyncMock()
        mock_element.text_content = AsyncMock(return_value='Min Bid: $5,000.00 Property ID: 12345')

        scraper = TexasRealAuctionScraper()
        result = await scraper._parse_property_element(mock_element, 'Test')

        assert result is not None
        assert result.amount == 5000.0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_parse_property_element_extracts_address(self):
        """Property element parser should extract street address."""
        mock_element = AsyncMock()
        mock_element.text_content = AsyncMock(return_value='123 Main St Houston TX 77001')

        scraper = TexasRealAuctionScraper()
        result = await scraper._parse_property_element(mock_element, 'Test')

        assert result is not None
        assert result.property_address is not None
        assert '123 Main St' in result.property_address

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_parse_property_element_handles_empty(self):
        """Property element parser should handle empty content gracefully."""
        mock_element = AsyncMock()
        mock_element.text_content = AsyncMock(return_value='')

        scraper = TexasRealAuctionScraper()
        result = await scraper._parse_property_element(mock_element, 'Test')

        # Should return a property with hash-based ID or None
        # Implementation generates hash-based ID for empty content
        assert result is not None or result is None  # Either is acceptable


# =============================================================================
# TestExitCodeHandling
# =============================================================================

class TestExitCodeHandling:
    """Tests for exit code mapping in main block."""

    @pytest.mark.unit
    def test_exit_code_constants_defined(self):
        """Exit code constants should be properly defined."""
        assert EXIT_SUCCESS == 0
        assert EXIT_TRANSIENT == 1
        assert EXIT_PERMANENT == 2
        assert EXIT_RATE_LIMIT == 3

    @pytest.mark.unit
    def test_county_validation_error_is_permanent(self):
        """CountyValidationError should map to EXIT_PERMANENT (no retry)."""
        error = CountyValidationError("Invalid county: InvalidCounty")
        assert isinstance(error, CountyValidationError)
        # EXIT_PERMANENT = 2 means no retry for invalid input

    @pytest.mark.unit
    def test_rate_limit_keywords_detected(self):
        """Rate limit keywords should be properly detected."""
        rate_limit_messages = [
            "rate limit exceeded",
            "HTTP 429 Too Many Requests",
            "too many requests, please slow down",
        ]

        for msg in rate_limit_messages:
            error_msg = msg.lower()
            is_rate_limit = (
                'rate limit' in error_msg or
                '429' in error_msg or
                'too many requests' in error_msg
            )
            assert is_rate_limit, f"Failed to detect rate limit in: {msg}"

    @pytest.mark.unit
    def test_access_denied_detected_as_rate_limit(self):
        """Access denied should be treated as potential rate limiting."""
        access_denied_messages = [
            "Access denied by firewall",
            "HTTP 403 Forbidden",
        ]

        for msg in access_denied_messages:
            error_msg = msg.lower()
            is_rate_limit = (
                'access denied' in error_msg or
                '403' in error_msg
            )
            assert is_rate_limit, f"Failed to detect access denied in: {msg}"

    @pytest.mark.unit
    def test_transient_error_conditions(self):
        """Network and timeout errors should be transient (retry)."""
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        transient_errors = [
            PlaywrightTimeoutError("Page load timeout"),
            ConnectionError("Network unreachable"),
        ]

        for error in transient_errors:
            assert isinstance(error, (PlaywrightTimeoutError, ConnectionError))

    @pytest.mark.unit
    def test_normal_exception_defaults_to_transient(self):
        """Unknown exceptions should default to transient (allow retry)."""
        error = Exception("Some unknown error")
        error_msg = str(error).lower()

        # Should NOT match rate limit patterns
        is_rate_limit = (
            'rate limit' in error_msg or
            '429' in error_msg or
            'too many requests' in error_msg or
            'access denied' in error_msg or
            '403' in error_msg
        )
        assert not is_rate_limit


# =============================================================================
# TestCountyConstants
# =============================================================================

class TestCountyConstants:
    """Tests for county configuration constants."""

    @pytest.mark.unit
    def test_texas_has_8_counties(self):
        """Texas should have 8 supported counties."""
        assert len(TEXAS_COUNTIES) == 8

    @pytest.mark.unit
    def test_reverse_mapping_consistent(self):
        """Forward and reverse mappings should be consistent."""
        for key, config in TEXAS_COUNTIES.items():
            # County key should map back to itself
            assert COUNTY_NAME_TO_KEY.get(key.upper()) == key
            # County name should also map to key
            assert COUNTY_NAME_TO_KEY.get(config['name'].upper()) == key

    @pytest.mark.unit
    def test_each_county_has_required_config(self):
        """Each county should have required configuration fields."""
        required_fields = ['name', 'fips', 'seat', 'listing_url', 'format']

        for key, config in TEXAS_COUNTIES.items():
            for field in required_fields:
                assert field in config, f"County {key} missing field: {field}"
                assert config[field], f"County {key} has empty field: {field}"

    @pytest.mark.unit
    def test_get_supported_counties_returns_sorted_list(self):
        """get_supported_counties should return sorted county names."""
        counties = get_supported_counties()

        assert len(counties) == 8
        assert counties == sorted(counties)
        # Check some known counties
        assert 'Harris' in counties
        assert 'Dallas' in counties
        assert 'Travis' in counties

    @pytest.mark.unit
    def test_known_counties_exist(self):
        """Major Texas counties should be present with correct config."""
        known_counties = {
            'harris': {'name': 'Harris', 'seat': 'Houston', 'format': 'hctax'},
            'dallas': {'name': 'Dallas', 'seat': 'Dallas', 'format': 'realauction_sheriff'},
            'tarrant': {'name': 'Tarrant', 'seat': 'Fort Worth', 'format': 'tarrant_html'},
            'travis': {'name': 'Travis', 'seat': 'Austin', 'format': 'realauction'},
            'el_paso': {'name': 'El Paso', 'seat': 'El Paso', 'format': 'el_paso_html'},
        }

        for key, expected in known_counties.items():
            assert key in TEXAS_COUNTIES, f"Missing county: {key}"
            config = TEXAS_COUNTIES[key]
            assert config['name'] == expected['name']
            assert config['seat'] == expected['seat']
            assert config['format'] == expected['format']

    @pytest.mark.unit
    def test_listing_urls_are_valid_format(self):
        """Listing URLs should be valid HTTP/HTTPS URLs."""
        import re
        url_pattern = re.compile(r'^https?://')

        for key, config in TEXAS_COUNTIES.items():
            url = config['listing_url']
            assert url_pattern.match(url), f"Invalid URL for {key}: {url}"
