"""
Unit tests for scripts/scraper.py module.

Tests the Playwright-based web scraping functionality including
county validation, utility functions, and async scraping with mocked
browser interactions.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

from scripts.scraper import (
    validate_county_code,
    get_county_name,
    list_available_counties,
    search_counties,
    scrape_county_data,
    ALABAMA_COUNTY_CODES,
    COUNTY_NAME_TO_CODE,
    ADOR_BASE_URL
)
from scripts.exceptions import CountyValidationError, ScrapingError


class TestValidateCountyCode:
    """Tests for county code validation."""

    @pytest.mark.unit
    def test_validate_with_valid_numeric_code(self):
        """Valid numeric codes should be normalized and returned."""
        assert validate_county_code('05') == '05'
        assert validate_county_code('5') == '05'
        assert validate_county_code('37') == '37'
        assert validate_county_code('67') == '67'
        assert validate_county_code('01') == '01'
        assert validate_county_code('1') == '01'

    @pytest.mark.unit
    def test_validate_with_valid_county_name(self):
        """Valid county names should return the correct code."""
        assert validate_county_code('Baldwin') == '05'
        assert validate_county_code('BALDWIN') == '05'
        assert validate_county_code('baldwin') == '05'
        assert validate_county_code('Jefferson-Bham') == '01'
        assert validate_county_code('Mobile') == '02'
        assert validate_county_code('Montgomery') == '03'

    @pytest.mark.unit
    def test_validate_with_partial_name_match(self):
        """Partial county names should match via prefix or substring."""
        # These should match if the partial name is in or starts the full name
        assert validate_county_code('Bald') == '05'
        assert validate_county_code('Jeff') in ['01', '38', '68']  # Multiple Jeffersons
        assert validate_county_code('Mob') == '02'

    @pytest.mark.unit
    def test_validate_strips_whitespace(self):
        """Whitespace should be stripped before validation."""
        assert validate_county_code('  Baldwin  ') == '05'
        assert validate_county_code('\t05\n') == '05'

    @pytest.mark.unit
    def test_validate_invalid_code_raises_error(self):
        """Invalid codes should raise CountyValidationError."""
        with pytest.raises(CountyValidationError):
            validate_county_code('99')

        with pytest.raises(CountyValidationError):
            validate_county_code('00')

        with pytest.raises(CountyValidationError):
            validate_county_code('100')

    @pytest.mark.unit
    def test_validate_invalid_name_raises_error(self):
        """Invalid county names should raise CountyValidationError."""
        with pytest.raises(CountyValidationError):
            validate_county_code('InvalidCounty')

        with pytest.raises(CountyValidationError):
            validate_county_code('California')

        with pytest.raises(CountyValidationError):
            validate_county_code('XYZ123NotACounty')

    @pytest.mark.unit
    def test_validate_empty_string_raises_error(self):
        """Empty string should raise CountyValidationError."""
        with pytest.raises(CountyValidationError):
            validate_county_code('')

        with pytest.raises(CountyValidationError):
            validate_county_code('   ')  # Whitespace-only also rejected

    @pytest.mark.unit
    def test_validate_case_insensitive(self):
        """Validation should be case insensitive."""
        assert validate_county_code('bALdWiN') == '05'
        assert validate_county_code('JEFFERSON-BHAM') == '01'
        assert validate_county_code('mobile') == '02'


class TestGetCountyName:
    """Tests for county name lookup."""

    @pytest.mark.unit
    def test_valid_codes_return_county_name(self):
        """Valid codes should return the county name."""
        assert get_county_name('05') == 'Baldwin'
        assert get_county_name('01') == 'Jefferson-Bham'
        assert get_county_name('02') == 'Mobile'
        assert get_county_name('03') == 'Montgomery'

    @pytest.mark.unit
    def test_invalid_code_returns_fallback(self):
        """Invalid codes should return a fallback string."""
        result = get_county_name('99')
        assert 'County 99' in result

        result = get_county_name('00')
        assert 'County 00' in result


class TestListAvailableCounties:
    """Tests for listing all counties."""

    @pytest.mark.unit
    def test_returns_all_counties(self):
        """Should return all Alabama counties."""
        counties = list_available_counties()

        assert isinstance(counties, dict)
        assert len(counties) == len(ALABAMA_COUNTY_CODES)
        assert '05' in counties
        assert counties['05'] == 'Baldwin'

    @pytest.mark.unit
    def test_returns_copy_not_reference(self):
        """Should return a copy, not the original dict."""
        counties = list_available_counties()
        counties['TEST'] = 'Test County'

        # Original should be unchanged
        assert 'TEST' not in ALABAMA_COUNTY_CODES


class TestSearchCounties:
    """Tests for county search functionality."""

    @pytest.mark.unit
    def test_search_returns_matching_counties(self):
        """Search should return counties matching the query."""
        results = search_counties('Baldwin')
        assert '05' in results
        assert results['05'] == 'Baldwin'

    @pytest.mark.unit
    def test_search_is_case_insensitive(self):
        """Search should be case insensitive."""
        results_lower = search_counties('baldwin')
        results_upper = search_counties('BALDWIN')
        results_mixed = search_counties('BaLdWiN')

        assert results_lower == results_upper == results_mixed

    @pytest.mark.unit
    def test_search_partial_match(self):
        """Search should match partial names."""
        results = search_counties('Jeff')

        # Should match multiple Jefferson counties
        assert len(results) >= 1
        for name in results.values():
            assert 'JEFF' in name.upper()

    @pytest.mark.unit
    def test_search_no_match_returns_empty(self):
        """No matches should return empty dict."""
        results = search_counties('California')
        assert results == {}

    @pytest.mark.unit
    def test_search_strips_whitespace(self):
        """Query whitespace should be stripped."""
        results = search_counties('  Baldwin  ')
        assert '05' in results


class TestConstants:
    """Tests for module constants."""

    @pytest.mark.unit
    def test_county_codes_mapping_complete(self):
        """County codes should cover all Alabama counties."""
        # Alabama has 67 counties, but ADOR uses 68 codes (split Jefferson)
        assert len(ALABAMA_COUNTY_CODES) >= 67

    @pytest.mark.unit
    def test_reverse_mapping_consistent(self):
        """Reverse mapping should be consistent with forward mapping."""
        for code, name in ALABAMA_COUNTY_CODES.items():
            assert COUNTY_NAME_TO_CODE.get(name.upper()) == code

    @pytest.mark.unit
    def test_ador_base_url_valid(self):
        """Base URL should be a valid HTTPS URL."""
        assert ADOR_BASE_URL.startswith('https://')
        assert 'alabama.gov' in ADOR_BASE_URL


class TestScrapeCountyDataAsync:
    """Tests for async scraping function with mocked Playwright."""

    @pytest.fixture
    def mock_browser_context(self):
        """Create mock Playwright browser context."""
        # Mock page
        mock_page = AsyncMock()
        mock_page.set_default_timeout = Mock()
        mock_page.goto = AsyncMock()
        mock_page.select_option = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()

        # Sample HTML table for testing
        sample_html = """
        <table class="table-striped">
            <tr><th>Parcel</th><th>Amount</th></tr>
            <tr><td>PARCEL-001</td><td>$1,000</td></tr>
            <tr><td>PARCEL-002</td><td>$2,000</td></tr>
        </table>
        """
        mock_page.inner_html = AsyncMock(return_value=sample_html)
        mock_page.query_selector = AsyncMock(return_value=None)  # No next button

        # Mock browser
        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()

        # Mock playwright
        mock_playwright = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        return mock_playwright, mock_browser, mock_page

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_validates_county_code(self, mock_browser_context):
        """Scraping should validate the county code first."""
        mock_playwright, _, _ = mock_browser_context

        with patch('scripts.scraper.async_playwright') as mock_async_playwright:
            mock_async_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_playwright)
            mock_async_playwright.return_value.__aexit__ = AsyncMock()

            with pytest.raises(CountyValidationError):
                await scrape_county_data('InvalidCounty')

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_returns_dataframe(self, mock_browser_context):
        """Successful scrape should return a DataFrame."""
        mock_playwright, _, mock_page = mock_browser_context

        with patch('scripts.scraper.async_playwright') as mock_async_playwright:
            mock_async_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_playwright)
            mock_async_playwright.return_value.__aexit__ = AsyncMock()

            with patch('scripts.scraper.Path'):
                result = await scrape_county_data('05', save_raw=False)

        assert isinstance(result, pd.DataFrame)
        assert 'County' in result.columns
        assert 'County Code' in result.columns

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_adds_county_metadata(self, mock_browser_context):
        """Scraped data should include county name and code columns."""
        mock_playwright, _, mock_page = mock_browser_context

        with patch('scripts.scraper.async_playwright') as mock_async_playwright:
            mock_async_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_playwright)
            mock_async_playwright.return_value.__aexit__ = AsyncMock()

            with patch('scripts.scraper.Path'):
                result = await scrape_county_data('Baldwin', save_raw=False)

        assert all(result['County'] == 'Baldwin')
        assert all(result['County Code'] == '05')

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_handles_empty_results(self, mock_browser_context):
        """Scraping with no data should return empty DataFrame."""
        mock_playwright, _, mock_page = mock_browser_context

        # Return empty or "no records" message
        mock_page.inner_html = AsyncMock(return_value="No matching records found")

        with patch('scripts.scraper.async_playwright') as mock_async_playwright:
            mock_async_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_playwright)
            mock_async_playwright.return_value.__aexit__ = AsyncMock()

            result = await scrape_county_data('05', save_raw=False)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_respects_max_pages(self, mock_browser_context):
        """Scraping should stop at max_pages limit."""
        mock_playwright, _, mock_page = mock_browser_context

        # Simulate having a "Next" button available
        mock_next_button = AsyncMock()
        mock_next_button.click = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=mock_next_button)

        page_count = [0]

        async def track_pages(*args, **kwargs):
            page_count[0] += 1
            return """<table class="table-striped">
                <tr><th>Parcel</th></tr>
                <tr><td>TEST</td></tr>
            </table>"""

        mock_page.inner_html = track_pages

        with patch('scripts.scraper.async_playwright') as mock_async_playwright:
            mock_async_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_playwright)
            mock_async_playwright.return_value.__aexit__ = AsyncMock()

            with patch('scripts.scraper.Path'):
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    await scrape_county_data('05', max_pages=3, save_raw=False)

        assert page_count[0] == 3

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_error_raises_scraping_error(self):
        """Playwright errors should be wrapped in ScrapingError."""
        # Create a fresh mock that raises on goto
        mock_page = AsyncMock()
        mock_page.set_default_timeout = Mock()
        mock_page.goto = AsyncMock(side_effect=Exception("Network error"))

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        # Create a proper async context manager mock
        async_cm = MagicMock()
        async_cm.__aenter__ = AsyncMock(return_value=mock_playwright)
        async_cm.__aexit__ = AsyncMock(return_value=None)

        with patch('scripts.scraper.async_playwright', return_value=async_cm):
            with pytest.raises(ScrapingError) as exc_info:
                await scrape_county_data('05', save_raw=False)

            assert 'Baldwin' in str(exc_info.value)
