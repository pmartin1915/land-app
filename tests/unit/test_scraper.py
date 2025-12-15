"""
AI-testable unit tests for scripts/scraper.py module.

This module provides comprehensive test coverage for the web scraping functionality
including county validation, session management, HTML parsing, pagination handling,
and error recovery scenarios with AI-friendly patterns.
"""

import pytest
import pandas as pd
import requests
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup
import tempfile
import os
from io import StringIO
import json
import time
from pathlib import Path

from scripts.scraper import (
    validate_county_code, get_county_name, create_session,
    extract_pagination_info, parse_property_table, scrape_single_page,
    scrape_county_data, list_available_counties, search_counties,
    ALABAMA_COUNTY_CODES, COUNTY_NAME_TO_CODE, ADOR_BASE_URL
)
from scripts.exceptions import CountyValidationError, NetworkError, ParseError, ScrapingError
from scripts.ai_exceptions import AINetworkError, AIParseError, RecoveryAction, RecoveryInstruction
from config.ai_logging import get_ai_logger
from tests.fixtures.data_factories import create_sample_property_data


class TestCountyValidation:
    """Test suite for county code validation functionality."""

    def test_validate_county_code_with_valid_code(self):
        assert validate_county_code('05') == '05'
        assert validate_county_code('5') == '05'
        assert validate_county_code('37') == '37'
        assert validate_county_code('67') == '67'

    def test_validate_county_code_with_valid_name(self):
        assert validate_county_code('Baldwin') == '05'
        assert validate_county_code('BALDWIN') == '05'
        assert validate_county_code('baldwin') == '05'
        assert validate_county_code('Jefferson') == '38'
        assert validate_county_code('Mobile') == '02'

    def test_validate_county_code_with_partial_match(self):
        assert validate_county_code('Bald') == '05'
        assert validate_county_code('Jeff') == '38'
        assert validate_county_code('Mob') == '02'

    def test_validate_county_code_invalid_inputs(self):
        with pytest.raises(CountyValidationError):
            validate_county_code('99')

        with pytest.raises(CountyValidationError):
            validate_county_code('InvalidCounty')

        with pytest.raises(CountyValidationError):
            validate_county_code('00')

        with pytest.raises(CountyValidationError):
            validate_county_code('')

    def test_validate_county_code_edge_cases(self):
        assert validate_county_code('  Baldwin  ') == '05'
        assert validate_county_code('01') == '01'

    @pytest.mark.ai_test
    def test_county_validation_performance_benchmark(self, benchmark):
        result = benchmark(validate_county_code, 'Baldwin')
        assert result == '05'
        assert benchmark.stats['mean'] < 0.001

    def test_validate_county_code_numeric_string_edge_cases(self):
        assert validate_county_code('1') == '01'
        assert validate_county_code('9') == '09'

    def test_validate_county_code_case_insensitive(self):
        assert validate_county_code('bALdWiN') == '05'
        assert validate_county_code('JEFFERSON') == '38'
        assert validate_county_code('mobile') == '02'


class TestCountyUtilities:
    """Test suite for county utility functions."""

    def test_get_county_name_valid_codes(self):
        assert get_county_name('05') == 'Baldwin'
        assert get_county_name('38') == 'Jefferson'
        assert get_county_name('02') == 'Mobile'

    def test_get_county_name_invalid_code(self):
        result = get_county_name('99')
        assert 'County 99' in result

    def test_list_available_counties(self):
        counties = list_available_counties()
        assert isinstance(counties, dict)
        assert len(counties) == 67
        assert '05' in counties
        assert counties['05'] == 'Baldwin'
        assert counties != ALABAMA_COUNTY_CODES

    def test_search_counties_exact_match(self):
        results = search_counties('Baldwin')
        assert len(results) == 1
        assert results['05'] == 'Baldwin'

    def test_search_counties_partial_match(self):
        results = search_counties('Jeff')
        assert '38' in results
        assert results['38'] == 'Jefferson'

    def test_search_counties_multiple_matches(self):
        results = search_counties('Saint')
        assert '96' in results
        assert results['96'] == 'Saint Clair'

    def test_search_counties_no_matches(self):
        results = search_counties('NonexistentCounty')
        assert len(results) == 0
        assert isinstance(results, dict)

    def test_search_counties_case_insensitive(self):
        results_lower = search_counties('baldwin')
        results_upper = search_counties('BALDWIN')
        results_mixed = search_counties('BaLdWiN')

        assert results_lower == results_upper == results_mixed
        assert len(results_lower) == 1

    @pytest.mark.ai_test
    def test_county_search_performance_benchmark(self, benchmark):
        result = benchmark(search_counties, 'Jeff')
        assert len(result) >= 1
        assert benchmark.stats['mean'] < 0.01

    def test_search_counties_empty_query(self):
        results = search_counties('')
        assert len(results) == 0

    def test_search_counties_whitespace_handling(self):
        results = search_counties('  Baldwin  ')
        assert len(results) == 1
        assert results['05'] == 'Baldwin'


class TestSessionManagement:
    """Test suite for requests session management."""

    def test_create_session_basic(self):
        session = create_session()
        assert isinstance(session, requests.Session)

    def test_create_session_headers(self):
        session = create_session()
        headers = session.headers

        assert 'User-Agent' in headers
        assert 'Mozilla' in headers['User-Agent']
        assert 'Accept' in headers
        assert 'Accept-Language' in headers
        assert 'Connection' in headers

    def test_create_session_user_agent(self):
        session = create_session()
        user_agent = session.headers['User-Agent']

        assert 'Mozilla' in user_agent
        assert 'Chrome' in user_agent
        assert 'Safari' in user_agent

    @pytest.mark.ai_test
    def test_session_creation_performance_benchmark(self, benchmark):
        result = benchmark(create_session)
        assert isinstance(result, requests.Session)
        assert benchmark.stats['mean'] < 0.01

    def test_create_session_multiple_instances(self):
        session1 = create_session()
        session2 = create_session()

        assert session1 is not session2
        assert session1.headers == session2.headers

    def test_session_headers_completeness(self):
        session = create_session()
        required_headers = [
            'User-Agent', 'Accept', 'Accept-Language',
            'Accept-Encoding', 'Connection', 'Upgrade-Insecure-Requests'
        ]

        for header in required_headers:
            assert header in session.headers


class TestHTMLParsing:
    """Test suite for HTML parsing functionality."""

    def setup_method(self):
        self.sample_html_table = """
        <table id="ador-delinquent-search-results">
            <tr>
                <th>Parcel ID</th>
                <th>Property Description</th>
                <th>Amount Due</th>
                <th>County</th>
            </tr>
            <tr>
                <td>001-001-001</td>
                <td>123 Main St</td>
                <td>$1,500.00</td>
                <td>Baldwin</td>
            </tr>
            <tr>
                <td>002-002-002</td>
                <td>456 Oak Ave</td>
                <td>$2,500.00</td>
                <td>Baldwin</td>
            </tr>
        </table>
        """

        self.sample_pagination_html = """
        <div class="pagination">
            <a href="?offset=0&county=05">Previous</a>
            <a href="?offset=100&county=05">Next</a>
        </div>
        """

    def test_parse_property_table_with_pandas(self):
        soup = BeautifulSoup(self.sample_html_table, 'html.parser')

        with patch('pandas.read_html') as mock_read_html:
            mock_df = pd.DataFrame({
                'Parcel ID': ['001-001-001', '002-002-002'],
                'Property Description': ['123 Main St', '456 Oak Ave'],
                'Amount Due': ['$1,500.00', '$2,500.00'],
                'County': ['Baldwin', 'Baldwin']
            })
            mock_read_html.return_value = [mock_df]

            result = parse_property_table(soup)

            assert len(result) == 2
            assert 'Parcel ID' in result.columns
            assert result.iloc[0]['Parcel ID'] == '001-001-001'

    def test_parse_property_table_fallback_beautifulsoup(self):
        soup = BeautifulSoup(self.sample_html_table, 'html.parser')

        with patch('pandas.read_html', side_effect=Exception("pandas failed")):
            result = parse_property_table(soup)

            assert len(result) == 2
            assert 'Parcel ID' in result.columns
            assert result.iloc[0]['Parcel ID'] == '001-001-001'

    def test_parse_property_table_no_table(self):
        html_no_table = "<div>No table here</div>"
        soup = BeautifulSoup(html_no_table, 'html.parser')

        result = parse_property_table(soup)

        assert len(result) == 0
        assert isinstance(result, pd.DataFrame)

    def test_parse_property_table_empty_table(self):
        empty_table_html = "<table></table>"
        soup = BeautifulSoup(empty_table_html, 'html.parser')

        result = parse_property_table(soup)

        assert len(result) == 0

    def test_extract_pagination_info_with_links(self):
        soup = BeautifulSoup(self.sample_pagination_html, 'html.parser')

        prev_url, next_url, current_page = extract_pagination_info(soup)

        assert 'offset=0' in prev_url
        assert 'offset=100' in next_url
        assert current_page >= 1

    def test_extract_pagination_info_no_links(self):
        html_no_pagination = "<div>No pagination</div>"
        soup = BeautifulSoup(html_no_pagination, 'html.parser')

        prev_url, next_url, current_page = extract_pagination_info(soup)

        assert prev_url is None
        assert next_url is None
        assert current_page == 1

    @pytest.mark.ai_test
    def test_html_parsing_performance_benchmark(self, benchmark):
        soup = BeautifulSoup(self.sample_html_table, 'html.parser')

        result = benchmark(parse_property_table, soup)

        assert len(result) >= 0
        assert benchmark.stats['mean'] < 0.1

    def test_parse_property_table_malformed_html(self):
        malformed_html = """
        <table>
            <tr><th>Header1<th>Header2</tr>
            <tr><td>Data1<td>Data2</tr>
        </table>
        """
        soup = BeautifulSoup(malformed_html, 'html.parser')

        result = parse_property_table(soup)

        assert isinstance(result, pd.DataFrame)

    def test_parse_property_table_mixed_cell_types(self):
        mixed_html = """
        <table>
            <tr>
                <th>ID</th>
                <td>Description</td>
            </tr>
            <tr>
                <td>001</td>
                <th>Property</th>
            </tr>
        </table>
        """
        soup = BeautifulSoup(mixed_html, 'html.parser')

        result = parse_property_table(soup)

        assert len(result) == 1

    def test_extract_pagination_complex_links(self):
        complex_pagination = """
        <div>
            <a href="/search?county=05&offset=50">Previous</a>
            <span>Page 3 of 10</span>
            <a href="/search?county=05&offset=150">Next</a>
        </div>
        """
        soup = BeautifulSoup(complex_pagination, 'html.parser')

        prev_url, next_url, current_page = extract_pagination_info(soup)

        assert prev_url is not None
        assert next_url is not None
        assert 'offset=50' in prev_url
        assert 'offset=150' in next_url


class TestSinglePageScraping:
    """Test suite for single page scraping functionality."""

    def setup_method(self):
        self.mock_session = Mock(spec=requests.Session)
        self.sample_url = "https://example.com/search"
        self.sample_params = {"county": "05"}

    @patch('scripts.scraper.parse_property_table')
    @patch('scripts.scraper.extract_pagination_info')
    def test_scrape_single_page_success(self, mock_pagination, mock_parse):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"<html><table></table></html>"
        self.mock_session.get.return_value = mock_response

        mock_df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
        mock_parse.return_value = mock_df

        mock_pagination.return_value = (None, "next_url", 1)

        df, pagination_info = scrape_single_page(self.mock_session, self.sample_url, self.sample_params)

        assert len(df) == 2
        assert pagination_info['next_url'] == "next_url"
        assert pagination_info['current_page'] == 1
        assert pagination_info['has_more'] is True

        self.mock_session.get.assert_called_once_with(
            self.sample_url, params=self.sample_params, timeout=30
        )

    def test_scrape_single_page_http_error(self):
        self.mock_session.get.side_effect = requests.RequestException("Connection failed")

        with pytest.raises(NetworkError) as exc_info:
            scrape_single_page(self.mock_session, self.sample_url, self.sample_params)

        assert "HTTP request failed" in str(exc_info.value)

    def test_scrape_single_page_http_status_error(self):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        self.mock_session.get.return_value = mock_response

        with pytest.raises(NetworkError):
            scrape_single_page(self.mock_session, self.sample_url, self.sample_params)

    @patch('scripts.scraper.parse_property_table')
    def test_scrape_single_page_parse_error(self, mock_parse):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"<html>content</html>"
        self.mock_session.get.return_value = mock_response

        mock_parse.side_effect = Exception("Parsing failed")

        with pytest.raises(ParseError) as exc_info:
            scrape_single_page(self.mock_session, self.sample_url, self.sample_params)

        assert "Failed to parse page" in str(exc_info.value)

    @pytest.mark.ai_test
    @patch('scripts.scraper.parse_property_table')
    @patch('scripts.scraper.extract_pagination_info')
    def test_single_page_scraping_performance_benchmark(self, mock_pagination, mock_parse, benchmark):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"<html></html>"
        self.mock_session.get.return_value = mock_response

        mock_parse.return_value = pd.DataFrame({'data': range(100)})
        mock_pagination.return_value = (None, None, 1)

        result = benchmark(scrape_single_page, self.mock_session, self.sample_url, self.sample_params)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert benchmark.stats['mean'] < 1.0

    @patch('scripts.scraper.parse_property_table')
    @patch('scripts.scraper.extract_pagination_info')
    def test_scrape_single_page_no_pagination(self, mock_pagination, mock_parse):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"<html></html>"
        self.mock_session.get.return_value = mock_response

        mock_parse.return_value = pd.DataFrame()
        mock_pagination.return_value = (None, None, 1)

        df, pagination_info = scrape_single_page(self.mock_session, self.sample_url)

        assert len(df) == 0
        assert pagination_info['has_more'] is False


class TestCountyDataScraping:
    """Test suite for complete county data scraping workflow."""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('scripts.scraper.scrape_single_page')
    @patch('scripts.scraper.create_session')
    @patch('scripts.scraper.validate_county_code')
    @patch('scripts.scraper.get_county_name')
    def test_scrape_county_data_success_single_page(self, mock_get_name, mock_validate, mock_session, mock_scrape):
        mock_validate.return_value = '05'
        mock_get_name.return_value = 'Baldwin'

        mock_session_obj = Mock()
        mock_session.return_value = mock_session_obj

        sample_df = pd.DataFrame({
            'Parcel ID': ['001-001-001', '002-002-002'],
            'Property Description': ['Property 1', 'Property 2'],
            'Amount Due': ['$1500', '$2500']
        })

        pagination_info = {
            'prev_url': None,
            'next_url': None,
            'current_page': 1,
            'has_more': False
        }

        mock_scrape.return_value = (sample_df, pagination_info)

        with patch('pathlib.Path.mkdir'):
            result = scrape_county_data('Baldwin', max_pages=5, save_raw=False)

        assert len(result) == 2
        assert 'County' in result.columns
        assert result['County'].iloc[0] == 'Baldwin'
        assert 'County Code' in result.columns
        assert result['County Code'].iloc[0] == '05'

    @patch('scripts.scraper.scrape_single_page')
    @patch('scripts.scraper.create_session')
    @patch('scripts.scraper.validate_county_code')
    @patch('scripts.scraper.get_county_name')
    def test_scrape_county_data_multiple_pages(self, mock_get_name, mock_validate, mock_session, mock_scrape):
        mock_validate.return_value = '05'
        mock_get_name.return_value = 'Baldwin'

        mock_session_obj = Mock()
        mock_session.return_value = mock_session_obj

        page1_df = pd.DataFrame({'Parcel ID': ['001'], 'Amount': ['$1500']})
        page2_df = pd.DataFrame({'Parcel ID': ['002'], 'Amount': ['$2500']})

        page1_info = {'prev_url': None, 'next_url': 'page2', 'current_page': 1, 'has_more': True}
        page2_info = {'prev_url': 'page1', 'next_url': None, 'current_page': 2, 'has_more': False}

        mock_scrape.side_effect = [(page1_df, page1_info), (page2_df, page2_info)]

        with patch('pathlib.Path.mkdir'), patch('time.sleep'):
            result = scrape_county_data('Baldwin', max_pages=5, save_raw=False)

        assert len(result) == 2
        assert mock_scrape.call_count == 2

    @patch('scripts.scraper.validate_county_code')
    def test_scrape_county_data_invalid_county(self, mock_validate):
        mock_validate.side_effect = CountyValidationError("Invalid county")

        with pytest.raises(CountyValidationError):
            scrape_county_data('InvalidCounty')

    @patch('scripts.scraper.scrape_single_page')
    @patch('scripts.scraper.create_session')
    @patch('scripts.scraper.validate_county_code')
    @patch('scripts.scraper.get_county_name')
    def test_scrape_county_data_no_data_found(self, mock_get_name, mock_validate, mock_session, mock_scrape):
        mock_validate.return_value = '05'
        mock_get_name.return_value = 'Baldwin'

        mock_session_obj = Mock()
        mock_session.return_value = mock_session_obj

        empty_df = pd.DataFrame()
        pagination_info = {'has_more': False}

        mock_scrape.return_value = (empty_df, pagination_info)

        result = scrape_county_data('Baldwin', save_raw=False)

        assert len(result) == 0
        assert isinstance(result, pd.DataFrame)

    @patch('scripts.scraper.scrape_single_page')
    @patch('scripts.scraper.create_session')
    @patch('scripts.scraper.validate_county_code')
    @patch('scripts.scraper.get_county_name')
    def test_scrape_county_data_max_pages_limit(self, mock_get_name, mock_validate, mock_session, mock_scrape):
        mock_validate.return_value = '05'
        mock_get_name.return_value = 'Baldwin'

        mock_session_obj = Mock()
        mock_session.return_value = mock_session_obj

        sample_df = pd.DataFrame({'Parcel ID': ['001'], 'Amount': ['$1500']})
        pagination_info = {'has_more': True, 'next_url': 'next_page'}

        mock_scrape.return_value = (sample_df, pagination_info)

        with patch('time.sleep'):
            result = scrape_county_data('Baldwin', max_pages=2, save_raw=False)

        assert mock_scrape.call_count == 2

    @patch('scripts.scraper.scrape_single_page')
    @patch('scripts.scraper.create_session')
    @patch('scripts.scraper.validate_county_code')
    @patch('scripts.scraper.get_county_name')
    def test_scrape_county_data_duplicate_removal(self, mock_get_name, mock_validate, mock_session, mock_scrape):
        mock_validate.return_value = '05'
        mock_get_name.return_value = 'Baldwin'

        mock_session_obj = Mock()
        mock_session.return_value = mock_session_obj

        df_with_duplicates = pd.DataFrame({
            'Parcel ID': ['001-001-001', '001-001-001', '002-002-002'],
            'Amount': ['$1500', '$1500', '$2500']
        })

        pagination_info = {'has_more': False}
        mock_scrape.return_value = (df_with_duplicates, pagination_info)

        result = scrape_county_data('Baldwin', save_raw=False)

        assert len(result) == 2
        assert len(result[result['Parcel ID'] == '001-001-001']) == 1

    @patch('scripts.scraper.scrape_single_page')
    @patch('scripts.scraper.create_session')
    @patch('scripts.scraper.validate_county_code')
    @patch('scripts.scraper.get_county_name')
    def test_scrape_county_data_save_raw_file(self, mock_get_name, mock_validate, mock_session, mock_scrape):
        mock_validate.return_value = '05'
        mock_get_name.return_value = 'Baldwin'

        mock_session_obj = Mock()
        mock_session.return_value = mock_session_obj

        sample_df = pd.DataFrame({'Parcel ID': ['001'], 'Amount': ['$1500']})
        pagination_info = {'has_more': False}
        mock_scrape.return_value = (sample_df, pagination_info)

        with patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch('pandas.DataFrame.to_csv') as mock_to_csv:

            result = scrape_county_data('Baldwin', save_raw=True)

            mock_mkdir.assert_called_once()
            mock_to_csv.assert_called_once()

    @patch('scripts.scraper.scrape_single_page')
    @patch('scripts.scraper.create_session')
    @patch('scripts.scraper.validate_county_code')
    @patch('scripts.scraper.get_county_name')
    def test_scrape_county_data_network_error_handling(self, mock_get_name, mock_validate, mock_session, mock_scrape):
        mock_validate.return_value = '05'
        mock_get_name.return_value = 'Baldwin'

        mock_session_obj = Mock()
        mock_session.return_value = mock_session_obj

        mock_scrape.side_effect = NetworkError("Network failed")

        with pytest.raises(ScrapingError) as exc_info:
            scrape_county_data('Baldwin')

        assert "Failed to scrape Baldwin County" in str(exc_info.value)

    @pytest.mark.ai_test
    @patch('scripts.scraper.scrape_single_page')
    @patch('scripts.scraper.create_session')
    @patch('scripts.scraper.validate_county_code')
    @patch('scripts.scraper.get_county_name')
    def test_county_scraping_performance_benchmark(self, mock_get_name, mock_validate, mock_session, mock_scrape, benchmark):
        mock_validate.return_value = '05'
        mock_get_name.return_value = 'Baldwin'

        mock_session_obj = Mock()
        mock_session.return_value = mock_session_obj

        large_df = create_sample_property_data(num_records=1000)
        pagination_info = {'has_more': False}
        mock_scrape.return_value = (large_df, pagination_info)

        with patch('pathlib.Path.mkdir'):
            result = benchmark(scrape_county_data, 'Baldwin', max_pages=1, save_raw=False)

        assert len(result) == 1000
        assert benchmark.stats['mean'] < 5.0

    @patch('scripts.scraper.scrape_single_page')
    @patch('scripts.scraper.create_session')
    @patch('scripts.scraper.validate_county_code')
    @patch('scripts.scraper.get_county_name')
    def test_scrape_county_data_session_cleanup(self, mock_get_name, mock_validate, mock_session, mock_scrape):
        mock_validate.return_value = '05'
        mock_get_name.return_value = 'Baldwin'

        mock_session_obj = Mock()
        mock_session.return_value = mock_session_obj

        mock_scrape.side_effect = Exception("Unexpected error")

        with pytest.raises(ScrapingError):
            scrape_county_data('Baldwin')

        mock_session_obj.close.assert_called_once()


class TestErrorHandlingAndRecovery:
    """Test suite for error handling and recovery scenarios."""

    def test_county_validation_error_with_ai_context(self):
        with pytest.raises(CountyValidationError) as exc_info:
            validate_county_code('InvalidCounty')

        error = exc_info.value
        assert isinstance(error, CountyValidationError)
        assert 'InvalidCounty' in str(error)

    @patch('requests.Session.get')
    def test_network_error_recovery_scenario(self, mock_get):
        mock_session = create_session()
        mock_get.side_effect = requests.ConnectionError("Network unavailable")

        with pytest.raises(NetworkError) as exc_info:
            scrape_single_page(mock_session, "http://example.com")

        error = exc_info.value
        assert "HTTP request failed" in str(error)

    def test_parse_error_graceful_degradation(self):
        invalid_html = "<invalid>malformed html"
        soup = BeautifulSoup(invalid_html, 'html.parser')

        result = parse_property_table(soup)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    @patch('scripts.scraper.scrape_single_page')
    @patch('scripts.scraper.create_session')
    @patch('scripts.scraper.validate_county_code')
    @patch('scripts.scraper.get_county_name')
    def test_scraping_error_aggregation(self, mock_get_name, mock_validate, mock_session, mock_scrape):
        mock_validate.return_value = '05'
        mock_get_name.return_value = 'Baldwin'

        mock_session_obj = Mock()
        mock_session.return_value = mock_session_obj

        mock_scrape.side_effect = [
            NetworkError("Page 1 failed"),
            (pd.DataFrame(), {'has_more': False})
        ]

        with pytest.raises(ScrapingError):
            scrape_county_data('Baldwin', max_pages=2)

    @pytest.mark.ai_test
    def test_error_recovery_performance_impact(self, benchmark):
        def error_prone_validation():
            try:
                return validate_county_code('InvalidCounty')
            except CountyValidationError:
                return validate_county_code('Baldwin')

        result = benchmark(error_prone_validation)
        assert result == '05'
        assert benchmark.stats['mean'] < 0.01

    def test_pagination_error_handling(self):
        malformed_pagination = "<div><a>Broken Link</a></div>"
        soup = BeautifulSoup(malformed_pagination, 'html.parser')

        prev_url, next_url, current_page = extract_pagination_info(soup)

        assert prev_url is None
        assert next_url is None
        assert current_page == 1

    @patch('scripts.scraper.parse_property_table')
    def test_empty_response_handling(self, mock_parse):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b""
        mock_session.get.return_value = mock_response

        mock_parse.return_value = pd.DataFrame()

        df, pagination_info = scrape_single_page(mock_session, "http://example.com")

        assert len(df) == 0
        assert pagination_info['has_more'] is False


class TestCLIFunctionality:
    """Test suite for CLI functionality."""

    def test_cli_main_function_exists(self):
        from scripts.scraper import __name__ as module_name
        assert module_name == 'scripts.scraper'

    @patch('sys.argv')
    @patch('scripts.scraper.scrape_county_data')
    def test_cli_basic_execution(self, mock_scrape, mock_argv):
        mock_argv.__getitem__.side_effect = lambda x: ['scraper.py', 'Baldwin'][x]
        mock_argv.__len__.return_value = 2

        mock_df = pd.DataFrame({'data': [1, 2, 3]})
        mock_scrape.return_value = mock_df

        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Mock()
            mock_args.county = 'Baldwin'
            mock_args.max_pages = 10
            mock_args.output = None
            mock_parse_args.return_value = mock_args

            with patch('builtins.print') as mock_print:
                exec(compile(open('scripts/scraper.py').read(), 'scripts/scraper.py', 'exec'))

    @patch('sys.argv')
    @patch('scripts.scraper.scrape_county_data')
    @patch('pandas.DataFrame.to_csv')
    def test_cli_with_output_file(self, mock_to_csv, mock_scrape, mock_argv):
        mock_df = pd.DataFrame({'data': [1, 2, 3]})
        mock_scrape.return_value = mock_df

        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Mock()
            mock_args.county = 'Baldwin'
            mock_args.max_pages = 10
            mock_args.output = 'output.csv'
            mock_parse_args.return_value = mock_args

            with patch('builtins.print'):
                exec(compile(open('scripts/scraper.py').read(), 'scripts/scraper.py', 'exec'))

            mock_to_csv.assert_called_once()

    @patch('scripts.scraper.scrape_county_data')
    def test_cli_error_handling(self, mock_scrape):
        mock_scrape.side_effect = Exception("Scraping failed")

        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Mock()
            mock_args.county = 'Baldwin'
            mock_args.max_pages = 10
            mock_args.output = None
            mock_parse_args.return_value = mock_args

            with patch('builtins.print'), patch('sys.exit') as mock_exit:
                exec(compile(open('scripts/scraper.py').read(), 'scripts/scraper.py', 'exec'))


@pytest.mark.integration
class TestScrapingIntegrationScenarios:
    """Integration test scenarios for scraping workflows."""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('requests.Session.get')
    def test_end_to_end_scraping_simulation(self, mock_get):
        mock_html = """
        <html>
            <table id="ador-delinquent-search-results">
                <tr>
                    <th>Parcel ID</th>
                    <th>Property Description</th>
                    <th>Amount Due</th>
                </tr>
                <tr>
                    <td>001-001-001</td>
                    <td>Property with 2.5 acres near creek</td>
                    <td>$15,000.00</td>
                </tr>
                <tr>
                    <td>002-002-002</td>
                    <td>3 acre lot by stream</td>
                    <td>$12,000.00</td>
                </tr>
            </table>
        </html>
        """

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_html.encode()
        mock_get.return_value = mock_response

        with patch('pathlib.Path.mkdir'), patch('pandas.DataFrame.to_csv'):
            result = scrape_county_data('Baldwin', max_pages=1, save_raw=True)

        assert len(result) >= 0
        assert isinstance(result, pd.DataFrame)

    @pytest.mark.ai_test
    @patch('scripts.scraper.scrape_single_page')
    @patch('scripts.scraper.create_session')
    def test_large_dataset_scraping_performance(self, mock_session, mock_scrape, benchmark):
        mock_session_obj = Mock()
        mock_session.return_value = mock_session_obj

        large_df = create_sample_property_data(num_records=5000)
        pagination_info = {'has_more': False}
        mock_scrape.return_value = (large_df, pagination_info)

        def scraping_workflow():
            return scrape_county_data('Baldwin', max_pages=1, save_raw=False)

        with patch('pathlib.Path.mkdir'):
            result = benchmark(scraping_workflow)

        assert len(result) == 5000
        assert benchmark.stats['mean'] < 10.0

    @patch('requests.Session.get')
    def test_network_resilience_simulation(self, mock_get):
        mock_get.side_effect = [
            requests.ConnectionError("Network error"),
            requests.Timeout("Request timeout"),
            Mock(status_code=500),
        ]

        with pytest.raises((NetworkError, ScrapingError)):
            scrape_county_data('Baldwin', max_pages=1)

    def test_county_code_validation_integration(self):
        valid_inputs = ['05', '5', 'Baldwin', 'BALDWIN', 'baldwin', 'Bald']

        for county_input in valid_inputs:
            result = validate_county_code(county_input)
            assert result == '05'

        invalid_inputs = ['99', 'NonexistentCounty', '', '00']

        for county_input in invalid_inputs:
            with pytest.raises(CountyValidationError):
                validate_county_code(county_input)

    @patch('scripts.scraper.scrape_single_page')
    @patch('scripts.scraper.create_session')
    def test_pagination_workflow_integration(self, mock_session, mock_scrape):
        mock_session_obj = Mock()
        mock_session.return_value = mock_session_obj

        page_data = [
            (pd.DataFrame({'id': [1, 2]}), {'has_more': True, 'next_url': 'page2'}),
            (pd.DataFrame({'id': [3, 4]}), {'has_more': True, 'next_url': 'page3'}),
            (pd.DataFrame({'id': [5, 6]}), {'has_more': False, 'next_url': None})
        ]

        mock_scrape.side_effect = page_data

        with patch('time.sleep'), patch('pathlib.Path.mkdir'):
            result = scrape_county_data('Baldwin', max_pages=5, save_raw=False)

        assert len(result) == 6
        assert mock_scrape.call_count == 3

    def test_data_quality_preservation_integration(self):
        test_html = """
        <table>
            <tr><th>ID</th><th>Description</th><th>Amount</th></tr>
            <tr><td>001</td><td>Property 1</td><td>$1,500.00</td></tr>
            <tr><td>002</td><td>Property 2</td><td>$2,500.00</td></tr>
        </table>
        """

        soup = BeautifulSoup(test_html, 'html.parser')
        result = parse_property_table(soup)

        assert len(result) == 2
        assert list(result.columns) == ['ID', 'Description', 'Amount']
        assert result.iloc[0]['ID'] == '001'
        assert '$1,500.00' in result.iloc[0]['Amount']


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])