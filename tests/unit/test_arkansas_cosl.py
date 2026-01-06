"""
Unit tests for Arkansas COSL scraper module.

Tests the aiohttp-based web scraping functionality including
property parsing, county validation, pagination, retry logic,
and async context management.
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from aioresponses import aioresponses
import aiohttp

from core.scrapers.arkansas_cosl import (
    ArkansasCOSLScraper,
    COSLProperty,
    ARKANSAS_COUNTIES,
    COUNTY_NAME_TO_CODE,
)


# Sample API response data for testing
SAMPLE_API_RESPONSE = {
    'Data': [
        {
            'ListingToken': 'token-123',
            'CoSLParcelNumber': '001-03667-000',
            'CoSLCountyName': 'PHILLIPS',
            'Owner': 'JOHN DOE',
            'Acreage': 5.94,
            'Section': '30',
            'Township': '4S',
            'Range': '2E',
            'StartingBid': 2000.0,
            'CurrentBid': 2325.0,
            'Added': '2025-12-20T06:05:26.6002548',
            'GisId': '12345',
        },
        {
            'ListingToken': 'token-456',
            'CoSLParcelNumber': '002-00001-000',
            'CoSLCountyName': 'PULASKI',
            'Owner': 'JANE SMITH',
            'Acreage': 2.5,
            'Section': '15',
            'Township': '2N',
            'Range': '12W',
            'StartingBid': 1500.0,
            'CurrentBid': 0,
            'Added': '/Date(1734678326000)/',
            'GisId': None,
        },
    ],
    'Total': 2
}


class TestCOSLPropertyDataclass:
    """Tests for COSLProperty dataclass."""

    @pytest.mark.unit
    def test_to_dict_returns_correct_fields(self):
        """to_dict should return all expected fields."""
        prop = COSLProperty(
            listing_token='token-123',
            parcel_number='001-03667-000',
            county='PHILLIPS',
            owner='JOHN DOE',
            acres=5.94,
            section='30',
            township='4S',
            range='2E',
            starting_bid=2000.0,
            current_bid=2325.0,
            added_on=datetime(2025, 12, 20),
            gis_id='12345',
            acreage_source='api',
            acreage_confidence='high',
        )

        result = prop.to_dict()

        assert result['parcel_id'] == '001-03667-000'
        assert result['county'] == 'PHILLIPS'
        assert result['owner_name'] == 'JOHN DOE'
        assert result['acreage'] == 5.94
        assert result['state'] == 'AR'
        assert result['sale_type'] == 'tax_deed'
        assert result['redemption_period_days'] == 0
        assert result['time_to_ownership_days'] == 1
        assert result['data_source'] == 'arkansas_cosl'
        assert result['auction_platform'] == 'COSL Website'
        assert result['acreage_source'] == 'api'
        assert result['acreage_confidence'] == 'high'

    @pytest.mark.unit
    def test_to_dict_uses_current_bid_over_starting(self):
        """to_dict should use current_bid when available."""
        prop = COSLProperty(
            listing_token='token-123',
            parcel_number='001-03667-000',
            county='PHILLIPS',
            owner='JOHN DOE',
            acres=5.94,
            section=None,
            township=None,
            range=None,
            starting_bid=2000.0,
            current_bid=2325.0,
            added_on=None,
            gis_id=None,
        )

        result = prop.to_dict()
        assert result['amount'] == 2325.0

    @pytest.mark.unit
    def test_to_dict_uses_starting_bid_when_no_current(self):
        """to_dict should fall back to starting_bid when current_bid is 0."""
        prop = COSLProperty(
            listing_token='token-123',
            parcel_number='001-03667-000',
            county='PHILLIPS',
            owner='JOHN DOE',
            acres=5.94,
            section=None,
            township=None,
            range=None,
            starting_bid=2000.0,
            current_bid=0,
            added_on=None,
            gis_id=None,
        )

        result = prop.to_dict()
        assert result['amount'] == 2000.0

    @pytest.mark.unit
    def test_build_legal_description_with_all_parts(self):
        """Legal description should include section, township, range, and acres."""
        prop = COSLProperty(
            listing_token='token-123',
            parcel_number='001-03667-000',
            county='PHILLIPS',
            owner='JOHN DOE',
            acres=5.94,
            section='30',
            township='4S',
            range='2E',
            starting_bid=2000.0,
            current_bid=2325.0,
            added_on=None,
            gis_id=None,
        )

        result = prop._build_legal_description()
        assert 'SEC 30' in result
        assert 'TWP 4S' in result
        assert 'RNG 2E' in result
        assert '5.94 ACRES' in result

    @pytest.mark.unit
    def test_build_legal_description_missing_parts(self):
        """Legal description should handle missing parts gracefully."""
        prop = COSLProperty(
            listing_token='token-123',
            parcel_number='001-03667-000',
            county='PHILLIPS',
            owner='JOHN DOE',
            acres=0,
            section=None,
            township=None,
            range=None,
            starting_bid=2000.0,
            current_bid=0,
            added_on=None,
            gis_id=None,
        )

        result = prop._build_legal_description()
        assert 'Parcel 001-03667-000' in result


class TestArkansasCOSLScraperInit:
    """Tests for scraper initialization."""

    @pytest.mark.unit
    def test_default_initialization(self):
        """Scraper should initialize with default values."""
        scraper = ArkansasCOSLScraper()

        assert scraper._session is None
        assert scraper._owns_session is True
        assert scraper._max_retries == 3
        assert scraper._base_delay == 1.0

    @pytest.mark.unit
    def test_custom_retry_configuration(self):
        """Scraper should accept custom retry configuration."""
        scraper = ArkansasCOSLScraper(max_retries=5, base_delay=2.0)

        assert scraper._max_retries == 5
        assert scraper._base_delay == 2.0

    @pytest.mark.unit
    def test_external_session_provided(self):
        """Scraper should use external session when provided."""
        mock_session = Mock()
        scraper = ArkansasCOSLScraper(session=mock_session)

        assert scraper._session is mock_session
        assert scraper._owns_session is False


class TestKendoRequestBuilder:
    """Tests for Kendo UI grid request building."""

    @pytest.mark.unit
    def test_build_kendo_request_pagination(self):
        """Request should include correct pagination parameters."""
        scraper = ArkansasCOSLScraper()

        payload = scraper._build_kendo_request(page=3, page_size=100)

        assert payload['page'] == 3
        assert payload['pageSize'] == 100
        assert payload['take'] == 100
        assert payload['skip'] == 200  # (3-1) * 100

    @pytest.mark.unit
    def test_build_kendo_request_first_page(self):
        """First page request should have skip=0."""
        scraper = ArkansasCOSLScraper()

        payload = scraper._build_kendo_request(page=1, page_size=500)

        assert payload['page'] == 1
        assert payload['skip'] == 0
        assert payload['take'] == 500

    @pytest.mark.unit
    def test_build_kendo_request_with_county_filter(self):
        """Request should include county filter when specified."""
        scraper = ArkansasCOSLScraper()

        payload = scraper._build_kendo_request(page=1, county_filter='Pulaski')

        assert payload['filter[filters][0][field]'] == 'County'
        assert payload['filter[filters][0][operator]'] == 'contains'
        assert payload['filter[filters][0][value]'] == 'Pulaski'
        assert payload['filter[logic]'] == 'and'

    @pytest.mark.unit
    def test_build_kendo_request_default_page_size(self):
        """Request should use default page size when not specified."""
        scraper = ArkansasCOSLScraper()

        payload = scraper._build_kendo_request(page=1)

        assert payload['pageSize'] == 500


class TestPropertyParsing:
    """Tests for property parsing from API response."""

    @pytest.mark.unit
    def test_parse_property_from_api_response(self):
        """Should correctly parse property from API response."""
        scraper = ArkansasCOSLScraper()
        raw_data = SAMPLE_API_RESPONSE['Data'][0]

        with patch('core.scrapers.arkansas_cosl.extract_acreage_with_lineage', return_value=None):
            prop = scraper._parse_property(raw_data)

        assert prop.parcel_number == '001-03667-000'
        assert prop.county == 'PHILLIPS'
        assert prop.owner == 'JOHN DOE'
        assert prop.acres == 5.94
        assert prop.starting_bid == 2000.0
        assert prop.current_bid == 2325.0
        assert prop.acreage_source == 'api'
        assert prop.acreage_confidence == 'high'

    @pytest.mark.unit
    def test_parse_property_with_iso_date_format(self):
        """Should parse ISO format dates correctly."""
        scraper = ArkansasCOSLScraper()
        raw_data = {
            'ListingToken': 'token-123',
            'CoSLParcelNumber': '001-03667-000',
            'CoSLCountyName': 'PHILLIPS',
            'Owner': 'JOHN DOE',
            'Acreage': 5.94,
            'StartingBid': 2000.0,
            'CurrentBid': 0,
            'Added': '2025-12-20T06:05:26.6002548',
        }

        with patch('core.scrapers.arkansas_cosl.extract_acreage_with_lineage', return_value=None):
            prop = scraper._parse_property(raw_data)

        assert prop.added_on is not None
        assert prop.added_on.year == 2025
        assert prop.added_on.month == 12
        assert prop.added_on.day == 20

    @pytest.mark.unit
    def test_parse_property_with_net_date_format(self):
        """Should parse .NET JSON date format correctly."""
        scraper = ArkansasCOSLScraper()
        raw_data = {
            'ListingToken': 'token-123',
            'CoSLParcelNumber': '001-03667-000',
            'CoSLCountyName': 'PHILLIPS',
            'Owner': 'JOHN DOE',
            'Acreage': 5.94,
            'StartingBid': 2000.0,
            'CurrentBid': 0,
            'Added': '/Date(1734678326000)/',
        }

        with patch('core.scrapers.arkansas_cosl.extract_acreage_with_lineage', return_value=None):
            prop = scraper._parse_property(raw_data)

        assert prop.added_on is not None

    @pytest.mark.unit
    def test_parse_property_api_acreage_preferred_over_parsed(self):
        """API acreage should be used when available, not parsed acreage."""
        scraper = ArkansasCOSLScraper()
        raw_data = {
            'ListingToken': 'token-123',
            'CoSLParcelNumber': '001-03667-000',
            'CoSLCountyName': 'PHILLIPS',
            'Owner': 'JOHN DOE',
            'Acreage': 5.94,
            'Section': '30',
            'Township': '4S',
            'Range': '2E',
            'StartingBid': 2000.0,
            'CurrentBid': 0,
        }

        # Mock should not be called since API provides acreage
        with patch('core.scrapers.arkansas_cosl.extract_acreage_with_lineage') as mock_extract:
            prop = scraper._parse_property(raw_data)

        mock_extract.assert_not_called()
        assert prop.acres == 5.94
        assert prop.acreage_source == 'api'

    @pytest.mark.unit
    def test_parse_property_missing_acreage_triggers_parsing(self):
        """Should attempt to parse acreage when API doesn't provide it."""
        scraper = ArkansasCOSLScraper()
        raw_data = {
            'ListingToken': 'token-123',
            'CoSLParcelNumber': '001-03667-000',
            'CoSLCountyName': 'PHILLIPS',
            'Owner': 'JOHN DOE',
            'Acreage': 0,  # No acreage from API
            'Section': '30',
            'Township': '4S',
            'Range': '2E',
            'StartingBid': 2000.0,
            'CurrentBid': 0,
        }

        mock_result = Mock()
        mock_result.acreage = 2.5
        mock_result.source = 'parsed_plss'
        mock_result.confidence = 'medium'
        mock_result.raw_text = 'SEC 30 TWP 4S RNG 2E'

        with patch('core.scrapers.arkansas_cosl.extract_acreage_with_lineage', return_value=mock_result):
            prop = scraper._parse_property(raw_data)

        assert prop.acres == 2.5
        assert prop.acreage_source == 'parsed_plss'
        assert prop.acreage_confidence == 'medium'


class TestFetchGridPage:
    """Tests for grid page fetching with retry logic."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_returns_data_on_success(self):
        """Should return data on successful request."""
        with aioresponses() as m:
            m.post(
                'https://auction.cosl.org/auctions/grid_read',
                payload=SAMPLE_API_RESPONSE
            )

            async with ArkansasCOSLScraper() as scraper:
                data = await scraper._fetch_grid_page(scraper.GRID_ENDPOINT)

        assert len(data['Data']) == 2
        assert data['Total'] == 2

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_returns_empty_on_http_4xx_error(self):
        """Should return empty data on 4xx client errors (no retry)."""
        with aioresponses() as m:
            m.post(
                'https://auction.cosl.org/auctions/grid_read',
                status=404
            )

            async with ArkansasCOSLScraper() as scraper:
                data = await scraper._fetch_grid_page(scraper.GRID_ENDPOINT)

        assert data == {'Data': [], 'Total': 0}

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_retries_on_5xx_error(self):
        """Should retry on 5xx server errors."""
        with aioresponses() as m:
            # First two calls fail with 500, third succeeds
            m.post(
                'https://auction.cosl.org/auctions/grid_read',
                status=500
            )
            m.post(
                'https://auction.cosl.org/auctions/grid_read',
                status=500
            )
            m.post(
                'https://auction.cosl.org/auctions/grid_read',
                payload=SAMPLE_API_RESPONSE
            )

            async with ArkansasCOSLScraper(base_delay=0.01) as scraper:  # Short delay for test
                data = await scraper._fetch_grid_page(scraper.GRID_ENDPOINT)

        assert len(data['Data']) == 2

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_returns_empty_after_max_retries(self):
        """Should return empty data after exhausting retries."""
        with aioresponses() as m:
            # All calls fail
            for _ in range(3):
                m.post(
                    'https://auction.cosl.org/auctions/grid_read',
                    status=500
                )

            async with ArkansasCOSLScraper(max_retries=3, base_delay=0.01) as scraper:
                data = await scraper._fetch_grid_page(scraper.GRID_ENDPOINT)

        assert data == {'Data': [], 'Total': 0}

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_retries_on_network_error(self):
        """Should retry on network errors."""
        with aioresponses() as m:
            # First call raises exception, second succeeds
            m.post(
                'https://auction.cosl.org/auctions/grid_read',
                exception=aiohttp.ClientError('Connection failed')
            )
            m.post(
                'https://auction.cosl.org/auctions/grid_read',
                payload=SAMPLE_API_RESPONSE
            )

            async with ArkansasCOSLScraper(base_delay=0.01) as scraper:
                data = await scraper._fetch_grid_page(scraper.GRID_ENDPOINT)

        assert len(data['Data']) == 2

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_returns_empty_on_json_decode_error(self):
        """Should return empty data on JSON decode errors (no retry)."""
        with aioresponses() as m:
            m.post(
                'https://auction.cosl.org/auctions/grid_read',
                body='not valid json'
            )

            async with ArkansasCOSLScraper() as scraper:
                data = await scraper._fetch_grid_page(scraper.GRID_ENDPOINT)

        assert data == {'Data': [], 'Total': 0}


class TestScrapeAllProperties:
    """Tests for full property scraping."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_paginates_until_complete(self):
        """Should fetch all pages until complete."""
        page1_response = {
            'Data': [{'ListingToken': f'token-{i}', 'CoSLParcelNumber': f'parcel-{i}',
                      'CoSLCountyName': 'TEST', 'Owner': 'TEST', 'Acreage': 1.0,
                      'StartingBid': 1000, 'CurrentBid': 0} for i in range(500)],
            'Total': 600
        }
        page2_response = {
            'Data': [{'ListingToken': f'token-{i}', 'CoSLParcelNumber': f'parcel-{i}',
                      'CoSLCountyName': 'TEST', 'Owner': 'TEST', 'Acreage': 1.0,
                      'StartingBid': 1000, 'CurrentBid': 0} for i in range(500, 600)],
            'Total': 600
        }
        ongoing_response = {'Data': [], 'Total': 0}

        with aioresponses() as m:
            m.post('https://auction.cosl.org/auctions/grid_read', payload=page1_response)
            m.post('https://auction.cosl.org/auctions/grid_read', payload=page2_response)
            m.post('https://auction.cosl.org/auctions/ongoing-auctions_grid_read', payload=ongoing_response)

            with patch('core.scrapers.arkansas_cosl.extract_acreage_with_lineage', return_value=None):
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    async with ArkansasCOSLScraper() as scraper:
                        properties = await scraper.scrape_all_properties()

        assert len(properties) == 600

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_respects_max_pages(self):
        """Should stop at max_pages limit."""
        large_response = {
            'Data': [{'ListingToken': f'token-{i}', 'CoSLParcelNumber': f'parcel-{i}',
                      'CoSLCountyName': 'TEST', 'Owner': 'TEST', 'Acreage': 1.0,
                      'StartingBid': 1000, 'CurrentBid': 0} for i in range(500)],
            'Total': 10000  # More than we'll fetch
        }
        ongoing_response = {'Data': [], 'Total': 0}

        with aioresponses() as m:
            # Add enough responses for max_pages
            for _ in range(3):
                m.post('https://auction.cosl.org/auctions/grid_read', payload=large_response)
            m.post('https://auction.cosl.org/auctions/ongoing-auctions_grid_read', payload=ongoing_response)

            with patch('core.scrapers.arkansas_cosl.extract_acreage_with_lineage', return_value=None):
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    async with ArkansasCOSLScraper() as scraper:
                        properties = await scraper.scrape_all_properties(max_pages=2)

        # Should only fetch 2 pages * 500 = 1000 properties
        assert len(properties) == 1000

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_includes_ongoing_auctions_by_default(self):
        """Should include ongoing auctions by default."""
        main_response = {
            'Data': [{'ListingToken': 'main-token', 'CoSLParcelNumber': 'main-parcel',
                      'CoSLCountyName': 'TEST', 'Owner': 'TEST', 'Acreage': 1.0,
                      'StartingBid': 1000, 'CurrentBid': 0}],
            'Total': 1
        }
        ongoing_response = {
            'Data': [{'ListingToken': 'ongoing-token', 'CoSLParcelNumber': 'ongoing-parcel',
                      'CoSLCountyName': 'TEST', 'Owner': 'TEST', 'Acreage': 1.0,
                      'StartingBid': 1000, 'CurrentBid': 0}],
            'Total': 1
        }

        with aioresponses() as m:
            m.post('https://auction.cosl.org/auctions/grid_read', payload=main_response)
            m.post('https://auction.cosl.org/auctions/ongoing-auctions_grid_read', payload=ongoing_response)

            with patch('core.scrapers.arkansas_cosl.extract_acreage_with_lineage', return_value=None):
                async with ArkansasCOSLScraper() as scraper:
                    properties = await scraper.scrape_all_properties()

        assert len(properties) == 2
        parcel_numbers = [p.parcel_number for p in properties]
        assert 'main-parcel' in parcel_numbers
        assert 'ongoing-parcel' in parcel_numbers

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_excludes_ongoing_when_disabled(self):
        """Should not fetch ongoing auctions when disabled."""
        main_response = {
            'Data': [{'ListingToken': 'main-token', 'CoSLParcelNumber': 'main-parcel',
                      'CoSLCountyName': 'TEST', 'Owner': 'TEST', 'Acreage': 1.0,
                      'StartingBid': 1000, 'CurrentBid': 0}],
            'Total': 1
        }

        with aioresponses() as m:
            m.post('https://auction.cosl.org/auctions/grid_read', payload=main_response)
            # Don't add ongoing endpoint - should not be called

            with patch('core.scrapers.arkansas_cosl.extract_acreage_with_lineage', return_value=None):
                async with ArkansasCOSLScraper() as scraper:
                    properties = await scraper.scrape_all_properties(include_ongoing=False)

        assert len(properties) == 1
        assert properties[0].parcel_number == 'main-parcel'

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scrape_applies_county_filter(self):
        """Should pass county filter to API requests."""
        response = {
            'Data': [{'ListingToken': 'token', 'CoSLParcelNumber': 'parcel',
                      'CoSLCountyName': 'PULASKI', 'Owner': 'TEST', 'Acreage': 1.0,
                      'StartingBid': 1000, 'CurrentBid': 0}],
            'Total': 1
        }
        ongoing_response = {'Data': [], 'Total': 0}

        with aioresponses() as m:
            m.post('https://auction.cosl.org/auctions/grid_read', payload=response)
            m.post('https://auction.cosl.org/auctions/ongoing-auctions_grid_read', payload=ongoing_response)

            with patch('core.scrapers.arkansas_cosl.extract_acreage_with_lineage', return_value=None):
                async with ArkansasCOSLScraper() as scraper:
                    properties = await scraper.scrape_all_properties(county_filter='Pulaski')

        assert len(properties) == 1


class TestContextManager:
    """Tests for async context manager behavior."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_context_manager_creates_session(self):
        """Context manager should create session on enter."""
        scraper = ArkansasCOSLScraper()
        assert scraper._session is None

        async with scraper:
            assert scraper._session is not None
            assert isinstance(scraper._session, aiohttp.ClientSession)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_context_manager_closes_session(self):
        """Context manager should close session on exit."""
        scraper = ArkansasCOSLScraper()

        async with scraper:
            session = scraper._session

        assert session.closed

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_context_manager_preserves_external_session(self):
        """Context manager should not close external session."""
        async with aiohttp.ClientSession() as external_session:
            scraper = ArkansasCOSLScraper(session=external_session)

            async with scraper:
                assert scraper._session is external_session

            # External session should still be open
            assert not external_session.closed


class TestCountyConstants:
    """Tests for county constants."""

    @pytest.mark.unit
    def test_all_75_arkansas_counties_present(self):
        """Should have all 75 Arkansas counties."""
        assert len(ARKANSAS_COUNTIES) == 75

    @pytest.mark.unit
    def test_reverse_mapping_consistent(self):
        """Reverse mapping should match forward mapping."""
        for code, name in ARKANSAS_COUNTIES.items():
            assert COUNTY_NAME_TO_CODE.get(name.upper()) == code

    @pytest.mark.unit
    def test_county_codes_are_3_digit_strings(self):
        """County codes should be 3-digit zero-padded strings."""
        for code in ARKANSAS_COUNTIES.keys():
            assert len(code) == 3
            assert code.isdigit()

    @pytest.mark.unit
    def test_known_counties_exist(self):
        """Known major counties should be present."""
        known_counties = ['Pulaski', 'Washington', 'Benton', 'Sebastian', 'Garland']
        county_names = list(ARKANSAS_COUNTIES.values())

        for county in known_counties:
            assert county in county_names, f"{county} not found in county list"
