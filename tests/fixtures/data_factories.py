"""
Comprehensive test data factories for AI-testable data generation.

This module provides Factory Boy factories for generating consistent,
realistic test data that AI systems can use for automated testing.
"""

import random
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import factory
import pandas as pd
from faker import Faker
from factory import fuzzy

# Import project components
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.scraper import ALABAMA_COUNTY_CODES
from config.settings import PRIMARY_WATER_KEYWORDS, SECONDARY_WATER_KEYWORDS


# Initialize Faker with a fixed seed for consistent test data
fake = Faker()
fake.seed_instance(42)


class CountyFactory(factory.Factory):
    """Factory for generating Alabama county data."""

    class Meta:
        model = dict

    code = factory.LazyFunction(lambda: fake.random_element(list(ALABAMA_COUNTY_CODES.keys())))
    name = factory.LazyAttribute(lambda obj: ALABAMA_COUNTY_CODES[obj.code])

    @classmethod
    def create_all_counties(cls) -> List[Dict[str, str]]:
        """Generate data for all 67 Alabama counties."""
        return [{"code": code, "name": name} for code, name in ALABAMA_COUNTY_CODES.items()]


class PropertyDataFactory(factory.Factory):
    """Factory for generating realistic property auction data."""

    class Meta:
        model = dict

    # Core property identification
    parcel_id = factory.Sequence(lambda n: f"{fake.random_element(['12345', '23456', '34567'])}-{n:03d}")
    cs_number = factory.LazyAttribute(lambda obj: obj.parcel_id)  # Often the same as parcel_id

    # Financial data
    amount = fuzzy.FuzzyInteger(low=500, high=20000)  # Bid amount
    assessed_value = factory.LazyAttribute(lambda obj: obj.amount + fuzzy.FuzzyInteger(5000, 50000).fuzz())
    minimum_bid = factory.LazyAttribute(lambda obj: max(obj.amount * 0.8, 100))

    # Property characteristics
    acreage = factory.LazyFunction(lambda: fake.random_element([0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]))

    # Location and description
    county = factory.LazyFunction(lambda: fake.random_element(list(ALABAMA_COUNTY_CODES.values())))
    description = factory.LazyFunction(lambda: fake.sentence(nb_words=8).upper())

    # Owner information
    owner_name = factory.Faker('name')
    owner_address = factory.Faker('address')

    # Temporal data
    year_sold = factory.LazyFunction(lambda: fake.random_element([2022, 2023, 2024]))
    sale_date = factory.LazyFunction(lambda: fake.date_between(start_date='-2y', end_date='today'))

    # Calculated fields (would be computed by the system)
    price_per_acre = factory.LazyAttribute(lambda obj: round(obj.amount / obj.acreage, 2) if obj.acreage > 0 else 0)
    water_score = factory.LazyFunction(lambda: fake.random_int(min=0, max=5))
    investment_score = factory.LazyFunction(lambda: round(fake.random.uniform(0.0, 10.0), 1))

    @classmethod
    def with_water_features(cls, water_type: str = "random", **kwargs) -> Dict[str, Any]:
        """Generate property data with specific water features."""
        water_descriptions = {
            "creek": [
                "LOT WITH CREEK FRONTAGE {acreage} AC",
                "PROPERTY ON DEER CREEK {acreage} ACRES",
                "CREEK ACCESS TRACT {acreage} AC",
                "MEADOWBROOK CREEK PROPERTY {acreage} ACRES"
            ],
            "river": [
                "RIVERSIDE PROPERTY {acreage} AC",
                "RIVER FRONTAGE LOT {acreage} ACRES",
                "PROPERTY ON CAHABA RIVER {acreage} AC",
                "WATERFRONT RIVER ACCESS {acreage} ACRES"
            ],
            "lake": [
                "LAKE FRONT PROPERTY {acreage} AC",
                "LOT ON SMITH LAKE {acreage} ACRES",
                "LAKESIDE TRACT {acreage} AC",
                "WATERFRONT LAKE ACCESS {acreage} ACRES"
            ],
            "spring": [
                "PROPERTY WITH NATURAL SPRING {acreage} AC",
                "SPRING-FED CREEK LOT {acreage} ACRES",
                "ARTESIAN SPRING PROPERTY {acreage} AC",
                "LOT WITH FRESHWATER SPRING {acreage} ACRES"
            ],
            "stream": [
                "STREAM FRONTAGE PROPERTY {acreage} AC",
                "LOT ON MOUNTAIN STREAM {acreage} ACRES",
                "PROPERTY WITH STREAM ACCESS {acreage} AC",
                "CREEK STREAM FRONTAGE {acreage} ACRES"
            ]
        }

        if water_type == "random":
            water_type = fake.random_element(list(water_descriptions.keys()))

        acreage = kwargs.get('acreage', fake.random_element([1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]))
        description_template = fake.random_element(water_descriptions[water_type])

        kwargs.update({
            'description': description_template.format(acreage=acreage),
            'water_score': fake.random_int(min=3, max=10),  # Higher water score
            'acreage': acreage
        })

        return cls(**kwargs)

    @classmethod
    def create_batch_with_distribution(cls, size: int, water_percentage: float = 0.3) -> List[Dict[str, Any]]:
        """Create a batch of properties with realistic distribution of water features."""
        properties = []
        water_count = int(size * water_percentage)

        # Create properties with water features
        for _ in range(water_count):
            properties.append(cls.with_water_features())

        # Create regular properties
        for _ in range(size - water_count):
            properties.append(cls())

        return properties


class CSVDataFactory(factory.Factory):
    """Factory for generating realistic CSV file data structures."""

    class Meta:
        model = dict

    @classmethod
    def create_ador_csv_format(cls, num_records: int = 100, include_headers: bool = True) -> pd.DataFrame:
        """Generate data in ADOR CSV format."""
        properties = PropertyDataFactory.create_batch_with_distribution(num_records)

        data = []
        for prop in properties:
            # Format data to match ADOR CSV structure
            record = {
                'Parcel ID': prop['parcel_id'],
                'CS Number': prop['cs_number'],
                'Amount Bid at Tax Sale': f"${prop['amount']:,.2f}",
                'Assessed Value': f"${prop['assessed_value']:,.2f}",
                'Description': prop['description'],
                'Owner Name': prop['owner_name'],
                'County': prop['county'],
                'Year Sold': str(prop['year_sold'])
            }
            data.append(record)

        return pd.DataFrame(data)

    @classmethod
    def create_alternative_csv_format(cls, num_records: int = 50) -> pd.DataFrame:
        """Generate data in alternative CSV format (different column names)."""
        properties = PropertyDataFactory.create_batch_with_distribution(num_records)

        data = []
        for prop in properties:
            # Alternative column naming convention
            record = {
                'tax_id': prop['parcel_id'],
                'sale_amount': prop['amount'],
                'market_value': prop['assessed_value'],
                'property_description': prop['description'],
                'property_owner': prop['owner_name'],
                'county_name': prop['county'],
                'acres': prop['acreage'],
                'sale_year': prop['year_sold']
            }
            data.append(record)

        return pd.DataFrame(data)


class HTMLResponseFactory(factory.Factory):
    """Factory for generating realistic HTML responses from ADOR website."""

    class Meta:
        model = dict

    @classmethod
    def create_ador_search_response(cls, num_records: int = 50, county: str = "Baldwin",
                                  has_next_page: bool = False) -> str:
        """Generate realistic ADOR search results HTML."""
        properties = PropertyDataFactory.create_batch_with_distribution(num_records)

        # Build table rows
        table_rows = []
        for prop in properties:
            row = f"""
            <tr>
                <td>{prop['parcel_id']}</td>
                <td>{prop['cs_number']}</td>
                <td>${prop['amount']:,.2f}</td>
                <td>${prop['assessed_value']:,.2f}</td>
                <td>{prop['description']}</td>
                <td>{prop['owner_name']}</td>
                <td>{county}</td>
                <td>{prop['year_sold']}</td>
            </tr>
            """
            table_rows.append(row)

        # Build pagination links
        pagination = ""
        if has_next_page:
            pagination = '<a href="?offset=50&county=05">Next</a>'

        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Alabama Department of Revenue - Delinquent Property Search</title>
        </head>
        <body>
            <div id="search-results">
                <table id="ador-delinquent-search-results" class="results-table">
                    <thead>
                        <tr>
                            <th>Parcel ID</th>
                            <th>CS Number</th>
                            <th>Amount Bid at Tax Sale</th>
                            <th>Assessed Value</th>
                            <th>Description</th>
                            <th>Owner Name</th>
                            <th>County</th>
                            <th>Year Sold</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(table_rows)}
                    </tbody>
                </table>
                <div class="pagination">
                    {pagination}
                </div>
            </div>
        </body>
        </html>
        """

        return html_template

    @classmethod
    def create_empty_response(cls, county: str = "Test") -> str:
        """Generate HTML response for counties with no data."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Alabama Department of Revenue - Delinquent Property Search</title>
        </head>
        <body>
            <div id="search-results">
                <p>No delinquent properties found for {county} County.</p>
            </div>
        </body>
        </html>
        """

    @classmethod
    def create_error_response(cls, error_type: str = "server_error") -> str:
        """Generate HTML error responses for testing error handling."""
        error_messages = {
            "server_error": "Internal Server Error - Please try again later",
            "not_found": "Page not found - Invalid county code",
            "timeout": "Request timeout - Server is temporarily unavailable",
            "maintenance": "Site under maintenance - Please try again later"
        }

        message = error_messages.get(error_type, "Unknown error occurred")

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error - Alabama Department of Revenue</title>
        </head>
        <body>
            <div class="error">
                <h1>Error</h1>
                <p>{message}</p>
            </div>
        </body>
        </html>
        """


class ErrorTestDataFactory(factory.Factory):
    """Factory for generating error test scenarios."""

    class Meta:
        model = dict

    @classmethod
    def create_network_error_scenarios(cls) -> List[Dict[str, Any]]:
        """Generate network error test scenarios."""
        return [
            {
                "error_type": "ConnectionError",
                "description": "Network connection failed",
                "http_status": None,
                "should_retry": True,
                "max_retries": 3,
                "expected_exception": "NetworkError"
            },
            {
                "error_type": "Timeout",
                "description": "Request timeout after 30 seconds",
                "http_status": None,
                "should_retry": True,
                "max_retries": 2,
                "expected_exception": "NetworkError"
            },
            {
                "error_type": "HTTPError",
                "description": "HTTP 500 Internal Server Error",
                "http_status": 500,
                "should_retry": True,
                "max_retries": 3,
                "expected_exception": "NetworkError"
            },
            {
                "error_type": "HTTPError",
                "description": "HTTP 404 Not Found",
                "http_status": 404,
                "should_retry": False,
                "max_retries": 0,
                "expected_exception": "NetworkError"
            }
        ]

    @classmethod
    def create_validation_error_scenarios(cls) -> List[Dict[str, Any]]:
        """Generate validation error test scenarios."""
        return [
            {
                "error_type": "CountyValidationError",
                "input_value": "99",
                "field": "county_code",
                "description": "Invalid county code - out of range",
                "recoverable": False,
                "suggested_action": "use_valid_county_code"
            },
            {
                "error_type": "CountyValidationError",
                "input_value": "XYZ",
                "field": "county_name",
                "description": "Invalid county name - not in Alabama",
                "recoverable": False,
                "suggested_action": "check_county_list"
            },
            {
                "error_type": "DataValidationError",
                "input_value": "invalid_price",
                "field": "amount",
                "description": "Invalid price format",
                "recoverable": True,
                "suggested_action": "normalize_price_format"
            },
            {
                "error_type": "FilterValidationError",
                "input_value": {"min_acres": 10, "max_acres": 5},
                "field": "acreage_range",
                "description": "Invalid range - minimum greater than maximum",
                "recoverable": True,
                "suggested_action": "fix_range_values"
            }
        ]

    @classmethod
    def create_parsing_error_scenarios(cls) -> List[Dict[str, Any]]:
        """Generate parsing error test scenarios."""
        return [
            {
                "error_type": "ParseError",
                "input_data": "<html><table><tr><td>Invalid</html>",
                "description": "Malformed HTML structure",
                "recoverable": False,
                "suggested_action": "retry_request"
            },
            {
                "error_type": "ParseError",
                "input_data": '{"invalid": "json",,}',
                "description": "Invalid JSON format",
                "recoverable": False,
                "suggested_action": "validate_data_format"
            }
        ]


class PerformanceTestDataFactory(factory.Factory):
    """Factory for generating performance test data."""

    class Meta:
        model = dict

    @classmethod
    def create_performance_scenarios(cls) -> List[Dict[str, Any]]:
        """Generate performance test scenarios."""
        return [
            {
                "scenario": "small_dataset",
                "record_count": 100,
                "expected_duration_max": 5.0,
                "expected_memory_mb_max": 50,
                "expected_rate_min": 20
            },
            {
                "scenario": "medium_dataset",
                "record_count": 1000,
                "expected_duration_max": 30.0,
                "expected_memory_mb_max": 200,
                "expected_rate_min": 30
            },
            {
                "scenario": "large_dataset",
                "record_count": 10000,
                "expected_duration_max": 300.0,
                "expected_memory_mb_max": 1000,
                "expected_rate_min": 50
            },
            {
                "scenario": "stress_test",
                "record_count": 50000,
                "expected_duration_max": 1800.0,
                "expected_memory_mb_max": 2000,
                "expected_rate_min": 25
            }
        ]

    @classmethod
    def create_benchmark_data(cls, scenario: str) -> Dict[str, Any]:
        """Create benchmark data for specific performance scenarios."""
        scenarios = {s["scenario"]: s for s in cls.create_performance_scenarios()}

        if scenario not in scenarios:
            raise ValueError(f"Unknown scenario: {scenario}")

        config = scenarios[scenario]
        properties = PropertyDataFactory.create_batch_with_distribution(config["record_count"])

        return {
            "data": properties,
            "performance_expectations": {
                "max_duration": config["expected_duration_max"],
                "max_memory_mb": config["expected_memory_mb_max"],
                "min_rate": config["expected_rate_min"]
            },
            "metadata": {
                "scenario": scenario,
                "record_count": config["record_count"],
                "generated_at": datetime.now().isoformat()
            }
        }


class SyncLogFactory(factory.Factory):
    """Factory for generating sync operation log data."""
    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    device_id = factory.Faker('uuid4')
    operation = fuzzy.FuzzyChoice(['delta', 'full', 'upload', 'download'])
    status = fuzzy.FuzzyChoice(['success', 'failed', 'partial'])
    records_processed = fuzzy.FuzzyInteger(0, 10000)
    conflicts_detected = fuzzy.FuzzyInteger(0, 100)
    conflicts_resolved = factory.LazyAttribute(lambda o: fake.random_int(0, o.conflicts_detected))
    started_at = factory.Faker('date_time_this_year', tzinfo=None)
    completed_at = factory.LazyAttribute(lambda o: o.started_at + timedelta(seconds=fake.random_int(1, 600)))
    duration_seconds = factory.LazyAttribute(lambda o: (o.completed_at - o.started_at).total_seconds())
    error_message = None
    algorithm_validation_passed = True

    @classmethod
    def successful_sync(cls, operation: str = 'delta', **kwargs) -> Dict[str, Any]:
        """Generate a successful sync log."""
        kwargs.update({
            'operation': operation,
            'status': 'success',
            'error_message': None,
            'conflicts_detected': 0,
            'conflicts_resolved': 0,
        })
        return cls(**kwargs)

    @classmethod
    def failed_sync(cls, error_type: str = 'network', **kwargs) -> Dict[str, Any]:
        """Generate a failed sync log with an error message."""
        error_messages = {
            'network': 'Network connection timed out.',
            'validation': 'Data validation failed: checksum mismatch.',
            'server': 'Internal Server Error (500).',
        }
        kwargs.update({
            'status': 'failed',
            'error_message': error_messages.get(error_type, 'Unknown error.'),
            'completed_at': None,
            'duration_seconds': None,
        })
        return cls(**kwargs)

    @classmethod
    def with_conflicts(cls, **kwargs) -> Dict[str, Any]:
        """Generate a sync log with detected and resolved conflicts."""
        conflicts = fake.random_int(1, 50)
        kwargs.update({
            'status': 'partial',
            'conflicts_detected': conflicts,
            'conflicts_resolved': fake.random_int(1, conflicts),
        })
        return cls(**kwargs)


class UserProfileFactory(factory.Factory):
    """Factory for generating user profile data."""
    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    full_name = factory.Faker('name')
    email = factory.Faker('email')
    phone = factory.Faker('phone_number')
    address = factory.Faker('street_address')
    city = factory.Faker('city')
    state = factory.Faker('state_abbr')
    zip_code = factory.Faker('zipcode')
    max_investment_amount = fuzzy.FuzzyFloat(50000, 1000000)
    min_acreage = fuzzy.FuzzyFloat(1.0, 20.0)
    max_acreage = factory.LazyAttribute(lambda o: o.min_acreage + fake.random_int(20, 200))
    preferred_counties = factory.LazyFunction(lambda: json.dumps(fake.random_elements(
        elements=list(ALABAMA_COUNTY_CODES.values()), length=fake.random_int(1, 5), unique=True
    )))
    created_at = factory.Faker('date_time_this_year', tzinfo=None)
    updated_at = factory.LazyAttribute(lambda o: o.created_at)
    is_active = True

    @classmethod
    def aggressive_investor(cls, **kwargs) -> Dict[str, Any]:
        """Generate a profile for an aggressive investor."""
        kwargs.update({
            'max_investment_amount': fake.random_int(500000, 5000000),
            'min_acreage': fake.random_int(10, 50),
            'max_acreage': fake.random_int(200, 1000),
        })
        return cls(**kwargs)

    @classmethod
    def conservative_investor(cls, **kwargs) -> Dict[str, Any]:
        """Generate a profile for a conservative investor."""
        kwargs.update({
            'max_investment_amount': fake.random_int(10000, 50000),
            'min_acreage': 0.5,
            'max_acreage': 5.0,
        })
        return cls(**kwargs)

    @classmethod
    def minimal_profile(cls, **kwargs) -> Dict[str, Any]:
        """Generate a profile with only required fields."""
        kwargs.update({
            'max_investment_amount': None,
            'min_acreage': None,
            'max_acreage': None,
            'preferred_counties': None,
        })
        return cls(**kwargs)


class PropertyApplicationFactory(factory.Factory):
    """Factory for generating property application tracking data."""
    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    user_profile_id = factory.Faker('uuid4')
    property_id = factory.Faker('uuid4')
    cs_number = factory.Sequence(lambda n: f"CS-{n:05d}")
    parcel_number = factory.Sequence(lambda n: f"PN-01-02-03-{n:04d}")
    sale_year = factory.Faker('year')
    county = factory.LazyFunction(lambda: fake.random_element(list(ALABAMA_COUNTY_CODES.values())))
    description = factory.Faker('text', max_nb_chars=200)
    assessed_name = factory.Faker('name')
    amount = fuzzy.FuzzyFloat(1000, 75000)
    acreage = fuzzy.FuzzyFloat(0.5, 100.0)
    investment_score = fuzzy.FuzzyFloat(60.0, 98.0)
    estimated_total_cost = factory.LazyAttribute(lambda o: o.amount * 1.15)
    roi_estimate = fuzzy.FuzzyFloat(8.0, 30.0)
    status = fuzzy.FuzzyChoice(['draft', 'submitted', 'price_requested', 'price_received', 'completed', 'cancelled'])
    notes = factory.Faker('paragraph')
    price_request_date = None
    price_received_date = None
    final_price = None
    created_at = factory.Faker('date_time_this_year', tzinfo=None)
    updated_at = factory.LazyAttribute(lambda o: o.created_at)

    @classmethod
    def draft_application(cls, **kwargs) -> Dict[str, Any]:
        """Generate a draft application."""
        kwargs.update({
            'status': 'draft',
            'price_request_date': None,
            'price_received_date': None,
            'final_price': None,
        })
        return cls(**kwargs)

    @classmethod
    def submitted_application(cls, **kwargs) -> Dict[str, Any]:
        """Generate a submitted application awaiting price."""
        now = datetime.now()
        kwargs.update({
            'status': 'submitted',
            'price_request_date': now - timedelta(days=fake.random_int(1, 10)),
            'price_received_date': None,
            'final_price': None,
        })
        return cls(**kwargs)

    @classmethod
    def with_price_received(cls, **kwargs) -> Dict[str, Any]:
        """Generate an application where the final price has been received."""
        request_date = datetime.now() - timedelta(days=fake.random_int(10, 20))
        # Generate base application first to get the amount
        base_app = cls(**kwargs)
        final_price = base_app['amount'] * fuzzy.FuzzyFloat(1.2, 1.5).fuzz()
        base_app.update({
            'status': 'price_received',
            'price_request_date': request_date,
            'price_received_date': request_date + timedelta(days=fake.random_int(1, 9)),
            'final_price': round(final_price, 2),
        })
        return base_app


class ApplicationBatchFactory(factory.Factory):
    """Factory for generating application batch data."""
    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    user_profile_id = factory.Faker('uuid4')
    batch_name = factory.Faker('catch_phrase')
    total_estimated_investment = fuzzy.FuzzyFloat(10000, 1000000)
    forms_generated = fuzzy.FuzzyInteger(1, 100)
    applications_submitted = factory.LazyAttribute(lambda o: fake.random_int(0, o.forms_generated))
    prices_received = factory.LazyAttribute(lambda o: fake.random_int(0, o.applications_submitted))
    status = fuzzy.FuzzyChoice(['draft', 'in_progress', 'completed', 'cancelled'])
    created_at = factory.Faker('date_time_this_year', tzinfo=None)
    updated_at = factory.LazyAttribute(lambda o: o.created_at)

    @classmethod
    def small_batch(cls, **kwargs) -> Dict[str, Any]:
        """Generate a small batch of applications."""
        forms_gen = fake.random_int(1, 5)
        apps_sub = fake.random_int(0, forms_gen)
        kwargs.update({
            'forms_generated': forms_gen,
            'applications_submitted': apps_sub,
            'prices_received': fake.random_int(0, apps_sub),
            'status': 'in_progress',
        })
        return cls(**kwargs)

    @classmethod
    def large_batch(cls, **kwargs) -> Dict[str, Any]:
        """Generate a large batch of applications."""
        forms_gen = fake.random_int(50, 150)
        apps_sub = fake.random_int(20, forms_gen)
        kwargs.update({
            'forms_generated': forms_gen,
            'applications_submitted': apps_sub,
            'prices_received': fake.random_int(10, apps_sub),
            'status': 'in_progress',
        })
        return cls(**kwargs)

    @classmethod
    def completed_batch(cls, **kwargs) -> Dict[str, Any]:
        """Generate a completed batch where all steps are finished."""
        count = fake.random_int(10, 50)
        kwargs.update({
            'forms_generated': count,
            'applications_submitted': count,
            'prices_received': count,
            'status': 'completed',
        })
        return cls(**kwargs)


class ApplicationNotificationFactory(factory.Factory):
    """Factory for generating application notification data."""
    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    user_profile_id = factory.Faker('uuid4')
    property_id = factory.Faker('uuid4')
    notification_type = fuzzy.FuzzyChoice(['price_update', 'status_change', 'deadline_reminder', 'error_alert'])
    title = factory.Faker('sentence', nb_words=5)
    message = factory.Faker('paragraph')
    state_email_expected = factory.Faker('boolean')
    state_email_received = factory.LazyAttribute(lambda o: o.state_email_expected and fake.boolean())
    price_amount = None
    read_at = None
    action_required = factory.Faker('boolean')
    action_deadline = None
    created_at = factory.Faker('date_time_this_year', tzinfo=None)

    @classmethod
    def price_notification(cls, **kwargs) -> Dict[str, Any]:
        """Generate a price update notification."""
        kwargs.update({
            'notification_type': 'price_update',
            'title': 'Price Received for Parcel',
            'state_email_expected': True,
            'state_email_received': True,
            'price_amount': fuzzy.FuzzyFloat(2000, 80000).fuzz(),
            'action_required': True,
        })
        return cls(**kwargs)

    @classmethod
    def deadline_reminder(cls, **kwargs) -> Dict[str, Any]:
        """Generate a deadline reminder notification."""
        kwargs.update({
            'notification_type': 'deadline_reminder',
            'title': 'Action Required: Application Deadline Approaching',
            'action_required': True,
            'action_deadline': datetime.now() + timedelta(days=fake.random_int(3, 14)),
        })
        return cls(**kwargs)

    @classmethod
    def error_alert(cls, **kwargs) -> Dict[str, Any]:
        """Generate an error alert notification."""
        kwargs.update({
            'notification_type': 'error_alert',
            'title': 'Error Processing Application Batch',
            'message': 'There was an error processing your recent application batch. Please review.',
            'action_required': True,
            'read_at': None,
        })
        return cls(**kwargs)


# AI-friendly factory registry
AI_FACTORY_REGISTRY = {
    "property_data": PropertyDataFactory,
    "county_data": CountyFactory,
    "csv_data": CSVDataFactory,
    "html_response": HTMLResponseFactory,
    "error_scenarios": ErrorTestDataFactory,
    "performance_data": PerformanceTestDataFactory,
    "sync_log": SyncLogFactory,
    "user_profile": UserProfileFactory,
    "property_application": PropertyApplicationFactory,
    "application_batch": ApplicationBatchFactory,
    "application_notification": ApplicationNotificationFactory,
}


def get_factory(factory_name: str):
    """AI-friendly factory getter."""
    if factory_name not in AI_FACTORY_REGISTRY:
        raise ValueError(f"Unknown factory: {factory_name}. Available: {list(AI_FACTORY_REGISTRY.keys())}")

    return AI_FACTORY_REGISTRY[factory_name]


def generate_test_dataset(factory_name: str, method_name: str, **kwargs) -> Any:
    """AI-friendly test data generation interface."""
    factory = get_factory(factory_name)

    if not hasattr(factory, method_name):
        raise ValueError(f"Factory {factory_name} does not have method {method_name}")

    method = getattr(factory, method_name)
    return method(**kwargs)


# Convenience functions for backwards compatibility
def create_sample_property_data(**kwargs) -> Dict[str, Any]:
    """Create a single sample property data dictionary."""
    return PropertyDataFactory(**kwargs)


def create_sample_csv_content(num_records: int = 10) -> str:
    """Create sample CSV content as a string."""
    df = CSVDataFactory.create_ador_csv_format(num_records=num_records)
    return df.to_csv(index=False)


def create_complex_property_data(num_records: int = 50) -> List[Dict[str, Any]]:
    """Create a batch of complex property data with varied characteristics."""
    return PropertyDataFactory.create_batch_with_distribution(num_records, water_percentage=0.4)


def create_water_feature_data(water_type: str = "random", **kwargs) -> Dict[str, Any]:
    """Create property data with specific water features."""
    return PropertyDataFactory.with_water_features(water_type=water_type, **kwargs)