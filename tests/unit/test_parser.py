"""
AI-testable unit tests for scripts/parser.py module.

This module provides comprehensive test coverage for the AuctionParser class
and related functionality, following AI-friendly patterns with machine-readable
specifications and performance benchmarks.
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
import time
from io import StringIO

from scripts.parser import AuctionParser, main
from scripts.ai_exceptions import (
    AIDataValidationError, AIFileOperationError, AIDataProcessingError,
    RecoveryInstruction, RecoveryAction
)
from config.ai_logging import get_ai_logger
from tests.fixtures.data_factories import (
    create_sample_property_data, create_sample_csv_content,
    create_complex_property_data, create_water_feature_data
)


class TestAuctionParserInitialization:
    """Test suite for AuctionParser initialization and configuration."""

    def test_default_initialization(self):
        parser = AuctionParser()

        assert parser.min_acres == 0.001
        assert parser.max_acres == 500.0
        assert parser.max_price == 20000.0
        assert parser.infer_acres is False
        assert parser.column_mapping == {}
        assert parser.original_records == 0
        assert parser.filtered_records == 0

    def test_custom_initialization(self):
        parser = AuctionParser(
            min_acres=2.5,
            max_acres=10.0,
            max_price=50000.0,
            infer_acres=True
        )

        assert parser.min_acres == 2.5
        assert parser.max_acres == 10.0
        assert parser.max_price == 50000.0
        assert parser.infer_acres is True

    @pytest.mark.ai_test
    def test_initialization_performance_benchmark(self, benchmark):
        result = benchmark(AuctionParser)
        assert result is not None
        assert benchmark.stats['mean'] < 0.001

    def test_initialization_with_extreme_values(self):
        parser = AuctionParser(
            min_acres=0.1,
            max_acres=1000.0,
            max_price=1000000.0
        )

        assert parser.min_acres == 0.1
        assert parser.max_acres == 1000.0
        assert parser.max_price == 1000000.0

    def test_initialization_validation(self):
        # Implementation does NOT validate parameters - accepts any values
        parser1 = AuctionParser(min_acres=-1.0)
        assert parser1.min_acres == -1.0

        parser2 = AuctionParser(max_acres=0.0)
        assert parser2.max_acres == 0.0

        parser3 = AuctionParser(max_price=-100.0)
        assert parser3.max_price == -100.0


class TestCSVFileLoading:
    """Test suite for CSV file loading functionality."""

    def setup_method(self):
        self.parser = AuctionParser()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_temp_csv(self, content: str, encoding: str = 'utf-8', delimiter: str = ',') -> str:
        temp_file = os.path.join(self.temp_dir, 'test.csv')
        with open(temp_file, 'w', encoding=encoding) as f:
            f.write(content)
        return temp_file

    def test_load_basic_csv_file(self):
        csv_content = create_sample_csv_content()
        temp_file = self.create_temp_csv(csv_content)

        df = self.parser.load_csv_file(temp_file)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert self.parser.original_records == len(df)

    def test_load_csv_with_different_delimiters(self):
        csv_content = "ParcelNumber;PropertyDescription;TaxesOwed\n001-001-001;123 Main St;1500.00"
        temp_file = self.create_temp_csv(csv_content)

        df = self.parser.load_csv_file(temp_file)

        assert len(df) == 1
        assert 'ParcelNumber' in df.columns

    def test_load_csv_with_different_encodings(self):
        csv_content = "ParcelNumber,PropertyDescription,TaxesOwed\n001-001-001,123 Main St,1500.00"
        temp_file = self.create_temp_csv(csv_content, encoding='latin-1')

        df = self.parser.load_csv_file(temp_file)

        assert len(df) == 1

    def test_load_nonexistent_file(self):
        with pytest.raises(FileNotFoundError) as exc_info:
            self.parser.load_csv_file("nonexistent_file.csv")

        assert "File not found" in str(exc_info.value)

    def test_load_empty_csv_file(self):
        temp_file = self.create_temp_csv("")

        with pytest.raises(Exception):
            self.parser.load_csv_file(temp_file)

    def test_load_malformed_csv_file(self):
        malformed_content = "ParcelNumber,PropertyDescription\n001-001-001,123 Main St,Extra Column"
        temp_file = self.create_temp_csv(malformed_content)

        df = self.parser.load_csv_file(temp_file)
        assert isinstance(df, pd.DataFrame)

    @pytest.mark.ai_test
    def test_csv_loading_performance_benchmark(self, benchmark):
        csv_content = create_sample_csv_content(num_records=1000)
        temp_file = self.create_temp_csv(csv_content)

        result = benchmark(self.parser.load_csv_file, temp_file)

        assert len(result) == 1000
        assert benchmark.stats['mean'] < 5.0

    def test_load_csv_with_unicode_characters(self):
        csv_content = "ParcelNumber,PropertyDescription,TaxesOwed\n001-001-001,Café near rivière,1500.00"
        temp_file = self.create_temp_csv(csv_content, encoding='utf-8')

        df = self.parser.load_csv_file(temp_file)

        assert len(df) == 1
        assert "Café" in df.iloc[0]['PropertyDescription']

    def test_load_csv_with_na_values(self):
        csv_content = "ParcelNumber,PropertyDescription,TaxesOwed\n001-001-001,123 Main St,N/A\n002-002-002,456 Oak Ave,NULL"
        temp_file = self.create_temp_csv(csv_content)

        df = self.parser.load_csv_file(temp_file)

        assert len(df) == 2
        assert pd.isna(df.iloc[0]['TaxesOwed'])
        assert pd.isna(df.iloc[1]['TaxesOwed'])


class TestColumnMapping:
    """Test suite for column mapping functionality."""

    def setup_method(self):
        self.parser = AuctionParser()

    def test_map_columns_standard_format(self):
        # Use column names that exist in COLUMN_MAPPINGS
        df = pd.DataFrame({
            'ParcelNumber': ['001-001-001', '002-002-002'],
            'PropertyDescription': ['123 Main St', '456 Oak Ave'],
            'Amount': ['1500.00', '2500.00'],  # 'amount' is in COLUMN_MAPPINGS
            'AssessedValue': ['15000', '25000']
        })

        mapped_df = self.parser.map_columns(df)

        expected_mappings = {
            'parcel_id': 'ParcelNumber',
            'description': 'PropertyDescription',
            'amount': 'Amount',
            'assessed_value': 'AssessedValue'
        }

        for field, column in expected_mappings.items():
            assert field in mapped_df.columns
            assert self.parser.column_mapping[field] == column

    def test_map_columns_alternative_format(self):
        df = pd.DataFrame({
            'PARCEL_ID': ['001-001-001'],
            'PROP_DESC': ['123 Main St'],
            'AMOUNT_DUE': ['1500.00']
        })

        mapped_df = self.parser.map_columns(df)

        assert 'parcel_id' in mapped_df.columns
        assert 'description' in mapped_df.columns
        assert 'amount' in mapped_df.columns

    def test_map_columns_missing_fields(self):
        df = pd.DataFrame({
            'ParcelNumber': ['001-001-001'],
            'SomeOtherField': ['value']
        })

        mapped_df = self.parser.map_columns(df)

        assert 'parcel_id' in self.parser.column_mapping
        assert 'description' not in self.parser.column_mapping

    def test_map_columns_empty_dataframe(self):
        df = pd.DataFrame()

        mapped_df = self.parser.map_columns(df)

        assert len(mapped_df) == 0
        assert len(self.parser.column_mapping) == 0

    @pytest.mark.ai_test
    def test_column_mapping_performance_benchmark(self, benchmark):
        df = create_sample_property_data(num_records=10000)

        result = benchmark(self.parser.map_columns, df)

        assert len(result) == 10000
        assert benchmark.stats['mean'] < 1.0

    def test_map_columns_case_insensitive(self):
        df = pd.DataFrame({
            'PARCELNUMBER': ['001-001-001'],
            'propertydescription': ['123 Main St'],
            'TaXeS_OwEd': ['1500.00']
        })

        mapped_df = self.parser.map_columns(df)

        assert 'parcel_id' in mapped_df.columns
        assert 'description' in mapped_df.columns
        assert 'amount' in mapped_df.columns


class TestDataNormalization:
    """Test suite for data normalization functionality."""

    def setup_method(self):
        self.parser = AuctionParser(infer_acres=True)

    def test_normalize_prices(self):
        df = pd.DataFrame({
            'amount': ['$1,500.00', '2500', '$3,000'],
            'assessed_value': ['$15,000.00', '25000', '$30,000']
        })

        normalized_df = self.parser.normalize_data(df)

        assert normalized_df['amount'].iloc[0] == 1500.0
        assert normalized_df['amount'].iloc[1] == 2500.0
        assert normalized_df['amount'].iloc[2] == 3000.0
        assert normalized_df['assessed_value'].iloc[0] == 15000.0

    def test_normalize_acreage_direct_column(self):
        df = pd.DataFrame({
            'amount': [1500.0],
            'acreage': ['2.5']
        })

        normalized_df = self.parser.normalize_data(df)

        assert normalized_df['acreage'].iloc[0] == 2.5

    def test_infer_acreage_from_description(self):
        df = pd.DataFrame({
            'amount': [1500.0],
            'description': ['Property with 3.2 acres near creek']
        })

        normalized_df = self.parser.normalize_data(df)

        assert 'acreage' in normalized_df.columns
        assert normalized_df['acreage'].iloc[0] == 3.2

    def test_normalize_data_without_infer_acres(self):
        parser = AuctionParser(infer_acres=False)
        df = pd.DataFrame({
            'amount': [1500.0],
            'description': ['Property with 3.2 acres']
        })

        normalized_df = parser.normalize_data(df)

        # normalize_data() doesn't create acreage column - that happens in map_columns()
        # When called directly without map_columns(), acreage column won't exist
        assert 'acreage' not in normalized_df.columns

    def test_normalize_invalid_prices(self):
        df = pd.DataFrame({
            'amount': ['invalid', 'N/A', '0', '-100'],
            'description': ['test'] * 4
        })

        normalized_df = self.parser.normalize_data(df)

        assert pd.isna(normalized_df['amount'].iloc[0])
        assert pd.isna(normalized_df['amount'].iloc[1])
        assert normalized_df['amount'].iloc[2] == 0.0
        # normalize_price returns None for negative values
        assert pd.isna(normalized_df['amount'].iloc[3])

    @pytest.mark.ai_test
    def test_data_normalization_performance_benchmark(self, benchmark):
        df = create_complex_property_data(num_records=5000)

        result = benchmark(self.parser.normalize_data, df)

        assert len(result) == 5000
        assert benchmark.stats['mean'] < 2.0

    def test_normalize_missing_columns(self):
        df = pd.DataFrame({
            'other_field': ['value1', 'value2']
        })

        normalized_df = self.parser.normalize_data(df)

        assert len(normalized_df) == 2
        assert 'other_field' in normalized_df.columns

    def test_normalize_mixed_acreage_sources(self):
        df = pd.DataFrame({
            'amount': [1500.0, 2500.0],
            'acreage': [2.5, np.nan],
            'description': ['Property 1', 'Property with 4.1 acres']
        })

        normalized_df = self.parser.normalize_data(df)

        assert normalized_df['acreage'].iloc[0] == 2.5
        assert normalized_df['acreage'].iloc[1] == 4.1


class TestDataFiltering:
    """Test suite for data filtering functionality."""

    def setup_method(self):
        self.parser = AuctionParser(min_acres=1.0, max_acres=5.0, max_price=20000.0)
        # Set column_mapping so acreage filter is applied
        self.parser.column_mapping = {'acreage': 'acreage'}

    def test_apply_price_filter(self):
        df = pd.DataFrame({
            'amount': [15000.0, 25000.0, 10000.0],
            'description': ['prop1', 'prop2', 'prop3'],
            'acreage': [2.0, 2.0, 2.0]
        })

        filtered_df = self.parser.apply_filters(df)

        assert len(filtered_df) == 2
        assert 25000.0 not in filtered_df['amount'].values

    def test_apply_acreage_filter(self):
        df = pd.DataFrame({
            'amount': [15000.0, 15000.0, 15000.0],
            'description': ['prop1', 'prop2', 'prop3'],
            'acreage': [2.0, 6.0, 0.5]
        })

        filtered_df = self.parser.apply_filters(df)

        assert len(filtered_df) == 1
        assert filtered_df['acreage'].iloc[0] == 2.0

    def test_filter_missing_essential_data(self):
        df = pd.DataFrame({
            'amount': [15000.0, np.nan, 15000.0],
            'description': ['prop1', 'prop2', np.nan],
            'acreage': [2.0, 2.0, 2.0]
        })

        filtered_df = self.parser.apply_filters(df)

        assert len(filtered_df) == 1
        assert filtered_df['description'].iloc[0] == 'prop1'

    def test_filter_empty_dataframe(self):
        df = pd.DataFrame(columns=['amount', 'description', 'acreage'])

        filtered_df = self.parser.apply_filters(df)

        assert len(filtered_df) == 0
        assert self.parser.filtered_records == 0

    @pytest.mark.ai_test
    def test_filtering_performance_benchmark(self, benchmark):
        df = create_sample_property_data(num_records=50000)

        result = benchmark(self.parser.apply_filters, df)

        assert len(result) <= len(df)
        assert benchmark.stats['mean'] < 3.0

    def test_filter_edge_case_values(self):
        df = pd.DataFrame({
            'amount': [20000.0, 20000.01, 0.0],
            'description': ['prop1', 'prop2', 'prop3'],
            'acreage': [1.0, 5.0, 5.01]
        })

        filtered_df = self.parser.apply_filters(df)

        assert len(filtered_df) == 2
        assert 20000.01 not in filtered_df['amount'].values
        assert 5.01 not in filtered_df['acreage'].values

    def test_filter_updates_record_counts(self):
        df = pd.DataFrame({
            'amount': [15000.0, 25000.0],
            'description': ['prop1', 'prop2'],
            'acreage': [2.0, 2.0]
        })

        filtered_df = self.parser.apply_filters(df)

        assert self.parser.filtered_records == 1
        assert len(filtered_df) == self.parser.filtered_records


class TestMetricsCalculation:
    """Test suite for investment metrics calculation."""

    def setup_method(self):
        self.parser = AuctionParser()

    def test_calculate_price_per_acre(self):
        df = pd.DataFrame({
            'amount': [10000.0, 20000.0],
            'acreage': [2.0, 4.0],
            'description': ['prop1', 'prop2']
        })

        metrics_df = self.parser.calculate_metrics(df)

        assert 'price_per_acre' in metrics_df.columns
        assert metrics_df['price_per_acre'].iloc[0] == 5000.0
        assert metrics_df['price_per_acre'].iloc[1] == 5000.0

    def test_calculate_estimated_all_in_cost(self):
        df = pd.DataFrame({
            'amount': [10000.0],
            'description': ['prop1']
        })

        metrics_df = self.parser.calculate_metrics(df)

        assert 'estimated_all_in_cost' in metrics_df.columns
        assert metrics_df['estimated_all_in_cost'].iloc[0] > 10000.0

    def test_calculate_water_scores(self):
        df = pd.DataFrame({
            'description': [
                'Property near creek and stream',
                'Regular property',
                'Property with pond access'
            ]
        })

        metrics_df = self.parser.calculate_metrics(df)

        assert 'water_score' in metrics_df.columns
        assert metrics_df['water_score'].iloc[0] > 0
        assert metrics_df['water_score'].iloc[1] == 0
        assert metrics_df['water_score'].iloc[2] > 0

    def test_calculate_assessed_value_ratio(self):
        df = pd.DataFrame({
            'amount': [10000.0, 15000.0],
            'assessed_value': [20000.0, 0.0],
            'description': ['prop1', 'prop2']
        })

        metrics_df = self.parser.calculate_metrics(df)

        assert 'assessed_value_ratio' in metrics_df.columns
        assert metrics_df['assessed_value_ratio'].iloc[0] == 0.5
        assert pd.isna(metrics_df['assessed_value_ratio'].iloc[1])

    def test_calculate_investment_score(self):
        df = pd.DataFrame({
            'amount': [10000.0],
            'acreage': [2.0],
            'description': ['Property near creek'],
            'assessed_value': [20000.0]
        })

        metrics_df = self.parser.calculate_metrics(df)

        required_cols = ['price_per_acre', 'water_score', 'assessed_value_ratio']
        assert all(col in metrics_df.columns for col in required_cols)
        assert 'investment_score' in metrics_df.columns
        assert metrics_df['investment_score'].iloc[0] > 0

    @pytest.mark.ai_test
    def test_metrics_calculation_performance_benchmark(self, benchmark):
        df = create_water_feature_data(num_records=10000)

        result = benchmark(self.parser.calculate_metrics, df)

        assert len(result) == 10000
        assert benchmark.stats['mean'] < 5.0

    def test_calculate_metrics_missing_columns(self):
        df = pd.DataFrame({
            'other_field': ['value1', 'value2']
        })

        metrics_df = self.parser.calculate_metrics(df)

        assert len(metrics_df) == 2
        assert 'other_field' in metrics_df.columns

    def test_calculate_metrics_with_nan_values(self):
        df = pd.DataFrame({
            'amount': [10000.0, np.nan],
            'acreage': [2.0, 3.0],
            'description': ['prop1', 'prop2']
        })

        metrics_df = self.parser.calculate_metrics(df)

        assert 'price_per_acre' in metrics_df.columns
        assert metrics_df['price_per_acre'].iloc[0] == 5000.0
        assert pd.isna(metrics_df['price_per_acre'].iloc[1])


class TestPropertyRanking:
    """Test suite for property ranking functionality."""

    def setup_method(self):
        self.parser = AuctionParser()

    def test_rank_by_investment_score(self):
        df = pd.DataFrame({
            'investment_score': [3.5, 8.2, 5.1],
            'price_per_acre': [5000.0, 3000.0, 4000.0],
            'water_score': [1.0, 3.0, 2.0]
        })

        ranked_df = self.parser.rank_properties(df)

        assert 'rank' in ranked_df.columns
        assert ranked_df['rank'].iloc[0] == 1
        assert ranked_df['investment_score'].iloc[0] == 8.2

    def test_rank_by_price_per_acre_tiebreaker(self):
        df = pd.DataFrame({
            'investment_score': [5.0, 5.0],
            'price_per_acre': [4000.0, 3000.0],
            'water_score': [1.0, 1.0]
        })

        ranked_df = self.parser.rank_properties(df)

        assert ranked_df['price_per_acre'].iloc[0] == 3000.0
        assert ranked_df['rank'].iloc[0] == 1

    def test_rank_missing_score_columns(self):
        df = pd.DataFrame({
            'description': ['prop1', 'prop2', 'prop3']
        })

        ranked_df = self.parser.rank_properties(df)

        assert 'rank' in ranked_df.columns
        assert len(ranked_df) == 3

    def test_rank_empty_dataframe(self):
        df = pd.DataFrame()

        ranked_df = self.parser.rank_properties(df)

        assert len(ranked_df) == 0

    @pytest.mark.ai_test
    def test_ranking_performance_benchmark(self, benchmark):
        df = create_complex_property_data(num_records=25000)
        df['investment_score'] = np.random.uniform(1, 10, 25000)
        df['price_per_acre'] = np.random.uniform(1000, 10000, 25000)

        result = benchmark(self.parser.rank_properties, df)

        assert len(result) == 25000
        assert 'rank' in result.columns
        assert benchmark.stats['mean'] < 2.0

    def test_rank_maintains_data_integrity(self):
        df = pd.DataFrame({
            'parcel_id': ['001', '002', '003'],
            'investment_score': [3.5, 8.2, 5.1],
            'price_per_acre': [5000.0, 3000.0, 4000.0]
        })

        ranked_df = self.parser.rank_properties(df)

        assert len(ranked_df) == 3
        assert set(ranked_df['parcel_id']) == set(df['parcel_id'])
        assert ranked_df['parcel_id'].iloc[0] == '002'


class TestResultsExport:
    """Test suite for results export functionality."""

    def setup_method(self):
        self.parser = AuctionParser()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_results_basic(self):
        df = pd.DataFrame({
            'rank': [1, 2],
            'parcel_id': ['001-001-001', '002-002-002'],
            'amount': [15000.0, 12000.0],
            'description': ['Property 1', 'Property 2'],
            'acreage': [2.5, 3.0],
            'price_per_acre': [6000.0, 4000.0]
        })

        output_path = os.path.join(self.temp_dir, 'test_output.csv')
        self.parser.export_results(df, output_path)

        assert os.path.exists(output_path)

        exported_df = pd.read_csv(output_path)
        assert len(exported_df) == 2
        assert 'rank' in exported_df.columns

    def test_export_creates_directory(self):
        df = pd.DataFrame({'rank': [1], 'parcel_id': ['001-001-001']})

        nested_path = os.path.join(self.temp_dir, 'nested', 'dir', 'output.csv')
        self.parser.export_results(df, nested_path)

        assert os.path.exists(nested_path)

    def test_export_rounds_numeric_columns(self):
        df = pd.DataFrame({
            'rank': [1],
            'amount': [15000.123456],
            'price_per_acre': [6000.789123],
            'acreage': [2.567891234],
            'water_score': [3.456789],
            'investment_score': [7.891234]
        })

        output_path = os.path.join(self.temp_dir, 'rounded_output.csv')
        self.parser.export_results(df, output_path)

        exported_df = pd.read_csv(output_path)
        assert exported_df['amount'].iloc[0] == 15000.12
        assert exported_df['acreage'].iloc[0] == 2.568
        assert exported_df['water_score'].iloc[0] == 3.5

    def test_export_filters_columns(self):
        df = pd.DataFrame({
            'rank': [1],
            'parcel_id': ['001-001-001'],
            'amount': [15000.0],
            'unwanted_column': ['should_not_export']
        })

        output_path = os.path.join(self.temp_dir, 'filtered_output.csv')
        self.parser.export_results(df, output_path)

        exported_df = pd.read_csv(output_path)
        assert 'unwanted_column' not in exported_df.columns
        assert 'parcel_id' in exported_df.columns

    @pytest.mark.ai_test
    def test_export_performance_benchmark(self, benchmark):
        df = create_sample_property_data(num_records=10000)
        df['rank'] = range(1, 10001)
        output_path = os.path.join(self.temp_dir, 'benchmark_output.csv')

        benchmark(self.parser.export_results, df, output_path)

        assert os.path.exists(output_path)
        assert benchmark.stats['mean'] < 5.0

    def test_export_empty_dataframe(self):
        df = pd.DataFrame()
        output_path = os.path.join(self.temp_dir, 'empty_output.csv')

        self.parser.export_results(df, output_path)

        assert os.path.exists(output_path)
        exported_df = pd.read_csv(output_path)
        assert len(exported_df) == 0


class TestSummaryReporting:
    """Test suite for summary report generation."""

    def setup_method(self):
        self.parser = AuctionParser()
        self.parser.original_records = 1000
        self.parser.filtered_records = 100

    def test_generate_basic_summary(self):
        df = pd.DataFrame({
            'amount': [15000.0, 12000.0, 18000.0],
            'acreage': [2.5, 3.0, 2.0],
            'price_per_acre': [6000.0, 4000.0, 9000.0],
            'water_score': [0.0, 3.0, 1.0],
            'investment_score': [5.2, 7.8, 6.1]
        })

        summary = self.parser.generate_summary_report(df)

        assert summary['original_records'] == 1000
        assert summary['filtered_records'] == 100
        assert 'filter_retention_rate' in summary
        assert 'avg_price' in summary
        assert 'median_price' in summary

    def test_summary_with_water_features(self):
        df = pd.DataFrame({
            'water_score': [0.0, 3.0, 1.0, 0.0, 2.0]
        })

        summary = self.parser.generate_summary_report(df)

        assert 'properties_with_water' in summary
        water_info = summary['properties_with_water']
        assert '3 (60.0%)' == water_info

    def test_summary_with_investment_scores(self):
        df = pd.DataFrame({
            'investment_score': [5.2, 7.8, 6.1, 8.5, 9.2, 4.1, 7.3, 8.9, 5.8, 6.7]
        })

        summary = self.parser.generate_summary_report(df)

        assert 'avg_investment_score' in summary
        assert 'top_10_percent_avg_score' in summary

    def test_summary_empty_dataframe(self):
        df = pd.DataFrame()

        summary = self.parser.generate_summary_report(df)

        assert summary['original_records'] == 1000
        assert summary['filtered_records'] == 100
        assert len(summary) == 3

    def test_summary_missing_columns(self):
        df = pd.DataFrame({
            'other_field': ['value1', 'value2']
        })

        summary = self.parser.generate_summary_report(df)

        basic_fields = ['original_records', 'filtered_records', 'filter_retention_rate']
        assert all(field in summary for field in basic_fields)

    @pytest.mark.ai_test
    def test_summary_generation_performance_benchmark(self, benchmark):
        df = create_complex_property_data(num_records=50000)

        result = benchmark(self.parser.generate_summary_report, df)

        assert isinstance(result, dict)
        assert len(result) > 3
        assert benchmark.stats['mean'] < 1.0


class TestScrapedDataProcessing:
    """Test suite for scraped data processing workflow."""

    def setup_method(self):
        self.parser = AuctionParser()

    @patch('scripts.parser.scrape_county_data')
    @patch('scripts.parser.validate_county_code')
    @patch('scripts.parser.get_county_name')
    def test_process_scraped_data_success(self, mock_get_name, mock_validate, mock_scrape):
        mock_validate.return_value = '05'
        mock_get_name.return_value = 'Baldwin'
        mock_scrape.return_value = create_sample_property_data()

        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            output_path = tmp.name

        try:
            summary = self.parser.process_scraped_data('Baldwin', output_path)

            assert isinstance(summary, dict)
            assert 'data_source' in summary
            assert 'Baldwin County' in summary['data_source']
            assert os.path.exists(output_path)

        finally:
            os.unlink(output_path)

    @patch('scripts.parser.scrape_county_data')
    @patch('scripts.parser.validate_county_code')
    def test_process_scraped_data_empty_result(self, mock_validate, mock_scrape):
        mock_validate.return_value = '05'
        mock_scrape.return_value = pd.DataFrame()

        with pytest.raises(Exception, match="No data found"):
            self.parser.process_scraped_data('Baldwin', 'output.csv')

    @patch('scripts.parser.validate_county_code')
    def test_process_scraped_data_invalid_county(self, mock_validate):
        from scripts.exceptions import CountyValidationError
        mock_validate.side_effect = CountyValidationError("Invalid county")

        with pytest.raises(CountyValidationError):
            self.parser.process_scraped_data('InvalidCounty', 'output.csv')

    @patch('scripts.parser.scrape_county_data')
    def test_process_scraped_data_scraping_error(self, mock_scrape):
        from scripts.exceptions import ScrapingError
        mock_scrape.side_effect = ScrapingError("Network error")

        with pytest.raises(ScrapingError):
            self.parser.process_scraped_data('Baldwin', 'output.csv')


class TestFileProcessing:
    """Test suite for CSV file processing workflow."""

    def setup_method(self):
        self.parser = AuctionParser()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_process_file_complete_workflow(self):
        csv_content = create_sample_csv_content()
        input_path = os.path.join(self.temp_dir, 'input.csv')
        output_path = os.path.join(self.temp_dir, 'output.csv')

        with open(input_path, 'w') as f:
            f.write(csv_content)

        summary = self.parser.process_file(input_path, output_path)

        assert isinstance(summary, dict)
        assert os.path.exists(output_path)
        assert self.parser.original_records > 0

    def test_process_file_nonexistent_input(self):
        with pytest.raises(FileNotFoundError):
            self.parser.process_file('nonexistent.csv', 'output.csv')

    @pytest.mark.ai_test
    def test_process_file_performance_benchmark(self, benchmark):
        csv_content = create_sample_csv_content(num_records=5000)
        input_path = os.path.join(self.temp_dir, 'large_input.csv')
        output_path = os.path.join(self.temp_dir, 'large_output.csv')

        with open(input_path, 'w') as f:
            f.write(csv_content)

        result = benchmark(self.parser.process_file, input_path, output_path)

        assert isinstance(result, dict)
        assert os.path.exists(output_path)
        assert benchmark.stats['mean'] < 10.0


class TestMainCLIFunction:
    """Test suite for main CLI function."""

    def test_main_list_counties(self, capsys):
        with patch('sys.argv', ['parser.py', '--list-counties']):
            with patch('scripts.parser.list_available_counties') as mock_list:
                mock_list.return_value = {'05': 'Baldwin', '37': 'Jefferson'}

                with pytest.raises(SystemExit):
                    main()

                captured = capsys.readouterr()
                assert 'Available Alabama Counties' in captured.out
                assert 'Baldwin' in captured.out

    def test_main_missing_required_args(self, capsys):
        with patch('sys.argv', ['parser.py']):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert 'Must specify either --input' in captured.out

    def test_main_conflicting_args(self, capsys):
        with patch('sys.argv', ['parser.py', '--input', 'test.csv', '--scrape-county', 'Baldwin']):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert 'Cannot specify multiple input methods' in captured.out

    @patch('scripts.parser.AuctionParser')
    def test_main_scrape_county_success(self, mock_parser_class, capsys):
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_parser.process_scraped_data.return_value = {'status': 'success'}

        with patch('sys.argv', ['parser.py', '--scrape-county', 'Baldwin', '--output', 'test.csv']):
            main()

        mock_parser.process_scraped_data.assert_called_once()
        captured = capsys.readouterr()
        assert 'completed successfully' in captured.out

    @patch('scripts.parser.AuctionParser')
    @patch('os.path.exists')
    def test_main_process_file_success(self, mock_exists, mock_parser_class, capsys):
        mock_exists.return_value = True
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_parser.process_file.return_value = {'status': 'success'}

        with patch('sys.argv', ['parser.py', '--input', 'test.csv', '--output', 'output.csv']):
            main()

        mock_parser.process_file.assert_called_once()
        captured = capsys.readouterr()
        assert 'completed successfully' in captured.out

    def test_main_file_not_exists(self, capsys):
        with patch('sys.argv', ['parser.py', '--input', 'nonexistent.csv']):
            with patch('os.path.exists', return_value=False):
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert 'does not exist' in captured.out


class TestErrorHandling:
    """Test suite for error handling and recovery scenarios."""

    def setup_method(self):
        self.parser = AuctionParser()

    def test_invalid_initialization_parameters(self):
        # Implementation does NOT validate initialization parameters
        parser = AuctionParser(min_acres=-1.0)
        assert parser.min_acres == -1.0

    def test_file_operation_error_handling(self):
        with pytest.raises(FileNotFoundError) as exc_info:
            self.parser.load_csv_file('/nonexistent/path/file.csv')

        assert "File not found" in str(exc_info.value)

    def test_data_validation_error_handling(self):
        df = pd.DataFrame({'invalid_column': ['data']})

        result = self.parser.map_columns(df)
        assert isinstance(result, pd.DataFrame)

    def test_graceful_degradation_missing_data(self):
        df = pd.DataFrame({
            'description': ['Property 1', 'Property 2']
        })

        result = self.parser.calculate_metrics(df)
        assert len(result) == 2
        assert 'description' in result.columns

    @pytest.mark.ai_test
    def test_error_recovery_performance(self, benchmark):
        def error_prone_operation():
            try:
                df = pd.DataFrame({'amount': ['invalid', '1000', 'bad_data']})
                return self.parser.normalize_data(df)
            except Exception:
                return pd.DataFrame()

        result = benchmark(error_prone_operation)
        assert isinstance(result, pd.DataFrame)
        assert benchmark.stats['mean'] < 0.1


@pytest.mark.integration
class TestIntegrationScenarios:
    """Integration test scenarios combining multiple parser operations."""

    def setup_method(self):
        self.parser = AuctionParser(min_acres=1.0, max_acres=5.0, max_price=20000.0, infer_acres=True)
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_end_to_end_csv_processing(self):
        csv_content = """ParcelNumber,PropertyDescription,TaxesOwed,AssessedValue
001-001-001,"Property with 2.5 acres near creek",$15000.00,$30000
002-002-002,"3 acre lot by stream",$12000.00,$25000
003-003-003,"Large 10 acre property",$25000.00,$50000
004-004-004,"Small 0.5 acre lot",$8000.00,$15000"""

        input_path = os.path.join(self.temp_dir, 'test_input.csv')
        output_path = os.path.join(self.temp_dir, 'test_output.csv')

        with open(input_path, 'w') as f:
            f.write(csv_content)

        summary = self.parser.process_file(input_path, output_path)

        assert os.path.exists(output_path)
        assert isinstance(summary, dict)
        assert self.parser.original_records == 4
        assert self.parser.filtered_records == 2

        result_df = pd.read_csv(output_path)
        assert len(result_df) == 2
        assert all(result_df['water_score'] > 0)

    @pytest.mark.ai_test
    def test_large_dataset_processing_performance(self, benchmark):
        large_csv = create_sample_csv_content(num_records=10000)
        input_path = os.path.join(self.temp_dir, 'large_test.csv')
        output_path = os.path.join(self.temp_dir, 'large_output.csv')

        with open(input_path, 'w') as f:
            f.write(large_csv)

        result = benchmark(self.parser.process_file, input_path, output_path)

        assert isinstance(result, dict)
        assert os.path.exists(output_path)
        assert benchmark.stats['mean'] < 30.0

    def test_data_quality_validation_integration(self):
        poor_quality_csv = """ParcelNumber,PropertyDescription,TaxesOwed
001-001-001,"Property 1",$15000.00
002-002-002,"Property 2",invalid_price
003-003-003,,12000
,Property 4,$8000.00"""

        input_path = os.path.join(self.temp_dir, 'poor_quality.csv')
        output_path = os.path.join(self.temp_dir, 'cleaned_output.csv')

        with open(input_path, 'w') as f:
            f.write(poor_quality_csv)

        summary = self.parser.process_file(input_path, output_path)

        assert os.path.exists(output_path)
        result_df = pd.read_csv(output_path)
        assert len(result_df) <= 4
        assert all(pd.notna(result_df['amount']))

    def test_mixed_format_handling(self):
        mixed_csv = """PARCEL_ID,PROP_DESC,AMOUNT_DUE,VALUE
001-001-001,"Property with 2 acres","$15,000.00","$30,000"
002-002-002,"3.5 acre lot",12000,25000
003-003-003,"Property near water","$18,500","$35,000\""""

        input_path = os.path.join(self.temp_dir, 'mixed_format.csv')
        output_path = os.path.join(self.temp_dir, 'normalized_output.csv')

        with open(input_path, 'w') as f:
            f.write(mixed_csv)

        summary = self.parser.process_file(input_path, output_path)

        assert os.path.exists(output_path)
        result_df = pd.read_csv(output_path)
        assert len(result_df) >= 1
        assert all(isinstance(val, (int, float)) for val in result_df['amount'] if pd.notna(val))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])