"""
AI-testable unit tests for scripts/utils.py module.

This module provides comprehensive test coverage for utility functions including
CSV parsing, data normalization, acreage extraction, scoring calculations,
and data validation with AI-friendly patterns and performance benchmarks.
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import os
from unittest.mock import Mock, patch, mock_open
import csv
from io import StringIO
import math

from scripts.utils import (
    detect_csv_delimiter, find_column_mapping, normalize_price,
    parse_acreage_from_description, calculate_water_score,
    calculate_estimated_all_in_cost, calculate_investment_score,
    validate_data_quality, clean_dataframe, format_currency,
    format_acreage, format_score
)
from config.settings import (
    COLUMN_MAPPINGS, PRIMARY_WATER_KEYWORDS, SECONDARY_WATER_KEYWORDS,
    TERTIARY_WATER_KEYWORDS, WATER_SCORE_WEIGHTS, INVESTMENT_SCORE_WEIGHTS,
    MIN_REASONABLE_PRICE, MAX_REASONABLE_PRICE, MIN_REASONABLE_ACRES,
    MAX_REASONABLE_ACRES, MAX_REASONABLE_PRICE_PER_ACRE, ACREAGE_PATTERNS,
    PREFERRED_MIN_ACRES, PREFERRED_MAX_ACRES
)
from tests.fixtures.data_factories import create_sample_property_data


class TestCSVDelimiterDetection:
    """Test suite for CSV delimiter detection functionality."""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_temp_csv(self, content: str, filename: str = 'test.csv') -> str:
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path

    def test_detect_comma_delimiter(self):
        csv_content = "ParcelID,Description,Amount\n001,Property 1,1500\n002,Property 2,2500"
        file_path = self.create_temp_csv(csv_content)

        delimiter = detect_csv_delimiter(file_path)
        assert delimiter == ','

    def test_detect_tab_delimiter(self):
        csv_content = "ParcelID\tDescription\tAmount\n001\tProperty 1\t1500\n002\tProperty 2\t2500"
        file_path = self.create_temp_csv(csv_content)

        delimiter = detect_csv_delimiter(file_path)
        assert delimiter == '\t'

    def test_detect_semicolon_delimiter(self):
        csv_content = "ParcelID;Description;Amount\n001;Property 1;1500\n002;Property 2;2500"
        file_path = self.create_temp_csv(csv_content)

        delimiter = detect_csv_delimiter(file_path)
        assert delimiter == ';'

    def test_detect_pipe_delimiter(self):
        csv_content = "ParcelID|Description|Amount\n001|Property 1|1500\n002|Property 2|2500"
        file_path = self.create_temp_csv(csv_content)

        delimiter = detect_csv_delimiter(file_path)
        assert delimiter == '|'

    def test_detect_delimiter_fallback_to_comma(self):
        irregular_content = "This is not a CSV file with clear delimiters"
        file_path = self.create_temp_csv(irregular_content)

        delimiter = detect_csv_delimiter(file_path)
        assert delimiter == ','

    def test_detect_delimiter_custom_sample_size(self):
        large_csv = "A,B,C\n" + "\n".join([f"{i},{i+1},{i+2}" for i in range(1000)])
        file_path = self.create_temp_csv(large_csv)

        delimiter = detect_csv_delimiter(file_path, sample_size=100)
        assert delimiter == ','

    @pytest.mark.ai_test
    def test_delimiter_detection_performance_benchmark(self, benchmark):
        csv_content = "A,B,C\n" + "\n".join([f"{i},{i+1},{i+2}" for i in range(100)])
        file_path = self.create_temp_csv(csv_content)

        result = benchmark(detect_csv_delimiter, file_path)
        assert result == ','
        assert benchmark.stats['mean'] < 0.01

    def test_detect_delimiter_empty_file(self):
        file_path = self.create_temp_csv("")

        delimiter = detect_csv_delimiter(file_path)
        assert delimiter == ','

    def test_detect_delimiter_single_line(self):
        csv_content = "ParcelID,Description,Amount"
        file_path = self.create_temp_csv(csv_content)

        delimiter = detect_csv_delimiter(file_path)
        assert delimiter == ','

    def test_detect_delimiter_mixed_delimiters(self):
        mixed_content = "A,B;C\n1,2;3\n4,5;6"
        file_path = self.create_temp_csv(mixed_content)

        delimiter = detect_csv_delimiter(file_path)
        assert delimiter in [',', ';']


class TestColumnMapping:
    """Test suite for column mapping functionality."""

    def test_find_exact_match(self):
        df_columns = ['Parcel ID', 'Property Description', 'Amount']
        result = find_column_mapping(df_columns, 'parcel_id')
        assert result == 'Parcel ID'

    def test_find_case_insensitive_match(self):
        df_columns = ['PARCEL_ID', 'DESCRIPTION', 'AMOUNT']
        result = find_column_mapping(df_columns, 'parcel_id')
        assert result == 'PARCEL_ID'

    def test_find_partial_match(self):
        df_columns = ['CS Number', 'Prop Desc', 'Sale Amount']
        result = find_column_mapping(df_columns, 'parcel_id')
        assert result == 'CS Number'

    def test_find_alternative_column_names(self):
        df_columns = ['Tax ID', 'Location', 'Bid Amount']

        result1 = find_column_mapping(df_columns, 'parcel_id')
        assert result1 == 'Tax ID'

        result2 = find_column_mapping(df_columns, 'description')
        assert result2 == 'Location'

        result3 = find_column_mapping(df_columns, 'amount')
        assert result3 == 'Bid Amount'

    def test_find_no_match(self):
        df_columns = ['Unknown1', 'Unknown2', 'Unknown3']
        result = find_column_mapping(df_columns, 'parcel_id')
        assert result is None

    def test_find_invalid_target_field(self):
        df_columns = ['Parcel ID', 'Description', 'Amount']
        result = find_column_mapping(df_columns, 'nonexistent_field')
        assert result is None

    def test_find_with_whitespace(self):
        df_columns = ['  Parcel ID  ', ' Description ', 'Amount ']
        result = find_column_mapping(df_columns, 'parcel_id')
        assert result == '  Parcel ID  '

    @pytest.mark.ai_test
    def test_column_mapping_performance_benchmark(self, benchmark):
        df_columns = [f'Column_{i}' for i in range(100)] + ['Parcel ID']

        result = benchmark(find_column_mapping, df_columns, 'parcel_id')
        assert result == 'Parcel ID'
        assert benchmark.stats['mean'] < 0.01

    def test_find_all_standard_fields(self):
        standard_columns = [
            'Parcel Number', 'Property Description', 'Amount Bid at Tax Sale',
            'Assessed Value', 'Acreage', 'Year Sold', 'Owner Name', 'County'
        ]

        expected_mappings = {
            'parcel_id': 'Parcel Number',
            'description': 'Property Description',
            'amount': 'Amount Bid at Tax Sale',
            'assessed_value': 'Assessed Value',
            'acreage': 'Acreage',
            'year_sold': 'Year Sold',
            'owner_name': 'Owner Name',
            'county': 'County'
        }

        for field, expected in expected_mappings.items():
            result = find_column_mapping(standard_columns, field)
            assert result == expected

    def test_find_with_underscore_variations(self):
        df_columns = ['parcel_number', 'property_description', 'sale_price']

        assert find_column_mapping(df_columns, 'parcel_id') == 'parcel_number'
        assert find_column_mapping(df_columns, 'description') == 'property_description'
        assert find_column_mapping(df_columns, 'amount') == 'sale_price'


class TestPriceNormalization:
    """Test suite for price normalization functionality."""

    def test_normalize_simple_numbers(self):
        assert normalize_price('1500') == 1500.0
        assert normalize_price('2500.50') == 2500.50
        assert normalize_price(1500) == 1500.0
        assert normalize_price(2500.75) == 2500.75

    def test_normalize_currency_format(self):
        assert normalize_price('$1,500.00') == 1500.0
        assert normalize_price('$2,500.50') == 2500.50
        assert normalize_price('$15,000') == 15000.0

    def test_normalize_with_commas(self):
        assert normalize_price('1,500') == 1500.0
        assert normalize_price('15,000.00') == 15000.0
        # 1,234,567.89 exceeds MAX_REASONABLE_PRICE (1000000.0), so returns None
        assert normalize_price('999,999.99') == 999999.99

    def test_normalize_with_whitespace(self):
        assert normalize_price('  1500  ') == 1500.0
        assert normalize_price('$ 1,500.00 ') == 1500.0

    def test_normalize_invalid_inputs(self):
        assert normalize_price('') is None
        assert normalize_price('N/A') is None
        assert normalize_price('null') is None
        assert normalize_price('invalid') is None
        assert normalize_price(None) is None
        assert normalize_price(np.nan) is None

    def test_normalize_unreasonable_values(self):
        # 0 is less than MIN_REASONABLE_PRICE (1.0), so returns None
        assert normalize_price('0') is None
        assert normalize_price('-100') is None
        assert normalize_price('10000000') is None

    def test_normalize_edge_case_values(self):
        assert normalize_price(str(MIN_REASONABLE_PRICE)) == MIN_REASONABLE_PRICE
        assert normalize_price(str(MAX_REASONABLE_PRICE)) == MAX_REASONABLE_PRICE
        assert normalize_price(str(MAX_REASONABLE_PRICE + 1)) is None

    @pytest.mark.ai_test
    def test_price_normalization_performance_benchmark(self, benchmark):
        test_prices = ['$1,500.00', '$2,500.50', '$15,000', '25000', 'invalid']

        def normalize_batch():
            return [normalize_price(price) for price in test_prices]

        result = benchmark(normalize_batch)
        assert len(result) == 5
        assert result[0] == 1500.0
        assert result[-1] is None
        assert benchmark.stats['mean'] < 0.001

    def test_normalize_decimal_edge_cases(self):
        assert normalize_price('1500.') == 1500.0
        assert normalize_price('.50') == 0.5
        assert normalize_price('1500.000') == 1500.0

    def test_normalize_scientific_notation(self):
        assert normalize_price('1.5e3') == 1500.0
        assert normalize_price('2.5E4') == 25000.0

    def test_normalize_currency_symbols(self):
        assert normalize_price('$1500') == 1500.0
        assert normalize_price('USD 1500') is None


class TestAcreageParsing:
    """Test suite for acreage parsing from descriptions."""

    def test_parse_direct_acres(self):
        assert parse_acreage_from_description('Property with 2.5 acres') == 2.5
        assert parse_acreage_from_description('3 AC lot') == 3.0
        assert parse_acreage_from_description('1.25 ACRE property') == 1.25

    def test_parse_fractional_acres(self):
        assert parse_acreage_from_description('1/2 acre lot') == 0.5
        assert parse_acreage_from_description('3/4 ACRES') == 0.75
        assert parse_acreage_from_description('2/3 AC') == pytest.approx(0.667, rel=1e-2)

    def test_parse_square_feet(self):
        assert parse_acreage_from_description('43560 SF lot') == 1.0
        assert parse_acreage_from_description('87120 SQ FT') == 2.0
        assert parse_acreage_from_description('21780 square feet') == 0.5

    def test_parse_rectangular_dimensions(self):
        assert parse_acreage_from_description('100\' X 150\'') == pytest.approx(0.344, rel=1e-2)
        assert parse_acreage_from_description('200 x 218.7') == pytest.approx(1.003, rel=1e-2)
        assert parse_acreage_from_description('75\'X100\'') == pytest.approx(0.172, rel=1e-2)

    def test_parse_no_acreage_found(self):
        assert parse_acreage_from_description('Property description without acreage') is None
        assert parse_acreage_from_description('Nice location') is None
        assert parse_acreage_from_description('') is None
        assert parse_acreage_from_description(None) is None

    def test_parse_invalid_inputs(self):
        assert parse_acreage_from_description(123) is None
        assert parse_acreage_from_description(np.nan) is None
        assert parse_acreage_from_description([]) is None

    def test_parse_unreasonable_values(self):
        assert parse_acreage_from_description('0.001 acres') is None
        assert parse_acreage_from_description('2000 acres') is None
        assert parse_acreage_from_description('10000000 SF') is None

    def test_parse_case_insensitive(self):
        assert parse_acreage_from_description('2.5 acres') == 2.5
        assert parse_acreage_from_description('2.5 ACRES') == 2.5
        assert parse_acreage_from_description('2.5 Acres') == 2.5

    @pytest.mark.ai_test
    def test_acreage_parsing_performance_benchmark(self, benchmark):
        descriptions = [
            'Property with 2.5 acres',
            '43560 SF lot',
            '1/2 acre',
            '100\' X 200\'',
            'No acreage mentioned'
        ]

        def parse_batch():
            return [parse_acreage_from_description(desc) for desc in descriptions]

        result = benchmark(parse_batch)
        assert len(result) == 5
        assert result[0] == 2.5
        assert result[1] == 1.0
        assert benchmark.stats['mean'] < 0.001

    def test_parse_multiple_patterns_priority(self):
        desc = '2.5 acres with 43560 SF'
        result = parse_acreage_from_description(desc)
        assert result == 2.5

    def test_parse_edge_case_dimensions(self):
        assert parse_acreage_from_description('208.7\' x 208.7\'') == pytest.approx(1.0, rel=1e-2)
        assert parse_acreage_from_description('1\'x43560\'') == pytest.approx(1.0, rel=1e-2)

    def test_parse_fractional_edge_cases(self):
        assert parse_acreage_from_description('0/1 acres') is None
        assert parse_acreage_from_description('1/0 acres') is None
        assert parse_acreage_from_description('10/3 acres') == pytest.approx(3.333, rel=1e-2)


class TestWaterScoreCalculation:
    """Test suite for water score calculation functionality."""

    def test_calculate_primary_keywords(self):
        descriptions = {
            'Property near creek': WATER_SCORE_WEIGHTS['primary'],
            'Lake front property': WATER_SCORE_WEIGHTS['primary'],
            'Property with stream': WATER_SCORE_WEIGHTS['primary'],
            'River access lot': WATER_SCORE_WEIGHTS['primary'],
            'Pond on property': WATER_SCORE_WEIGHTS['primary'],
            'Natural spring': WATER_SCORE_WEIGHTS['primary']
        }

        for desc, expected_score in descriptions.items():
            score = calculate_water_score(desc)
            assert score == expected_score

    def test_calculate_secondary_keywords(self):
        descriptions = {
            'Property near branch': WATER_SCORE_WEIGHTS['secondary'],
            'Creek run access': WATER_SCORE_WEIGHTS['secondary'],
            'Brook nearby': WATER_SCORE_WEIGHTS['secondary'],
            'Tributary access': WATER_SCORE_WEIGHTS['secondary'],
            'Wetland area': WATER_SCORE_WEIGHTS['secondary'],
            'Marsh property': WATER_SCORE_WEIGHTS['secondary']
        }

        for desc, expected_score in descriptions.items():
            score = calculate_water_score(desc)
            assert score == expected_score

    def test_calculate_tertiary_keywords(self):
        descriptions = {
            'Water access': WATER_SCORE_WEIGHTS['tertiary'],
            'Aquatic habitat': WATER_SCORE_WEIGHTS['tertiary'],
            'Riparian rights': WATER_SCORE_WEIGHTS['tertiary'],
            'Shore access': WATER_SCORE_WEIGHTS['tertiary'],
            'Bank property': WATER_SCORE_WEIGHTS['tertiary'],
            'Waterfront lot': WATER_SCORE_WEIGHTS['tertiary']
        }

        for desc, expected_score in descriptions.items():
            score = calculate_water_score(desc)
            assert score == expected_score

    def test_calculate_multiple_keywords(self):
        desc = 'Creek and pond property with river access'
        expected = WATER_SCORE_WEIGHTS['primary'] * 3
        score = calculate_water_score(desc)
        assert score == expected

    def test_calculate_mixed_keyword_types(self):
        desc = 'Creek property with branch and water access'
        expected = (WATER_SCORE_WEIGHTS['primary'] +
                   WATER_SCORE_WEIGHTS['secondary'] +
                   WATER_SCORE_WEIGHTS['tertiary'])
        score = calculate_water_score(desc)
        assert score == expected

    def test_calculate_no_water_features(self):
        descriptions = [
            'Regular property',
            'Mountain view lot',
            'Forest property',
            'Open field',
            ''
        ]

        for desc in descriptions:
            score = calculate_water_score(desc)
            assert score == 0.0

    def test_calculate_case_insensitive(self):
        descriptions = [
            'CREEK property',
            'creek PROPERTY',
            'Creek Property',
            'cReEk property'
        ]

        expected_score = WATER_SCORE_WEIGHTS['primary']
        for desc in descriptions:
            score = calculate_water_score(desc)
            assert score == expected_score

    def test_calculate_invalid_inputs(self):
        assert calculate_water_score(None) == 0.0
        assert calculate_water_score(np.nan) == 0.0
        assert calculate_water_score(123) == 0.0
        assert calculate_water_score([]) == 0.0

    @pytest.mark.ai_test
    def test_water_score_performance_benchmark(self, benchmark):
        descriptions = [
            'Property near creek and pond with stream access',
            'Mountain view property with no water',
            'Lake front with river and branch access',
            'Regular residential lot',
            'Wetland area with aquatic habitat'
        ]

        def calculate_batch():
            return [calculate_water_score(desc) for desc in descriptions]

        result = benchmark(calculate_batch)
        assert len(result) == 5
        assert result[0] > 0
        assert result[1] == 0
        assert benchmark.stats['mean'] < 0.001

    def test_calculate_partial_word_matches(self):
        desc = 'Creekside property'
        score = calculate_water_score(desc)
        assert score == WATER_SCORE_WEIGHTS['primary']

    def test_calculate_duplicate_keywords(self):
        desc = 'Creek property near creek with creek access'
        expected = WATER_SCORE_WEIGHTS['primary'] * 3
        score = calculate_water_score(desc)
        assert score == expected


class TestCostCalculation:
    """Test suite for estimated all-in cost calculation."""

    def test_calculate_basic_cost(self):
        bid_amount = 10000.0
        expected = 10000.0 + 35.0 + (10000.0 * 0.05) + 100.0
        result = calculate_estimated_all_in_cost(bid_amount)
        assert result == expected

    def test_calculate_custom_fees(self):
        bid_amount = 10000.0
        recording_fee = 50.0
        county_fee_percent = 0.03
        misc_fees = 150.0

        expected = 10000.0 + 50.0 + (10000.0 * 0.03) + 150.0
        result = calculate_estimated_all_in_cost(
            bid_amount, recording_fee, county_fee_percent, misc_fees
        )
        assert result == expected

    def test_calculate_zero_bid(self):
        result = calculate_estimated_all_in_cost(0.0)
        assert result == 0.0

    def test_calculate_negative_bid(self):
        result = calculate_estimated_all_in_cost(-1000.0)
        assert result == 0.0

    def test_calculate_invalid_bid(self):
        assert calculate_estimated_all_in_cost(np.nan) == 0.0
        assert calculate_estimated_all_in_cost(None) == 0.0

    def test_calculate_large_amounts(self):
        bid_amount = 100000.0
        expected = 100000.0 + 35.0 + (100000.0 * 0.05) + 100.0
        result = calculate_estimated_all_in_cost(bid_amount)
        assert result == expected

    @pytest.mark.ai_test
    def test_cost_calculation_performance_benchmark(self, benchmark):
        bid_amounts = [1000, 5000, 10000, 15000, 20000]

        def calculate_batch():
            return [calculate_estimated_all_in_cost(amount) for amount in bid_amounts]

        result = benchmark(calculate_batch)
        assert len(result) == 5
        assert all(cost > amount for cost, amount in zip(result, bid_amounts))
        assert benchmark.stats['mean'] < 0.001

    def test_calculate_fractional_amounts(self):
        bid_amount = 1500.75
        expected = 1500.75 + 35.0 + (1500.75 * 0.05) + 100.0
        result = calculate_estimated_all_in_cost(bid_amount)
        assert result == pytest.approx(expected, rel=1e-6)

    def test_calculate_fee_edge_cases(self):
        bid_amount = 1000.0

        result_zero_fees = calculate_estimated_all_in_cost(
            bid_amount, recording_fee=0.0, county_fee_percent=0.0, misc_fees=0.0
        )
        assert result_zero_fees == 1000.0

        result_high_percent = calculate_estimated_all_in_cost(
            bid_amount, county_fee_percent=0.1
        )
        expected_high = 1000.0 + 35.0 + (1000.0 * 0.1) + 100.0
        assert result_high_percent == expected_high


class TestInvestmentScoreCalculation:
    """Test suite for investment score calculation functionality."""

    def test_calculate_basic_score(self):
        score = calculate_investment_score(
            price_per_acre=5000.0,
            acreage=3.0,
            water_score=3.0,
            assessed_value_ratio=0.5,
            weights=INVESTMENT_SCORE_WEIGHTS
        )

        assert isinstance(score, float)
        assert score > 0

    def test_calculate_perfect_acreage_score(self):
        perfect_acreage = (PREFERRED_MIN_ACRES + PREFERRED_MAX_ACRES) / 2

        score = calculate_investment_score(
            price_per_acre=5000.0,
            acreage=perfect_acreage,
            water_score=0.0,
            assessed_value_ratio=1.0,
            weights=INVESTMENT_SCORE_WEIGHTS
        )

        assert score > 0

    def test_calculate_low_price_per_acre_bonus(self):
        low_price_score = calculate_investment_score(
            price_per_acre=1000.0,
            acreage=3.0,
            water_score=0.0,
            assessed_value_ratio=1.0,
            weights=INVESTMENT_SCORE_WEIGHTS
        )

        high_price_score = calculate_investment_score(
            price_per_acre=10000.0,
            acreage=3.0,
            water_score=0.0,
            assessed_value_ratio=1.0,
            weights=INVESTMENT_SCORE_WEIGHTS
        )

        assert low_price_score > high_price_score

    def test_calculate_water_feature_bonus(self):
        with_water = calculate_investment_score(
            price_per_acre=5000.0,
            acreage=3.0,
            water_score=6.0,
            assessed_value_ratio=1.0,
            weights=INVESTMENT_SCORE_WEIGHTS
        )

        without_water = calculate_investment_score(
            price_per_acre=5000.0,
            acreage=3.0,
            water_score=0.0,
            assessed_value_ratio=1.0,
            weights=INVESTMENT_SCORE_WEIGHTS
        )

        assert with_water > without_water

    def test_calculate_assessed_value_ratio_bonus(self):
        good_deal_score = calculate_investment_score(
            price_per_acre=5000.0,
            acreage=3.0,
            water_score=0.0,
            assessed_value_ratio=0.5,
            weights=INVESTMENT_SCORE_WEIGHTS
        )

        expensive_score = calculate_investment_score(
            price_per_acre=5000.0,
            acreage=3.0,
            water_score=0.0,
            assessed_value_ratio=2.0,
            weights=INVESTMENT_SCORE_WEIGHTS
        )

        assert good_deal_score > expensive_score

    def test_calculate_zero_values(self):
        score = calculate_investment_score(
            price_per_acre=0.0,
            acreage=0.0,
            water_score=0.0,
            assessed_value_ratio=0.0,
            weights=INVESTMENT_SCORE_WEIGHTS
        )

        assert score == 0.0

    def test_calculate_custom_weights(self):
        custom_weights = {
            'price_per_acre': 1.0,
            'acreage_preference': 0.0,
            'water_features': 0.0,
            'assessed_value_ratio': 0.0
        }

        score = calculate_investment_score(
            price_per_acre=5000.0,
            acreage=3.0,
            water_score=3.0,
            assessed_value_ratio=0.5,
            weights=custom_weights
        )

        assert score > 0

    @pytest.mark.ai_test
    def test_investment_score_performance_benchmark(self, benchmark):
        test_cases = [
            (1000.0, 3.0, 6.0, 0.5),
            (5000.0, 2.0, 3.0, 1.0),
            (8000.0, 4.0, 0.0, 1.5),
            (3000.0, 1.5, 9.0, 0.3),
            (15000.0, 5.0, 1.0, 2.0)
        ]

        def calculate_batch():
            return [
                calculate_investment_score(ppa, acre, water, ratio, INVESTMENT_SCORE_WEIGHTS)
                for ppa, acre, water, ratio in test_cases
            ]

        result = benchmark(calculate_batch)
        assert len(result) == 5
        assert all(isinstance(score, float) for score in result)
        assert benchmark.stats['mean'] < 0.001

    def test_calculate_acreage_penalties(self):
        too_small_score = calculate_investment_score(
            price_per_acre=5000.0,
            acreage=0.5,
            water_score=0.0,
            assessed_value_ratio=1.0,
            weights=INVESTMENT_SCORE_WEIGHTS
        )

        too_large_score = calculate_investment_score(
            price_per_acre=5000.0,
            acreage=10.0,
            water_score=0.0,
            assessed_value_ratio=1.0,
            weights=INVESTMENT_SCORE_WEIGHTS
        )

        perfect_score = calculate_investment_score(
            price_per_acre=5000.0,
            acreage=3.0,
            water_score=0.0,
            assessed_value_ratio=1.0,
            weights=INVESTMENT_SCORE_WEIGHTS
        )

        assert perfect_score > too_small_score
        assert perfect_score > too_large_score

    def test_calculate_score_rounding(self):
        score = calculate_investment_score(
            price_per_acre=3333.333,
            acreage=2.666,
            water_score=1.234,
            assessed_value_ratio=0.777,
            weights=INVESTMENT_SCORE_WEIGHTS
        )

        assert len(str(score).split('.')[-1]) <= 1


class TestDataQualityValidation:
    """Test suite for data quality validation functionality."""

    def test_validate_complete_data(self):
        df = pd.DataFrame({
            'parcel_id': ['001', '002', '003'],
            'amount': [1500.0, 2500.0, 1800.0],
            'description': ['Property 1', 'Property 2', 'Property 3']
        })

        result = validate_data_quality(df)

        assert result['total_records'] == 3
        assert len(result['issues']) == 0
        assert len(result['warnings']) == 0

    def test_validate_missing_required_columns(self):
        df = pd.DataFrame({
            'other_column': ['value1', 'value2']
        })

        result = validate_data_quality(df)

        assert len(result['issues']) > 0
        assert 'Missing required columns' in result['issues'][0]

    def test_validate_missing_amount_data(self):
        df = pd.DataFrame({
            'parcel_id': ['001', '002', '003'],
            'amount': [1500.0, np.nan, 1800.0],
            'description': ['Property 1', 'Property 2', 'Property 3']
        })

        result = validate_data_quality(df)

        assert any('missing amount data' in warning for warning in result['warnings'])

    def test_validate_missing_parcel_data(self):
        df = pd.DataFrame({
            'parcel_id': ['001', np.nan, '003'],
            'amount': [1500.0, 2500.0, 1800.0],
            'description': ['Property 1', 'Property 2', 'Property 3']
        })

        result = validate_data_quality(df)

        assert any('missing parcel ID' in warning for warning in result['warnings'])

    def test_validate_high_price_per_acre(self):
        df = pd.DataFrame({
            'parcel_id': ['001', '002'],
            'amount': [1500.0, 2500.0],
            'description': ['Property 1', 'Property 2'],
            'price_per_acre': [5000.0, 100000.0]
        })

        result = validate_data_quality(df)

        assert any('unusually high price per acre' in warning for warning in result['warnings'])

    def test_validate_empty_dataframe(self):
        df = pd.DataFrame()

        result = validate_data_quality(df)

        assert result['total_records'] == 0
        assert len(result['issues']) > 0

    @pytest.mark.ai_test
    def test_data_validation_performance_benchmark(self, benchmark):
        df = create_sample_property_data(num_records=1000)

        result = benchmark(validate_data_quality, df)

        assert isinstance(result, dict)
        assert 'total_records' in result
        assert result['total_records'] == 1000
        assert benchmark.stats['mean'] < 0.1

    def test_validate_partial_required_columns(self):
        df = pd.DataFrame({
            'parcel_id': ['001', '002'],
            'amount': [1500.0, 2500.0]
        })

        result = validate_data_quality(df)

        assert any('description' in issue for issue in result['issues'])

    def test_validate_all_warnings_scenarios(self):
        df = pd.DataFrame({
            'parcel_id': ['001', np.nan, '003'],
            'amount': [1500.0, np.nan, 1800.0],
            'description': ['Property 1', 'Property 2', 'Property 3'],
            'price_per_acre': [5000.0, 75000.0, 3000.0]
        })

        result = validate_data_quality(df)

        assert len(result['warnings']) == 3


class TestDataFrameCleaning:
    """Test suite for DataFrame cleaning functionality."""

    def test_clean_basic_dataframe(self):
        df = pd.DataFrame({
            'parcel_id': ['  001  ', '002', '  003  '],
            'description': ['Property 1', 'Property 2', 'Property 3'],
            'amount': ['1500', '2500', '1800']
        })

        cleaned = clean_dataframe(df)

        assert cleaned['parcel_id'].iloc[0] == '001'
        assert cleaned['parcel_id'].iloc[2] == '003'
        assert len(cleaned) == 3

    def test_clean_remove_null_representations(self):
        df = pd.DataFrame({
            'parcel_id': ['001', 'null', '003'],
            'description': ['Property 1', 'NaN', 'Property 3'],
            'amount': ['1500', 'NULL', '1800']
        })

        cleaned = clean_dataframe(df)

        assert pd.isna(cleaned['parcel_id'].iloc[1])
        assert pd.isna(cleaned['description'].iloc[1])
        assert pd.isna(cleaned['amount'].iloc[1])

    def test_clean_remove_empty_rows(self):
        df = pd.DataFrame({
            'parcel_id': ['001', np.nan, '003'],
            'description': ['Property 1', np.nan, 'Property 3'],
            'amount': ['1500', np.nan, '1800']
        })

        cleaned = clean_dataframe(df)

        assert len(cleaned) == 2
        assert '001' in cleaned['parcel_id'].values
        assert '003' in cleaned['parcel_id'].values

    def test_clean_remove_duplicates(self):
        df = pd.DataFrame({
            'parcel_id': ['001', '002', '001', '003'],
            'description': ['Property 1', 'Property 2', 'Property 1 Duplicate', 'Property 3'],
            'amount': ['1500', '2500', '1600', '1800']
        })

        cleaned = clean_dataframe(df)

        assert len(cleaned) == 3
        assert cleaned[cleaned['parcel_id'] == '001']['description'].iloc[0] == 'Property 1'

    def test_clean_no_parcel_id_column(self):
        df = pd.DataFrame({
            'description': ['Property 1', 'Property 2', 'Property 3'],
            'amount': ['1500', '2500', '1800']
        })

        cleaned = clean_dataframe(df)

        assert len(cleaned) == 3
        assert 'description' in cleaned.columns

    @pytest.mark.ai_test
    def test_dataframe_cleaning_performance_benchmark(self, benchmark):
        df = create_sample_property_data(num_records=5000)
        df.loc[::100, 'parcel_id'] = '  ' + df.loc[::100, 'parcel_id'] + '  '
        df.loc[::200, 'description'] = 'null'

        result = benchmark(clean_dataframe, df)

        assert len(result) <= 5000
        assert isinstance(result, pd.DataFrame)
        assert benchmark.stats['mean'] < 1.0

    def test_clean_preserve_data_types(self):
        df = pd.DataFrame({
            'parcel_id': ['001', '002', '003'],
            'amount': [1500.0, 2500.0, 1800.0],
            'count': [1, 2, 3]
        })

        cleaned = clean_dataframe(df)

        assert cleaned['amount'].dtype == df['amount'].dtype
        assert cleaned['count'].dtype == df['count'].dtype

    def test_clean_complex_null_patterns(self):
        df = pd.DataFrame({
            'parcel_id': ['001', '', 'none', 'NONE', '002'],
            'description': ['Property 1', 'null', 'NULL', 'nan', 'Property 2'],
            'amount': ['1500', 'NaN', '', 'null', '2500']
        })

        cleaned = clean_dataframe(df)

        non_null_parcels = cleaned['parcel_id'].notna().sum()
        assert non_null_parcels == 2

    def test_clean_empty_dataframe(self):
        df = pd.DataFrame()

        cleaned = clean_dataframe(df)

        assert len(cleaned) == 0
        assert isinstance(cleaned, pd.DataFrame)


class TestFormattingFunctions:
    """Test suite for formatting utility functions."""

    def test_format_currency_basic(self):
        assert format_currency(1500.0) == '$1,500.00'
        assert format_currency(2500.50) == '$2,500.50'
        assert format_currency(15000) == '$15,000.00'

    def test_format_currency_large_amounts(self):
        assert format_currency(1000000) == '$1,000,000.00'
        assert format_currency(1234567.89) == '$1,234,567.89'

    def test_format_currency_small_amounts(self):
        assert format_currency(0.50) == '$0.50'
        assert format_currency(0.01) == '$0.01'
        assert format_currency(0) == '$0.00'

    def test_format_currency_invalid_inputs(self):
        assert format_currency(None) == 'N/A'
        assert format_currency(np.nan) == 'N/A'

    def test_format_acreage_basic(self):
        assert format_acreage(2.5) == '2.50'
        assert format_acreage(1.0) == '1.00'
        assert format_acreage(3.333) == '3.33'

    def test_format_acreage_edge_cases(self):
        assert format_acreage(0.1) == '0.10'
        assert format_acreage(100.0) == '100.00'
        assert format_acreage(0.001) == '0.00'

    def test_format_acreage_invalid_inputs(self):
        assert format_acreage(None) == 'N/A'
        assert format_acreage(np.nan) == 'N/A'

    def test_format_score_basic(self):
        assert format_score(8.5) == '8.5'
        assert format_score(10.0) == '10.0'
        assert format_score(7.33) == '7.3'

    def test_format_score_rounding(self):
        assert format_score(8.56) == '8.6'
        assert format_score(8.54) == '8.5'
        assert format_score(8.55) == '8.6'

    def test_format_score_invalid_inputs(self):
        assert format_score(None) == 'N/A'
        assert format_score(np.nan) == 'N/A'

    @pytest.mark.ai_test
    def test_formatting_performance_benchmark(self, benchmark):
        values = [1500.50, 2.75, 8.33, 25000.0, 1.25]

        def format_batch():
            currencies = [format_currency(v) for v in values]
            acreages = [format_acreage(v) for v in values]
            scores = [format_score(v) for v in values]
            return currencies, acreages, scores

        result = benchmark(format_batch)

        currencies, acreages, scores = result
        assert len(currencies) == 5
        assert len(acreages) == 5
        assert len(scores) == 5
        assert benchmark.stats['mean'] < 0.001

    def test_format_currency_negative_values(self):
        assert format_currency(-1500.0) == '-$1,500.00'

    def test_format_consistency_across_functions(self):
        value = 1234.56

        currency = format_currency(value)
        acreage = format_acreage(value)
        score = format_score(value)

        assert '$' in currency
        assert '.' in acreage
        assert '.' in score


@pytest.mark.integration
class TestUtilitiesIntegrationScenarios:
    """Integration test scenarios combining multiple utility functions."""

    def test_complete_property_processing_workflow(self):
        raw_property_data = {
            'description': 'Property with 2.5 acres near creek and pond',
            'amount': '$15,000.00',
            'assessed_value': '$30,000'
        }

        # Parse acreage
        acreage = parse_acreage_from_description(raw_property_data['description'])
        assert acreage == 2.5

        # Normalize price
        amount = normalize_price(raw_property_data['amount'])
        assert amount == 15000.0

        assessed_value = normalize_price(raw_property_data['assessed_value'])
        assert assessed_value == 30000.0

        # Calculate water score
        water_score = calculate_water_score(raw_property_data['description'])
        assert water_score == WATER_SCORE_WEIGHTS['primary'] * 2

        # Calculate metrics
        price_per_acre = amount / acreage
        all_in_cost = calculate_estimated_all_in_cost(amount)
        assessed_ratio = amount / assessed_value
        investment_score = calculate_investment_score(
            price_per_acre, acreage, water_score, assessed_ratio, INVESTMENT_SCORE_WEIGHTS
        )

        # Format outputs
        formatted_amount = format_currency(amount)
        formatted_acreage = format_acreage(acreage)
        formatted_score = format_score(investment_score)

        assert formatted_amount == '$15,000.00'
        assert formatted_acreage == '2.50'
        assert '.' in formatted_score

    def test_csv_processing_integration(self):
        csv_content = 'Parcel ID,Description,Amount\n001,"2.5 acres near creek",$15000\n002,"No water features",12000'

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name

        try:
            # Detect delimiter
            delimiter = detect_csv_delimiter(temp_path)
            assert delimiter == ','

            # Load and process data
            df = pd.read_csv(temp_path, delimiter=delimiter)

            # Find column mappings
            parcel_col = find_column_mapping(df.columns.tolist(), 'parcel_id')
            desc_col = find_column_mapping(df.columns.tolist(), 'description')
            amount_col = find_column_mapping(df.columns.tolist(), 'amount')

            assert parcel_col == 'Parcel ID'
            assert desc_col == 'Description'
            assert amount_col == 'Amount'

            # Clean and process
            df_clean = clean_dataframe(df)

            # Validate quality
            quality_report = validate_data_quality(df_clean)
            assert quality_report['total_records'] == 2

        finally:
            os.unlink(temp_path)

    @pytest.mark.ai_test
    def test_large_dataset_processing_performance(self, benchmark):
        def process_large_dataset():
            # Create large dataset
            descriptions = [
                'Property with 2.5 acres near creek',
                '43560 SF lot with pond',
                'Regular 3 acre property',
                '1/2 acre waterfront lot',
                'Large 5 acre parcel'
            ] * 200

            prices = ['$15,000', '$12,500', '$18,000', '$8,500', '$22,000'] * 200

            # Process all data
            acreages = [parse_acreage_from_description(desc) for desc in descriptions]
            water_scores = [calculate_water_score(desc) for desc in descriptions]
            amounts = [normalize_price(price) for price in prices]

            # Calculate derived metrics
            results = []
            for i in range(len(descriptions)):
                if acreages[i] and amounts[i]:
                    price_per_acre = amounts[i] / acreages[i]
                    all_in_cost = calculate_estimated_all_in_cost(amounts[i])
                    investment_score = calculate_investment_score(
                        price_per_acre, acreages[i], water_scores[i], 0.5, INVESTMENT_SCORE_WEIGHTS
                    )
                    results.append({
                        'acreage': acreages[i],
                        'amount': amounts[i],
                        'water_score': water_scores[i],
                        'investment_score': investment_score
                    })

            return results

        results = benchmark(process_large_dataset)

        assert len(results) > 500
        assert all('investment_score' in result for result in results)
        assert benchmark.stats['mean'] < 5.0

    def test_error_handling_integration(self):
        problematic_data = [
            ('invalid price', None),
            ('No acreage mentioned', None),
            ('', 0.0),
            (None, 0.0),
            ('43560 SF property', 1.0)
        ]

        for description, expected_acreage in problematic_data:
            # Should not raise exceptions
            acreage = parse_acreage_from_description(description)
            water_score = calculate_water_score(description)

            if expected_acreage is not None:
                assert acreage == expected_acreage

            assert isinstance(water_score, float)
            assert water_score >= 0

    def test_data_quality_edge_cases_integration(self):
        edge_case_df = pd.DataFrame({
            'parcel_id': ['', '001', 'null', 'NULL', '002'],
            'amount': [0, 15000, np.nan, 'invalid', 25000],
            'description': ['', 'Property 1', 'nan', 'Property with NaN', 'Property 2'],
            'price_per_acre': [0, 6000, 100000, 5000, 12500]
        })

        # Clean data
        cleaned = clean_dataframe(edge_case_df)

        # Validate quality
        quality_report = validate_data_quality(cleaned)

        # Should handle edge cases gracefully
        assert isinstance(quality_report, dict)
        assert 'total_records' in quality_report
        assert 'issues' in quality_report
        assert 'warnings' in quality_report


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])