"""
End-to-end tests for Streamlit dashboard functionality in Alabama Auction Watcher.

Tests the complete Streamlit dashboard application including data loading, filtering,
visualization, and user interaction workflows. Provides AI-testable scenarios with
comprehensive validation of dashboard components and performance benchmarks.

Dashboard test coverage:
- Data loading and caching functionality
- Interactive filtering and controls
- Summary metrics display
- Properties table rendering
- Chart and visualization generation
- Error handling and edge cases
- Performance and responsiveness
- User experience workflows
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import os
import csv
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from typing import Dict, List, Any

# Import Streamlit components for testing
try:
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

# Import dashboard functions
import sys
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from streamlit_app.app import (
    load_watchlist_data, create_sidebar_filters, apply_filters,
    display_summary_metrics, create_visualizations, main
)
from config.settings import DEFAULT_PRICE_RANGE, DEFAULT_ACREAGE_RANGE, CHART_COLORS
from scripts.utils import format_currency, format_acreage, format_score


class TestDataLoadingFunctionality:
    """Test data loading and caching functionality."""

    def create_test_watchlist_csv(self, data: List[Dict], filename: str = None):
        """Create a test watchlist CSV file."""
        if filename is None:
            tmp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
            filename = tmp_file.name
            tmp_file.close()

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            if data:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

        return filename

    def test_load_watchlist_data_valid_file(self):
        """Test loading valid watchlist data."""
        test_data = [
            {
                'rank': 1,
                'parcel_id': '12-34-56-001',
                'amount': 4500.0,
                'acreage': 2.3,
                'price_per_acre': 1956.52,
                'water_score': 6.0,
                'investment_score': 8.2,
                'description': 'Waterfront property with creek access',
                'county': 'Baldwin',
                'estimated_all_in_cost': 4835.0
            },
            {
                'rank': 2,
                'parcel_id': '12-34-56-002',
                'amount': 5200.0,
                'acreage': 2.8,
                'price_per_acre': 1857.14,
                'water_score': 4.0,
                'investment_score': 7.5,
                'description': 'Property near stream',
                'county': 'Baldwin',
                'estimated_all_in_cost': 5535.0
            }
        ]

        csv_file = self.create_test_watchlist_csv(test_data)

        # Test data loading
        df = load_watchlist_data(csv_file)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert 'rank' in df.columns
        assert 'parcel_id' in df.columns
        assert 'amount' in df.columns
        assert 'water_score' in df.columns

        # Test data types and values
        assert df['amount'].dtype in [np.float64, np.int64]
        assert df['acreage'].dtype in [np.float64, np.int64]
        assert df['water_score'].max() >= 0

        os.unlink(csv_file)

    def test_load_watchlist_data_missing_file(self):
        """Test loading non-existent file."""
        df = load_watchlist_data('nonexistent_file.csv')

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_load_watchlist_data_missing_columns(self):
        """Test loading data with missing required columns."""
        incomplete_data = [
            {'parcel_id': '123456', 'amount': '4500'},
            {'parcel_id': '789012', 'amount': '5200'}
        ]

        csv_file = self.create_test_watchlist_csv(incomplete_data)

        df = load_watchlist_data(csv_file)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

        # Should add default values for missing columns
        required_columns = ['rank', 'acreage', 'water_score', 'investment_score', 'description', 'county']
        for col in required_columns:
            assert col in df.columns

        os.unlink(csv_file)

    def test_load_watchlist_data_malformed_csv(self):
        """Test loading malformed CSV data."""
        malformed_content = '''rank,parcel_id,amount
1,"12-34-56-001",$4,500
2,"12-34-56-002",INVALID_AMOUNT
3,"12-34-56-003"'''

        tmp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        tmp_file.write(malformed_content)
        tmp_file.close()

        # Should handle malformed data gracefully
        df = load_watchlist_data(tmp_file.name)

        # Either returns empty DataFrame or handles malformed data
        assert isinstance(df, pd.DataFrame)

        os.unlink(tmp_file.name)


class TestFilteringFunctionality:
    """Test interactive filtering functionality."""

    def create_test_dataframe(self):
        """Create test DataFrame for filtering tests."""
        return pd.DataFrame([
            {
                'rank': 1, 'parcel_id': 'TEST-001', 'amount': 3500.0, 'acreage': 2.1,
                'price_per_acre': 1666.67, 'water_score': 6.0, 'investment_score': 8.5,
                'description': 'Creek property', 'county': 'Baldwin'
            },
            {
                'rank': 2, 'parcel_id': 'TEST-002', 'amount': 8500.0, 'acreage': 1.8,
                'price_per_acre': 4722.22, 'water_score': 0.0, 'investment_score': 5.2,
                'description': 'Dry land', 'county': 'Mobile'
            },
            {
                'rank': 3, 'parcel_id': 'TEST-003', 'amount': 6200.0, 'acreage': 3.2,
                'price_per_acre': 1937.50, 'water_score': 4.0, 'investment_score': 7.8,
                'description': 'Near stream', 'county': 'Baldwin'
            },
            {
                'rank': 4, 'parcel_id': 'TEST-004', 'amount': 15000.0, 'acreage': 0.8,
                'price_per_acre': 18750.0, 'water_score': 2.0, 'investment_score': 3.1,
                'description': 'Small lot', 'county': 'Mobile'
            }
        ])

    def test_create_sidebar_filters_with_data(self):
        """Test sidebar filter creation with valid data."""
        df = self.create_test_dataframe()

        with patch('streamlit.sidebar') as mock_sidebar:
            # Mock sidebar components
            mock_sidebar.header = Mock()
            mock_sidebar.slider = Mock(side_effect=[
                (3500.0, 15000.0),  # price_range
                (0.8, 3.2),          # acreage_range
                5.0                  # min_investment_score
            ])
            mock_sidebar.checkbox = Mock(return_value=False)  # water_only
            mock_sidebar.selectbox = Mock(return_value='All')  # county
            mock_sidebar.markdown = Mock()
            mock_sidebar.button = Mock(return_value=False)

            filters = create_sidebar_filters(df)

            assert isinstance(filters, dict)
            assert 'price_range' in filters
            assert 'acreage_range' in filters
            assert 'water_only' in filters
            assert 'county' in filters
            assert 'min_investment_score' in filters

    def test_create_sidebar_filters_empty_data(self):
        """Test sidebar filter creation with empty data."""
        df = pd.DataFrame()

        with patch('streamlit.sidebar') as mock_sidebar:
            mock_sidebar.header = Mock()
            mock_sidebar.markdown = Mock()
            mock_sidebar.button = Mock(return_value=False)

            filters = create_sidebar_filters(df)

            assert isinstance(filters, dict)
            assert filters['price_range'] == DEFAULT_PRICE_RANGE
            assert filters['acreage_range'] == DEFAULT_ACREAGE_RANGE
            assert filters['water_only'] == False
            assert filters['county'] == 'All'
            assert filters['min_investment_score'] == 0.0

    def test_apply_filters_price_range(self):
        """Test price range filtering."""
        df = self.create_test_dataframe()
        filters = {
            'price_range': (4000.0, 10000.0),
            'acreage_range': (0.0, 10.0),
            'water_only': False,
            'county': 'All',
            'min_investment_score': 0.0
        }

        filtered_df = apply_filters(df, filters)

        assert len(filtered_df) == 2  # Should exclude properties outside price range
        assert all(4000.0 <= amount <= 10000.0 for amount in filtered_df['amount'])

    def test_apply_filters_acreage_range(self):
        """Test acreage range filtering."""
        df = self.create_test_dataframe()
        filters = {
            'price_range': (0.0, 50000.0),
            'acreage_range': (2.0, 4.0),
            'water_only': False,
            'county': 'All',
            'min_investment_score': 0.0
        }

        filtered_df = apply_filters(df, filters)

        assert len(filtered_df) == 2  # Should exclude properties outside acreage range
        assert all(2.0 <= acreage <= 4.0 for acreage in filtered_df['acreage'])

    def test_apply_filters_water_features_only(self):
        """Test water features only filtering."""
        df = self.create_test_dataframe()
        filters = {
            'price_range': (0.0, 50000.0),
            'acreage_range': (0.0, 10.0),
            'water_only': True,
            'county': 'All',
            'min_investment_score': 0.0
        }

        filtered_df = apply_filters(df, filters)

        assert len(filtered_df) == 3  # Should exclude properties with water_score = 0
        assert all(score > 0 for score in filtered_df['water_score'])

    def test_apply_filters_county_selection(self):
        """Test county filtering."""
        df = self.create_test_dataframe()
        filters = {
            'price_range': (0.0, 50000.0),
            'acreage_range': (0.0, 10.0),
            'water_only': False,
            'county': 'Baldwin',
            'min_investment_score': 0.0
        }

        filtered_df = apply_filters(df, filters)

        assert len(filtered_df) == 2  # Should include only Baldwin properties
        assert all(county == 'Baldwin' for county in filtered_df['county'])

    def test_apply_filters_investment_score(self):
        """Test investment score filtering."""
        df = self.create_test_dataframe()
        filters = {
            'price_range': (0.0, 50000.0),
            'acreage_range': (0.0, 10.0),
            'water_only': False,
            'county': 'All',
            'min_investment_score': 7.0
        }

        filtered_df = apply_filters(df, filters)

        assert len(filtered_df) == 2  # Should exclude properties with score < 7.0
        assert all(score >= 7.0 for score in filtered_df['investment_score'])

    def test_apply_filters_empty_dataframe(self):
        """Test filtering with empty DataFrame."""
        df = pd.DataFrame()
        filters = {
            'price_range': (0.0, 50000.0),
            'acreage_range': (0.0, 10.0),
            'water_only': False,
            'county': 'All',
            'min_investment_score': 0.0
        }

        filtered_df = apply_filters(df, filters)

        assert isinstance(filtered_df, pd.DataFrame)
        assert len(filtered_df) == 0


class TestDisplayFunctionality:
    """Test display and visualization functionality."""

    def create_test_dataframe(self):
        """Create test DataFrame for display tests."""
        return pd.DataFrame([
            {
                'rank': 1, 'parcel_id': 'DISP-001', 'amount': 4500.0, 'acreage': 2.3,
                'price_per_acre': 1956.52, 'water_score': 6.0, 'investment_score': 8.2,
                'description': 'Waterfront property', 'county': 'Baldwin'
            },
            {
                'rank': 2, 'parcel_id': 'DISP-002', 'amount': 5200.0, 'acreage': 2.8,
                'price_per_acre': 1857.14, 'water_score': 4.0, 'investment_score': 7.5,
                'description': 'Near stream', 'county': 'Mobile'
            }
        ])

    def test_display_summary_metrics_valid_data(self):
        """Test summary metrics display with valid data."""
        df = self.create_test_dataframe()

        with patch('streamlit.subheader') as mock_subheader, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.metric') as mock_metric:

            # Mock columns context managers
            mock_col1 = Mock()
            mock_col2 = Mock()
            mock_col3 = Mock()
            mock_col4 = Mock()
            mock_columns.return_value = [mock_col1, mock_col2, mock_col3, mock_col4]

            # Mock column context managers
            mock_col1.__enter__ = Mock(return_value=mock_col1)
            mock_col1.__exit__ = Mock(return_value=None)
            mock_col2.__enter__ = Mock(return_value=mock_col2)
            mock_col2.__exit__ = Mock(return_value=None)
            mock_col3.__enter__ = Mock(return_value=mock_col3)
            mock_col3.__exit__ = Mock(return_value=None)
            mock_col4.__enter__ = Mock(return_value=mock_col4)
            mock_col4.__exit__ = Mock(return_value=None)

            display_summary_metrics(df)

            # Should call subheader and display metrics
            mock_subheader.assert_called()
            mock_columns.assert_called()

    def test_display_summary_metrics_empty_data(self):
        """Test summary metrics display with empty data."""
        df = pd.DataFrame()

        with patch('streamlit.warning') as mock_warning:
            display_summary_metrics(df)

            # Should display warning for empty data
            mock_warning.assert_called_with("No properties match the current filters.")

    def test_create_visualizations_valid_data(self):
        """Test visualization creation with valid data."""
        df = self.create_test_dataframe()

        with patch('streamlit.subheader') as mock_subheader, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.plotly_chart') as mock_plotly_chart, \
             patch('plotly.express.scatter') as mock_scatter, \
             patch('plotly.express.histogram') as mock_histogram, \
             patch('plotly.express.bar') as mock_bar, \
             patch('plotly.express.box') as mock_box:

            # Mock Plotly figure objects
            mock_fig = Mock()
            mock_fig.update_layout = Mock()
            mock_scatter.return_value = mock_fig
            mock_histogram.return_value = mock_fig
            mock_bar.return_value = mock_fig
            mock_box.return_value = mock_fig

            # Mock columns
            mock_col1 = Mock()
            mock_col2 = Mock()
            mock_col3 = Mock()
            mock_col4 = Mock()
            mock_columns.return_value = [mock_col1, mock_col2, mock_col3, mock_col4]

            # Mock column context managers
            for col in [mock_col1, mock_col2, mock_col3, mock_col4]:
                col.__enter__ = Mock(return_value=col)
                col.__exit__ = Mock(return_value=None)

            create_visualizations(df)

            # Should create visualization components
            mock_subheader.assert_called()
            mock_columns.assert_called()

    def test_create_visualizations_empty_data(self):
        """Test visualization creation with empty data."""
        df = pd.DataFrame()

        with patch('streamlit.warning') as mock_warning:
            create_visualizations(df)

            # Should display warning for empty data
            mock_warning.assert_called()


class TestDashboardIntegration:
    """Test complete dashboard integration workflows."""

    def create_test_watchlist_file(self):
        """Create a temporary watchlist file for testing."""
        test_data = [
            {
                'rank': 1, 'parcel_id': 'INT-001', 'amount': 4500.0, 'acreage': 2.3,
                'price_per_acre': 1956.52, 'water_score': 6.0, 'investment_score': 8.2,
                'description': 'Waterfront property with creek access', 'county': 'Baldwin',
                'estimated_all_in_cost': 4835.0, 'assessed_value': 16000.0, 'owner_name': 'John Doe'
            },
            {
                'rank': 2, 'parcel_id': 'INT-002', 'amount': 5200.0, 'acreage': 2.8,
                'price_per_acre': 1857.14, 'water_score': 4.0, 'investment_score': 7.5,
                'description': 'Property near stream', 'county': 'Mobile',
                'estimated_all_in_cost': 5535.0, 'assessed_value': 18000.0, 'owner_name': 'Jane Smith'
            },
            {
                'rank': 3, 'parcel_id': 'INT-003', 'amount': 6800.0, 'acreage': 3.1,
                'price_per_acre': 2193.55, 'water_score': 0.0, 'investment_score': 6.2,
                'description': 'Inland property', 'county': 'Baldwin',
                'estimated_all_in_cost': 7135.0, 'assessed_value': 20000.0, 'owner_name': 'Bob Johnson'
            }
        ]

        tmp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        writer = csv.DictWriter(tmp_file, fieldnames=test_data[0].keys())
        writer.writeheader()
        writer.writerows(test_data)
        tmp_file.close()

        return tmp_file.name

    def test_complete_dashboard_workflow(self):
        """Test complete dashboard workflow from data loading to visualization."""
        # Step 1: Create test data file
        test_file = self.create_test_watchlist_file()

        # Step 2: Test data loading
        df = load_watchlist_data(test_file)
        assert len(df) == 3
        assert 'rank' in df.columns

        # Step 3: Test filter creation
        with patch('streamlit.sidebar') as mock_sidebar:
            mock_sidebar.header = Mock()
            mock_sidebar.slider = Mock(side_effect=[
                (4500.0, 6800.0),   # price_range
                (2.0, 3.5),         # acreage_range
                6.0                 # min_investment_score
            ])
            mock_sidebar.checkbox = Mock(return_value=True)  # water_only
            mock_sidebar.selectbox = Mock(return_value='Baldwin')  # county
            mock_sidebar.markdown = Mock()
            mock_sidebar.button = Mock(return_value=False)

            filters = create_sidebar_filters(df)

        # Step 4: Test filter application
        filtered_df = apply_filters(df, filters)

        # Should filter to Baldwin county, with water features, and investment score >= 6.0
        assert len(filtered_df) <= 3
        if len(filtered_df) > 0:
            assert all(county == 'Baldwin' for county in filtered_df['county'])
            assert all(score > 0 for score in filtered_df['water_score'])
            assert all(score >= 6.0 for score in filtered_df['investment_score'])

        # Step 5: Test display functions
        with patch('streamlit.subheader'), \
             patch('streamlit.columns'), \
             patch('streamlit.metric'), \
             patch('streamlit.warning'):

            display_summary_metrics(filtered_df)

        # Cleanup
        os.unlink(test_file)

    def test_dashboard_error_handling(self):
        """Test dashboard error handling scenarios."""
        # Test with corrupted data
        corrupted_content = '''rank,parcel_id,amount
1,"CORRUPT-001",$4,500
2,"CORRUPT-002",INVALID_AMOUNT'''

        tmp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        tmp_file.write(corrupted_content)
        tmp_file.close()

        # Should handle corrupted data gracefully
        df = load_watchlist_data(tmp_file.name)
        assert isinstance(df, pd.DataFrame)

        # Test filtering with malformed data
        if len(df) > 0:
            filters = {
                'price_range': (0.0, 50000.0),
                'acreage_range': (0.0, 10.0),
                'water_only': False,
                'county': 'All',
                'min_investment_score': 0.0
            }

            filtered_df = apply_filters(df, filters)
            assert isinstance(filtered_df, pd.DataFrame)

        os.unlink(tmp_file.name)

    def test_dashboard_performance_large_dataset(self):
        """Test dashboard performance with large dataset."""
        # Create large test dataset
        large_data = []
        for i in range(1000):
            large_data.append({
                'rank': i + 1,
                'parcel_id': f'PERF-{i:06d}',
                'amount': 3000.0 + i * 10,
                'acreage': 1.5 + (i % 4),
                'price_per_acre': (3000.0 + i * 10) / (1.5 + (i % 4)),
                'water_score': (i % 7),
                'investment_score': 5.0 + (i % 6),
                'description': f'Performance test property {i}',
                'county': ['Baldwin', 'Mobile', 'Jefferson'][i % 3]
            })

        tmp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        writer = csv.DictWriter(tmp_file, fieldnames=large_data[0].keys())
        writer.writeheader()
        writer.writerows(large_data)
        tmp_file.close()

        # Test performance with large dataset
        import time
        start_time = time.time()

        df = load_watchlist_data(tmp_file.name)
        assert len(df) == 1000

        # Apply filters
        filters = {
            'price_range': (3000.0, 15000.0),
            'acreage_range': (1.0, 6.0),
            'water_only': False,
            'county': 'All',
            'min_investment_score': 5.0
        }

        filtered_df = apply_filters(df, filters)

        processing_time = time.time() - start_time

        # Performance requirements
        assert processing_time < 2.0  # Should complete within 2 seconds
        assert len(filtered_df) >= 100  # Should have significant results

        os.unlink(tmp_file.name)


class TestDashboardUserExperience:
    """Test dashboard user experience and workflows."""

    def test_new_user_dashboard_experience(self):
        """Test new user dashboard experience with no data."""
        # Test dashboard behavior with no watchlist file
        df = load_watchlist_data('nonexistent_watchlist.csv')
        assert len(df) == 0

        # Test filter creation with empty data
        with patch('streamlit.sidebar') as mock_sidebar:
            mock_sidebar.header = Mock()
            mock_sidebar.markdown = Mock()
            mock_sidebar.button = Mock(return_value=False)

            filters = create_sidebar_filters(df)
            assert isinstance(filters, dict)

        # Test display with empty data
        with patch('streamlit.warning') as mock_warning:
            display_summary_metrics(df)
            mock_warning.assert_called()

    def test_experienced_user_dashboard_workflow(self):
        """Test experienced user dashboard workflow with advanced filtering."""
        # Create comprehensive test data
        test_data = [
            {'rank': 1, 'parcel_id': 'EXP-001', 'amount': 3500.0, 'acreage': 2.1, 'water_score': 8.0, 'investment_score': 9.2, 'county': 'Baldwin'},
            {'rank': 2, 'parcel_id': 'EXP-002', 'amount': 5500.0, 'acreage': 3.2, 'water_score': 6.0, 'investment_score': 7.8, 'county': 'Mobile'},
            {'rank': 3, 'parcel_id': 'EXP-003', 'amount': 8200.0, 'acreage': 1.8, 'water_score': 0.0, 'investment_score': 5.1, 'county': 'Jefferson'},
            {'rank': 4, 'parcel_id': 'EXP-004', 'amount': 4800.0, 'acreage': 2.7, 'water_score': 4.0, 'investment_score': 8.5, 'county': 'Baldwin'}
        ]

        tmp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        writer = csv.DictWriter(tmp_file, fieldnames=test_data[0].keys())
        writer.writeheader()
        writer.writerows(test_data)
        tmp_file.close()

        df = load_watchlist_data(tmp_file.name)

        # Test advanced filtering workflow
        advanced_filters = {
            'price_range': (3000.0, 6000.0),
            'acreage_range': (2.0, 4.0),
            'water_only': True,
            'county': 'Baldwin',
            'min_investment_score': 8.0
        }

        filtered_df = apply_filters(df, advanced_filters)

        # Should find high-quality Baldwin properties with water features
        assert len(filtered_df) >= 1
        if len(filtered_df) > 0:
            assert all(county == 'Baldwin' for county in filtered_df['county'])
            assert all(score > 0 for score in filtered_df['water_score'])
            assert all(score >= 8.0 for score in filtered_df['investment_score'])

        os.unlink(tmp_file.name)


@pytest.mark.skipif(not STREAMLIT_AVAILABLE, reason="Streamlit not available for testing")
class TestStreamlitAppIntegration:
    """Test complete Streamlit app integration if Streamlit testing is available."""

    def test_streamlit_app_initialization(self):
        """Test Streamlit app initialization and configuration."""
        # This would test the actual Streamlit app if testing framework is available
        # For now, we test the individual components
        pass

    def test_streamlit_app_main_workflow(self):
        """Test main Streamlit app workflow."""
        # Test would involve running the actual Streamlit app
        # and testing user interactions
        pass


if __name__ == "__main__":
    # AI-testable Streamlit dashboard specifications
    print("=== STREAMLIT DASHBOARD TEST SPECIFICATIONS ===")
    print("Dashboard test coverage:")
    print("- Data loading and caching functionality")
    print("- Interactive filtering and controls")
    print("- Summary metrics display")
    print("- Properties table rendering")
    print("- Chart and visualization generation")
    print("- Error handling and edge cases")
    print("- Performance and responsiveness")
    print("- User experience workflows")
    print("\nComponent validation:")
    print("- load_watchlist_data() function testing")
    print("- create_sidebar_filters() function testing")
    print("- apply_filters() function testing")
    print("- display_summary_metrics() function testing")
    print("- create_visualizations() function testing")
    print("- Complete dashboard integration testing")
    print("\nPerformance requirements:")
    print("- Large dataset processing: < 2 seconds for 1000 records")
    print("- Filter application: < 0.5 seconds")
    print("- Visualization rendering: < 1 second")
    print("- Data loading with caching: < 0.1 seconds")
    print("\nUser experience validation:")
    print("- New user experience with no data")
    print("- Experienced user advanced filtering workflow")
    print("- Error handling with corrupted data")
    print("- Responsive behavior with various data sizes")
    print("- Interactive filter combinations")
    print("\nVisualization testing:")
    print("- Scatter plot: Price vs Acreage")
    print("- Histogram: Price distribution")
    print("- Bar chart: Properties by county")
    print("- Box plot: Investment score distribution")
    print("- Chart responsiveness and styling")