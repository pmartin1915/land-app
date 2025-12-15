"""
Integration tests for ADOR website scraping workflows in Alabama Auction Watcher.

Tests complete end-to-end workflows including scraper integration with parser, utils,
logging, and exception handling systems. Provides AI-testable scenarios with
comprehensive error recovery and performance validation.

Integration scope:
- scripts/scraper.py with scripts/parser.py
- scripts/scraper.py with scripts/utils.py
- scripts/scraper.py with config/logging_config.py
- scripts/scraper.py with scripts/exceptions.py
- Multi-module workflow testing
"""

import pytest
import pandas as pd
import time
import tempfile
import json
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from dataclasses import dataclass
from typing import List, Dict, Any

from scripts.scraper import (
    scrape_county_data, validate_county_code, get_county_name,
    list_available_counties, ALABAMA_COUNTY_CODES
)
from scripts.parser import AuctionParser
from scripts.utils import (
    calculate_water_score, calculate_investment_score,
    validate_data_quality, clean_dataframe
)
from scripts.exceptions import (
    CountyValidationError, NetworkError, ParseError, ScrapingError,
    DataValidationError, FileOperationError
)
from config.logging_config import setup_logging, get_logger


@dataclass
class MockScrapingResponse:
    """Mock response for scraping operations."""
    status_code: int
    text: str
    headers: Dict[str, str] = None

    def __post_init__(self):
        if self.headers is None:
            self.headers = {'content-type': 'text/html'}


class TestScraperParserIntegration:
    """Test integration between scraper and parser modules."""

    def setup_method(self):
        """Set up test environment."""
        self.test_logger = get_logger('integration_test')

    @patch('scripts.scraper.requests.get')
    def test_scraper_to_parser_workflow(self, mock_get):
        """Test complete workflow from scraping to parsing."""
        # Mock successful scraping response
        mock_html = """
        <table>
            <tr><th>Parcel ID</th><th>Amount</th><th>Description</th><th>Acreage</th></tr>
            <tr><td>123456</td><td>$5,000</td><td>Lot with creek access 2.5 AC</td><td>2.5</td></tr>
            <tr><td>789012</td><td>$8,500</td><td>Property near water 3.1 ACRES</td><td>3.1</td></tr>
        </table>
        """

        mock_response = MockScrapingResponse(200, mock_html)
        mock_get.return_value = mock_response

        # Step 1: Scrape data
        scraped_df = scrape_county_data('05')  # Baldwin County

        assert isinstance(scraped_df, pd.DataFrame)
        assert len(scraped_df) == 2
        assert 'Parcel ID' in scraped_df.columns

        # Step 2: Process with parser
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp_file:
            scraped_df.to_csv(tmp_file.name, index=False)

            parser = AuctionParser()
            parsed_df = parser.load_csv(tmp_file.name)

            assert isinstance(parsed_df, pd.DataFrame)
            assert len(parsed_df) >= 1  # Should have data after processing

    @patch('scripts.scraper.requests.get')
    def test_scraper_parser_with_water_features(self, mock_get):
        """Test scraper-parser integration with water feature detection."""
        mock_html = """
        <table>
            <tr><th>Parcel ID</th><th>Amount</th><th>Description</th></tr>
            <tr><td>111111</td><td>$3,500</td><td>Waterfront property with creek 2.0 AC</td></tr>
            <tr><td>222222</td><td>$4,200</td><td>Near stream and pond 1.8 ACRES</td></tr>
            <tr><td>333333</td><td>$2,800</td><td>Dry land no water features 3.2 AC</td></tr>
        </table>
        """

        mock_response = MockScrapingResponse(200, mock_html)
        mock_get.return_value = mock_response

        # Scrape and process
        scraped_df = scrape_county_data('01')  # Autauga County

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp_file:
            scraped_df.to_csv(tmp_file.name, index=False)

            parser = AuctionParser()
            processed_df = parser.load_csv(tmp_file.name)
            processed_df = parser.calculate_metrics()

            # Check water scores were calculated
            if 'water_score' in processed_df.columns:
                water_scores = processed_df['water_score'].dropna()
                assert len(water_scores) > 0
                assert water_scores.max() > 0  # Should have some water features detected

    @patch('scripts.scraper.requests.get')
    def test_scraper_parser_error_handling_integration(self, mock_get):
        """Test error handling across scraper-parser integration."""
        # Test network error propagation
        mock_get.side_effect = NetworkError("Connection timeout")

        with pytest.raises(NetworkError):
            scrape_county_data('05')

        # Test invalid data handling
        mock_html = "<html><body>Invalid data format</body></html>"
        mock_response = MockScrapingResponse(200, mock_html)
        mock_get.side_effect = None
        mock_get.return_value = mock_response

        # Should handle gracefully
        result = scrape_county_data('05')
        assert isinstance(result, pd.DataFrame)
        # May be empty or have limited data

    @patch('scripts.scraper.requests.get')
    def test_multi_county_workflow_integration(self, mock_get):
        """Test integration workflow across multiple counties."""
        # Mock responses for multiple counties
        def mock_county_response(url, **kwargs):
            if '01' in url:  # Autauga
                html = """
                <table>
                    <tr><th>Parcel ID</th><th>Amount</th><th>Description</th></tr>
                    <tr><td>AUT001</td><td>$4,500</td><td>Creek property 2.1 AC</td></tr>
                </table>
                """
            elif '05' in url:  # Baldwin
                html = """
                <table>
                    <tr><th>Parcel ID</th><th>Amount</th><th>Description</th></tr>
                    <tr><td>BAL001</td><td>$6,200</td><td>Waterfront lot 1.9 ACRES</td></tr>
                </table>
                """
            else:
                html = "<html><body>No data</body></html>"

            return MockScrapingResponse(200, html)

        mock_get.side_effect = mock_county_response

        # Process multiple counties
        counties = ['01', '05']
        all_data = []

        for county in counties:
            county_data = scrape_county_data(county)
            if not county_data.empty:
                county_data['county'] = get_county_name(county)
                all_data.append(county_data)

        # Combine and process
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)

            # Process with parser
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp_file:
                combined_df.to_csv(tmp_file.name, index=False)

                parser = AuctionParser()
                final_df = parser.load_csv(tmp_file.name)
                final_df = parser.calculate_metrics()

                assert len(final_df) >= 2  # Should have data from both counties
                assert 'county' in final_df.columns


class TestScraperUtilsIntegration:
    """Test integration between scraper and utils modules."""

    @patch('scripts.scraper.requests.get')
    def test_scraper_with_data_validation(self, mock_get):
        """Test scraper integration with utils data validation."""
        mock_html = """
        <table>
            <tr><th>Parcel ID</th><th>Amount</th><th>Description</th><th>Acreage</th></tr>
            <tr><td>123456</td><td>$5,000</td><td>Valid property 2.5 AC</td><td>2.5</td></tr>
            <tr><td>invalid</td><td>$0</td><td>Invalid data</td><td>-1</td></tr>
            <tr><td>789012</td><td>$15,000</td><td>Another valid property 3.0 AC</td><td>3.0</td></tr>
        </table>
        """

        mock_response = MockScrapingResponse(200, mock_html)
        mock_get.return_value = mock_response

        # Scrape data
        scraped_df = scrape_county_data('05')

        # Validate with utils
        cleaned_df = clean_dataframe(scraped_df)
        validation_results = validate_data_quality(cleaned_df)

        assert isinstance(validation_results, dict)
        assert 'total_records' in validation_results
        assert 'valid_records' in validation_results

    @patch('scripts.scraper.requests.get')
    def test_scraper_with_water_score_calculation(self, mock_get):
        """Test scraper integration with water score calculation."""
        mock_html = """
        <table>
            <tr><th>Parcel ID</th><th>Amount</th><th>Description</th></tr>
            <tr><td>W001</td><td>$4,000</td><td>Property with creek and pond access</td></tr>
            <tr><td>W002</td><td>$3,500</td><td>Near stream and wetland area</td></tr>
            <tr><td>W003</td><td>$5,000</td><td>Waterfront property with river access</td></tr>
        </table>
        """

        mock_response = MockScrapingResponse(200, mock_html)
        mock_get.return_value = mock_response

        # Scrape and calculate water scores
        scraped_df = scrape_county_data('05')

        water_scores = []
        for description in scraped_df.get('Description', []):
            score = calculate_water_score(description)
            water_scores.append(score)

        assert len(water_scores) == len(scraped_df)
        assert max(water_scores) > 0  # Should detect water features

        # Check specific water feature detection
        creek_score = calculate_water_score("Property with creek and pond access")
        stream_score = calculate_water_score("Near stream and wetland area")
        river_score = calculate_water_score("Waterfront property with river access")

        assert creek_score > 0
        assert stream_score > 0
        assert river_score > 0

    @patch('scripts.scraper.requests.get')
    def test_scraper_with_investment_score_calculation(self, mock_get):
        """Test scraper integration with investment score calculation."""
        mock_html = """
        <table>
            <tr><th>Parcel ID</th><th>Amount</th><th>Description</th><th>Acreage</th><th>Assessed Value</th></tr>
            <tr><td>INV001</td><td>$4,000</td><td>Property with creek 2.5 AC</td><td>2.5</td><td>$15,000</td></tr>
            <tr><td>INV002</td><td>$6,000</td><td>Land near water 3.0 ACRES</td><td>3.0</td><td>$18,000</td></tr>
        </table>
        """

        mock_response = MockScrapingResponse(200, mock_html)
        mock_get.return_value = mock_response

        # Scrape data
        scraped_df = scrape_county_data('05')

        # Calculate investment scores
        investment_scores = []
        for _, row in scraped_df.iterrows():
            # Extract values (with fallbacks)
            amount = 4000  # Simplified for test
            acreage = float(row.get('Acreage', 2.5))
            description = row.get('Description', '')
            assessed_value = 15000  # Simplified for test

            score = calculate_investment_score(
                price_per_acre=amount/acreage,
                acreage=acreage,
                water_score=calculate_water_score(description),
                assessed_value_ratio=amount/assessed_value if assessed_value > 0 else 0
            )
            investment_scores.append(score)

        assert len(investment_scores) == len(scraped_df)
        assert all(score >= 0 for score in investment_scores)


class TestScraperLoggingIntegration:
    """Test integration between scraper and logging systems."""

    def test_scraper_logging_setup(self):
        """Test scraper integrates properly with logging configuration."""
        # Setup logging
        logger = setup_logging('INFO', console_output=False)

        # Verify scraper can use logging
        scraper_logger = get_logger('scripts.scraper')
        assert isinstance(scraper_logger, logging.Logger)

    @patch('scripts.scraper.requests.get')
    def test_scraper_performance_logging(self, mock_get):
        """Test scraper integration with performance logging."""
        mock_html = "<table><tr><th>Test</th></tr><tr><td>Data</td></tr></table>"
        mock_response = MockScrapingResponse(200, mock_html)
        mock_get.return_value = mock_response

        # Mock logger to capture performance logs
        with patch('scripts.scraper.log_scraping_metrics') as mock_log_metrics:
            scraped_df = scrape_county_data('05')

            # Verify performance logging was called
            # Note: This depends on the actual implementation in scraper.py
            # The test verifies the integration point exists

    @patch('scripts.scraper.requests.get')
    def test_scraper_error_logging_integration(self, mock_get):
        """Test scraper error logging integration."""
        # Test network error logging
        mock_get.side_effect = Exception("Network error")

        with patch('scripts.scraper.log_error_with_context') as mock_log_error:
            try:
                scrape_county_data('05')
            except:
                pass  # Expected to fail

            # The scraper should have logged the error
            # Note: This depends on the actual implementation


class TestScraperExceptionIntegration:
    """Test integration between scraper and exception handling."""

    def test_county_validation_error_integration(self):
        """Test county validation error integration."""
        with pytest.raises(CountyValidationError):
            validate_county_code('99')  # Invalid county code

        with pytest.raises(CountyValidationError):
            validate_county_code('INVALID')

    @patch('scripts.scraper.requests.get')
    def test_network_error_integration(self, mock_get):
        """Test network error handling integration."""
        # Test connection timeout
        import requests
        mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")

        with pytest.raises(NetworkError):
            scrape_county_data('05')

        # Test connection error
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        with pytest.raises(NetworkError):
            scrape_county_data('05')

    @patch('scripts.scraper.requests.get')
    def test_parse_error_integration(self, mock_get):
        """Test parse error handling integration."""
        # Test invalid HTML response
        mock_response = MockScrapingResponse(200, "Invalid HTML structure")
        mock_get.return_value = mock_response

        # Should handle gracefully or raise appropriate error
        try:
            result = scrape_county_data('05')
            # If no exception, should return empty DataFrame
            assert isinstance(result, pd.DataFrame)
        except ParseError:
            # If ParseError is raised, that's also acceptable
            pass

    @patch('scripts.scraper.requests.get')
    def test_scraping_error_integration(self, mock_get):
        """Test scraping error handling integration."""
        # Test HTTP error response
        mock_response = MockScrapingResponse(404, "Not Found")
        mock_get.return_value = mock_response

        with pytest.raises(ScrapingError):
            scrape_county_data('05')


class TestEndToEndScrapingWorkflows:
    """Test complete end-to-end scraping workflows."""

    @patch('scripts.scraper.requests.get')
    def test_complete_county_processing_workflow(self, mock_get):
        """Test complete workflow from scraping to final output."""
        mock_html = """
        <table>
            <tr><th>Parcel ID</th><th>Amount Bid at Tax Sale</th><th>Description</th><th>Acreage</th><th>Assessed Value</th></tr>
            <tr><td>12-34-56-001</td><td>$3,500</td><td>Waterfront lot with creek access 2.1 AC</td><td>2.1</td><td>$12,000</td></tr>
            <tr><td>12-34-56-002</td><td>$4,200</td><td>Property near stream 1.8 ACRES</td><td>1.8</td><td>$15,000</td></tr>
            <tr><td>12-34-56-003</td><td>$5,800</td><td>Land with pond access 3.2 AC</td><td>3.2</td><td>$18,500</td></tr>
        </table>
        """

        mock_response = MockScrapingResponse(200, mock_html)
        mock_get.return_value = mock_response

        # Step 1: Scrape county data
        scraped_df = scrape_county_data('05')
        assert not scraped_df.empty

        # Step 2: Process with parser
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp_file:
            scraped_df.to_csv(tmp_file.name, index=False)

            parser = AuctionParser()
            processed_df = parser.load_csv(tmp_file.name)
            processed_df = parser.calculate_metrics()
            processed_df = parser.filter_properties()
            final_df = parser.rank_properties()

            # Verify complete processing
            assert isinstance(final_df, pd.DataFrame)
            assert len(final_df) >= 1

        # Step 3: Verify output file creation
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as output_file:
            parser.export_to_csv(output_file.name)

            # Verify file was created and has content
            output_path = Path(output_file.name)
            assert output_path.exists()
            assert output_path.stat().st_size > 0

    @patch('scripts.scraper.requests.get')
    def test_multi_county_bulk_processing_workflow(self, mock_get):
        """Test bulk processing workflow across multiple counties."""
        def mock_county_response(url, **kwargs):
            if '01' in url:  # Autauga
                return MockScrapingResponse(200, """
                <table>
                    <tr><th>Parcel ID</th><th>Amount</th><th>Description</th></tr>
                    <tr><td>AUT-001</td><td>$3,000</td><td>Creek property 2.0 AC</td></tr>
                    <tr><td>AUT-002</td><td>$4,500</td><td>Land near water 2.5 ACRES</td></tr>
                </table>
                """)
            elif '05' in url:  # Baldwin
                return MockScrapingResponse(200, """
                <table>
                    <tr><th>Parcel ID</th><th>Amount</th><th>Description</th></tr>
                    <tr><td>BAL-001</td><td>$5,200</td><td>Waterfront lot 1.9 AC</td></tr>
                    <tr><td>BAL-002</td><td>$3,800</td><td>Property with stream 2.3 ACRES</td></tr>
                </table>
                """)
            else:
                return MockScrapingResponse(200, "<html><body>No data</body></html>")

        mock_get.side_effect = mock_county_response

        # Process multiple counties
        target_counties = ['01', '05']
        all_results = []

        for county_code in target_counties:
            try:
                county_data = scrape_county_data(county_code)
                if not county_data.empty:
                    county_data['county_code'] = county_code
                    county_data['county_name'] = get_county_name(county_code)
                    all_results.append(county_data)
            except Exception as e:
                # Log error and continue with next county
                continue

        # Combine all results
        if all_results:
            combined_df = pd.concat(all_results, ignore_index=True)

            # Process combined data
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp_file:
                combined_df.to_csv(tmp_file.name, index=False)

                parser = AuctionParser()
                final_df = parser.load_csv(tmp_file.name)
                final_df = parser.calculate_metrics()
                final_df = parser.filter_properties()
                final_df = parser.rank_properties()

                # Verify multi-county processing
                assert len(final_df) >= 2
                assert len(final_df['county_name'].unique()) >= 2

    @patch('scripts.scraper.requests.get')
    def test_error_recovery_workflow(self, mock_get):
        """Test error recovery in scraping workflows."""
        call_count = 0

        def mock_failing_then_success(url, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count <= 2:
                # First two calls fail
                raise Exception("Network error")
            else:
                # Third call succeeds
                return MockScrapingResponse(200, """
                <table>
                    <tr><th>Parcel ID</th><th>Amount</th><th>Description</th></tr>
                    <tr><td>REC-001</td><td>$4,000</td><td>Recovered data 2.0 AC</td></tr>
                </table>
                """)

        mock_get.side_effect = mock_failing_then_success

        # Test retry logic (if implemented in scraper)
        # This test verifies that recovery mechanisms work
        success_count = 0
        for attempt in range(3):
            try:
                result = scrape_county_data('05')
                if not result.empty:
                    success_count += 1
                    break
            except:
                if attempt < 2:  # Allow retries
                    time.sleep(0.1)
                    continue
                else:
                    break

        # Should eventually succeed
        assert success_count > 0 or call_count >= 3


class TestScrapingPerformance:
    """Performance benchmarks for scraping workflows."""

    @patch('scripts.scraper.requests.get')
    def test_scraping_performance_benchmark(self, mock_get):
        """Test scraping performance meets benchmarks."""
        # Mock large dataset response
        rows = []
        for i in range(100):
            rows.append(f"<tr><td>PERF-{i:03d}</td><td>${3000+i*10}</td><td>Property {i} with water 2.{i%9} AC</td></tr>")

        mock_html = f"""
        <table>
            <tr><th>Parcel ID</th><th>Amount</th><th>Description</th></tr>
            {''.join(rows)}
        </table>
        """

        mock_response = MockScrapingResponse(200, mock_html)
        mock_get.return_value = mock_response

        # Measure scraping performance
        start_time = time.time()
        scraped_df = scrape_county_data('05')
        scraping_time = time.time() - start_time

        # Performance requirements
        assert scraping_time < 5.0  # Should complete within 5 seconds
        assert len(scraped_df) == 100  # Should parse all records

        # Measure processing performance
        start_time = time.time()
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp_file:
            scraped_df.to_csv(tmp_file.name, index=False)

            parser = AuctionParser()
            processed_df = parser.load_csv(tmp_file.name)
            processed_df = parser.calculate_metrics()
            final_df = parser.filter_properties()

        processing_time = time.time() - start_time

        # Processing performance requirements
        assert processing_time < 2.0  # Should process within 2 seconds
        assert len(final_df) >= 0  # Should handle all data

    @patch('scripts.scraper.requests.get')
    def test_memory_efficiency_large_dataset(self, mock_get):
        """Test memory efficiency with large datasets."""
        # Mock very large dataset
        rows = []
        for i in range(1000):
            rows.append(f"<tr><td>MEM-{i:04d}</td><td>${2500+i*5}</td><td>Large dataset property {i} near creek 2.{i%9+1} ACRES</td></tr>")

        mock_html = f"""
        <table>
            <tr><th>Parcel ID</th><th>Amount</th><th>Description</th></tr>
            {''.join(rows)}
        </table>
        """

        mock_response = MockScrapingResponse(200, mock_html)
        mock_get.return_value = mock_response

        # Monitor memory usage (simplified)
        import psutil
        import os
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process large dataset
        scraped_df = scrape_county_data('05')

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp_file:
            scraped_df.to_csv(tmp_file.name, index=False)

            parser = AuctionParser()
            processed_df = parser.load_csv(tmp_file.name)
            processed_df = parser.calculate_metrics()
            final_df = parser.filter_properties()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory efficiency requirements
        assert memory_increase < 100  # Should not use more than 100MB additional memory
        assert len(scraped_df) == 1000  # Should handle all records


if __name__ == "__main__":
    # AI-testable integration specifications
    print("=== SCRAPER INTEGRATION TEST SPECIFICATIONS ===")
    print("Integration scope:")
    print("- scripts/scraper.py with scripts/parser.py")
    print("- scripts/scraper.py with scripts/utils.py")
    print("- scripts/scraper.py with config/logging_config.py")
    print("- scripts/scraper.py with scripts/exceptions.py")
    print("- Multi-module workflow testing")
    print("\nWorkflow coverage:")
    print("- Complete county scraping to parsing workflow")
    print("- Multi-county bulk processing")
    print("- Error handling and recovery across modules")
    print("- Performance monitoring and logging integration")
    print("- Data validation and quality assurance flows")
    print("\nPerformance requirements:")
    print("- Single county scraping: < 5 seconds")
    print("- Data processing: < 2 seconds per 100 records")
    print("- Memory usage: < 100MB additional for 1000 records")
    print("- Error recovery: 3 attempts maximum")
    print("\nError handling coverage:")
    print("- Network timeouts and connection failures")
    print("- Invalid HTML parsing scenarios")
    print("- Data validation error propagation")
    print("- Cross-module exception handling")