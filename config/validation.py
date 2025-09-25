"""
Comprehensive Input Validation and Sanitization for Alabama Auction Watcher

This module provides secure validation, sanitization, and protection against
injection attacks and malformed data across all input vectors.
"""

import re
import html
import bleach
from typing import Any, Optional, List, Dict, Union
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Force reload timestamp to ensure backend picks up changes
VALIDATION_MODULE_VERSION = "2025-09-23-15:39:00"


@dataclass
class ValidationResult:
    """Result of input validation with details."""
    is_valid: bool
    sanitized_value: Any
    errors: List[str]
    warnings: List[str]


class InputSanitizer:
    """Comprehensive input sanitization system."""

    # Allowed HTML tags (very restrictive)
    ALLOWED_HTML_TAGS = []

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bselect\b.*\bfrom\b)",
        r"(\bdrop\b.*\btable\b)",
        r"(\binsert\b.*\binto\b)",
        r"(\bupdate\b.*\bset\b)",
        r"(\bdelete\b.*\bfrom\b)",
        r"(\bexec\b|\bexecute\b)",
        r"(\bscript\b|\balert\b)",
        r"(--|#|/\*|\*/)",
        r"(\bor\b.*=.*\bor\b)",
        r"(1=1|2=2|'=')",
        r"(\;\s*drop\b)",
        r"(\;\s*shutdown\b)"
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"on\w+\s*=",
        r"expression\s*\(",
        r"eval\s*\(",
        r"document\.",
        r"window\.",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>"
    ]

    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"(\||\&|\;|\$\(|\`)",
        r"(rm\s+|del\s+|format\s+)",
        r"(wget\s+|curl\s+|nc\s+|netcat\s+)",
        r"(chmod\s+|chown\s+|sudo\s+)",
        r"(>\s*|<\s*|>>\s*)",
        r"(\.\./|\.\.\\\\)",
        r"(/etc/passwd|/etc/shadow)",
        r"(cmd\.exe|powershell\.exe|bash|sh)"
    ]

    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 1000,
                       allow_html: bool = False) -> ValidationResult:
        """
        Sanitize string input with comprehensive security checks.

        Args:
            value: Input string to sanitize
            max_length: Maximum allowed length
            allow_html: Whether to allow HTML (very restrictive)

        Returns:
            ValidationResult with sanitized value
        """
        errors = []
        warnings = []

        if not isinstance(value, str):
            return ValidationResult(False, "", ["Input must be a string"], [])


        # Length validation
        if len(value) > max_length:
            errors.append(f"Input too long (max {max_length} characters)")
            value = value[:max_length]
            warnings.append("Input truncated to maximum length")

        # SQL injection detection
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                errors.append("Potential SQL injection detected")
                logger.warning(f"SQL injection pattern detected: {pattern}")
                break

        # XSS detection
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                errors.append("Potential XSS attack detected")
                logger.warning(f"XSS pattern detected: {pattern}")
                break

        # Command injection detection
        for pattern in cls.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                errors.append("Potential command injection detected")
                logger.warning(f"Command injection pattern detected: {pattern}")
                break

        # HTML sanitization
        if allow_html:
            value = bleach.clean(value, tags=cls.ALLOWED_HTML_TAGS, strip=True)
        else:
            value = html.escape(value)

        # Normalize whitespace
        value = re.sub(r'\s+', ' ', value).strip()

        # Remove null bytes and control characters
        value = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', value)

        return ValidationResult(
            is_valid=len(errors) == 0,
            sanitized_value=value,
            errors=errors,
            warnings=warnings
        )

    @classmethod
    def sanitize_numeric(cls, value: Union[int, float, str],
                        min_value: Optional[float] = None,
                        max_value: Optional[float] = None,
                        allow_negative: bool = True) -> ValidationResult:
        """
        Sanitize and validate numeric input.

        Args:
            value: Input value to sanitize
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            allow_negative: Whether negative values are allowed

        Returns:
            ValidationResult with sanitized numeric value
        """
        errors = []
        warnings = []

        try:
            # Convert to float for validation
            if isinstance(value, str):
                # Remove common formatting
                clean_value = re.sub(r'[,$\s]', '', value)
                numeric_value = float(clean_value)
            else:
                numeric_value = float(value)

            # Range validation
            if not allow_negative and numeric_value < 0:
                errors.append("Negative values not allowed")

            if min_value is not None and numeric_value < min_value:
                errors.append(f"Value below minimum ({min_value})")

            if max_value is not None and numeric_value > max_value:
                errors.append(f"Value above maximum ({max_value})")

            # Check for suspicious values
            if abs(numeric_value) > 1e15:
                warnings.append("Extremely large numeric value")

            return ValidationResult(
                is_valid=len(errors) == 0,
                sanitized_value=numeric_value,
                errors=errors,
                warnings=warnings
            )

        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                sanitized_value=0,
                errors=["Invalid numeric value"],
                warnings=[]
            )


class PropertyValidator:
    """Specialized validator for property data."""

    # Valid Alabama counties (same as in property model)
    VALID_COUNTIES = {
        "Autauga", "Mobile", "Baldwin", "Barbour", "Bibb", "Blount", "Bullock", "Butler",
        "Calhoun", "Chambers", "Cherokee", "Chilton", "Choctaw", "Clarke", "Clay",
        "Cleburne", "Coffee", "Colbert", "Conecuh", "Coosa", "Covington", "Crenshaw",
        "Cullman", "Dale", "Dallas", "DeKalb", "Elmore", "Escambia", "Etowah",
        "Fayette", "Franklin", "Geneva", "Greene", "Hale", "Henry", "Houston",
        "Jackson", "Jefferson", "Lamar", "Lauderdale", "Lawrence", "Lee", "Limestone",
        "Lowndes", "Macon", "Madison", "Marengo", "Marion", "Marshall", "Monroe",
        "Montgomery", "Morgan", "Perry", "Pickens", "Pike", "Randolph", "Russell",
        "St. Clair", "Shelby", "Sumter", "Talladega", "Tallapoosa", "Tuscaloosa",
        "Walker", "Washington", "Wilcox", "Winston"
    }

    @classmethod
    def validate_parcel_id(cls, parcel_id: str) -> ValidationResult:
        """Validate property parcel ID."""
        result = InputSanitizer.sanitize_string(parcel_id, max_length=50)

        if result.is_valid:
            # Additional parcel ID specific validation
            sanitized = result.sanitized_value

            if len(sanitized) < 3:
                result.errors.append("Parcel ID too short (minimum 3 characters)")
                result.is_valid = False

            # Check for reasonable parcel ID pattern
            if not re.match(r'^[A-Z0-9\s-]+$', sanitized.upper()):
                result.warnings.append("Unusual characters in parcel ID")

        return result

    @classmethod
    def validate_amount(cls, amount: Union[float, str]) -> ValidationResult:
        """Validate property bid/sale amount."""
        return InputSanitizer.sanitize_numeric(
            amount,
            min_value=0.01,
            max_value=10_000_000,  # $10M max
            allow_negative=False
        )

    @classmethod
    def validate_acreage(cls, acreage: Union[float, str]) -> ValidationResult:
        """Validate property acreage."""
        return InputSanitizer.sanitize_numeric(
            acreage,
            min_value=0.001,  # 1/1000 acre minimum
            max_value=10_000,  # 10,000 acres maximum
            allow_negative=False
        )

    @classmethod
    def validate_county(cls, county: str) -> ValidationResult:
        """Validate Alabama county name."""
        result = InputSanitizer.sanitize_string(county, max_length=50)

        if result.is_valid:
            sanitized = result.sanitized_value.strip()

            if sanitized not in cls.VALID_COUNTIES:
                result.errors.append(f"Invalid Alabama county: {sanitized}")
                result.is_valid = False

        return result

    @classmethod
    def validate_description(cls, description: str) -> ValidationResult:
        """Validate property description."""
        return InputSanitizer.sanitize_string(
            description,
            max_length=2000,
            allow_html=False
        )

    @classmethod
    def validate_owner_name(cls, owner_name: str) -> ValidationResult:
        """Validate property owner name."""
        result = InputSanitizer.sanitize_string(owner_name, max_length=200)

        if result.is_valid:
            sanitized = result.sanitized_value

            # Check for reasonable name pattern
            if not re.match(r'^[A-Za-z\s\.\,\'\&-]+$', sanitized):
                result.warnings.append("Unusual characters in owner name")

        return result

    @classmethod
    def validate_year_sold(cls, year_sold: Union[str, int]) -> ValidationResult:
        """Validate sale year."""
        try:
            year = int(year_sold)
            current_year = datetime.now().year

            if year < 1900 or year > current_year + 1:
                return ValidationResult(
                    is_valid=False,
                    sanitized_value=year_sold,
                    errors=[f"Invalid year: {year} (must be 1900-{current_year + 1})"],
                    warnings=[]
                )

            return ValidationResult(
                is_valid=True,
                sanitized_value=str(year),
                errors=[],
                warnings=[]
            )

        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                sanitized_value=year_sold,
                errors=["Invalid year format"],
                warnings=[]
            )


class QueryValidator:
    """Validator for API query parameters."""

    @classmethod
    def validate_search_query(cls, search_query: str) -> ValidationResult:
        """Validate search query input."""
        result = InputSanitizer.sanitize_string(search_query, max_length=200)

        if result.is_valid:
            sanitized = result.sanitized_value

            # Additional search-specific validation
            if len(sanitized) < 2:
                result.warnings.append("Search query very short, may not return useful results")

            # Check for wildcard abuse
            if sanitized.count('%') > 5 or sanitized.count('*') > 5:
                result.warnings.append("Too many wildcards in search query")

        return result

    @classmethod
    def validate_sort_parameter(cls, sort_param: str) -> ValidationResult:
        """Validate sort parameter."""
        valid_sort_fields = {
            "parcel_id", "amount", "acreage", "investment_score",
            "water_score", "price_per_acre", "county", "year_sold",
            "created_at", "updated_at"
        }

        result = InputSanitizer.sanitize_string(sort_param, max_length=50)

        if result.is_valid:
            sanitized = result.sanitized_value.lower()

            if sanitized not in valid_sort_fields:
                result.errors.append(f"Invalid sort field: {sanitized}")
                result.is_valid = False

        return result


def validate_property_data(data: Dict[str, Any]) -> Dict[str, ValidationResult]:
    """
    Validate complete property data object.

    Args:
        data: Dictionary of property data to validate

    Returns:
        Dictionary of field names to ValidationResult objects
    """
    results = {}

    # Validate required fields
    if 'parcel_id' in data:
        results['parcel_id'] = PropertyValidator.validate_parcel_id(data['parcel_id'])

    if 'amount' in data:
        results['amount'] = PropertyValidator.validate_amount(data['amount'])

    # Validate optional fields
    if 'acreage' in data and data['acreage'] is not None:
        results['acreage'] = PropertyValidator.validate_acreage(data['acreage'])

    if 'county' in data and data['county'] is not None:
        results['county'] = PropertyValidator.validate_county(data['county'])

    if 'description' in data and data['description'] is not None:
        results['description'] = PropertyValidator.validate_description(data['description'])

    if 'owner_name' in data and data['owner_name'] is not None:
        results['owner_name'] = PropertyValidator.validate_owner_name(data['owner_name'])

    if 'year_sold' in data and data['year_sold'] is not None:
        results['year_sold'] = PropertyValidator.validate_year_sold(data['year_sold'])

    return results


def get_validation_summary(results: Dict[str, ValidationResult]) -> Dict[str, Any]:
    """
    Get summary of validation results.

    Args:
        results: Dictionary of validation results

    Returns:
        Summary with overall status and details
    """
    total_fields = len(results)
    valid_fields = sum(1 for r in results.values() if r.is_valid)
    total_errors = sum(len(r.errors) for r in results.values())
    total_warnings = sum(len(r.warnings) for r in results.values())

    return {
        "overall_valid": total_errors == 0,
        "total_fields": total_fields,
        "valid_fields": valid_fields,
        "invalid_fields": total_fields - valid_fields,
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "field_results": {
            field: {
                "valid": result.is_valid,
                "errors": result.errors,
                "warnings": result.warnings,
                "sanitized_value": result.sanitized_value
            }
            for field, result in results.items()
        }
    }