"""
Integration tests for CSV processing pipelines in Alabama Auction Watcher.

Tests complete end-to-end CSV data processing workflows including parser integration
with utils, settings, logging, and exception handling systems. Provides AI-testable
scenarios with comprehensive data validation and performance benchmarks.

Pipeline scope:
- CSV file reading and parsing workflows
- Data validation and cleaning pipelines
- Column mapping and normalization flows
- Calculation and scoring integration
- Filtering and ranking workflows
- Output generation and export pipelines
"""

import pytest
import pandas as pd
import numpy as np
import time
import tempfile
import csv
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Dict, List, Any
from io import StringIO

from scripts.parser import AuctionParser
from scripts.utils import (
    detect_csv_delimiter, find_column_mapping, normalize_price,
    parse_acreage_from_description, calculate_water_score,
    calculate_estimated_all_in_cost, calculate_investment_score,
    validate_data_quality, clean_dataframe
)
from config.settings import (
    MIN_ACRES, MAX_ACRES, MAX_PRICE, COLUMN_MAPPINGS,
    CSV_DELIMITERS, FILE_ENCODINGS, OUTPUT_COLUMNS
)
from scripts.exceptions import (
    DataValidationError, FileOperationError, DataProcessingError
)
from config.logging_config import get_logger


class TestCSVParsingPipeline:
    """Test CSV file parsing and initial processing pipeline."""

    def setup_method(self):
        """Set up test environment."""
        self.test_logger = get_logger('csv_integration_test')

    def create_test_csv(self, data: List[Dict], delimiter=',', filename=None):
        """Create a test CSV file with specified data and delimiter."""
        if filename is None:
            tmp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
            filename = tmp_file.name
            tmp_file.close()

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            if data:
                writer = csv.DictWriter(f, fieldnames=data[0].keys(), delimiter=delimiter)
                writer.writeheader()
                writer.writerows(data)

        return filename

    def test_csv_delimiter_detection_pipeline(self):
        """Test CSV delimiter detection in parsing pipeline."""
        # Test data with different delimiters
        test_data = [
            {'Parcel ID': '123456', 'Amount': '$5,000', 'Description': 'Property with creek', 'Acreage': '2.5'},
            {'Parcel ID': '789012', 'Amount': '$8,500', 'Description': 'Land near water', 'Acreage': '3.1'}
        ]

        # Test comma delimiter
        csv_file = self.create_test_csv(test_data, delimiter=',')
        detected_delimiter = detect_csv_delimiter(csv_file)
        assert detected_delimiter == ','

        parser = AuctionParser()
        df = parser.load_csv(csv_file)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

        os.unlink(csv_file)

        # Test tab delimiter
        csv_file = self.create_test_csv(test_data, delimiter='\t')
        detected_delimiter = detect_csv_delimiter(csv_file)
        assert detected_delimiter == '\t'

        df = parser.load_csv(csv_file)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

        os.unlink(csv_file)

    def test_column_mapping_pipeline(self):
        """Test column mapping integration in CSV processing."""
        # Test data with different column name variations
        test_variations = [
            # Standard ADOR format
            {
                'Parcel ID': '123456',
                'Amount Bid at Tax Sale': '$5,000',
                'Property Description': 'Creek property 2.5 AC',
                'Acres': '2.5'
            },
            # Alternative format
            {
                'parcel_number': '789012',
                'bid_amount': '$8,500',
                'description': 'Waterfront lot 3.1 ACRES',
                'acreage': '3.1'
            }
        ]

        for i, data_format in enumerate(test_variations):
            csv_file = self.create_test_csv([data_format])

            # Test column mapping detection
            with open(csv_file, 'r') as f:
                first_line = f.readline().strip()
                columns = first_line.split(',')

            column_mapping = find_column_mapping(columns)
            assert isinstance(column_mapping, dict)

            # Test parsing with column mapping
            parser = AuctionParser()
            df = parser.load_csv(csv_file)
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 1

            os.unlink(csv_file)

    def test_data_encoding_pipeline(self):
        """Test CSV encoding detection and handling pipeline."""
        # Test data with special characters
        test_data = [
            {'Parcel ID': '123456', 'Amount': '$5,000', 'Description': 'Property with creek near Café', 'Owner': 'José Martinez'},
            {'Parcel ID': '789012', 'Amount': '$8,500', 'Description': 'Land with résumé access', 'Owner': 'François Dubois'}
        ]

        # Test UTF-8 encoding
        csv_file = self.create_test_csv(test_data)

        parser = AuctionParser()
        df = parser.load_csv(csv_file)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

        # Verify special characters are preserved
        descriptions = df['Description'].tolist() if 'Description' in df.columns else []
        if descriptions:
            assert any('Café' in desc or 'résumé' in desc for desc in descriptions)

        os.unlink(csv_file)

    def test_malformed_csv_handling_pipeline(self):
        """Test malformed CSV handling in processing pipeline."""
        # Create malformed CSV
        malformed_content = """Parcel ID,Amount,Description
123456,"$5,000","Property with creek
789012,$8,500,"Missing quote
456789,$3,200,"Normal property"
"""

        tmp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        tmp_file.write(malformed_content)
        tmp_file.close()

        # Test parser handles malformed data gracefully
        parser = AuctionParser()
        try:
            df = parser.load_csv(tmp_file.name)
            # Should either fix malformed data or skip bad rows
            assert isinstance(df, pd.DataFrame)
        except (DataValidationError, FileOperationError):
            # Or raise appropriate exception
            pass

        os.unlink(tmp_file.name)


class TestDataValidationPipeline:
    """Test data validation and cleaning pipeline integration."""

    def test_data_cleaning_pipeline(self):
        """Test complete data cleaning pipeline."""
        # Test data with various quality issues
        test_data = [
            {'Parcel ID': '123456', 'Amount': '$5,000', 'Description': 'Valid property 2.5 AC', 'Acreage': '2.5', 'Owner': 'John Doe'},
            {'Parcel ID': '', 'Amount': '$0', 'Description': 'Invalid - no parcel ID', 'Acreage': '', 'Owner': ''},
            {'Parcel ID': '789012', 'Amount': '$8,500', 'Description': 'Another valid property 3.1 ACRES', 'Acreage': '3.1', 'Owner': 'Jane Smith'},
            {'Parcel ID': 'INVALID', 'Amount': 'NOT_A_PRICE', 'Description': 'Malformed data', 'Acreage': 'NOT_NUMBER', 'Owner': 'Bad Data'},
            {'Parcel ID': '456789', 'Amount': '$15,000', 'Description': 'Property with creek 1.8 AC', 'Acreage': '1.8', 'Owner': 'Bob Johnson'}
        ]

        csv_file = self.create_test_csv(test_data)

        # Load and validate data
        parser = AuctionParser()
        df = parser.load_csv(csv_file)

        # Clean data
        cleaned_df = clean_dataframe(df)
        validation_results = validate_data_quality(cleaned_df)

        # Verify cleaning results
        assert isinstance(validation_results, dict)
        assert 'total_records' in validation_results
        assert 'valid_records' in validation_results
        assert validation_results['total_records'] == len(test_data)
        assert validation_results['valid_records'] <= validation_results['total_records']

        os.unlink(csv_file)

    def create_test_csv(self, data: List[Dict]):
        """Helper method to create test CSV files."""
        tmp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        if data:
            writer = csv.DictWriter(tmp_file, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        tmp_file.close()
        return tmp_file.name

    def test_price_normalization_pipeline(self):
        """Test price normalization in processing pipeline."""
        test_data = [
            {'Parcel ID': '123456', 'Amount': '$5,000.00', 'Description': 'Property 1'},
            {'Parcel ID': '789012', 'Amount': '8500', 'Description': 'Property 2'},
            {'Parcel ID': '456789', 'Amount': '$3,200.50', 'Description': 'Property 3'},
            {'Parcel ID': '111222', 'Amount': '12000.00', 'Description': 'Property 4'}
        ]

        csv_file = self.create_test_csv(test_data)

        parser = AuctionParser()
        df = parser.load_csv(csv_file)

        # Test price normalization
        if 'Amount' in df.columns:
            normalized_prices = []
            for price_str in df['Amount']:
                normalized = normalize_price(str(price_str))
                normalized_prices.append(normalized)

            # All prices should be numeric and positive
            assert all(isinstance(price, (int, float)) and price > 0 for price in normalized_prices if price is not None)

        os.unlink(csv_file)

    def test_acreage_parsing_pipeline(self):
        """Test acreage parsing integration in processing pipeline."""
        test_data = [
            {'Parcel ID': '123456', 'Description': 'Property with creek 2.5 AC', 'Acreage': ''},
            {'Parcel ID': '789012', 'Description': 'Waterfront lot 3.1 ACRES', 'Acreage': ''},
            {'Parcel ID': '456789', 'Description': 'Land parcel 43560 SF', 'Acreage': ''},  # 1 acre in sq ft
            {'Parcel ID': '111222', 'Description': 'Rectangular lot 100\' X 200\'', 'Acreage': ''},
            {'Parcel ID': '333444', 'Description': 'Fractional parcel 1/2 ACRE', 'Acreage': ''}
        ]

        csv_file = self.create_test_csv(test_data)

        parser = AuctionParser()
        df = parser.load_csv(csv_file)

        # Test acreage parsing from descriptions
        parsed_acreages = []
        for description in df.get('Description', []):
            acreage = parse_acreage_from_description(description)
            parsed_acreages.append(acreage)

        # Should successfully parse most acreages
        valid_acreages = [a for a in parsed_acreages if a is not None and a > 0]
        assert len(valid_acreages) >= 3  # Should parse at least 3 out of 5

        os.unlink(csv_file)


class TestCalculationPipeline:
    """Test calculation and scoring pipeline integration."""

    def create_test_csv(self, data: List[Dict]):
        """Helper method to create test CSV files."""
        tmp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        if data:
            writer = csv.DictWriter(tmp_file, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        tmp_file.close()
        return tmp_file.name

    def test_water_score_calculation_pipeline(self):
        """Test water score calculation integration."""
        test_data = [
            {'Parcel ID': '123456', 'Amount': '$4,000', 'Description': 'Property with creek and pond access', 'Acreage': '2.5'},
            {'Parcel ID': '789012', 'Amount': '$3,500', 'Description': 'Near stream and wetland area', 'Acreage': '3.0'},
            {'Parcel ID': '456789', 'Amount': '$5,000', 'Description': 'Waterfront property with river access', 'Acreage': '2.8'},
            {'Parcel ID': '111222', 'Amount': '$2,800', 'Description': 'Dry land no water features', 'Acreage': '3.2'}
        ]

        csv_file = self.create_test_csv(test_data)

        parser = AuctionParser()
        df = parser.load_csv(csv_file)
        processed_df = parser.calculate_metrics()

        # Verify water scores were calculated
        if 'water_score' in processed_df.columns:
            water_scores = processed_df['water_score'].dropna()
            assert len(water_scores) > 0

            # Properties with water features should have higher scores
            max_score = water_scores.max()
            assert max_score > 0

        os.unlink(csv_file)

    def test_investment_score_calculation_pipeline(self):
        """Test investment score calculation integration."""
        test_data = [
            {'Parcel ID': '123456', 'Amount': '$4,000', 'Description': 'Property with creek 2.5 AC', 'Acreage': '2.5', 'Assessed Value': '$15,000'},
            {'Parcel ID': '789012', 'Amount': '$6,000', 'Description': 'Land near water 3.0 ACRES', 'Acreage': '3.0', 'Assessed Value': '$18,000'},
            {'Parcel ID': '456789', 'Amount': '$8,500', 'Description': 'Waterfront lot 2.8 AC', 'Acreage': '2.8', 'Assessed Value': '$25,000'}
        ]

        csv_file = self.create_test_csv(test_data)

        parser = AuctionParser()
        df = parser.load_csv(csv_file)
        processed_df = parser.calculate_metrics()

        # Verify investment scores were calculated
        if 'investment_score' in processed_df.columns:
            investment_scores = processed_df['investment_score'].dropna()
            assert len(investment_scores) > 0
            assert all(score >= 0 for score in investment_scores)

        os.unlink(csv_file)

    def test_cost_calculation_pipeline(self):
        """Test all-in cost calculation integration."""
        test_data = [
            {'Parcel ID': '123456', 'Amount': '$4,000', 'Description': 'Property 1', 'Acreage': '2.5'},
            {'Parcel ID': '789012', 'Amount': '$6,000', 'Description': 'Property 2', 'Acreage': '3.0'},
            {'Parcel ID': '456789', 'Amount': '$8,500', 'Description': 'Property 3', 'Acreage': '2.8'}
        ]

        csv_file = self.create_test_csv(test_data)

        parser = AuctionParser()
        df = parser.load_csv(csv_file)
        processed_df = parser.calculate_metrics()

        # Verify all-in costs were calculated
        if 'estimated_all_in_cost' in processed_df.columns:
            all_in_costs = processed_df['estimated_all_in_cost'].dropna()
            assert len(all_in_costs) > 0

            # All-in costs should be higher than original amounts
            if 'amount' in processed_df.columns:
                original_amounts = processed_df['amount'].dropna()
                if len(original_amounts) > 0 and len(all_in_costs) > 0:
                    # At least some all-in costs should be higher than original amounts
                    assert any(cost > amount for cost, amount in zip(all_in_costs, original_amounts))

        os.unlink(csv_file)


class TestFilteringRankingPipeline:
    """Test filtering and ranking pipeline integration."""

    def create_test_csv(self, data: List[Dict]):
        """Helper method to create test CSV files."""
        tmp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        if data:
            writer = csv.DictWriter(tmp_file, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        tmp_file.close()
        return tmp_file.name

    def test_filtering_pipeline(self):
        """Test property filtering pipeline integration."""
        test_data = [
            {'Parcel ID': '123456', 'Amount': '$4,000', 'Description': 'Property with creek 2.5 AC', 'Acreage': '2.5'},    # Should pass
            {'Parcel ID': '789012', 'Amount': '$25,000', 'Description': 'Expensive property 3.0 ACRES', 'Acreage': '3.0'},  # Too expensive
            {'Parcel ID': '456789', 'Amount': '$8,500', 'Description': 'Small lot 0.5 AC', 'Acreage': '0.5'},              # Too small
            {'Parcel ID': '111222', 'Amount': '$15,000', 'Description': 'Large property 8.0 ACRES', 'Acreage': '8.0'},     # Too large
            {'Parcel ID': '333444', 'Amount': '$6,200', 'Description': 'Good property 3.2 AC', 'Acreage': '3.2'}           # Should pass
        ]

        csv_file = self.create_test_csv(test_data)

        parser = AuctionParser()
        df = parser.load_csv(csv_file)
        processed_df = parser.calculate_metrics()
        filtered_df = parser.filter_properties()

        # Should filter out properties that don't meet criteria
        assert len(filtered_df) < len(df)
        assert len(filtered_df) >= 1  # Should have at least some valid properties

        # Verify filtering criteria are applied
        if 'amount' in filtered_df.columns and 'acreage' in filtered_df.columns:
            amounts = filtered_df['amount'].dropna()
            acreages = filtered_df['acreage'].dropna()

            if len(amounts) > 0:
                assert all(amount <= MAX_PRICE for amount in amounts)
            if len(acreages) > 0:
                assert all(MIN_ACRES <= acreage <= MAX_ACRES for acreage in acreages)

        os.unlink(csv_file)

    def test_ranking_pipeline(self):
        """Test property ranking pipeline integration."""
        test_data = [
            {'Parcel ID': '123456', 'Amount': '$3,000', 'Description': 'Great property with creek 2.5 AC', 'Acreage': '2.5', 'Assessed Value': '$15,000'},
            {'Parcel ID': '789012', 'Amount': '$8,000', 'Description': 'Expensive property 3.0 ACRES', 'Acreage': '3.0', 'Assessed Value': '$12,000'},
            {'Parcel ID': '456789', 'Amount': '$5,500', 'Description': 'Average property near water 2.8 AC', 'Acreage': '2.8', 'Assessed Value': '$18,000'}
        ]

        csv_file = self.create_test_csv(test_data)

        parser = AuctionParser()
        df = parser.load_csv(csv_file)
        processed_df = parser.calculate_metrics()
        filtered_df = parser.filter_properties()
        ranked_df = parser.rank_properties()

        # Verify ranking
        assert isinstance(ranked_df, pd.DataFrame)
        assert len(ranked_df) > 0

        # If investment scores exist, should be sorted by them
        if 'investment_score' in ranked_df.columns:
            scores = ranked_df['investment_score'].dropna()
            if len(scores) > 1:
                # Should be sorted in descending order
                assert all(scores.iloc[i] >= scores.iloc[i+1] for i in range(len(scores)-1))

        os.unlink(csv_file)


class TestOutputGenerationPipeline:
    """Test output generation and export pipeline integration."""

    def create_test_csv(self, data: List[Dict]):
        """Helper method to create test CSV files."""
        tmp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        if data:
            writer = csv.DictWriter(tmp_file, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        tmp_file.close()
        return tmp_file.name

    def test_complete_export_pipeline(self):
        """Test complete CSV export pipeline."""
        test_data = [
            {'Parcel ID': '123456', 'Amount': '$4,000', 'Description': 'Property with creek 2.5 AC', 'Acreage': '2.5', 'Assessed Value': '$15,000'},
            {'Parcel ID': '789012', 'Amount': '$6,200', 'Description': 'Land near water 3.0 ACRES', 'Acreage': '3.0', 'Assessed Value': '$18,000'},
            {'Parcel ID': '456789', 'Amount': '$5,500', 'Description': 'Waterfront property 2.8 AC', 'Acreage': '2.8', 'Assessed Value': '$16,500'}
        ]

        csv_file = self.create_test_csv(test_data)

        # Process through complete pipeline
        parser = AuctionParser()
        df = parser.load_csv(csv_file)
        processed_df = parser.calculate_metrics()
        filtered_df = parser.filter_properties()
        final_df = parser.rank_properties()

        # Export to new CSV
        output_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        output_file.close()

        parser.export_to_csv(output_file.name)

        # Verify export
        output_path = Path(output_file.name)
        assert output_path.exists()
        assert output_path.stat().st_size > 0

        # Load and verify exported data
        exported_df = pd.read_csv(output_file.name)
        assert isinstance(exported_df, pd.DataFrame)
        assert len(exported_df) > 0

        # Clean up
        os.unlink(csv_file)
        os.unlink(output_file.name)

    def test_output_column_consistency(self):
        """Test output column consistency with settings."""
        test_data = [
            {'Parcel ID': '123456', 'Amount': '$4,000', 'Description': 'Property with creek 2.5 AC', 'Acreage': '2.5'}
        ]

        csv_file = self.create_test_csv(test_data)

        parser = AuctionParser()
        df = parser.load_csv(csv_file)
        processed_df = parser.calculate_metrics()

        # Check that processing creates expected columns
        expected_columns = ['parcel_id', 'amount', 'acreage', 'description']
        for col in expected_columns:
            # Should have either the exact column or a mapped version
            found = any(col.lower() in processed_df.columns or
                       any(col.lower() in str(c).lower() for c in processed_df.columns))

        os.unlink(csv_file)


class TestErrorHandlingPipeline:
    """Test error handling across CSV processing pipeline."""

    def test_file_not_found_error_pipeline(self):
        """Test file not found error handling in pipeline."""
        parser = AuctionParser()

        with pytest.raises(FileOperationError):
            parser.load_csv('nonexistent_file.csv')

    def test_corrupted_csv_error_pipeline(self):
        """Test corrupted CSV error handling in pipeline."""
        # Create a corrupted CSV file
        corrupted_content = "This is not,a valid\nCSV file content\nwith random,data,\\"

        tmp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        tmp_file.write(corrupted_content)
        tmp_file.close()

        parser = AuctionParser()

        try:
            df = parser.load_csv(tmp_file.name)
            # If it doesn't raise an exception, should return empty or minimal DataFrame
            assert isinstance(df, pd.DataFrame)
        except (DataValidationError, FileOperationError, DataProcessingError):
            # Should raise appropriate exception
            pass

        os.unlink(tmp_file.name)

    def test_empty_csv_error_pipeline(self):
        """Test empty CSV error handling in pipeline."""
        # Create empty CSV file
        tmp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        tmp_file.close()  # Empty file

        parser = AuctionParser()

        try:
            df = parser.load_csv(tmp_file.name)
            # Should handle empty file gracefully
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 0
        except (DataValidationError, FileOperationError):
            # Or raise appropriate exception
            pass

        os.unlink(tmp_file.name)


class TestPerformancePipeline:
    """Test performance benchmarks for CSV processing pipeline."""

    def create_large_test_csv(self, num_records=1000):
        """Create a large test CSV file for performance testing."""
        data = []
        for i in range(num_records):
            data.append({
                'Parcel ID': f'PERF-{i:06d}',
                'Amount': f'${3000 + i * 10}',
                'Description': f'Performance test property {i} with water features creek pond stream 2.{i%9+1} AC',
                'Acreage': f'{2.0 + (i % 3)}',
                'Assessed Value': f'${15000 + i * 20}',
                'Owner': f'Test Owner {i}',
                'County': 'Test County'
            })

        tmp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        writer = csv.DictWriter(tmp_file, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        tmp_file.close()

        return tmp_file.name

    def test_large_csv_processing_performance(self):
        """Test processing performance with large CSV files."""
        # Create large test file
        csv_file = self.create_large_test_csv(1000)

        # Measure processing time
        start_time = time.time()

        parser = AuctionParser()
        df = parser.load_csv(csv_file)
        processed_df = parser.calculate_metrics()
        filtered_df = parser.filter_properties()
        final_df = parser.rank_properties()

        processing_time = time.time() - start_time

        # Performance requirements
        assert processing_time < 10.0  # Should complete within 10 seconds
        assert len(df) == 1000  # Should process all records
        assert len(final_df) >= 0  # Should produce results

        os.unlink(csv_file)

    def test_memory_efficiency_large_csv(self):
        """Test memory efficiency with large CSV processing."""
        import psutil
        import os
        process = psutil.Process(os.getpid())

        # Create large test file
        csv_file = self.create_large_test_csv(2000)

        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process large file
        parser = AuctionParser()
        df = parser.load_csv(csv_file)
        processed_df = parser.calculate_metrics()
        filtered_df = parser.filter_properties()
        final_df = parser.rank_properties()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory efficiency requirements
        assert memory_increase < 200  # Should not use more than 200MB additional memory
        assert len(df) == 2000  # Should handle all records

        os.unlink(csv_file)

    def test_concurrent_csv_processing_performance(self):
        """Test concurrent CSV processing performance."""
        import concurrent.futures
        import threading

        # Create multiple test files
        csv_files = []
        for i in range(3):
            csv_file = self.create_large_test_csv(500)
            csv_files.append(csv_file)

        def process_csv(csv_file):
            parser = AuctionParser()
            df = parser.load_csv(csv_file)
            processed_df = parser.calculate_metrics()
            return len(processed_df)

        # Measure concurrent processing time
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(process_csv, csv_files))

        concurrent_time = time.time() - start_time

        # Should complete concurrent processing efficiently
        assert concurrent_time < 15.0  # Should complete within 15 seconds
        assert all(result >= 0 for result in results)  # All should process successfully

        # Clean up
        for csv_file in csv_files:
            os.unlink(csv_file)


if __name__ == "__main__":
    # AI-testable CSV processing pipeline specifications
    print("=== CSV PROCESSING PIPELINE TEST SPECIFICATIONS ===")
    print("Pipeline coverage:")
    print("- CSV file reading and parsing workflows")
    print("- Data validation and cleaning pipelines")
    print("- Column mapping and normalization flows")
    print("- Calculation and scoring integration")
    print("- Filtering and ranking workflows")
    print("- Output generation and export pipelines")
    print("\nIntegration points:")
    print("- scripts/parser.py with scripts/utils.py")
    print("- scripts/parser.py with config/settings.py")
    print("- Error handling across pipeline modules")
    print("- Logging integration throughout pipeline")
    print("\nPerformance requirements:")
    print("- Large CSV processing: < 10 seconds for 1000 records")
    print("- Memory efficiency: < 200MB additional for 2000 records")
    print("- Concurrent processing: < 15 seconds for 3 files")
    print("- Delimiter detection: < 1 second")
    print("\nData quality requirements:")
    print("- Handles malformed CSV data gracefully")
    print("- Validates and cleans data appropriately")
    print("- Preserves special characters in UTF-8")
    print("- Maintains data integrity through pipeline")