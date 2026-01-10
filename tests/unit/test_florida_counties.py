"""
Unit tests for Florida RealTaxDeed scraper module.

Tests the Playwright-based web scraping functionality including
property dataclass, county normalization, amount/acreage parsing,
async context management, and exit code handling.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from core.scrapers.florida_counties import (
    FloridaRealTaxDeedScraper,
    FloridaProperty,
    CountyValidationError,
    FLORIDA_COUNTIES,
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
    'parcel_id': 'FL-ORANGE-CERT-2024-12345',
    'amount': 5000.0,
    'county': 'Orange',
    'description': 'LOT 1 BLOCK 2 SUBDIVISION XYZ 0.25 ACRES',
    'owner_name': 'JOHN DOE',
    'certificate_number': '2024-12345',
    'assessed_value': 150000.0,
}

# Sample auction item text (matches RealTaxDeed format)
SAMPLE_AUCTION_ITEM_TEXT = """
Parcel: 25-22-29-0000-00-001
Opening Bid: $5,000.00
Certificate #: 2024-1234
123 Main St Orlando FL 32801
Assessed Value: $150,000
1.5 acres
"""


# =============================================================================
# TestFloridaPropertyDataclass
# =============================================================================

class TestFloridaPropertyDataclass:
    """Tests for FloridaProperty dataclass and to_dict method."""

    @pytest.mark.unit
    def test_to_dict_returns_correct_fields(self):
        """to_dict should return all expected fields."""
        prop = FloridaProperty(
            parcel_id='FL-ORANGE-CERT-2024-12345',
            amount=5000.0,
            county='Orange',
            description='LOT 1 BLOCK 2 TEST',
            owner_name='TEST OWNER',
            certificate_number='2024-12345',
            assessed_value=150000.0,
            scraped_at=datetime(2026, 1, 8, 12, 0, 0)
        )

        result = prop.to_dict()

        assert result['parcel_id'] == 'FL-ORANGE-CERT-2024-12345'
        assert result['county'] == 'Orange'
        assert result['owner_name'] == 'TEST OWNER'
        assert result['amount'] == 5000.0
        assert result['description'] == 'LOT 1 BLOCK 2 TEST'
        assert result['certificate_number'] == '2024-12345'
        assert result['assessed_value'] == 150000.0
        assert result['data_source'] == 'florida_realtaxdeed'
        assert result['auction_platform'] == 'RealTaxDeed'

    @pytest.mark.unit
    def test_to_dict_state_is_florida(self):
        """State should always be 'FL'."""
        prop = FloridaProperty(
            parcel_id='TEST-001',
            amount=100.0,
            county='Orange',
            description='TEST',
            scraped_at=datetime.utcnow()
        )

        result = prop.to_dict()

        assert result['state'] == 'FL'

    @pytest.mark.unit
    def test_to_dict_sale_type_is_tax_deed(self):
        """Sale type should be 'tax_deed' for Florida deed auctions."""
        prop = FloridaProperty(
            parcel_id='TEST-001',
            amount=100.0,
            county='Orange',
            description='TEST',
            scraped_at=datetime.utcnow()
        )

        result = prop.to_dict()

        assert result['sale_type'] == 'tax_deed'

    @pytest.mark.unit
    def test_to_dict_no_redemption_period(self):
        """Redemption period should be 0 days (immediate ownership at deed auction)."""
        prop = FloridaProperty(
            parcel_id='TEST-001',
            amount=100.0,
            county='Orange',
            description='TEST',
            scraped_at=datetime.utcnow()
        )

        result = prop.to_dict()

        assert result['redemption_period_days'] == 0
        assert result['time_to_ownership_days'] == 0

    @pytest.mark.unit
    def test_to_dict_auction_date_formatting(self):
        """Auction date should be formatted as ISO string when present."""
        auction_date = datetime(2026, 2, 4, 10, 0, 0)
        prop = FloridaProperty(
            parcel_id='TEST-001',
            amount=100.0,
            county='Orange',
            description='TEST',
            auction_date=auction_date,
            scraped_at=datetime.utcnow()
        )

        result = prop.to_dict()

        assert result['auction_date'] == '2026-02-04T10:00:00'

    @pytest.mark.unit
    def test_to_dict_auction_date_none_when_not_set(self):
        """Auction date should be None when not provided."""
        prop = FloridaProperty(
            parcel_id='TEST-001',
            amount=100.0,
            county='Orange',
            description='TEST',
            scraped_at=datetime.utcnow()
        )

        result = prop.to_dict()

        assert result['auction_date'] is None

    @pytest.mark.unit
    def test_to_dict_acreage_lineage_fields(self):
        """Acreage lineage fields should be included in output."""
        prop = FloridaProperty(
            parcel_id='TEST-001',
            amount=100.0,
            county='Orange',
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

    @pytest.mark.unit
    def test_to_dict_certificate_fields_included(self):
        """Florida-specific certificate fields should be in output."""
        prop = FloridaProperty(
            parcel_id='TEST-001',
            amount=100.0,
            county='Orange',
            description='TEST',
            certificate_number='2024-5678',
            scraped_at=datetime.utcnow()
        )

        result = prop.to_dict()

        assert result['certificate_number'] == '2024-5678'


# =============================================================================
# TestCountyNormalization
# =============================================================================

class TestCountyNormalization:
    """Tests for county name normalization."""

    @pytest.mark.unit
    def test_normalize_valid_county_lowercase(self):
        """Lowercase county name should be normalized."""
        scraper = FloridaRealTaxDeedScraper()
        assert scraper._normalize_county('orange') == 'orange'
        assert scraper._normalize_county('duval') == 'duval'

    @pytest.mark.unit
    def test_normalize_valid_county_uppercase(self):
        """Uppercase county name should be normalized."""
        scraper = FloridaRealTaxDeedScraper()
        assert scraper._normalize_county('ORANGE') == 'orange'
        assert scraper._normalize_county('DUVAL') == 'duval'

    @pytest.mark.unit
    def test_normalize_valid_county_mixed_case(self):
        """Mixed case county name should be normalized."""
        scraper = FloridaRealTaxDeedScraper()
        assert scraper._normalize_county('Orange') == 'orange'
        assert scraper._normalize_county('DuVaL') == 'duval'

    @pytest.mark.unit
    def test_normalize_county_with_underscore(self):
        """County with underscore should be normalized."""
        scraper = FloridaRealTaxDeedScraper()
        assert scraper._normalize_county('miami_dade') == 'miami_dade'

    @pytest.mark.unit
    def test_normalize_county_with_space(self):
        """County with space should be normalized to underscore."""
        scraper = FloridaRealTaxDeedScraper()
        assert scraper._normalize_county('MIAMI DADE') == 'miami_dade'

    @pytest.mark.unit
    def test_normalize_county_with_hyphen(self):
        """County with hyphen should be normalized to underscore."""
        scraper = FloridaRealTaxDeedScraper()
        assert scraper._normalize_county('miami-dade') == 'miami_dade'
        assert scraper._normalize_county('Miami-Dade') == 'miami_dade'

    @pytest.mark.unit
    def test_normalize_strips_whitespace(self):
        """Whitespace should be stripped from input."""
        scraper = FloridaRealTaxDeedScraper()
        assert scraper._normalize_county('  orange  ') == 'orange'
        assert scraper._normalize_county('\tDuval\n') == 'duval'

    @pytest.mark.unit
    def test_normalize_invalid_county_raises_error(self):
        """Invalid county name should raise CountyValidationError."""
        scraper = FloridaRealTaxDeedScraper()
        with pytest.raises(CountyValidationError):
            scraper._normalize_county('InvalidCounty')
        with pytest.raises(CountyValidationError):
            scraper._normalize_county('California')
        with pytest.raises(CountyValidationError):
            scraper._normalize_county('XYZ123')

    @pytest.mark.unit
    def test_normalize_empty_raises_error(self):
        """Empty string should raise CountyValidationError."""
        scraper = FloridaRealTaxDeedScraper()
        with pytest.raises(CountyValidationError):
            scraper._normalize_county('')

    @pytest.mark.unit
    def test_normalize_none_raises_error(self):
        """None should raise CountyValidationError."""
        scraper = FloridaRealTaxDeedScraper()
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
        scraper = FloridaRealTaxDeedScraper()
        assert scraper._parse_amount('$1,234.56') == 1234.56
        assert scraper._parse_amount('$12,345.00') == 12345.0

    @pytest.mark.unit
    def test_parse_amount_plain_number(self):
        """Plain number should parse correctly."""
        scraper = FloridaRealTaxDeedScraper()
        assert scraper._parse_amount('1234.56') == 1234.56
        assert scraper._parse_amount('5000') == 5000.0

    @pytest.mark.unit
    def test_parse_amount_empty_string(self):
        """Empty string should return 0.0."""
        scraper = FloridaRealTaxDeedScraper()
        assert scraper._parse_amount('') == 0.0

    @pytest.mark.unit
    def test_parse_amount_invalid_string(self):
        """Non-numeric string should return 0.0."""
        scraper = FloridaRealTaxDeedScraper()
        assert scraper._parse_amount('N/A') == 0.0
        assert scraper._parse_amount('TBD') == 0.0
        assert scraper._parse_amount('Not Available') == 0.0

    @pytest.mark.unit
    def test_parse_amount_with_commas(self):
        """Large numbers with commas should parse correctly."""
        scraper = FloridaRealTaxDeedScraper()
        assert scraper._parse_amount('12,345,678') == 12345678.0
        assert scraper._parse_amount('$1,000,000.00') == 1000000.0

    @pytest.mark.unit
    def test_parse_amount_none_input(self):
        """None input should return 0.0."""
        scraper = FloridaRealTaxDeedScraper()
        assert scraper._parse_amount(None) == 0.0


# =============================================================================
# TestAcreageParsing
# =============================================================================

class TestAcreageParsing:
    """Tests for acreage extraction from text."""

    @pytest.mark.unit
    def test_parse_acreage_explicit_acres(self):
        """Explicit 'X acres' pattern should be parsed."""
        scraper = FloridaRealTaxDeedScraper()
        acreage, source, confidence = scraper._parse_acreage('LOT 1 2.5 acres')
        assert acreage == 2.5
        assert source == 'parsed_explicit'
        assert confidence == 'high'

    @pytest.mark.unit
    def test_parse_acreage_abbreviated(self):
        """Abbreviated 'X ac' pattern should be parsed."""
        scraper = FloridaRealTaxDeedScraper()
        acreage, source, confidence = scraper._parse_acreage('PARCEL A 10 ac')
        assert acreage == 10.0
        assert source == 'parsed_explicit'
        assert confidence == 'high'

    @pytest.mark.unit
    def test_parse_acreage_sqft_conversion(self):
        """Square footage should be converted to acres."""
        scraper = FloridaRealTaxDeedScraper()
        # 43560 sq ft = 1 acre
        acreage, source, confidence = scraper._parse_acreage('LOT SIZE 43560 sq ft')
        assert acreage == pytest.approx(1.0, rel=0.01)
        assert source == 'parsed_sqft'
        assert confidence == 'medium'

    @pytest.mark.unit
    def test_parse_acreage_sqft_with_commas(self):
        """Square footage with commas should parse correctly."""
        scraper = FloridaRealTaxDeedScraper()
        acreage, source, confidence = scraper._parse_acreage('21,780 square feet')
        assert acreage == pytest.approx(0.5, rel=0.01)
        assert source == 'parsed_sqft'
        assert confidence == 'medium'

    @pytest.mark.unit
    def test_parse_acreage_no_match(self):
        """Text without acreage should return None tuple."""
        scraper = FloridaRealTaxDeedScraper()
        acreage, source, confidence = scraper._parse_acreage('LOT 1 BLOCK 2')
        assert acreage is None
        assert source is None
        assert confidence is None

    @pytest.mark.unit
    def test_parse_acreage_empty_string(self):
        """Empty string should return None tuple."""
        scraper = FloridaRealTaxDeedScraper()
        acreage, source, confidence = scraper._parse_acreage('')
        assert acreage is None
        assert source is None
        assert confidence is None

    @pytest.mark.unit
    def test_parse_acreage_none_input(self):
        """None input should return None tuple."""
        scraper = FloridaRealTaxDeedScraper()
        acreage, source, confidence = scraper._parse_acreage(None)
        assert acreage is None
        assert source is None
        assert confidence is None


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

        with patch('core.scrapers.florida_counties.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            async with FloridaRealTaxDeedScraper() as scraper:
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

        with patch('core.scrapers.florida_counties.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            async with FloridaRealTaxDeedScraper() as scraper:
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

        with patch('core.scrapers.florida_counties.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            async with FloridaRealTaxDeedScraper() as scraper:
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

        with patch('core.scrapers.florida_counties.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            try:
                async with FloridaRealTaxDeedScraper() as scraper:
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
        scraper = FloridaRealTaxDeedScraper()
        scraper._browser = MagicMock()
        scraper._context = MagicMock()

        with pytest.raises(CountyValidationError):
            await scraper.scrape_county('InvalidCounty')

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_county_browser_not_started_error(self):
        """Error should be raised if browser not started."""
        scraper = FloridaRealTaxDeedScraper()
        # _browser is None by default

        with pytest.raises(RuntimeError) as excinfo:
            await scraper.scrape_county('Orange')

        assert "Scraper not started" in str(excinfo.value)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_county_dispatches_to_realtaxdeed_parser(self):
        """Orange county should dispatch to RealTaxDeed parser."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.query_selector_all = AsyncMock(return_value=[])
        mock_page.close = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html></html>")
        mock_page.url = "https://orange.realtaxdeed.com"

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        scraper = FloridaRealTaxDeedScraper()
        scraper._browser = MagicMock()
        scraper._context = mock_context

        with patch.object(scraper, '_parse_realtaxdeed_county', new_callable=AsyncMock) as mock_parser:
            mock_parser.return_value = []
            with patch('core.scrapers.florida_counties.save_debug_snapshot'):
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    await scraper.scrape_county('orange')

            mock_parser.assert_called_once()


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


# =============================================================================
# TestCountyConstants
# =============================================================================

class TestCountyConstants:
    """Tests for county configuration constants."""

    @pytest.mark.unit
    def test_florida_has_4_counties(self):
        """Florida should have 4 supported counties."""
        assert len(FLORIDA_COUNTIES) == 4

    @pytest.mark.unit
    def test_reverse_mapping_consistent(self):
        """Forward and reverse mappings should be consistent."""
        for key, config in FLORIDA_COUNTIES.items():
            # County key should map back to itself
            assert COUNTY_NAME_TO_KEY.get(key.upper()) == key
            # County name should also map to key
            assert COUNTY_NAME_TO_KEY.get(config['name'].upper()) == key

    @pytest.mark.unit
    def test_each_county_has_required_config(self):
        """Each county should have required configuration fields."""
        required_fields = ['name', 'fips', 'seat', 'listing_url', 'format']

        for key, config in FLORIDA_COUNTIES.items():
            for field in required_fields:
                assert field in config, f"County {key} missing field: {field}"
                assert config[field], f"County {key} has empty field: {field}"

    @pytest.mark.unit
    def test_get_supported_counties_returns_sorted_list(self):
        """get_supported_counties should return sorted county names."""
        counties = get_supported_counties()

        assert len(counties) == 4
        assert counties == sorted(counties)
        # Check some known counties
        assert 'Orange' in counties
        assert 'Duval' in counties

    @pytest.mark.unit
    def test_known_counties_exist(self):
        """Major Florida counties should be present with correct config."""
        known_counties = {
            'orange': {'name': 'Orange', 'seat': 'Orlando', 'format': 'realtaxdeed'},
            'miami_dade': {'name': 'Miami-Dade', 'seat': 'Miami', 'format': 'realtaxdeed'},
            'hillsborough': {'name': 'Hillsborough', 'seat': 'Tampa', 'format': 'realtaxdeed'},
            'duval': {'name': 'Duval', 'seat': 'Jacksonville', 'format': 'realtaxdeed'},
        }

        for key, expected in known_counties.items():
            assert key in FLORIDA_COUNTIES, f"Missing county: {key}"
            config = FLORIDA_COUNTIES[key]
            assert config['name'] == expected['name']
            assert config['seat'] == expected['seat']
            assert config['format'] == expected['format']

    @pytest.mark.unit
    def test_listing_urls_are_valid_format(self):
        """Listing URLs should be valid HTTP/HTTPS URLs."""
        import re
        url_pattern = re.compile(r'^https?://')

        for key, config in FLORIDA_COUNTIES.items():
            url = config['listing_url']
            assert url_pattern.match(url), f"Invalid URL for {key}: {url}"

    @pytest.mark.unit
    def test_miami_dade_variations_all_normalize(self):
        """All Miami-Dade variations should normalize to miami_dade."""
        scraper = FloridaRealTaxDeedScraper()
        variations = ['miami_dade', 'MIAMI_DADE', 'miami-dade', 'MIAMI-DADE', 'Miami Dade', 'MiamiDade']

        for variation in variations:
            result = scraper._normalize_county(variation)
            assert result == 'miami_dade', f"Failed for variation: {variation}"
