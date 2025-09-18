"""
Custom exception classes for Alabama Auction Watcher

This module defines specific exception types for better error handling
and more informative error messages throughout the application.
"""


class AuctionWatcherError(Exception):
    """Base exception class for all auction watcher errors."""
    pass


class DataValidationError(AuctionWatcherError):
    """Raised when data validation fails."""

    def __init__(self, message: str, field: str = None, value: str = None):
        self.field = field
        self.value = value

        if field and value:
            message = f"Invalid {field}: '{value}' - {message}"

        super().__init__(message)


class CountyValidationError(AuctionWatcherError):
    """Raised when county code or name validation fails."""

    def __init__(self, county_input: str):
        message = f"Invalid county '{county_input}'. Use 2-digit code (01-67) or valid Alabama county name."
        super().__init__(message)
        self.county_input = county_input


class ScrapingError(AuctionWatcherError):
    """Base class for web scraping related errors."""
    pass


class NetworkError(ScrapingError):
    """Raised when network-related errors occur during scraping."""

    def __init__(self, message: str, url: str = None, status_code: int = None):
        self.url = url
        self.status_code = status_code

        if url:
            message = f"Network error for {url}: {message}"
        if status_code:
            message += f" (Status: {status_code})"

        super().__init__(message)


class ParseError(ScrapingError):
    """Raised when HTML parsing fails during scraping."""

    def __init__(self, message: str, page_content_length: int = None):
        self.page_content_length = page_content_length

        if page_content_length:
            message = f"Parse error (content length: {page_content_length}): {message}"

        super().__init__(message)


class RateLimitError(ScrapingError):
    """Raised when rate limiting is triggered."""

    def __init__(self, retry_after: int = None):
        message = "Rate limit exceeded"
        self.retry_after = retry_after

        if retry_after:
            message += f". Retry after {retry_after} seconds."

        super().__init__(message)


class DataProcessingError(AuctionWatcherError):
    """Raised when data processing operations fail."""

    def __init__(self, message: str, operation: str = None, records_affected: int = None):
        self.operation = operation
        self.records_affected = records_affected

        if operation:
            message = f"Data processing error in {operation}: {message}"
        if records_affected:
            message += f" (Affected records: {records_affected})"

        super().__init__(message)


class ConfigurationError(AuctionWatcherError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str, config_key: str = None):
        self.config_key = config_key

        if config_key:
            message = f"Configuration error for '{config_key}': {message}"

        super().__init__(message)


class FileOperationError(AuctionWatcherError):
    """Raised when file operations fail."""

    def __init__(self, message: str, file_path: str = None, operation: str = None):
        self.file_path = file_path
        self.operation = operation

        if file_path and operation:
            message = f"Failed to {operation} file '{file_path}': {message}"
        elif file_path:
            message = f"File operation failed for '{file_path}': {message}"
        elif operation:
            message = f"{operation} operation failed: {message}"

        super().__init__(message)


class InvestmentCalculationError(DataProcessingError):
    """Raised when investment metric calculations fail."""

    def __init__(self, message: str, property_id: str = None, metric: str = None):
        self.property_id = property_id
        self.metric = metric

        if property_id and metric:
            message = f"Failed to calculate {metric} for property {property_id}: {message}"
        elif property_id:
            message = f"Investment calculation failed for property {property_id}: {message}"
        elif metric:
            message = f"Failed to calculate {metric}: {message}"

        super().__init__(message, operation="investment_calculation")


class FilterValidationError(DataValidationError):
    """Raised when filter parameters are invalid."""

    def __init__(self, message: str, filter_name: str = None, filter_value: str = None):
        self.filter_name = filter_name
        self.filter_value = filter_value

        if filter_name and filter_value:
            message = f"Invalid filter '{filter_name}' with value '{filter_value}': {message}"
        elif filter_name:
            message = f"Invalid filter '{filter_name}': {message}"

        super().__init__(message, field=filter_name, value=filter_value)


# Error handling utilities
def handle_validation_error(func):
    """Decorator to wrap functions and convert common errors to validation errors."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            raise DataValidationError(str(e))
        except TypeError as e:
            raise DataValidationError(f"Type error: {e}")

    return wrapper


def safe_float_conversion(value, field_name: str = None) -> float:
    """
    Safely convert value to float with meaningful error messages.

    Args:
        value: Value to convert
        field_name: Optional field name for error context

    Returns:
        Converted float value

    Raises:
        DataValidationError: If conversion fails
    """
    try:
        if value is None or str(value).strip() == '':
            raise DataValidationError("Empty or null value", field=field_name)

        result = float(value)

        if not isinstance(result, (int, float)) or result != result:  # Check for NaN
            raise DataValidationError("Invalid numeric value", field=field_name, value=str(value))

        return result

    except (ValueError, TypeError) as e:
        raise DataValidationError(f"Cannot convert to number: {e}", field=field_name, value=str(value))


def safe_int_conversion(value, field_name: str = None) -> int:
    """
    Safely convert value to int with meaningful error messages.

    Args:
        value: Value to convert
        field_name: Optional field name for error context

    Returns:
        Converted int value

    Raises:
        DataValidationError: If conversion fails
    """
    try:
        if value is None or str(value).strip() == '':
            raise DataValidationError("Empty or null value", field=field_name)

        result = int(float(value))  # Allow conversion from float strings

        return result

    except (ValueError, TypeError) as e:
        raise DataValidationError(f"Cannot convert to integer: {e}", field=field_name, value=str(value))


def validate_positive_number(value, field_name: str = None) -> float:
    """
    Validate that a value is a positive number.

    Args:
        value: Value to validate
        field_name: Optional field name for error context

    Returns:
        Validated float value

    Raises:
        DataValidationError: If validation fails
    """
    number = safe_float_conversion(value, field_name)

    if number <= 0:
        raise DataValidationError("Must be a positive number", field=field_name, value=str(value))

    return number


def validate_range(value, min_val: float = None, max_val: float = None, field_name: str = None) -> float:
    """
    Validate that a value is within a specified range.

    Args:
        value: Value to validate
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)
        field_name: Optional field name for error context

    Returns:
        Validated float value

    Raises:
        DataValidationError: If validation fails
    """
    number = safe_float_conversion(value, field_name)

    if min_val is not None and number < min_val:
        raise DataValidationError(f"Value {number} is below minimum {min_val}", field=field_name, value=str(value))

    if max_val is not None and number > max_val:
        raise DataValidationError(f"Value {number} is above maximum {max_val}", field=field_name, value=str(value))

    return number