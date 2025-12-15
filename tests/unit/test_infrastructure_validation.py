"""
Infrastructure validation tests to verify the AI-testable framework is working correctly.

These tests validate that the testing infrastructure itself is functioning
and can be reliably used by AI systems for automated testing.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

# Import the test fixtures and utilities
from tests.conftest import PropertyDataFactory
from scripts.utils import normalize_price, find_column_mapping
from scripts.exceptions import DataValidationError, CountyValidationError


class TestInfrastructureValidation:
    """Test class to validate the testing infrastructure."""

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_fixture_loading(self, sample_csv_data, property_factory):
        """Validate that test fixtures are loading correctly."""
        # Test sample CSV data fixture
        assert not sample_csv_data.empty
        assert len(sample_csv_data) == 3
        assert 'Parcel ID' in sample_csv_data.columns
        assert 'Amount Bid at Tax Sale' in sample_csv_data.columns

        # Test property factory
        test_property = property_factory()
        assert hasattr(test_property, 'parcel_id')
        assert hasattr(test_property, 'amount')
        assert hasattr(test_property, 'acreage')

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_ai_test_validator(self, ai_test_validator):
        """Validate that AI test validation functions work."""
        # Test error structure validation
        valid_error = {
            "code": "TEST_001",
            "category": "network",
            "severity": "medium",
            "context": {"test": "data"},
            "suggested_actions": ["retry", "check_connection"]
        }
        assert ai_test_validator.validate_error_structure(valid_error)

        # Test invalid error structure
        invalid_error = {"code": "TEST_001"}
        assert not ai_test_validator.validate_error_structure(invalid_error)

        # Test performance metrics validation
        valid_metrics = {
            "duration": 1.5,
            "records_processed": 100,
            "records_per_second": 66.7
        }
        assert ai_test_validator.validate_performance_metrics(valid_metrics)

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_schema_validation(self, test_schemas):
        """Validate that JSON schemas are properly defined."""
        # Test that schemas exist
        assert "property_record" in test_schemas
        assert "error_response" in test_schemas
        assert "performance_metrics" in test_schemas

        # Test schema structure
        property_schema = test_schemas["property_record"]
        assert property_schema["type"] == "object"
        assert "required" in property_schema
        assert "parcel_id" in property_schema["required"]

    @pytest.mark.unit
    @pytest.mark.error_handling
    def test_custom_exception_handling(self):
        """Test that custom exceptions work with AI-friendly error codes."""
        # Test CountyValidationError
        with pytest.raises(CountyValidationError) as exc_info:
            raise CountyValidationError("99")

        error = exc_info.value
        assert "Invalid county '99'" in str(error)
        assert hasattr(error, 'county_input')
        assert error.county_input == "99"

        # Test DataValidationError
        with pytest.raises(DataValidationError) as exc_info:
            raise DataValidationError("Invalid data", field="test_field", value="bad_value")

        error = exc_info.value
        assert hasattr(error, 'field')
        assert hasattr(error, 'value')
        assert error.field == "test_field"
        assert error.value == "bad_value"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_mock_functionality(self, mock_requests, sample_scraped_html):
        """Test that mocking infrastructure works for AI tests."""
        # Test that we can mock HTTP requests
        mock_requests.get('http://test.com', text=sample_scraped_html)

        import requests
        response = requests.get('http://test.com')
        assert response.text == sample_scraped_html
        assert 'id="ador-delinquent-search-results"' in response.text

    @pytest.mark.unit
    @pytest.mark.benchmark
    @pytest.mark.ai_test
    def test_performance_measurement(self, benchmark):
        """Test that performance benchmarking works for AI validation."""
        def normalize_test_prices():
            """Test function for benchmarking."""
            test_prices = ["$1,234.56", "$999.99", "$15,000.00", "$500"]
            return [normalize_price(price) for price in test_prices]

        # Benchmark the function
        result = benchmark(normalize_test_prices)

        # Validate results
        expected = [1234.56, 999.99, 15000.00, 500.0]
        assert result == expected

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_data_factory_consistency(self, property_factory):
        """Test that data factories produce consistent, valid data."""
        # Generate multiple properties
        properties = [property_factory() for _ in range(10)]

        # Validate all properties have required attributes
        for prop in properties:
            assert hasattr(prop, 'parcel_id')
            assert hasattr(prop, 'amount')
            assert hasattr(prop, 'acreage')
            assert hasattr(prop, 'county')

            # Validate data types and ranges
            assert isinstance(prop.amount, int)
            assert 500 <= prop.amount <= 20000
            assert prop.acreage in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]

        # Test water feature factory
        water_prop = property_factory.with_water_features()
        water_keywords = ['creek', 'river', 'stream', 'lake', 'spring', 'water']
        description_lower = water_prop.description.lower()
        assert any(keyword in description_lower for keyword in water_keywords)

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_column_mapping_functionality(self, sample_csv_data):
        """Test that column mapping works for various CSV formats."""
        columns = sample_csv_data.columns.tolist()

        # Test finding parcel ID column
        parcel_col = find_column_mapping(columns, 'parcel_id')
        assert parcel_col == 'Parcel ID'

        # Test finding amount column
        amount_col = find_column_mapping(columns, 'amount')
        assert amount_col == 'Amount Bid at Tax Sale'

        # Test non-existent field
        missing_col = find_column_mapping(columns, 'nonexistent_field')
        assert missing_col is None

    @pytest.mark.integration
    @pytest.mark.ai_test
    def test_end_to_end_data_flow(self, sample_csv_data, auction_parser):
        """Test complete data processing flow for AI validation."""
        # This test validates that data flows correctly through the system
        # Map columns
        mapped_data = auction_parser.map_columns(sample_csv_data)

        # Normalize data
        normalized_data = auction_parser.normalize_data(mapped_data)

        # Apply filters
        filtered_data = auction_parser.apply_filters(normalized_data)

        # Calculate metrics
        final_data = auction_parser.calculate_metrics(filtered_data)

        # Validate the complete flow worked
        assert not final_data.empty
        assert 'investment_score' in final_data.columns
        assert 'water_score' in final_data.columns
        assert 'price_per_acre' in final_data.columns


class TestAISpecificationValidation:
    """Validate that AI test specifications are properly structured."""

    @pytest.mark.ai_test
    def test_specification_file_exists(self):
        """Test that AI specification files exist and are valid JSON."""
        spec_path = Path("tests/schemas/test_specifications.json")
        assert spec_path.exists(), "AI test specifications file not found"

        # Validate JSON format
        with open(spec_path, 'r') as f:
            specs = json.load(f)

        assert isinstance(specs, dict)
        assert "test_suites" in specs
        assert "ai_execution_configuration" in specs

    @pytest.mark.ai_test
    def test_specification_structure(self):
        """Test that AI specifications follow the required structure."""
        spec_path = Path("tests/schemas/test_specifications.json")
        with open(spec_path, 'r') as f:
            specs = json.load(f)

        # Validate test suite structure
        test_suites = specs["test_suites"]
        assert "county_scraping" in test_suites
        assert "data_processing" in test_suites
        assert "error_handling" in test_suites

        # Validate test case structure
        county_scraping = test_suites["county_scraping"]
        assert "test_cases" in county_scraping
        assert len(county_scraping["test_cases"]) > 0

        first_test = county_scraping["test_cases"][0]
        required_fields = ["id", "description", "category", "input", "expected_output"]
        for field in required_fields:
            assert field in first_test, f"Missing required field: {field}"

    @pytest.mark.ai_test
    def test_ai_instructions_validation(self):
        """Test that AI instructions are properly formatted."""
        spec_path = Path("tests/schemas/test_specifications.json")
        with open(spec_path, 'r') as f:
            specs = json.load(f)

        # Find test cases with AI instructions
        for suite_name, suite in specs["test_suites"].items():
            for test_case in suite.get("test_cases", []):
                if "ai_instructions" in test_case:
                    ai_instructions = test_case["ai_instructions"]

                    # Validate AI instruction structure
                    assert isinstance(ai_instructions.get("can_auto_retry", True), bool)
                    assert isinstance(ai_instructions.get("max_retries", 3), int)
                    assert ai_instructions.get("max_retries", 3) >= 0


# Parametrized tests for comprehensive validation
@pytest.mark.parametrize("price_input,expected", [
    ("$1,234.56", 1234.56),
    ("999.99", 999.99),
    ("$15,000", 15000.0),
    ("500", 500.0),
    ("", None),
    ("N/A", None),
])
@pytest.mark.unit
@pytest.mark.ai_test
def test_price_normalization_comprehensive(price_input, expected):
    """Comprehensive test of price normalization with AI-generated test cases."""
    result = normalize_price(price_input)
    assert result == expected


@pytest.mark.parametrize("error_type,should_be_recoverable", [
    ("network_timeout", True),
    ("invalid_county", False),
    ("parsing_error", True),
    ("system_error", False),
])
@pytest.mark.unit
@pytest.mark.error_handling
@pytest.mark.ai_test
def test_error_recoverability(error_type, should_be_recoverable):
    """Test error recovery logic for AI automation."""
    # This would be expanded to test actual error recovery mechanisms
    # For now, it validates the test structure
    assert isinstance(should_be_recoverable, bool)
    assert error_type in ["network_timeout", "invalid_county", "parsing_error", "system_error"]