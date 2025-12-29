"""
Shared pytest fixtures and configurations for Alabama Auction Watcher tests.

This module provides reusable test fixtures, mock data, and test utilities
that enable comprehensive AI-testable validation of the auction system.
"""

# Note: Previously skipped tests have been fixed:
# - test_scraper.py was deleted and replaced with test_scraper_playwright.py
# - test_specification_system.py imports were aliased to avoid pytest collection issues

import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import Mock, patch

import pandas as pd
import pytest
import requests_mock
from faker import Faker
from factory import Factory, Faker as FactoryFaker, Sequence, SubFactory
from freezegun import freeze_time

# Import project modules for testing
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.scraper import ALABAMA_COUNTY_CODES
from scripts.exceptions import *
from scripts.utils import *
from scripts.scraper import *
from scripts.parser import AuctionParser


# Initialize Faker for consistent test data
fake = Faker()
Faker.seed(42)  # Deterministic test data


@pytest.fixture(scope="session")
def test_config():
    """Test configuration fixture with AI-testable parameters."""
    return {
        "test_data_dir": Path(__file__).parent / "fixtures",
        "mock_server_port": 8999,
        "test_timeout": 30,
        "performance_thresholds": {
            "scraping_rate_min": 10,  # records/second
            "processing_time_max": 5,  # seconds
            "memory_usage_max": 512  # MB
        },
        "error_simulation": {
            "network_failure_rate": 0.1,
            "parsing_error_rate": 0.05,
            "timeout_rate": 0.02
        }
    }


@pytest.fixture
def temp_directory():
    """Temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_csv_data():
    """Generate sample CSV data for testing."""
    return pd.DataFrame({
        'Parcel ID': ['12345-001', '12345-002', '12345-003'],
        'Amount Bid at Tax Sale': ['$1,500.00', '$2,250.50', '$850.00'],
        'Description': [
            'LOT 1 CREEK MEADOWS SUBDIVISION 2.5 AC',
            'TRACT B RIVERSIDE PROPERTY 1.8 AC SPRING',
            'PARCEL A HIGHLAND ESTATES 0.75 AC'
        ],
        'Assessed Value': ['$15,000', '$22,500', '$8,500'],
        'Owner Name': ['John Doe', 'Jane Smith', 'Bob Johnson'],
        'County': ['Baldwin', 'Baldwin', 'Baldwin']
    })


@pytest.fixture
def sample_scraped_html():
    """Sample HTML response for scraping tests."""
    return """
    <html>
    <body>
    <table id="ador-delinquent-search-results">
        <tr>
            <th>Parcel ID</th>
            <th>Amount</th>
            <th>Description</th>
            <th>County</th>
        </tr>
        <tr>
            <td>12345-001</td>
            <td>$1,500.00</td>
            <td>LOT 1 CREEK MEADOWS SUBDIVISION 2.5 AC</td>
            <td>Baldwin</td>
        </tr>
        <tr>
            <td>12345-002</td>
            <td>$2,250.50</td>
            <td>TRACT B RIVERSIDE PROPERTY 1.8 AC SPRING</td>
            <td>Baldwin</td>
        </tr>
    </table>
    <a href="?offset=50">Next</a>
    </body>
    </html>
    """


@pytest.fixture
def mock_requests():
    """Mock HTTP requests for scraping tests."""
    with requests_mock.Mocker() as m:
        yield m


@pytest.fixture
def auction_parser():
    """Factory for AuctionParser instances."""
    return AuctionParser(
        min_acres=1.0,
        max_acres=5.0,
        max_price=20000.0,
        infer_acres=True
    )


@pytest.fixture
def mock_ador_response(sample_scraped_html):
    """Mock ADOR website response."""
    def _mock_response(county_code='05', page=1, records_count=2):
        return sample_scraped_html
    return _mock_response


@pytest.fixture(scope="session")
def error_test_cases():
    """Comprehensive error test cases for AI validation."""
    return {
        "network_errors": [
            {"error_type": "ConnectionError", "description": "Network unreachable"},
            {"error_type": "Timeout", "description": "Request timeout"},
            {"error_type": "HTTPError", "description": "HTTP 500 error", "status_code": 500}
        ],
        "parsing_errors": [
            {"error_type": "ParseError", "description": "Invalid HTML structure"},
            {"error_type": "ValueError", "description": "Invalid data format"},
            {"error_type": "KeyError", "description": "Missing required field"}
        ],
        "validation_errors": [
            {"error_type": "CountyValidationError", "description": "Invalid county code", "input": "99"},
            {"error_type": "DataValidationError", "description": "Invalid price format", "input": "invalid_price"},
            {"error_type": "FilterValidationError", "description": "Invalid filter range", "input": {"min": 10, "max": 5}}
        ]
    }


@pytest.fixture
def performance_benchmark_data():
    """Test data for performance benchmarking."""
    return {
        "small_dataset": 100,
        "medium_dataset": 1000,
        "large_dataset": 10000,
        "memory_test_size": 100000
    }


class PropertyDataFactory(Factory):
    """Factory for generating realistic property data."""

    parcel_id = Sequence(lambda n: f"TEST-{n:06d}")
    amount = FactoryFaker('random_int', min=500, max=20000)
    acreage = FactoryFaker('random_element', elements=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0])
    description = FactoryFaker('sentence', nb_words=8)
    assessed_value = FactoryFaker('random_int', min=5000, max=50000)
    owner_name = FactoryFaker('name')
    county = FactoryFaker('random_element', elements=list(ALABAMA_COUNTY_CODES.values()))

    @classmethod
    def with_water_features(cls, **kwargs):
        """Generate property with water features."""
        water_descriptions = [
            "PROPERTY WITH CREEK ACCESS 2.5 AC",
            "RIVERSIDE LOT WITH SPRING 1.8 AC",
            "WATERFRONT PROPERTY ON LAKE 3.2 AC",
            "TRACT WITH STREAM FRONTAGE 2.1 AC"
        ]
        kwargs['description'] = fake.random_element(water_descriptions)
        return cls(**kwargs)


@pytest.fixture
def property_factory():
    """Factory fixture for generating test properties."""
    return PropertyDataFactory


# Store original open to avoid recursion
_original_open = open


@pytest.fixture(autouse=True)
def mock_file_operations():
    """Auto-used fixture to prevent actual file operations during tests."""
    with patch('builtins.open', mock_safe_file_operations):
        yield


def mock_safe_file_operations(*args, **kwargs):
    """Safe mock for file operations that prevents accidental file creation."""
    if len(args) > 0 and isinstance(args[0], (str, Path)):
        file_path = str(args[0])
        # Allow reading test fixtures, temp files, and fixture paths
        if 'test' in file_path.lower() or 'fixture' in file_path.lower() or 'temp' in file_path.lower() or 'tmp' in file_path.lower():
            return _original_open(*args, **kwargs)
        else:
            # Return a mock for write operations to prevent accidental file creation
            return Mock()
    return _original_open(*args, **kwargs)


@pytest.fixture
def ai_test_validator():
    """Validator for AI-testable outputs and behaviors."""
    class AITestValidator:
        def validate_error_structure(self, error_data: Dict[str, Any]) -> bool:
            """Validate that error data follows AI-readable format."""
            required_fields = ['code', 'category', 'severity', 'context', 'suggested_actions']
            return all(field in error_data for field in required_fields)

        def validate_performance_metrics(self, metrics: Dict[str, Any]) -> bool:
            """Validate performance metrics are within acceptable ranges."""
            required_metrics = ['duration', 'records_processed', 'records_per_second']
            return all(metric in metrics for metric in required_metrics)

        def validate_test_specification(self, spec: Dict[str, Any]) -> bool:
            """Validate that test specifications are machine-readable."""
            required_fields = ['test_case', 'input', 'expected_output', 'performance_thresholds']
            return all(field in spec for field in required_fields)

    return AITestValidator()


@pytest.fixture
def frozen_time():
    """Freeze time for consistent testing."""
    with freeze_time("2025-09-18 12:00:00"):
        yield


# Test data schemas for AI validation
@pytest.fixture(scope="session")
def test_schemas():
    """JSON schemas for validating test data structures."""
    return {
        "property_record": {
            "type": "object",
            "required": ["parcel_id", "amount", "description", "county"],
            "properties": {
                "parcel_id": {"type": "string"},
                "amount": {"type": "number", "minimum": 0},
                "description": {"type": "string"},
                "county": {"type": "string"},
                "acreage": {"type": "number", "minimum": 0},
                "water_score": {"type": "number", "minimum": 0}
            }
        },
        "error_response": {
            "type": "object",
            "required": ["code", "category", "severity"],
            "properties": {
                "code": {"type": "string"},
                "category": {"type": "string"},
                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "context": {"type": "object"},
                "suggested_actions": {"type": "array", "items": {"type": "string"}}
            }
        },
        "performance_metrics": {
            "type": "object",
            "required": ["duration", "records_processed"],
            "properties": {
                "duration": {"type": "number", "minimum": 0},
                "records_processed": {"type": "integer", "minimum": 0},
                "records_per_second": {"type": "number", "minimum": 0},
                "memory_usage_mb": {"type": "number", "minimum": 0}
            }
        }
    }


# Parametrized test data for comprehensive coverage
@pytest.fixture(scope="session")
def county_test_matrix():
    """Test matrix for all Alabama counties."""
    return [
        {"code": code, "name": name, "expected_records_range": (0, 10000)}
        for code, name in ALABAMA_COUNTY_CODES.items()
    ]


@pytest.fixture
def mock_logger():
    """Mock logger for testing logging functionality."""
    return Mock()


# Cleanup fixture
@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Auto-cleanup any test files created during testing."""
    yield
    # Cleanup logic here if needed
    test_files_pattern = ["test_*.csv", "test_*.json", "test_*.log"]
    for pattern in test_files_pattern:
        for file_path in Path('.').glob(pattern):
            try:
                file_path.unlink()
            except (FileNotFoundError, PermissionError):
                pass  # Already cleaned up or in use