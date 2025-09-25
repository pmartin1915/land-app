"""
Enhanced Error Handling System for Alabama Auction Watcher

This module provides comprehensive error handling with smart retry logic,
detailed error context, and user-friendly error messages for better reliability.
"""

import time
import random
import logging
import traceback
from typing import Optional, Dict, Any, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
from functools import wraps
import asyncio
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for categorization."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for different types of failures."""
    NETWORK = "network"
    VALIDATION = "validation"
    DATA_PROCESSING = "data_processing"
    SCRAPING = "scraping"
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    RATE_LIMITING = "rate_limiting"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Comprehensive error context information."""
    error_type: str
    message: str
    severity: ErrorSeverity
    category: ErrorCategory
    timestamp: float
    function_name: str
    file_name: str
    line_number: int
    stack_trace: str
    user_message: str
    recovery_suggestions: list
    metadata: Dict[str, Any]
    retry_count: int = 0
    max_retries: int = 3


class SmartRetryHandler:
    """Advanced retry handler with exponential backoff and jitter."""

    def __init__(self,
                 max_retries: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 jitter: bool = True):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def calculate_delay(self, retry_count: int) -> float:
        """Calculate delay with exponential backoff and optional jitter."""
        delay = self.base_delay * (self.exponential_base ** retry_count)
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add random jitter (±25%)
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)

    def should_retry(self, error: Exception, retry_count: int) -> bool:
        """Determine if error should be retried."""
        if retry_count >= self.max_retries:
            return False

        # Define retryable errors
        retryable_errors = (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError,
            ConnectionError,
            TimeoutError,
        )

        # Check for specific HTTP status codes that are retryable
        if isinstance(error, requests.exceptions.HTTPError):
            status_code = error.response.status_code if error.response else None
            retryable_status_codes = {500, 502, 503, 504, 429}  # Server errors and rate limiting
            return status_code in retryable_status_codes

        return isinstance(error, retryable_errors)


class EnhancedErrorHandler:
    """Comprehensive error handling system."""

    def __init__(self):
        self.retry_handler = SmartRetryHandler()
        self.error_history = []
        self.recovery_strategies = self._initialize_recovery_strategies()

    def _initialize_recovery_strategies(self) -> Dict[ErrorCategory, Dict[str, Any]]:
        """Initialize recovery strategies for different error categories."""
        return {
            ErrorCategory.NETWORK: {
                "user_message": "Network connection issue. Please check your internet connection.",
                "suggestions": [
                    "Check your internet connection",
                    "Try again in a few moments",
                    "Contact support if the issue persists"
                ],
                "auto_retry": True
            },
            ErrorCategory.RATE_LIMITING: {
                "user_message": "Request rate limit reached. Automatically retrying with delay.",
                "suggestions": [
                    "Wait for automatic retry",
                    "Consider reducing request frequency",
                    "Premium users have higher rate limits"
                ],
                "auto_retry": True
            },
            ErrorCategory.VALIDATION: {
                "user_message": "Data validation failed. Please check your input.",
                "suggestions": [
                    "Verify all required fields are filled",
                    "Check data format requirements",
                    "Ensure numeric values are within valid ranges"
                ],
                "auto_retry": False
            },
            ErrorCategory.DATA_PROCESSING: {
                "user_message": "Data processing error. Some features may be temporarily unavailable.",
                "suggestions": [
                    "Try refreshing the page",
                    "Check if all required data is available",
                    "Contact support if error persists"
                ],
                "auto_retry": True
            },
            ErrorCategory.SCRAPING: {
                "user_message": "Web scraping encountered an issue. Retrying automatically.",
                "suggestions": [
                    "Target website may be temporarily unavailable",
                    "Wait for automatic retry",
                    "Check system status page"
                ],
                "auto_retry": True
            },
            ErrorCategory.DATABASE: {
                "user_message": "Database connection issue. Please try again.",
                "suggestions": [
                    "Refresh the page",
                    "Check if backend services are running",
                    "Contact administrator if issue persists"
                ],
                "auto_retry": True
            },
            ErrorCategory.AUTHENTICATION: {
                "user_message": "Authentication error. Please verify credentials.",
                "suggestions": [
                    "Check username and password",
                    "Ensure account is active",
                    "Reset password if needed"
                ],
                "auto_retry": False
            }
        }

    def categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize error based on type and message."""
        error_msg = str(error).lower()

        if isinstance(error, (requests.exceptions.RequestException, ConnectionError)):
            if "rate limit" in error_msg or "429" in error_msg:
                return ErrorCategory.RATE_LIMITING
            return ErrorCategory.NETWORK

        if isinstance(error, (ValueError, TypeError)) and "validation" in error_msg:
            return ErrorCategory.VALIDATION

        if "database" in error_msg or "sql" in error_msg:
            return ErrorCategory.DATABASE

        if "authentication" in error_msg or "unauthorized" in error_msg:
            return ErrorCategory.AUTHENTICATION

        if "scraping" in error_msg or "parsing" in error_msg:
            return ErrorCategory.SCRAPING

        return ErrorCategory.UNKNOWN

    def determine_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Determine error severity based on type and impact."""
        critical_errors = (SystemError, MemoryError, KeyboardInterrupt)
        if isinstance(error, critical_errors):
            return ErrorSeverity.CRITICAL

        if category in [ErrorCategory.DATABASE, ErrorCategory.AUTHENTICATION]:
            return ErrorSeverity.HIGH

        if category in [ErrorCategory.NETWORK, ErrorCategory.RATE_LIMITING]:
            return ErrorSeverity.MEDIUM

        return ErrorSeverity.LOW

    def create_error_context(self,
                           error: Exception,
                           function_name: str,
                           retry_count: int = 0) -> ErrorContext:
        """Create comprehensive error context."""
        import inspect

        # Get caller frame information
        frame = inspect.currentframe()
        while frame and frame.f_code.co_name in ['create_error_context', 'handle_error']:
            frame = frame.f_back

        file_name = frame.f_code.co_filename if frame else "unknown"
        line_number = frame.f_lineno if frame else 0

        category = self.categorize_error(error)
        severity = self.determine_severity(error, category)
        recovery_info = self.recovery_strategies.get(category, {})

        return ErrorContext(
            error_type=type(error).__name__,
            message=str(error),
            severity=severity,
            category=category,
            timestamp=time.time(),
            function_name=function_name,
            file_name=file_name,
            line_number=line_number,
            stack_trace=traceback.format_exc(),
            user_message=recovery_info.get("user_message", "An unexpected error occurred."),
            recovery_suggestions=recovery_info.get("suggestions", []),
            metadata={
                "can_retry": recovery_info.get("auto_retry", False),
                "error_category": category.value,
                "severity_level": severity.value
            },
            retry_count=retry_count
        )

    def log_error(self, context: ErrorContext):
        """Log error with appropriate level based on severity."""
        log_msg = f"[{context.category.value.upper()}] {context.function_name}: {context.message}"

        if context.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_msg, extra={"context": context})
        elif context.severity == ErrorSeverity.HIGH:
            logger.error(log_msg, extra={"context": context})
        elif context.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_msg, extra={"context": context})
        else:
            logger.info(log_msg, extra={"context": context})

        # Add to error history for analysis
        self.error_history.append(context)

        # Keep only last 100 errors to prevent memory issues
        if len(self.error_history) > 100:
            self.error_history = self.error_history[-100:]


# Global error handler instance
enhanced_error_handler = EnhancedErrorHandler()


def smart_retry(max_retries: int = 3,
                base_delay: float = 1.0,
                exponential_base: float = 2.0,
                jitter: bool = True):
    """
    Decorator for smart retry functionality with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter to delay

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            retry_handler = SmartRetryHandler(
                max_retries=max_retries,
                base_delay=base_delay,
                exponential_base=exponential_base,
                jitter=jitter
            )

            last_error = None

            for retry_count in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except Exception as e:
                    last_error = e

                    # Create error context
                    context = enhanced_error_handler.create_error_context(
                        e, func.__name__, retry_count
                    )

                    # Log the error
                    enhanced_error_handler.log_error(context)

                    # Check if we should retry
                    if retry_count < max_retries and retry_handler.should_retry(e, retry_count):
                        delay = retry_handler.calculate_delay(retry_count)
                        logger.info(f"Retrying {func.__name__} in {delay:.2f}s (attempt {retry_count + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        # No more retries, raise the last error
                        break

            # If we get here, all retries failed
            raise last_error

        return wrapper
    return decorator


def async_smart_retry(max_retries: int = 3,
                     base_delay: float = 1.0,
                     exponential_base: float = 2.0,
                     jitter: bool = True):
    """
    Async version of smart_retry decorator.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retry_handler = SmartRetryHandler(
                max_retries=max_retries,
                base_delay=base_delay,
                exponential_base=exponential_base,
                jitter=jitter
            )

            last_error = None

            for retry_count in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)

                except Exception as e:
                    last_error = e

                    # Create error context
                    context = enhanced_error_handler.create_error_context(
                        e, func.__name__, retry_count
                    )

                    # Log the error
                    enhanced_error_handler.log_error(context)

                    # Check if we should retry
                    if retry_count < max_retries and retry_handler.should_retry(e, retry_count):
                        delay = retry_handler.calculate_delay(retry_count)
                        logger.info(f"Retrying {func.__name__} in {delay:.2f}s (attempt {retry_count + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        break

            raise last_error

        return wrapper
    return decorator


def create_resilient_session() -> requests.Session:
    """
    Create a requests session with built-in retry logic and error handling.

    Returns:
        Configured requests session with retry strategy
    """
    session = requests.Session()

    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        backoff_factor=1,
        raise_on_status=False
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set reasonable timeout
    session.timeout = 30

    return session


def get_user_friendly_error_message(error: Exception) -> Tuple[str, list]:
    """
    Get user-friendly error message and recovery suggestions.

    Args:
        error: Exception that occurred

    Returns:
        Tuple of (user_message, recovery_suggestions)
    """
    context = enhanced_error_handler.create_error_context(error, "user_request")
    return context.user_message, context.recovery_suggestions


def get_error_statistics() -> Dict[str, Any]:
    """
    Get error statistics for monitoring and analysis.

    Returns:
        Dictionary with error statistics
    """
    if not enhanced_error_handler.error_history:
        return {"total_errors": 0}

    total_errors = len(enhanced_error_handler.error_history)

    # Count by category
    category_counts = {}
    severity_counts = {}

    for error_context in enhanced_error_handler.error_history:
        category = error_context.category.value
        severity = error_context.severity.value

        category_counts[category] = category_counts.get(category, 0) + 1
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    return {
        "total_errors": total_errors,
        "by_category": category_counts,
        "by_severity": severity_counts,
        "last_error": enhanced_error_handler.error_history[-1] if enhanced_error_handler.error_history else None
    }