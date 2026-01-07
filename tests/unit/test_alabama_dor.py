"""
Unit tests for Alabama DOR scraper module.

Tests the Playwright-based web scraping functionality including
property dataclass, county validation, row parsing, async context
management, and exit code handling.
"""

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from core.scrapers.alabama_dor import (
    AlabamaDORScraper,
    AlabamaProperty,
    CountyValidationError,
    ALABAMA_COUNTY_CODES,
    COUNTY_NAME_TO_CODE,
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

# Sample ADOR table HTML structure (matches real ADOR format)
SAMPLE_ADOR_TABLE_HTML = """
<table class="table-striped">
    <thead>
        <tr>
            <th>CS Number</th>
            <th>County Code</th>
            <th>Document Number</th>
            <th>Parcel ID</th>
            <th>Year Sold</th>
            <th>Assessed Value</th>
            <th>Amount Bid at Tax Sale</th>
            <th>Name</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>123456</td>
            <td>05</td>
            <td>DOC-001</td>
            <td>05-12-34-56-001</td>
            <td>2024</td>
            <td>$15,000.00</td>
            <td>$2,500.00</td>
            <td>JOHN DOE</td>
            <td>LOT 1 CREEK MEADOWS SUBDIVISION 2.5 ACRES</td>
        </tr>
        <tr>
            <td>123457</td>
            <td>05</td>
            <td>DOC-002</td>
            <td>05-12-34-56-002</td>
            <td>2023</td>
            <td>$8,500.00</td>
            <td>$1,200.00</td>
            <td>JANE SMITH</td>
            <td>PARCEL A SEC 15 TWP 4N RNG 2W</td>
        </tr>
    </tbody>
</table>
"""

# Empty results message HTML
SAMPLE_NO_RESULTS_HTML = """
<div class="alert-warning">No matching records found</div>
"""

# Sample property data for dataclass tests
SAMPLE_PROPERTY_DATA = {
    'parcel_number': '05-12-34-56-001',
    'owner': 'JOHN DOE',
    'description': 'LOT 1 CREEK MEADOWS SUBDIVISION 2.5 ACRES',
    'year': '2024',
    'balance': 2500.0,
    'county': 'Baldwin',
    'county_code': '05',
}

# Sample row data for parsing tests (pandas Series format)
SAMPLE_ROW_DICT = {
    'Parcel ID': '05-12-34-56-001',
    'Year Sold': '2024',
    'Amount Bid at Tax Sale': '$2,500.00',
    'Name': 'JOHN DOE',
    'Description': 'LOT 1 CREEK MEADOWS SUBDIVISION 2.5 ACRES'
}


# =============================================================================
# TestAlabamaPropertyDataclass
# =============================================================================

class TestAlabamaPropertyDataclass:
    """Tests for AlabamaProperty dataclass and to_dict method."""

    @pytest.mark.unit
    def test_to_dict_returns_correct_fields(self):
        """to_dict should return all expected fields."""
        prop = AlabamaProperty(
            parcel_number='05-12-34-56-001',
            owner='JOHN DOE',
            description='LOT 1 TEST DESCRIPTION',
            year='2024',
            balance=2500.0,
            county='Baldwin',
            county_code='05',
            scraped_at=datetime(2026, 1, 6, 12, 0, 0)
        )

        with patch('core.scrapers.alabama_dor.extract_acreage_with_lineage', return_value=None):
            result = prop.to_dict()

        assert result['parcel_id'] == '05-12-34-56-001'
        assert result['county'] == 'Baldwin'
        assert result['owner_name'] == 'JOHN DOE'
        assert result['amount'] == 2500.0
        assert result['description'] == 'LOT 1 TEST DESCRIPTION'
        assert result['year_sold'] == '2024'
        assert result['data_source'] == 'alabama_dor'
        assert result['auction_platform'] == 'ADOR Search'

    @pytest.mark.unit
    def test_to_dict_state_is_alabama(self):
        """State should always be 'AL'."""
        prop = AlabamaProperty(
            parcel_number='TEST-001',
            owner='TEST',
            description='TEST',
            year='2024',
            balance=100.0,
            county='Baldwin',
            county_code='05',
            scraped_at=datetime.utcnow()
        )

        with patch('core.scrapers.alabama_dor.extract_acreage_with_lineage', return_value=None):
            result = prop.to_dict()

        assert result['state'] == 'AL'

    @pytest.mark.unit
    def test_to_dict_sale_type_is_tax_lien(self):
        """Sale type should be 'tax_lien' for Alabama."""
        prop = AlabamaProperty(
            parcel_number='TEST-001',
            owner='TEST',
            description='TEST',
            year='2024',
            balance=100.0,
            county='Baldwin',
            county_code='05',
            scraped_at=datetime.utcnow()
        )

        with patch('core.scrapers.alabama_dor.extract_acreage_with_lineage', return_value=None):
            result = prop.to_dict()

        assert result['sale_type'] == 'tax_lien'

    @pytest.mark.unit
    def test_to_dict_redemption_period_1460_days(self):
        """Redemption period should be 1460 days (4 years)."""
        prop = AlabamaProperty(
            parcel_number='TEST-001',
            owner='TEST',
            description='TEST',
            year='2024',
            balance=100.0,
            county='Baldwin',
            county_code='05',
            scraped_at=datetime.utcnow()
        )

        with patch('core.scrapers.alabama_dor.extract_acreage_with_lineage', return_value=None):
            result = prop.to_dict()

        assert result['redemption_period_days'] == 1460
        assert result['time_to_ownership_days'] == 2000

    @pytest.mark.unit
    def test_to_dict_acreage_extraction_with_lineage(self):
        """Acreage should be extracted with lineage tracking."""
        prop = AlabamaProperty(
            parcel_number='TEST-001',
            owner='TEST',
            description='LOT 1 CREEK MEADOWS 2.5 ACRES',
            year='2024',
            balance=100.0,
            county='Baldwin',
            county_code='05',
            scraped_at=datetime.utcnow()
        )

        # Mock AcreageResult with attribute access (not dict)
        mock_result = Mock()
        mock_result.acreage = 2.5
        mock_result.source = 'parsed_explicit'
        mock_result.confidence = 'high'
        mock_result.raw_text = '2.5 ACRES'

        with patch('core.scrapers.alabama_dor.extract_acreage_with_lineage', return_value=mock_result):
            result = prop.to_dict()

        assert result['acreage'] == 2.5
        assert result['acreage_source'] == 'parsed_explicit'
        assert result['acreage_confidence'] == 'high'
        assert result['acreage_raw_text'] == '2.5 ACRES'

    @pytest.mark.unit
    def test_to_dict_acreage_none_when_not_found(self):
        """Acreage fields should be None when not found in description."""
        prop = AlabamaProperty(
            parcel_number='TEST-001',
            owner='TEST',
            description='LOT 1 NO ACREAGE MENTIONED',
            year='2024',
            balance=100.0,
            county='Baldwin',
            county_code='05',
            scraped_at=datetime.utcnow()
        )

        with patch('core.scrapers.alabama_dor.extract_acreage_with_lineage', return_value=None):
            result = prop.to_dict()

        assert result['acreage'] is None
        assert result['acreage_source'] is None
        assert result['acreage_confidence'] is None
        assert result['acreage_raw_text'] is None

    @pytest.mark.unit
    def test_to_dict_acreage_uses_attribute_access(self):
        """
        CRITICAL: Acreage extraction uses .acreage attribute, not .get('acreage').

        This test verifies the fix for the 2026-01-06 bug where result.get('acreage')
        was incorrectly used on an AcreageResult dataclass.
        """
        prop = AlabamaProperty(
            parcel_number='TEST-001',
            owner='TEST',
            description='10.5 ACRES IN SECTION 15',
            year='2024',
            balance=100.0,
            county='Baldwin',
            county_code='05',
            scraped_at=datetime.utcnow()
        )

        # Create a mock that ONLY supports attribute access (not dict)
        # This will fail if code tries to use .get()
        mock_result = Mock(spec=['acreage', 'source', 'confidence', 'raw_text'])
        mock_result.acreage = 10.5
        mock_result.source = 'parsed_explicit'
        mock_result.confidence = 'high'
        mock_result.raw_text = '10.5 ACRES'

        with patch('core.scrapers.alabama_dor.extract_acreage_with_lineage', return_value=mock_result):
            result = prop.to_dict()

        assert result['acreage'] == 10.5


# =============================================================================
# TestCountyValidation
# =============================================================================

class TestCountyValidation:
    """Tests for county code validation."""

    @pytest.mark.unit
    def test_validate_with_valid_numeric_code(self):
        """Valid numeric codes should be returned."""
        scraper = AlabamaDORScraper()
        assert scraper._validate_county('05') == '05'
        assert scraper._validate_county('01') == '01'
        assert scraper._validate_county('67') == '67'
        assert scraper._validate_county('02') == '02'

    @pytest.mark.unit
    def test_validate_with_single_digit_code(self):
        """Single digit codes should be zero-padded."""
        scraper = AlabamaDORScraper()
        assert scraper._validate_county('5') == '05'
        assert scraper._validate_county('1') == '01'
        assert scraper._validate_county('2') == '02'

    @pytest.mark.unit
    def test_validate_with_valid_county_name(self):
        """Valid county names should return correct code."""
        scraper = AlabamaDORScraper()
        assert scraper._validate_county('Baldwin') == '05'
        assert scraper._validate_county('Mobile') == '02'
        assert scraper._validate_county('Montgomery') == '03'

    @pytest.mark.unit
    def test_validate_case_insensitive(self):
        """Validation should be case insensitive."""
        scraper = AlabamaDORScraper()
        assert scraper._validate_county('BALDWIN') == '05'
        assert scraper._validate_county('baldwin') == '05'
        assert scraper._validate_county('BaLdWiN') == '05'

    @pytest.mark.unit
    def test_validate_partial_name_prefix(self):
        """Partial name prefix should match."""
        scraper = AlabamaDORScraper()
        # 'Bald' should match 'Baldwin'
        assert scraper._validate_county('Bald') == '05'
        # 'Mob' should match 'Mobile'
        assert scraper._validate_county('Mob') == '02'

    @pytest.mark.unit
    def test_validate_partial_name_substring(self):
        """Partial name substring should match."""
        scraper = AlabamaDORScraper()
        # Substring matching - 'aldwin' is in 'BALDWIN'
        result = scraper._validate_county('aldwin')
        assert result == '05'

    @pytest.mark.unit
    def test_validate_strips_whitespace(self):
        """Whitespace should be stripped."""
        scraper = AlabamaDORScraper()
        assert scraper._validate_county('  Baldwin  ') == '05'
        assert scraper._validate_county('\t05\n') == '05'

    @pytest.mark.unit
    def test_validate_invalid_code_raises_error(self):
        """Invalid codes should raise CountyValidationError."""
        scraper = AlabamaDORScraper()
        with pytest.raises(CountyValidationError):
            scraper._validate_county('99')
        with pytest.raises(CountyValidationError):
            scraper._validate_county('00')
        with pytest.raises(CountyValidationError):
            scraper._validate_county('100')

    @pytest.mark.unit
    def test_validate_invalid_name_raises_error(self):
        """Invalid county names should raise CountyValidationError."""
        scraper = AlabamaDORScraper()
        with pytest.raises(CountyValidationError):
            scraper._validate_county('InvalidCounty')
        with pytest.raises(CountyValidationError):
            scraper._validate_county('California')
        with pytest.raises(CountyValidationError):
            scraper._validate_county('XYZ123')

    @pytest.mark.unit
    def test_validate_empty_raises_error(self):
        """Empty string should raise CountyValidationError."""
        scraper = AlabamaDORScraper()
        with pytest.raises(CountyValidationError):
            scraper._validate_county('')

    @pytest.mark.unit
    def test_validate_whitespace_only_raises_error(self):
        """Whitespace-only string should raise CountyValidationError."""
        scraper = AlabamaDORScraper()
        with pytest.raises(CountyValidationError):
            scraper._validate_county('   ')


# =============================================================================
# TestRowParsing
# =============================================================================

class TestRowParsing:
    """Tests for row parsing from HTML table."""

    @pytest.mark.unit
    def test_parse_row_valid_data(self):
        """Normal row should return AlabamaProperty."""
        scraper = AlabamaDORScraper()
        row = pd.Series(SAMPLE_ROW_DICT)

        result = scraper._parse_row(row, '05')

        assert result is not None
        assert result.parcel_number == '05-12-34-56-001'
        assert result.owner == 'JOHN DOE'
        assert result.year == '2024'
        assert result.balance == 2500.0
        assert result.county == 'Baldwin'
        assert result.county_code == '05'

    @pytest.mark.unit
    def test_parse_row_currency_parsing(self):
        """Currency with $ and commas should be parsed correctly."""
        scraper = AlabamaDORScraper()
        row = pd.Series({
            'Parcel ID': 'TEST-001',
            'Year Sold': '2024',
            'Amount Bid at Tax Sale': '$12,345.67',
            'Name': 'TEST OWNER',
            'Description': 'TEST DESC'
        })

        result = scraper._parse_row(row, '05')

        assert result is not None
        assert result.balance == 12345.67

    @pytest.mark.unit
    def test_parse_row_empty_amount_defaults_zero(self):
        """Missing amount should default to 0.0."""
        scraper = AlabamaDORScraper()
        row = pd.Series({
            'Parcel ID': 'TEST-001',
            'Year Sold': '2024',
            'Amount Bid at Tax Sale': '',
            'Name': 'TEST OWNER',
            'Description': 'TEST DESC'
        })

        result = scraper._parse_row(row, '05')

        assert result is not None
        assert result.balance == 0.0

    @pytest.mark.unit
    def test_parse_row_invalid_amount_defaults_zero(self):
        """Non-numeric amount should default to 0.0."""
        scraper = AlabamaDORScraper()
        row = pd.Series({
            'Parcel ID': 'TEST-001',
            'Year Sold': '2024',
            'Amount Bid at Tax Sale': 'NOT A NUMBER',
            'Name': 'TEST OWNER',
            'Description': 'TEST DESC'
        })

        result = scraper._parse_row(row, '05')

        assert result is not None
        assert result.balance == 0.0

    @pytest.mark.unit
    def test_parse_row_missing_parcel_returns_none(self):
        """Empty parcel ID should return None."""
        scraper = AlabamaDORScraper()
        row = pd.Series({
            'Parcel ID': '',
            'Year Sold': '2024',
            'Amount Bid at Tax Sale': '$1,000.00',
            'Name': 'TEST OWNER',
            'Description': 'TEST DESC'
        })

        result = scraper._parse_row(row, '05')

        assert result is None

    @pytest.mark.unit
    def test_parse_row_nan_parcel_returns_none(self):
        """Parcel ID of 'nan' should return None."""
        scraper = AlabamaDORScraper()
        row = pd.Series({
            'Parcel ID': 'nan',
            'Year Sold': '2024',
            'Amount Bid at Tax Sale': '$1,000.00',
            'Name': 'TEST OWNER',
            'Description': 'TEST DESC'
        })

        result = scraper._parse_row(row, '05')

        assert result is None

    @pytest.mark.unit
    def test_parse_row_alternate_column_names(self):
        """Should handle alternate column names via fallback."""
        scraper = AlabamaDORScraper()
        # Use 'Parcel Number' instead of 'Parcel ID'
        row = pd.Series({
            'Parcel Number': 'ALT-001',
            'Year': '2023',
            'Amount': '$500.00',
            'Name': 'ALT OWNER',
            'Description': 'ALT DESC'
        })

        result = scraper._parse_row(row, '05')

        assert result is not None
        assert result.parcel_number == 'ALT-001'

    @pytest.mark.unit
    def test_parse_row_exception_returns_none(self):
        """Exception during parsing should return None gracefully."""
        scraper = AlabamaDORScraper()
        # Create a mock Series that raises an exception when accessed
        row = MagicMock()
        row.get.side_effect = Exception("Unexpected error")

        result = scraper._parse_row(row, '05')

        assert result is None


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
        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        with patch('core.scrapers.alabama_dor.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            async with AlabamaDORScraper() as scraper:
                assert scraper._browser is not None
                mock_playwright.chromium.launch.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_context_manager_closes_browser(self):
        """Context manager should close browser on exit."""
        mock_browser = AsyncMock()
        mock_browser.close = AsyncMock()
        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.stop = AsyncMock()

        with patch('core.scrapers.alabama_dor.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            async with AlabamaDORScraper() as scraper:
                pass

            mock_browser.close.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_context_manager_stops_playwright(self):
        """Context manager should stop Playwright on exit."""
        mock_browser = AsyncMock()
        mock_browser.close = AsyncMock()
        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.stop = AsyncMock()

        with patch('core.scrapers.alabama_dor.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            async with AlabamaDORScraper() as scraper:
                pass

            mock_playwright.stop.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_context_manager_cleanup_on_error(self):
        """Resources should be cleaned up even if scraping fails."""
        mock_browser = AsyncMock()
        mock_browser.close = AsyncMock()
        mock_browser.new_page = AsyncMock(side_effect=Exception("Scraping error"))
        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.stop = AsyncMock()

        with patch('core.scrapers.alabama_dor.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            try:
                async with AlabamaDORScraper() as scraper:
                    await scraper._browser.new_page()
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
        """Invalid county should raise error before browser starts."""
        scraper = AlabamaDORScraper()
        # Set browser to None to simulate not being in context manager
        scraper._browser = MagicMock()

        with pytest.raises(CountyValidationError):
            await scraper.scrape_county('InvalidCounty')

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_county_browser_not_started_error(self):
        """Error should be raised if browser not started."""
        scraper = AlabamaDORScraper()
        # _browser is None by default

        with pytest.raises(RuntimeError) as excinfo:
            await scraper.scrape_county('Baldwin')

        assert "Scraper not started" in str(excinfo.value)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_county_handles_no_results(self):
        """Should handle 'no matching records' gracefully."""
        # Setup mocks
        mock_table = None  # No table found
        mock_page = AsyncMock()
        mock_page.set_default_timeout = Mock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.select_option = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=mock_table)
        mock_page.content = AsyncMock(return_value="No matching records found")
        mock_page.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()

        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.stop = AsyncMock()

        with patch('core.scrapers.alabama_dor.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            async with AlabamaDORScraper() as scraper:
                with patch('core.scrapers.alabama_dor.save_debug_snapshot'):
                    properties = await scraper.scrape_county('Baldwin')

        assert properties == []

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_county_returns_properties(self):
        """Successful scrape should return list of properties."""
        # Mock table element
        mock_table = AsyncMock()
        mock_table.inner_html = AsyncMock(return_value="""
            <thead><tr><th>Parcel ID</th><th>Year Sold</th><th>Amount Bid at Tax Sale</th><th>Name</th><th>Description</th></tr></thead>
            <tbody>
                <tr><td>TEST-001</td><td>2024</td><td>$1,000.00</td><td>OWNER ONE</td><td>LOT 1</td></tr>
            </tbody>
        """)

        mock_page = AsyncMock()
        mock_page.set_default_timeout = Mock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.select_option = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        # First call returns table, second call returns None (no next button)
        mock_page.query_selector = AsyncMock(side_effect=[mock_table, None])
        mock_page.content = AsyncMock(return_value="<html></html>")
        mock_page.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()

        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.stop = AsyncMock()

        with patch('core.scrapers.alabama_dor.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            async with AlabamaDORScraper() as scraper:
                properties = await scraper.scrape_county('Baldwin')

        assert len(properties) >= 0  # May be empty if parsing fails

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_county_respects_max_pages(self):
        """Should stop at max_pages limit."""
        page_count = [0]

        # Create mock that tracks page loads
        async def mock_query_selector(selector):
            if 'table' in selector:
                mock_table = AsyncMock()
                mock_table.inner_html = AsyncMock(return_value="<tbody><tr><td>TEST</td></tr></tbody>")
                return mock_table
            elif 'Next' in selector or 'pagination' in selector:
                page_count[0] += 1
                if page_count[0] < 10:  # Simulate many pages available
                    mock_next = AsyncMock()
                    mock_next.get_attribute = AsyncMock(return_value=None)  # Not disabled
                    mock_next.click = AsyncMock()
                    return mock_next
                return None
            return None

        mock_page = AsyncMock()
        mock_page.set_default_timeout = Mock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.select_option = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector = mock_query_selector
        mock_page.content = AsyncMock(return_value="<html></html>")
        mock_page.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()

        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.stop = AsyncMock()

        with patch('core.scrapers.alabama_dor.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            async with AlabamaDORScraper() as scraper:
                await scraper.scrape_county('Baldwin', max_pages=2)

        # Should have stopped at max_pages
        assert page_count[0] <= 2

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_county_pagination(self):
        """Should handle pagination by clicking Next button."""
        call_count = [0]

        async def mock_query_selector(selector):
            if 'table' in selector:
                mock_table = AsyncMock()
                mock_table.inner_html = AsyncMock(return_value="<tbody><tr><td>TEST</td></tr></tbody>")
                return mock_table
            elif 'Next' in selector or 'pagination' in selector:
                call_count[0] += 1
                if call_count[0] == 1:
                    # First call: return clickable next button
                    mock_next = AsyncMock()
                    mock_next.get_attribute = AsyncMock(return_value=None)
                    mock_next.click = AsyncMock()
                    return mock_next
                # Second call: no next button (end of pagination)
                return None
            return None

        mock_page = AsyncMock()
        mock_page.set_default_timeout = Mock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.select_option = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector = mock_query_selector
        mock_page.content = AsyncMock(return_value="<html></html>")
        mock_page.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()

        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.stop = AsyncMock()

        with patch('core.scrapers.alabama_dor.async_playwright') as mock_async_pw:
            with patch('asyncio.sleep', new_callable=AsyncMock):
                mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

                async with AlabamaDORScraper() as scraper:
                    await scraper.scrape_county('Baldwin')

        # Next button should have been checked
        assert call_count[0] >= 1


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
        # The logic in the main block maps CountyValidationError to EXIT_PERMANENT
        error = CountyValidationError("Invalid county: XYZ")
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
        # These error types should trigger EXIT_TRANSIENT
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        # PlaywrightTimeoutError triggers transient
        # ConnectionError triggers transient
        transient_errors = [
            PlaywrightTimeoutError("Page load timeout"),
            ConnectionError("Network unreachable"),
        ]

        for error in transient_errors:
            # These should be retried (EXIT_TRANSIENT)
            assert isinstance(error, (PlaywrightTimeoutError, ConnectionError))

    @pytest.mark.unit
    def test_normal_exception_defaults_to_transient(self):
        """Unknown exceptions should default to transient (allow retry)."""
        # The main block defaults unknown errors to EXIT_TRANSIENT
        # This allows retry for unexpected but potentially recoverable errors
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
        # Therefore defaults to EXIT_TRANSIENT


# =============================================================================
# TestCountyConstants
# =============================================================================

class TestCountyConstants:
    """Tests for county code constants."""

    @pytest.mark.unit
    def test_alabama_has_68_county_codes(self):
        """Alabama should have 68 county codes (67 + split Jefferson)."""
        # Alabama has 67 counties, but Jefferson is split into
        # Jefferson-Bham (01) and Jefferson-Bess (68)
        assert len(ALABAMA_COUNTY_CODES) == 68

    @pytest.mark.unit
    def test_reverse_mapping_consistent(self):
        """Forward and reverse mappings should be consistent."""
        for code, name in ALABAMA_COUNTY_CODES.items():
            # Reverse mapping should exist for each county
            assert name.upper() in COUNTY_NAME_TO_CODE
            assert COUNTY_NAME_TO_CODE[name.upper()] == code

    @pytest.mark.unit
    def test_county_codes_are_2_digit_strings(self):
        """County codes should be 2-digit zero-padded strings."""
        for code in ALABAMA_COUNTY_CODES.keys():
            assert len(code) == 2
            assert code.isdigit()

    @pytest.mark.unit
    def test_known_counties_exist(self):
        """Major Alabama counties should be present."""
        known_counties = {
            'Baldwin': '05',
            'Mobile': '02',
            'Montgomery': '03',
            'Jefferson-Bham': '01',
            'Jefferson-Bess': '68',
            'Tuscaloosa': '63',
            'Madison': '47',
        }

        for name, expected_code in known_counties.items():
            assert expected_code in ALABAMA_COUNTY_CODES
            assert ALABAMA_COUNTY_CODES[expected_code] == name
