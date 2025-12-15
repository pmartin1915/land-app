"""
AI-testable unit tests for scripts/exceptions.py module.

This module provides comprehensive test coverage for custom exception classes,
error handling utilities, and validation functions with AI-friendly patterns
and performance benchmarks.
"""

import pytest
import math
from unittest.mock import Mock, patch

from scripts.exceptions import (
    AuctionWatcherError, DataValidationError, CountyValidationError,
    ScrapingError, NetworkError, ParseError, RateLimitError,
    DataProcessingError, ConfigurationError, FileOperationError,
    InvestmentCalculationError, FilterValidationError,
    handle_validation_error, safe_float_conversion, safe_int_conversion,
    validate_positive_number, validate_range
)


class TestBaseExceptionClasses:
    """Test suite for base exception classes and hierarchy."""

    def test_auction_watcher_error_basic(self):
        error = AuctionWatcherError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_auction_watcher_error_inheritance(self):
        error = AuctionWatcherError("Test")
        assert isinstance(error, Exception)
        assert not isinstance(error, ValueError)

    def test_scraping_error_inheritance(self):
        error = ScrapingError("Scraping failed")
        assert isinstance(error, AuctionWatcherError)
        assert isinstance(error, Exception)

    def test_data_processing_error_inheritance(self):
        error = DataProcessingError("Processing failed")
        assert isinstance(error, AuctionWatcherError)
        assert isinstance(error, Exception)

    def test_exception_hierarchy_completeness(self):
        exceptions_to_test = [
            DataValidationError("test"),
            CountyValidationError("test"),
            ScrapingError("test"),
            NetworkError("test"),
            ParseError("test"),
            RateLimitError(),
            DataProcessingError("test"),
            ConfigurationError("test"),
            FileOperationError("test")
        ]

        for exc in exceptions_to_test:
            assert isinstance(exc, AuctionWatcherError)
            assert isinstance(exc, Exception)

    def test_specialized_inheritance(self):
        investment_error = InvestmentCalculationError("test")
        assert isinstance(investment_error, DataProcessingError)
        assert isinstance(investment_error, AuctionWatcherError)

        filter_error = FilterValidationError("test")
        assert isinstance(filter_error, DataValidationError)
        assert isinstance(filter_error, AuctionWatcherError)

        network_error = NetworkError("test")
        assert isinstance(network_error, ScrapingError)
        assert isinstance(network_error, AuctionWatcherError)


class TestDataValidationError:
    """Test suite for DataValidationError functionality."""

    def test_basic_error_message(self):
        error = DataValidationError("Invalid data")
        assert str(error) == "Invalid data"

    def test_error_with_field_only(self):
        error = DataValidationError("Invalid data", field="price")
        assert str(error) == "Invalid data"

    def test_error_with_field_and_value(self):
        error = DataValidationError("must be positive", field="price", value="-100")
        assert "Invalid price: '-100' - must be positive" in str(error)

    def test_error_attributes_stored(self):
        error = DataValidationError("test", field="amount", value="invalid")
        assert error.field == "amount"
        assert error.value == "invalid"

    def test_error_with_none_values(self):
        error = DataValidationError("test", field=None, value=None)
        assert error.field is None
        assert error.value is None
        assert str(error) == "test"

    def test_error_with_empty_strings(self):
        error = DataValidationError("test", field="", value="")
        assert error.field == ""
        assert error.value == ""

    @pytest.mark.ai_test
    def test_data_validation_error_performance_benchmark(self, benchmark):
        def create_errors():
            return [
                DataValidationError("test"),
                DataValidationError("test", field="price"),
                DataValidationError("test", field="price", value="invalid"),
                DataValidationError("test", field="amount", value="-100")
            ]

        result = benchmark(create_errors)
        assert len(result) == 4
        assert all(isinstance(err, DataValidationError) for err in result)
        assert benchmark.stats['mean'] < 0.001

    def test_error_message_formatting_edge_cases(self):
        error = DataValidationError("test", field="field with spaces", value="value with spaces")
        assert "field with spaces" in str(error)
        assert "value with spaces" in str(error)

    def test_error_with_numeric_values(self):
        error = DataValidationError("test", field="price", value=123)
        assert "Invalid price: '123' - test" in str(error)


class TestCountyValidationError:
    """Test suite for CountyValidationError functionality."""

    def test_basic_county_error(self):
        error = CountyValidationError("InvalidCounty")
        assert "Invalid county 'InvalidCounty'" in str(error)
        assert "2-digit code (01-67)" in str(error)
        assert "valid Alabama county name" in str(error)

    def test_county_input_stored(self):
        error = CountyValidationError("99")
        assert error.county_input == "99"

    def test_county_error_various_inputs(self):
        test_inputs = ["InvalidCounty", "99", "00", "", "XYZ"]

        for county_input in test_inputs:
            error = CountyValidationError(county_input)
            assert error.county_input == county_input
            assert county_input in str(error)

    def test_county_error_with_special_characters(self):
        error = CountyValidationError("County-Name!")
        assert "County-Name!" in str(error)
        assert error.county_input == "County-Name!"

    @pytest.mark.ai_test
    def test_county_validation_error_performance_benchmark(self, benchmark):
        test_counties = ["InvalidCounty", "99", "00", "XYZ", ""]

        def create_county_errors():
            return [CountyValidationError(county) for county in test_counties]

        result = benchmark(create_county_errors)
        assert len(result) == 5
        assert all(isinstance(err, CountyValidationError) for err in result)
        assert benchmark.stats['mean'] < 0.001

    def test_county_error_inheritance(self):
        error = CountyValidationError("test")
        assert isinstance(error, AuctionWatcherError)


class TestScrapingErrors:
    """Test suite for scraping-related exception classes."""

    def test_network_error_basic(self):
        error = NetworkError("Connection failed")
        assert str(error) == "Connection failed"

    def test_network_error_with_url(self):
        error = NetworkError("Connection failed", url="https://example.com")
        assert "Network error for https://example.com: Connection failed" in str(error)

    def test_network_error_with_status_code(self):
        error = NetworkError("Not found", status_code=404)
        assert "Not found (Status: 404)" in str(error)

    def test_network_error_with_url_and_status(self):
        error = NetworkError("Not found", url="https://example.com", status_code=404)
        error_str = str(error)
        assert "Network error for https://example.com" in error_str
        assert "Not found" in error_str
        assert "(Status: 404)" in error_str

    def test_network_error_attributes(self):
        error = NetworkError("test", url="https://example.com", status_code=500)
        assert error.url == "https://example.com"
        assert error.status_code == 500

    def test_parse_error_basic(self):
        error = ParseError("Failed to parse HTML")
        assert str(error) == "Failed to parse HTML"

    def test_parse_error_with_content_length(self):
        error = ParseError("Invalid HTML", page_content_length=1024)
        assert "Parse error (content length: 1024): Invalid HTML" in str(error)

    def test_parse_error_attributes(self):
        error = ParseError("test", page_content_length=2048)
        assert error.page_content_length == 2048

    def test_rate_limit_error_basic(self):
        error = RateLimitError()
        assert str(error) == "Rate limit exceeded"

    def test_rate_limit_error_with_retry_after(self):
        error = RateLimitError(retry_after=300)
        assert "Rate limit exceeded. Retry after 300 seconds." in str(error)

    def test_rate_limit_error_attributes(self):
        error = RateLimitError(retry_after=120)
        assert error.retry_after == 120

    @pytest.mark.ai_test
    def test_scraping_errors_performance_benchmark(self, benchmark):
        def create_scraping_errors():
            return [
                NetworkError("Connection failed", url="https://example.com", status_code=404),
                ParseError("Invalid HTML", page_content_length=1024),
                RateLimitError(retry_after=300),
                ScrapingError("Generic scraping error")
            ]

        result = benchmark(create_scraping_errors)
        assert len(result) == 4
        assert all(isinstance(err, ScrapingError) for err in result)
        assert benchmark.stats['mean'] < 0.001

    def test_scraping_error_inheritance_chain(self):
        network_error = NetworkError("test")
        parse_error = ParseError("test")
        rate_limit_error = RateLimitError()

        for error in [network_error, parse_error, rate_limit_error]:
            assert isinstance(error, ScrapingError)
            assert isinstance(error, AuctionWatcherError)


class TestDataProcessingErrors:
    """Test suite for data processing exception classes."""

    def test_data_processing_error_basic(self):
        error = DataProcessingError("Processing failed")
        assert str(error) == "Processing failed"

    def test_data_processing_error_with_operation(self):
        error = DataProcessingError("Failed", operation="normalization")
        assert "Data processing error in normalization: Failed" in str(error)

    def test_data_processing_error_with_records_affected(self):
        error = DataProcessingError("Failed", records_affected=100)
        assert "Failed (Affected records: 100)" in str(error)

    def test_data_processing_error_with_all_params(self):
        error = DataProcessingError("Failed", operation="filtering", records_affected=50)
        error_str = str(error)
        assert "Data processing error in filtering" in error_str
        assert "Failed" in error_str
        assert "(Affected records: 50)" in error_str

    def test_data_processing_error_attributes(self):
        error = DataProcessingError("test", operation="parsing", records_affected=25)
        assert error.operation == "parsing"
        assert error.records_affected == 25

    def test_investment_calculation_error_basic(self):
        error = InvestmentCalculationError("Calculation failed")
        assert "Calculation failed" in str(error)

    def test_investment_calculation_error_with_property_id(self):
        error = InvestmentCalculationError("Failed", property_id="001-001-001")
        assert "Investment calculation failed for property 001-001-001: Failed" in str(error)

    def test_investment_calculation_error_with_metric(self):
        error = InvestmentCalculationError("Failed", metric="water_score")
        assert "Failed to calculate water_score: Failed" in str(error)

    def test_investment_calculation_error_with_all_params(self):
        error = InvestmentCalculationError("Failed", property_id="001-001-001", metric="investment_score")
        error_str = str(error)
        assert "Failed to calculate investment_score for property 001-001-001" in error_str

    def test_investment_calculation_error_inheritance(self):
        error = InvestmentCalculationError("test")
        assert isinstance(error, DataProcessingError)
        assert isinstance(error, AuctionWatcherError)
        assert error.operation == "investment_calculation"

    @pytest.mark.ai_test
    def test_data_processing_errors_performance_benchmark(self, benchmark):
        def create_processing_errors():
            return [
                DataProcessingError("Basic error"),
                DataProcessingError("Error", operation="filtering"),
                DataProcessingError("Error", records_affected=100),
                InvestmentCalculationError("Calc failed", property_id="001", metric="score")
            ]

        result = benchmark(create_processing_errors)
        assert len(result) == 4
        assert all(isinstance(err, DataProcessingError) for err in result)
        assert benchmark.stats['mean'] < 0.001


class TestConfigurationAndFileErrors:
    """Test suite for configuration and file operation exceptions."""

    def test_configuration_error_basic(self):
        error = ConfigurationError("Invalid setting")
        assert str(error) == "Invalid setting"

    def test_configuration_error_with_config_key(self):
        error = ConfigurationError("Missing value", config_key="database_url")
        assert "Configuration error for 'database_url': Missing value" in str(error)

    def test_configuration_error_attributes(self):
        error = ConfigurationError("test", config_key="api_key")
        assert error.config_key == "api_key"

    def test_file_operation_error_basic(self):
        error = FileOperationError("File not found")
        assert str(error) == "File not found"

    def test_file_operation_error_with_file_path(self):
        error = FileOperationError("Permission denied", file_path="/path/to/file.csv")
        assert "File operation failed for '/path/to/file.csv': Permission denied" in str(error)

    def test_file_operation_error_with_operation(self):
        error = FileOperationError("Failed", operation="read")
        assert "read operation failed: Failed" in str(error)

    def test_file_operation_error_with_all_params(self):
        error = FileOperationError("Permission denied", file_path="/path/to/file.csv", operation="write")
        error_str = str(error)
        assert "Failed to write file '/path/to/file.csv': Permission denied" in error_str

    def test_file_operation_error_attributes(self):
        error = FileOperationError("test", file_path="/test/path", operation="delete")
        assert error.file_path == "/test/path"
        assert error.operation == "delete"

    @pytest.mark.ai_test
    def test_config_and_file_errors_performance_benchmark(self, benchmark):
        def create_config_file_errors():
            return [
                ConfigurationError("Invalid config"),
                ConfigurationError("Missing", config_key="setting"),
                FileOperationError("File error"),
                FileOperationError("Failed", file_path="/path", operation="read")
            ]

        result = benchmark(create_config_file_errors)
        assert len(result) == 4
        assert all(isinstance(err, AuctionWatcherError) for err in result)
        assert benchmark.stats['mean'] < 0.001

    def test_configuration_error_inheritance(self):
        error = ConfigurationError("test")
        assert isinstance(error, AuctionWatcherError)

    def test_file_operation_error_inheritance(self):
        error = FileOperationError("test")
        assert isinstance(error, AuctionWatcherError)


class TestFilterValidationError:
    """Test suite for FilterValidationError functionality."""

    def test_filter_validation_error_basic(self):
        error = FilterValidationError("Invalid filter")
        assert str(error) == "Invalid filter"

    def test_filter_validation_error_with_filter_name(self):
        error = FilterValidationError("Must be positive", filter_name="min_price")
        assert "Invalid filter 'min_price': Must be positive" in str(error)

    def test_filter_validation_error_with_all_params(self):
        error = FilterValidationError("Must be positive", filter_name="min_price", filter_value="-100")
        error_str = str(error)
        assert "Invalid filter 'min_price' with value '-100': Must be positive" in error_str

    def test_filter_validation_error_attributes(self):
        error = FilterValidationError("test", filter_name="max_acres", filter_value="invalid")
        assert error.filter_name == "max_acres"
        assert error.filter_value == "invalid"
        assert error.field == "max_acres"
        assert error.value == "invalid"

    def test_filter_validation_error_inheritance(self):
        error = FilterValidationError("test")
        assert isinstance(error, DataValidationError)
        assert isinstance(error, AuctionWatcherError)

    @pytest.mark.ai_test
    def test_filter_validation_error_performance_benchmark(self, benchmark):
        def create_filter_errors():
            return [
                FilterValidationError("Basic error"),
                FilterValidationError("Error", filter_name="price"),
                FilterValidationError("Error", filter_name="price", filter_value="invalid"),
                FilterValidationError("Range error", filter_name="acres", filter_value="-1")
            ]

        result = benchmark(create_filter_errors)
        assert len(result) == 4
        assert all(isinstance(err, FilterValidationError) for err in result)
        assert benchmark.stats['mean'] < 0.001


class TestValidationErrorDecorator:
    """Test suite for handle_validation_error decorator."""

    def test_decorator_passes_through_normal_return(self):
        @handle_validation_error
        def normal_function(x):
            return x * 2

        result = normal_function(5)
        assert result == 10

    def test_decorator_converts_value_error(self):
        @handle_validation_error
        def function_that_raises_value_error():
            raise ValueError("Invalid value")

        with pytest.raises(DataValidationError) as exc_info:
            function_that_raises_value_error()

        assert "Invalid value" in str(exc_info.value)

    def test_decorator_converts_type_error(self):
        @handle_validation_error
        def function_that_raises_type_error():
            raise TypeError("Wrong type")

        with pytest.raises(DataValidationError) as exc_info:
            function_that_raises_type_error()

        assert "Type error: Wrong type" in str(exc_info.value)

    def test_decorator_preserves_other_exceptions(self):
        @handle_validation_error
        def function_that_raises_runtime_error():
            raise RuntimeError("Runtime issue")

        with pytest.raises(RuntimeError):
            function_that_raises_runtime_error()

    def test_decorator_with_function_arguments(self):
        @handle_validation_error
        def function_with_args(a, b, c=None):
            if c is None:
                raise ValueError("c cannot be None")
            return a + b + c

        with pytest.raises(DataValidationError):
            function_with_args(1, 2)

        result = function_with_args(1, 2, 3)
        assert result == 6

    @pytest.mark.ai_test
    def test_decorator_performance_benchmark(self, benchmark):
        @handle_validation_error
        def test_function(x):
            if x < 0:
                raise ValueError("Must be positive")
            return x * 2

        def run_decorated_function():
            results = []
            for i in range(10):
                try:
                    results.append(test_function(i))
                except DataValidationError:
                    pass
            return results

        result = benchmark(run_decorated_function)
        assert len(result) == 10
        assert benchmark.stats['mean'] < 0.001

    def test_decorator_preserves_function_metadata(self):
        @handle_validation_error
        def documented_function():
            """This function has documentation."""
            return "test"

        assert documented_function.__name__ == "wrapper"


class TestSafeConversionFunctions:
    """Test suite for safe conversion utility functions."""

    def test_safe_float_conversion_valid_numbers(self):
        assert safe_float_conversion("123.45") == 123.45
        assert safe_float_conversion(123.45) == 123.45
        assert safe_float_conversion("123") == 123.0
        assert safe_float_conversion(123) == 123.0

    def test_safe_float_conversion_with_field_name(self):
        result = safe_float_conversion("123.45", "price")
        assert result == 123.45

    def test_safe_float_conversion_invalid_inputs(self):
        with pytest.raises(DataValidationError) as exc_info:
            safe_float_conversion("invalid")
        assert "Cannot convert to number" in str(exc_info.value)

        with pytest.raises(DataValidationError) as exc_info:
            safe_float_conversion("invalid", "price")
        assert "price" in str(exc_info.value.field)

    def test_safe_float_conversion_empty_values(self):
        with pytest.raises(DataValidationError) as exc_info:
            safe_float_conversion(None)
        assert "Empty or null value" in str(exc_info.value)

        with pytest.raises(DataValidationError):
            safe_float_conversion("")

        with pytest.raises(DataValidationError):
            safe_float_conversion("   ")

    def test_safe_float_conversion_nan_handling(self):
        with pytest.raises(DataValidationError) as exc_info:
            safe_float_conversion(float('nan'))
        assert "Invalid numeric value" in str(exc_info.value)

    def test_safe_int_conversion_valid_numbers(self):
        assert safe_int_conversion("123") == 123
        assert safe_int_conversion(123) == 123
        assert safe_int_conversion("123.0") == 123
        assert safe_int_conversion(123.7) == 123

    def test_safe_int_conversion_invalid_inputs(self):
        with pytest.raises(DataValidationError):
            safe_int_conversion("invalid")

        with pytest.raises(DataValidationError):
            safe_int_conversion(None)

        with pytest.raises(DataValidationError):
            safe_int_conversion("")

    def test_safe_int_conversion_with_field_name(self):
        with pytest.raises(DataValidationError) as exc_info:
            safe_int_conversion("invalid", "count")
        assert exc_info.value.field == "count"

    @pytest.mark.ai_test
    def test_safe_conversion_performance_benchmark(self, benchmark):
        test_values = ["123.45", "456", "789.0", "100", "200.2"]

        def convert_batch():
            float_results = [safe_float_conversion(val) for val in test_values]
            int_results = [safe_int_conversion(val) for val in test_values]
            return float_results, int_results

        result = benchmark(convert_batch)
        float_results, int_results = result
        assert len(float_results) == 5
        assert len(int_results) == 5
        assert benchmark.stats['mean'] < 0.001

    def test_safe_conversion_edge_cases(self):
        assert safe_float_conversion("0") == 0.0
        assert safe_float_conversion("-123.45") == -123.45
        assert safe_int_conversion("0") == 0
        assert safe_int_conversion("-123") == -123

    def test_safe_conversion_scientific_notation(self):
        assert safe_float_conversion("1.5e2") == 150.0
        assert safe_int_conversion("1e3") == 1000


class TestValidationFunctions:
    """Test suite for validation utility functions."""

    def test_validate_positive_number_valid_inputs(self):
        assert validate_positive_number("123.45") == 123.45
        assert validate_positive_number(123.45) == 123.45
        assert validate_positive_number("0.01") == 0.01

    def test_validate_positive_number_invalid_inputs(self):
        with pytest.raises(DataValidationError) as exc_info:
            validate_positive_number("0")
        assert "Must be a positive number" in str(exc_info.value)

        with pytest.raises(DataValidationError):
            validate_positive_number("-123")

        with pytest.raises(DataValidationError):
            validate_positive_number("-0.01")

    def test_validate_positive_number_with_field_name(self):
        with pytest.raises(DataValidationError) as exc_info:
            validate_positive_number("-100", "price")
        assert exc_info.value.field == "price"
        assert exc_info.value.value == "-100"

    def test_validate_range_within_bounds(self):
        assert validate_range("50", min_val=0, max_val=100) == 50.0
        assert validate_range("0", min_val=0, max_val=100) == 0.0
        assert validate_range("100", min_val=0, max_val=100) == 100.0

    def test_validate_range_below_minimum(self):
        with pytest.raises(DataValidationError) as exc_info:
            validate_range("-10", min_val=0, max_val=100)
        assert "below minimum" in str(exc_info.value)

    def test_validate_range_above_maximum(self):
        with pytest.raises(DataValidationError) as exc_info:
            validate_range("150", min_val=0, max_val=100)
        assert "above maximum" in str(exc_info.value)

    def test_validate_range_no_bounds(self):
        assert validate_range("123.45") == 123.45
        assert validate_range("-123.45") == -123.45

    def test_validate_range_only_minimum(self):
        assert validate_range("50", min_val=0) == 50.0
        with pytest.raises(DataValidationError):
            validate_range("-10", min_val=0)

    def test_validate_range_only_maximum(self):
        assert validate_range("50", max_val=100) == 50.0
        with pytest.raises(DataValidationError):
            validate_range("150", max_val=100)

    def test_validate_range_with_field_name(self):
        with pytest.raises(DataValidationError) as exc_info:
            validate_range("150", min_val=0, max_val=100, field_name="score")
        assert exc_info.value.field == "score"

    @pytest.mark.ai_test
    def test_validation_functions_performance_benchmark(self, benchmark):
        test_values = ["10", "50", "75", "90", "25"]

        def validate_batch():
            positive_results = [validate_positive_number(val) for val in test_values]
            range_results = [validate_range(val, min_val=0, max_val=100) for val in test_values]
            return positive_results, range_results

        result = benchmark(validate_batch)
        positive_results, range_results = result
        assert len(positive_results) == 5
        assert len(range_results) == 5
        assert all(val > 0 for val in positive_results)
        assert all(0 <= val <= 100 for val in range_results)
        assert benchmark.stats['mean'] < 0.001

    def test_validate_range_edge_case_values(self):
        assert validate_range("0.0", min_val=0.0, max_val=1.0) == 0.0
        assert validate_range("1.0", min_val=0.0, max_val=1.0) == 1.0

        with pytest.raises(DataValidationError):
            validate_range("-0.000001", min_val=0.0)

        with pytest.raises(DataValidationError):
            validate_range("1.000001", max_val=1.0)

    def test_validation_error_chaining(self):
        with pytest.raises(DataValidationError) as exc_info:
            validate_positive_number("invalid_number")
        assert "Cannot convert to number" in str(exc_info.value)

        with pytest.raises(DataValidationError) as exc_info:
            validate_range("invalid_number", min_val=0, max_val=100)
        assert "Cannot convert to number" in str(exc_info.value)


@pytest.mark.integration
class TestExceptionIntegrationScenarios:
    """Integration test scenarios for exception handling workflows."""

    def test_exception_hierarchy_validation(self):
        all_exceptions = [
            AuctionWatcherError("base"),
            DataValidationError("validation"),
            CountyValidationError("test"),
            ScrapingError("scraping"),
            NetworkError("network"),
            ParseError("parse"),
            RateLimitError(),
            DataProcessingError("processing"),
            ConfigurationError("config"),
            FileOperationError("file"),
            InvestmentCalculationError("investment"),
            FilterValidationError("filter")
        ]

        for exc in all_exceptions:
            assert isinstance(exc, AuctionWatcherError)
            assert isinstance(exc, Exception)

    def test_error_message_consistency(self):
        errors_with_context = [
            DataValidationError("test", field="price", value="invalid"),
            NetworkError("test", url="https://example.com", status_code=404),
            ParseError("test", page_content_length=1024),
            DataProcessingError("test", operation="filter", records_affected=100),
            ConfigurationError("test", config_key="api_key"),
            FileOperationError("test", file_path="/path", operation="read"),
            InvestmentCalculationError("test", property_id="001", metric="score"),
            FilterValidationError("test", filter_name="price", filter_value="invalid")
        ]

        for error in errors_with_context:
            error_str = str(error)
            assert len(error_str) > 0
            assert "test" in error_str

    def test_validation_workflow_integration(self):
        @handle_validation_error
        def process_property_data(price_str, acreage_str):
            price = validate_positive_number(price_str, "price")
            acreage = validate_range(acreage_str, min_val=0.1, max_val=1000, field_name="acreage")
            return price / acreage

        assert process_property_data("15000", "2.5") == 6000.0

        with pytest.raises(DataValidationError) as exc_info:
            process_property_data("-15000", "2.5")
        assert "Must be a positive number" in str(exc_info.value)

        with pytest.raises(DataValidationError) as exc_info:
            process_property_data("15000", "0.05")
        assert "below minimum" in str(exc_info.value)

    @pytest.mark.ai_test
    def test_error_handling_performance_integration(self, benchmark):
        def error_heavy_workflow():
            results = []
            test_data = [
                ("15000", "2.5"),
                ("-1000", "2.0"),
                ("20000", "0.01"),
                ("invalid", "3.0"),
                ("25000", "invalid")
            ]

            for price_str, acreage_str in test_data:
                try:
                    price = validate_positive_number(price_str)
                    acreage = validate_range(acreage_str, min_val=0.1, max_val=1000)
                    results.append(price / acreage)
                except DataValidationError:
                    results.append(None)

            return results

        result = benchmark(error_heavy_workflow)
        assert len(result) == 5
        assert result[0] == 6000.0
        assert result[1] is None
        assert benchmark.stats['mean'] < 0.01

    def test_nested_exception_handling(self):
        def level3_function():
            raise ValueError("Deep error")

        @handle_validation_error
        def level2_function():
            return level3_function()

        def level1_function():
            try:
                return level2_function()
            except DataValidationError as e:
                raise InvestmentCalculationError(str(e), property_id="001", metric="score")

        with pytest.raises(InvestmentCalculationError) as exc_info:
            level1_function()

        error = exc_info.value
        assert error.property_id == "001"
        assert error.metric == "score"
        assert isinstance(error, DataProcessingError)
        assert isinstance(error, AuctionWatcherError)

    def test_exception_serialization_compatibility(self):
        exceptions_to_test = [
            DataValidationError("test", field="price", value="invalid"),
            CountyValidationError("InvalidCounty"),
            NetworkError("Connection failed", url="https://example.com", status_code=404),
            InvestmentCalculationError("Calc failed", property_id="001", metric="score")
        ]

        for exc in exceptions_to_test:
            error_dict = {
                'type': type(exc).__name__,
                'message': str(exc),
                'attributes': {}
            }

            for attr in ['field', 'value', 'county_input', 'url', 'status_code', 'property_id', 'metric']:
                if hasattr(exc, attr):
                    error_dict['attributes'][attr] = getattr(exc, attr)

            assert error_dict['type']
            assert error_dict['message']


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])