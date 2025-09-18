"""
Logging configuration for Alabama Auction Watcher

This module provides centralized logging configuration with structured
logging, performance tracking, and different log levels for production use.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
import os

# Default log format with timestamp, level, module, and message
DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DETAILED_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'

# Log levels
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}


def setup_logging(
    log_level: str = 'INFO',
    log_file: Optional[str] = None,
    console_output: bool = True,
    detailed_format: bool = False
) -> logging.Logger:
    """
    Set up structured logging for the application.

    Args:
        log_level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        log_file: Optional log file path. If None, only console logging is used.
        console_output: Whether to output logs to console
        detailed_format: Whether to use detailed format with function names and line numbers

    Returns:
        Configured logger instance
    """
    # Convert string level to logging constant
    numeric_level = LOG_LEVELS.get(log_level.upper(), logging.INFO)

    # Choose format
    log_format = DETAILED_FORMAT if detailed_format else DEFAULT_FORMAT
    formatter = logging.Formatter(log_format)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Use rotating file handler to prevent huge log files
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_performance(logger: logging.Logger, operation: str, duration: float, records_processed: int = 0):
    """
    Log performance metrics in a structured way.

    Args:
        logger: Logger instance
        operation: Description of the operation
        duration: Duration in seconds
        records_processed: Number of records processed (if applicable)
    """
    if records_processed > 0:
        rate = records_processed / duration if duration > 0 else 0
        logger.info(f"PERFORMANCE: {operation} - Duration: {duration:.2f}s, Records: {records_processed}, Rate: {rate:.1f} records/sec")
    else:
        logger.info(f"PERFORMANCE: {operation} - Duration: {duration:.2f}s")


def log_scraping_metrics(logger: logging.Logger, county: str, pages: int, records: int, duration: float, errors: int = 0):
    """
    Log web scraping metrics in a structured way.

    Args:
        logger: Logger instance
        county: County name
        pages: Number of pages scraped
        records: Number of records extracted
        duration: Total duration in seconds
        errors: Number of errors encountered
    """
    rate = records / duration if duration > 0 else 0
    logger.info(f"SCRAPING_METRICS: County={county}, Pages={pages}, Records={records}, Duration={duration:.2f}s, Rate={rate:.1f} records/sec, Errors={errors}")


def log_processing_metrics(logger: logging.Logger, operation: str, input_records: int, output_records: int, duration: float):
    """
    Log data processing metrics in a structured way.

    Args:
        logger: Logger instance
        operation: Processing operation name
        input_records: Number of input records
        output_records: Number of output records
        duration: Processing duration in seconds
    """
    retention_rate = (output_records / input_records * 100) if input_records > 0 else 0
    rate = input_records / duration if duration > 0 else 0
    logger.info(f"PROCESSING_METRICS: Operation={operation}, Input={input_records}, Output={output_records}, Retention={retention_rate:.1f}%, Duration={duration:.2f}s, Rate={rate:.1f} records/sec")


def log_error_with_context(logger: logging.Logger, error: Exception, context: str, **kwargs):
    """
    Log errors with additional context information.

    Args:
        logger: Logger instance
        error: Exception instance
        context: Description of what was happening when the error occurred
        **kwargs: Additional context key-value pairs
    """
    context_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.error(f"ERROR: {context} - {type(error).__name__}: {str(error)} - Context: {context_str}")


# Environment-based logging setup
def setup_environment_logging():
    """
    Set up logging based on environment variables.

    Environment variables:
    - LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - LOG_FILE: Log file path (optional)
    - LOG_DETAILED: Use detailed format (true/false)
    """
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_file = os.getenv('LOG_FILE')
    log_detailed = os.getenv('LOG_DETAILED', 'false').lower() == 'true'

    setup_logging(
        log_level=log_level,
        log_file=log_file,
        detailed_format=log_detailed
    )


# Default setup for the application
if __name__ != "__main__":
    # Auto-setup when module is imported
    setup_environment_logging()