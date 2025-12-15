"""
Factory validation tests to ensure AI-testable data generation works correctly.

These tests validate that the data factories produce consistent, realistic
data that can be reliably used for AI-driven testing.
"""

import pytest
import pandas as pd
from typing import Dict, List, Any

from data_factories import (
    PropertyDataFactory, CountyFactory, CSVDataFactory, HTMLResponseFactory,
    ErrorTestDataFactory, PerformanceTestDataFactory, get_factory, generate_test_dataset
)


class TestPropertyDataFactory:
    """Test the property data factory functionality."""

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_basic_property_generation(self):
        """Test basic property data generation."""
        property_data = PropertyDataFactory()

        # Validate required fields exist
        required_fields = ['parcel_id', 'amount', 'acreage', 'county', 'description']
        for field in required_fields:
            assert field in property_data, f"Missing required field: {field}"

        # Validate data types and ranges
        assert isinstance(property_data['amount'], int)
        assert 500 <= property_data['amount'] <= 20000
        assert property_data['acreage'] > 0
        assert property_data['county'] in ['Autauga', 'Baldwin', 'Barbour', 'Bibb']  # Just check some known counties

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_water_feature_generation(self):
        """Test generation of properties with water features."""
        water_types = ['creek', 'river', 'lake', 'spring', 'stream']

        for water_type in water_types:
            property_data = PropertyDataFactory.with_water_features(water_type=water_type)

            # Validate water feature is in description
            description = property_data['description'].lower()
            assert water_type in description, f"Water type {water_type} not found in description"

            # Validate higher water score
            assert property_data['water_score'] >= 3, "Water properties should have higher water scores"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_batch_generation_with_distribution(self):
        """Test batch generation with realistic water feature distribution."""
        batch_size = 100
        water_percentage = 0.3
        properties = PropertyDataFactory.create_batch_with_distribution(
            size=batch_size,
            water_percentage=water_percentage
        )

        assert len(properties) == batch_size

        # Count properties with water features (water_score > 0)
        water_properties = [p for p in properties if p['water_score'] > 2]
        actual_water_percentage = len(water_properties) / batch_size

        # Allow some variance in the distribution
        assert 0.2 <= actual_water_percentage <= 0.4, f"Water percentage {actual_water_percentage} outside expected range"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_property_data_consistency(self):
        """Test that property data is internally consistent."""
        for _ in range(10):  # Test multiple generated properties
            property_data = PropertyDataFactory()

            # Price per acre should be calculated correctly
            if property_data['acreage'] > 0:
                expected_price_per_acre = property_data['amount'] / property_data['acreage']
                assert abs(property_data['price_per_acre'] - expected_price_per_acre) < 0.01

            # Assessed value should be higher than bid amount
            assert property_data['assessed_value'] >= property_data['amount']


class TestCountyFactory:
    """Test the county data factory functionality."""

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_county_generation(self):
        """Test county data generation."""
        county_data = CountyFactory()

        assert 'code' in county_data
        assert 'name' in county_data
        assert len(county_data['code']) == 2
        assert county_data['code'].isdigit()

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_all_counties_generation(self):
        """Test generation of all Alabama counties."""
        all_counties = CountyFactory.create_all_counties()

        assert len(all_counties) == 67  # Alabama has 67 counties
        codes = [county['code'] for county in all_counties]
        names = [county['name'] for county in all_counties]

        # Validate no duplicates
        assert len(set(codes)) == 67
        assert len(set(names)) == 67

        # Validate known counties exist
        known_counties = {'01': 'Autauga', '05': 'Baldwin', '38': 'Jefferson'}
        for code, name in known_counties.items():
            assert {'code': code, 'name': name} in all_counties


class TestCSVDataFactory:
    """Test the CSV data factory functionality."""

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_ador_csv_format_generation(self):
        """Test ADOR CSV format generation."""
        num_records = 50
        csv_data = CSVDataFactory.create_ador_csv_format(num_records=num_records)

        assert isinstance(csv_data, pd.DataFrame)
        assert len(csv_data) == num_records

        # Validate expected ADOR columns
        expected_columns = [
            'Parcel ID', 'CS Number', 'Amount Bid at Tax Sale',
            'Assessed Value', 'Description', 'Owner Name', 'County', 'Year Sold'
        ]
        for column in expected_columns:
            assert column in csv_data.columns

        # Validate data formatting
        first_row = csv_data.iloc[0]
        assert first_row['Amount Bid at Tax Sale'].startswith('$')
        assert first_row['Assessed Value'].startswith('$')

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_alternative_csv_format_generation(self):
        """Test alternative CSV format generation."""
        num_records = 25
        csv_data = CSVDataFactory.create_alternative_csv_format(num_records=num_records)

        assert isinstance(csv_data, pd.DataFrame)
        assert len(csv_data) == num_records

        # Validate alternative column names
        expected_columns = [
            'tax_id', 'sale_amount', 'market_value', 'property_description',
            'property_owner', 'county_name', 'acres', 'sale_year'
        ]
        for column in expected_columns:
            assert column in csv_data.columns


class TestHTMLResponseFactory:
    """Test the HTML response factory functionality."""

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_ador_search_response_generation(self):
        """Test ADOR search response HTML generation."""
        num_records = 30
        county = "Baldwin"
        html_response = HTMLResponseFactory.create_ador_search_response(
            num_records=num_records,
            county=county,
            has_next_page=True
        )

        assert isinstance(html_response, str)
        assert 'ador-delinquent-search-results' in html_response
        assert f'{county}' in html_response
        assert 'Next</a>' in html_response  # Pagination link

        # Count table rows (excluding header)
        import re
        row_pattern = r'<tr>.*?</tr>'
        rows = re.findall(row_pattern, html_response, re.DOTALL)
        # Should have header row + data rows
        assert len(rows) >= num_records

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_empty_response_generation(self):
        """Test empty response generation."""
        county = "TestCounty"
        html_response = HTMLResponseFactory.create_empty_response(county=county)

        assert isinstance(html_response, str)
        assert county in html_response
        assert 'No delinquent properties found' in html_response

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_error_response_generation(self):
        """Test error response generation."""
        error_types = ['server_error', 'not_found', 'timeout', 'maintenance']

        for error_type in error_types:
            html_response = HTMLResponseFactory.create_error_response(error_type=error_type)

            assert isinstance(html_response, str)
            assert 'Error' in html_response
            assert len(html_response) > 100  # Should have substantial content


class TestErrorTestDataFactory:
    """Test the error test data factory functionality."""

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_network_error_scenarios(self):
        """Test network error scenario generation."""
        scenarios = ErrorTestDataFactory.create_network_error_scenarios()

        assert len(scenarios) > 0
        for scenario in scenarios:
            required_fields = ['error_type', 'description', 'should_retry', 'expected_exception']
            for field in required_fields:
                assert field in scenario

            # Validate boolean fields
            assert isinstance(scenario['should_retry'], bool)
            assert isinstance(scenario['max_retries'], int)

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_validation_error_scenarios(self):
        """Test validation error scenario generation."""
        scenarios = ErrorTestDataFactory.create_validation_error_scenarios()

        assert len(scenarios) > 0
        for scenario in scenarios:
            required_fields = ['error_type', 'input_value', 'field', 'recoverable']
            for field in required_fields:
                assert field in scenario

            assert isinstance(scenario['recoverable'], bool)

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_parsing_error_scenarios(self):
        """Test parsing error scenario generation."""
        scenarios = ErrorTestDataFactory.create_parsing_error_scenarios()

        assert len(scenarios) > 0
        for scenario in scenarios:
            required_fields = ['error_type', 'input_data', 'description']
            for field in required_fields:
                assert field in scenario


class TestPerformanceTestDataFactory:
    """Test the performance test data factory functionality."""

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_performance_scenarios(self):
        """Test performance scenario generation."""
        scenarios = PerformanceTestDataFactory.create_performance_scenarios()

        assert len(scenarios) >= 4  # At least small, medium, large, stress scenarios

        scenario_names = [s['scenario'] for s in scenarios]
        expected_scenarios = ['small_dataset', 'medium_dataset', 'large_dataset', 'stress_test']
        for expected in expected_scenarios:
            assert expected in scenario_names

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_benchmark_data_creation(self):
        """Test benchmark data creation."""
        scenario = "small_dataset"
        benchmark_data = PerformanceTestDataFactory.create_benchmark_data(scenario)

        assert 'data' in benchmark_data
        assert 'performance_expectations' in benchmark_data
        assert 'metadata' in benchmark_data

        # Validate data structure
        assert isinstance(benchmark_data['data'], list)
        assert len(benchmark_data['data']) == 100  # Small dataset size

        # Validate performance expectations
        expectations = benchmark_data['performance_expectations']
        assert 'max_duration' in expectations
        assert 'max_memory_mb' in expectations
        assert 'min_rate' in expectations


class TestAIFactoryInterface:
    """Test the AI-friendly factory interface."""

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_factory_registry(self):
        """Test factory registry functionality."""
        from data_factories import AI_FACTORY_REGISTRY

        expected_factories = [
            'property_data', 'county_data', 'csv_data',
            'html_response', 'error_scenarios', 'performance_data'
        ]

        for factory_name in expected_factories:
            assert factory_name in AI_FACTORY_REGISTRY

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_get_factory_function(self):
        """Test get_factory function."""
        # Test valid factory
        factory = get_factory('property_data')
        assert factory == PropertyDataFactory

        # Test invalid factory
        with pytest.raises(ValueError):
            get_factory('nonexistent_factory')

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_generate_test_dataset_function(self):
        """Test generate_test_dataset function."""
        # Test property data generation
        property_data = generate_test_dataset('property_data', '__call__')
        assert isinstance(property_data, dict)
        assert 'parcel_id' in property_data

        # Test county data generation
        all_counties = generate_test_dataset('county_data', 'create_all_counties')
        assert isinstance(all_counties, list)
        assert len(all_counties) == 67

        # Test CSV data generation
        csv_data = generate_test_dataset('csv_data', 'create_ador_csv_format', num_records=10)
        assert isinstance(csv_data, pd.DataFrame)
        assert len(csv_data) == 10


@pytest.mark.parametrize("factory_name,method_name", [
    ("property_data", "__call__"),
    ("county_data", "create_all_counties"),
    ("csv_data", "create_ador_csv_format"),
    ("html_response", "create_ador_search_response"),
    ("error_scenarios", "create_network_error_scenarios"),
    ("performance_data", "create_performance_scenarios")
])
@pytest.mark.unit
@pytest.mark.ai_test
def test_all_factories_work(factory_name, method_name):
    """Parametrized test to ensure all factories work correctly."""
    try:
        result = generate_test_dataset(factory_name, method_name)
        assert result is not None
    except Exception as e:
        pytest.fail(f"Factory {factory_name}.{method_name} failed: {e}")


class TestDataConsistencyAndRealism:
    """Test that generated data is consistent and realistic."""

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_data_relationships(self):
        """Test that data relationships are realistic."""
        for _ in range(20):  # Test multiple samples
            property_data = PropertyDataFactory()

            # Assessed value should generally be higher than bid amount
            assert property_data['assessed_value'] >= property_data['amount']

            # Price per acre should be reasonable
            assert 0 <= property_data['price_per_acre'] <= 100000

            # Acreage should be in reasonable range
            assert 0.1 <= property_data['acreage'] <= 10.0

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_deterministic_generation(self):
        """Test that generation is deterministic with fixed seed."""
        # Generate same data twice
        properties1 = [PropertyDataFactory() for _ in range(5)]
        properties2 = [PropertyDataFactory() for _ in range(5)]

        # Due to fixed seed, results should be identical
        for i in range(5):
            assert properties1[i]['parcel_id'] == properties2[i]['parcel_id']
            assert properties1[i]['amount'] == properties2[i]['amount']