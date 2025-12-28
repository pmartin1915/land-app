"""
Unit tests for refactored async_loader.py using core services.

Tests verify:
1. _build_api_params() correctly uses PropertyFilterSpec and build_filter_params()
2. _load_from_database_direct() correctly uses build_sql_where_clause()
3. _process_properties_data() value object integration works correctly
4. Backward compatibility with existing callers
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
import sqlite3
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from streamlit_app.core.async_loader import (
    AsyncDataLoader,
    StreamlitDataLoader,
)
from core.services.property_filters import (
    PropertyFilterSpec,
    PropertySortSpec,
    ALLOWED_SORT_COLUMNS,
)


# =============================================================================
# _BUILD_API_PARAMS TESTS
# =============================================================================

class TestBuildApiParamsRefactored:
    """Test suite for refactored _build_api_params method."""

    @pytest.fixture
    def loader(self):
        """Create AsyncDataLoader instance for testing."""
        with patch('streamlit_app.core.async_loader.get_cache_manager'):
            with patch('streamlit_app.core.async_loader.get_performance_monitor'):
                return AsyncDataLoader()

    def test_empty_filters_returns_defaults(self, loader):
        """Test API params with empty filters."""
        params = loader._build_api_params({})
        assert params['page_size'] == 10000
        assert params['sort_by'] == 'investment_score DESC'

    def test_price_range_filters(self, loader):
        """Test price range conversion."""
        filters = {'price_range': (1000, 50000)}
        params = loader._build_api_params(filters)
        assert params['min_price'] == 1000
        assert params['max_price'] == 50000

    def test_price_range_at_min_boundary_excluded(self, loader):
        """Test that min_price=0 is excluded."""
        filters = {'price_range': (0, 50000)}
        params = loader._build_api_params(filters)
        assert 'min_price' not in params
        assert params['max_price'] == 50000

    def test_price_range_at_max_boundary_excluded(self, loader):
        """Test that max_price=1000000 is excluded."""
        filters = {'price_range': (1000, 1000000)}
        params = loader._build_api_params(filters)
        assert params['min_price'] == 1000
        assert 'max_price' not in params

    def test_acreage_range_filters(self, loader):
        """Test acreage range conversion."""
        filters = {'acreage_range': (5, 100)}
        params = loader._build_api_params(filters)
        assert params['min_acreage'] == 5
        assert params['max_acreage'] == 100

    def test_acreage_range_at_min_boundary_excluded(self, loader):
        """Test that min_acreage=0 is excluded."""
        filters = {'acreage_range': (0, 100)}
        params = loader._build_api_params(filters)
        assert 'min_acreage' not in params
        assert params['max_acreage'] == 100

    def test_acreage_range_at_max_boundary_excluded(self, loader):
        """Test that max_acreage=1000 is excluded."""
        filters = {'acreage_range': (5, 1000)}
        params = loader._build_api_params(filters)
        assert params['min_acreage'] == 5
        assert 'max_acreage' not in params

    def test_water_only_filter(self, loader):
        """Test water_only flag conversion."""
        filters = {'water_only': True}
        params = loader._build_api_params(filters)
        assert params['water_features'] is True

    def test_water_only_false_excluded(self, loader):
        """Test water_only=False is excluded."""
        filters = {'water_only': False}
        params = loader._build_api_params(filters)
        assert 'water_features' not in params

    def test_county_filter(self, loader):
        """Test county filter."""
        filters = {'county': 'Baldwin'}
        params = loader._build_api_params(filters)
        assert params['county'] == 'Baldwin'

    def test_county_all_excluded(self, loader):
        """Test 'All' county is not included in params."""
        filters = {'county': 'All'}
        params = loader._build_api_params(filters)
        assert 'county' not in params

    def test_score_filters(self, loader):
        """Test intelligence score filters."""
        filters = {
            'min_investment_score': 50,
            'min_county_market_score': 30,
            'min_geographic_score': 40,
        }
        params = loader._build_api_params(filters)
        assert params['min_investment_score'] == 50
        assert params['min_county_market_score'] == 30
        assert params['min_geographic_score'] == 40

    def test_score_filter_zero_excluded(self, loader):
        """Test that score filter of 0 is excluded."""
        filters = {'min_investment_score': 0}
        params = loader._build_api_params(filters)
        assert 'min_investment_score' not in params

    def test_sort_by_tuple_ascending(self, loader):
        """Test sort_by tuple with ascending."""
        filters = {'sort_by': ('amount', True)}
        params = loader._build_api_params(filters)
        assert params['sort_by'] == 'amount ASC'

    def test_sort_by_tuple_descending(self, loader):
        """Test sort_by tuple with descending."""
        filters = {'sort_by': ('acreage', False)}
        params = loader._build_api_params(filters)
        assert params['sort_by'] == 'acreage DESC'

    def test_sort_by_invalid_column_uses_default(self, loader):
        """Test invalid sort column falls back to investment_score."""
        filters = {'sort_by': ('invalid_column', True)}
        params = loader._build_api_params(filters)
        assert params['sort_by'] == 'investment_score ASC'

    def test_sort_by_missing_uses_default(self, loader):
        """Test missing sort_by uses default."""
        params = loader._build_api_params({})
        assert params['sort_by'] == 'investment_score DESC'

    def test_combined_filters(self, loader):
        """Test multiple filters combined."""
        filters = {
            'price_range': (5000, 50000),
            'acreage_range': (10, 100),
            'county': 'Mobile',
            'water_only': True,
            'min_investment_score': 60,
            'sort_by': ('water_score', False),
        }
        params = loader._build_api_params(filters)
        assert params['min_price'] == 5000
        assert params['max_price'] == 50000
        assert params['min_acreage'] == 10
        assert params['max_acreage'] == 100
        assert params['county'] == 'Mobile'
        assert params['water_features'] is True
        assert params['min_investment_score'] == 60
        assert params['sort_by'] == 'water_score DESC'
        assert params['page_size'] == 10000


# =============================================================================
# _LOAD_FROM_DATABASE_DIRECT TESTS
# =============================================================================

class TestLoadFromDatabaseDirectRefactored:
    """Test suite for refactored _load_from_database_direct method."""

    @pytest.fixture
    def loader(self):
        """Create StreamlitDataLoader for testing."""
        with patch('streamlit_app.core.async_loader.get_cache_manager'):
            with patch('streamlit_app.core.async_loader.get_performance_monitor'):
                with patch('streamlit_app.core.async_loader.st'):
                    return StreamlitDataLoader()

    @pytest.fixture
    def mock_db(self, mocker):
        """Mock database connection and query execution."""
        mock_conn = MagicMock()
        mocker.patch('sqlite3.connect', return_value=mock_conn)
        mocker.patch.object(Path, 'exists', return_value=True)
        return mock_conn

    def test_database_not_found_raises_error(self, loader, mocker):
        """Test FileNotFoundError when database doesn't exist."""
        mocker.patch.object(Path, 'exists', return_value=False)
        with pytest.raises(FileNotFoundError):
            loader._load_from_database_direct({})

    def test_empty_filters_generates_valid_sql(self, loader, mock_db, mocker):
        """Test empty filters generate valid SQL with 1=1 WHERE clause."""
        mock_read_sql = mocker.patch('pandas.read_sql_query', return_value=pd.DataFrame())

        loader._load_from_database_direct({})

        call_args = mock_read_sql.call_args
        query = call_args[0][0]
        assert 'SELECT * FROM properties' in query
        assert 'WHERE 1=1' in query
        assert 'ORDER BY investment_score DESC' in query

    def test_price_filters_in_sql(self, loader, mock_db, mocker):
        """Test price filters appear in SQL."""
        mock_read_sql = mocker.patch('pandas.read_sql_query', return_value=pd.DataFrame())

        loader._load_from_database_direct({'price_range': (1000, 50000)})

        call_args = mock_read_sql.call_args
        query = call_args[0][0]
        params = call_args[1].get('params', [])

        assert 'amount >= ?' in query
        assert 'amount <= ?' in query
        assert 1000 in params
        assert 50000 in params

    def test_county_filter_in_sql(self, loader, mock_db, mocker):
        """Test county filter appears in SQL."""
        mock_read_sql = mocker.patch('pandas.read_sql_query', return_value=pd.DataFrame())

        loader._load_from_database_direct({'county': 'Baldwin'})

        call_args = mock_read_sql.call_args
        query = call_args[0][0]
        params = call_args[1].get('params', [])

        assert 'county = ?' in query
        assert 'Baldwin' in params

    def test_water_only_filter_in_sql(self, loader, mock_db, mocker):
        """Test water_only filter appears in SQL."""
        mock_read_sql = mocker.patch('pandas.read_sql_query', return_value=pd.DataFrame())

        loader._load_from_database_direct({'water_only': True})

        call_args = mock_read_sql.call_args
        query = call_args[0][0]

        assert 'water_score > 0' in query

    def test_sort_by_in_sql(self, loader, mock_db, mocker):
        """Test sort_by appears in SQL ORDER BY."""
        mock_read_sql = mocker.patch('pandas.read_sql_query', return_value=pd.DataFrame())

        loader._load_from_database_direct({'sort_by': ('amount', True)})

        call_args = mock_read_sql.call_args
        query = call_args[0][0]

        assert 'ORDER BY amount ASC' in query

    def test_connection_closed_on_success(self, loader, mock_db, mocker):
        """Test database connection is closed after successful query."""
        mocker.patch('pandas.read_sql_query', return_value=pd.DataFrame())

        loader._load_from_database_direct({})

        mock_db.close.assert_called_once()

    def test_connection_closed_on_error(self, loader, mock_db, mocker):
        """Test database connection is closed even on error."""
        mocker.patch('pandas.read_sql_query', side_effect=Exception("Query failed"))

        with pytest.raises(Exception):
            loader._load_from_database_direct({})

        mock_db.close.assert_called_once()


# =============================================================================
# _PROCESS_PROPERTIES_DATA TESTS
# =============================================================================

class TestProcessPropertiesDataRefactored:
    """Test suite for refactored _process_properties_data method."""

    @pytest.fixture
    def loader(self):
        """Create StreamlitDataLoader for testing."""
        with patch('streamlit_app.core.async_loader.get_cache_manager'):
            with patch('streamlit_app.core.async_loader.get_performance_monitor'):
                with patch('streamlit_app.core.async_loader.st'):
                    return StreamlitDataLoader()

    def test_empty_dataframe_returned_unchanged(self, loader):
        """Test empty DataFrame returns unchanged."""
        df = pd.DataFrame()
        result = loader._process_properties_data(df)
        assert result.empty

    def test_required_columns_added(self, loader):
        """Test required columns are added with defaults."""
        df = pd.DataFrame({'id': [1, 2, 3]})
        result = loader._process_properties_data(df)

        assert 'rank' in result.columns
        assert 'parcel_id' in result.columns
        assert 'amount' in result.columns
        assert 'acreage' in result.columns
        assert 'investment_score' in result.columns
        assert 'water_score' in result.columns

    def test_price_per_acre_calculated(self, loader):
        """Test price_per_acre is calculated when column has NaN values."""
        df = pd.DataFrame({
            'amount': [10000, 20000],
            'acreage': [5.0, 10.0],
            'price_per_acre': [None, None],  # NaN values trigger recalculation
        })
        result = loader._process_properties_data(df)

        assert result['price_per_acre'].iloc[0] == 2000.0
        assert result['price_per_acre'].iloc[1] == 2000.0

    def test_price_per_acre_zero_acreage(self, loader):
        """Test price_per_acre is 0 when acreage is 0."""
        df = pd.DataFrame({
            'amount': [10000],
            'acreage': [0.0],
        })
        result = loader._process_properties_data(df)

        assert result['price_per_acre'].iloc[0] == 0

    def test_backward_compatibility_without_value_objects(self, loader):
        """Test default behavior does not add value object columns."""
        df = pd.DataFrame({
            'investment_score': [75.0],
            'water_score': [8.5],
            'amount': [5000],
            'acreage': [2.0],
        })

        result = loader._process_properties_data(df)

        assert 'investment_rating' not in result.columns
        assert 'water_category' not in result.columns
        assert 'is_high_value' not in result.columns

    def test_value_objects_add_investment_rating(self, loader):
        """Test investment_rating column is added with value objects."""
        df = pd.DataFrame({
            'investment_score': [95.0, 75.0, 45.0, 25.0],
            'water_score': [0.0, 0.0, 0.0, 0.0],
            'amount': [5000, 5000, 5000, 5000],
            'acreage': [2.0, 2.0, 2.0, 2.0],
        })

        result = loader._process_properties_data(df, use_value_objects=True)

        assert 'investment_rating' in result.columns
        assert result['investment_rating'].iloc[0] == 'A+'
        assert result['investment_rating'].iloc[1] == 'B'
        assert result['investment_rating'].iloc[2] == 'F'
        assert result['investment_rating'].iloc[3] == 'F'

    def test_value_objects_add_water_category(self, loader):
        """Test water_category column is added with value objects."""
        df = pd.DataFrame({
            'investment_score': [50.0, 50.0, 50.0, 50.0],
            'water_score': [0.0, 5.0, 10.0, 15.0],
            'amount': [5000, 5000, 5000, 5000],
            'acreage': [2.0, 2.0, 2.0, 2.0],
        })

        result = loader._process_properties_data(df, use_value_objects=True)

        assert 'water_category' in result.columns
        assert result['water_category'].iloc[0] == 'none'
        assert result['water_category'].iloc[1] == 'moderate'
        assert result['water_category'].iloc[2] == 'excellent'
        assert result['water_category'].iloc[3] == 'exceptional'

    def test_value_objects_add_is_high_value(self, loader):
        """Test is_high_value column is added with value objects."""
        df = pd.DataFrame({
            'investment_score': [80.0, 70.0, 69.0, 50.0],
            'water_score': [0.0, 0.0, 0.0, 0.0],
            'amount': [5000, 5000, 5000, 5000],
            'acreage': [2.0, 2.0, 2.0, 2.0],
        })

        result = loader._process_properties_data(df, use_value_objects=True)

        assert 'is_high_value' in result.columns
        assert result['is_high_value'].iloc[0] == True
        assert result['is_high_value'].iloc[1] == True
        assert result['is_high_value'].iloc[2] == False
        assert result['is_high_value'].iloc[3] == False

    def test_value_objects_handle_nan_values(self, loader):
        """Test value objects handle NaN gracefully."""
        df = pd.DataFrame({
            'investment_score': [75.0, None],
            'water_score': [5.0, None],
            'amount': [5000, 5000],
            'acreage': [2.0, 2.0],
        })

        result = loader._process_properties_data(df, use_value_objects=True)

        assert result['investment_rating'].iloc[0] == 'B'
        assert result['investment_rating'].iloc[1] == 'N/A'
        assert result['water_category'].iloc[0] == 'moderate'
        assert result['water_category'].iloc[1] == 'none'
        assert result['is_high_value'].iloc[0] == True
        assert result['is_high_value'].iloc[1] == False


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestAsyncLoaderIntegration:
    """Integration tests for refactored async_loader."""

    @pytest.fixture
    def loader(self):
        """Create AsyncDataLoader for testing."""
        with patch('streamlit_app.core.async_loader.get_cache_manager'):
            with patch('streamlit_app.core.async_loader.get_performance_monitor'):
                return AsyncDataLoader()

    def test_filter_spec_integration(self, loader):
        """Test that _build_api_params uses PropertyFilterSpec correctly."""
        filters = {
            'price_range': (5000, 50000),
            'county': 'Baldwin',
            'water_only': True,
        }

        # Create spec directly for comparison
        spec = PropertyFilterSpec.from_ui_filters(filters)

        # Get params from loader
        params = loader._build_api_params(filters)

        # Verify params match what spec would produce
        assert params.get('min_price') == spec.min_price
        assert params.get('max_price') == spec.max_price
        assert params.get('county') == spec.county
        assert params.get('water_features') == spec.water_features

    def test_sort_spec_integration(self, loader):
        """Test that _build_api_params uses PropertySortSpec correctly."""
        filters = {'sort_by': ('amount', True)}

        # Create spec directly for comparison
        sort_spec = PropertySortSpec.from_ui_tuple(filters['sort_by'])

        # Get params from loader
        params = loader._build_api_params(filters)

        # Verify sort matches
        expected_sort = f"{sort_spec.column} {sort_spec.order.value.upper()}"
        assert params['sort_by'] == expected_sort


# =============================================================================
# BACKWARD COMPATIBILITY TESTS
# =============================================================================

class TestBackwardCompatibility:
    """Tests ensuring backward compatibility with existing code."""

    @pytest.fixture
    def loader(self):
        """Create AsyncDataLoader for testing."""
        with patch('streamlit_app.core.async_loader.get_cache_manager'):
            with patch('streamlit_app.core.async_loader.get_performance_monitor'):
                return AsyncDataLoader()

    def test_app_py_filter_format_works(self, loader):
        """Test the exact filter format used by app.py works correctly."""
        # This is the exact format used by streamlit_app/app.py
        filters = {
            'price_range': (0.0, 1000000.0),
            'acreage_range': (0.0, 1000.0),
            'water_only': False,
            'county': 'All',
            'sort_by': ('investment_score', False),
            'min_investment_score': 0.0,
            'min_county_market_score': 0.0,
            'min_geographic_score': 0.0,
            'min_market_timing_score': 0.0,
            'min_total_description_score': 0.0,
            'min_road_access_score': 0.0,
        }

        params = loader._build_api_params(filters)

        # Should only have page_size and sort_by (all other filters at defaults)
        assert params['page_size'] == 10000
        assert params['sort_by'] == 'investment_score DESC'
        assert 'min_price' not in params
        assert 'max_price' not in params
        assert 'county' not in params
        assert 'water_features' not in params

    def test_active_filters_work(self, loader):
        """Test non-default filters are correctly applied."""
        filters = {
            'price_range': (5000.0, 50000.0),
            'acreage_range': (10.0, 100.0),
            'water_only': True,
            'county': 'Mobile',
            'sort_by': ('amount', True),
            'min_investment_score': 50.0,
        }

        params = loader._build_api_params(filters)

        assert params['min_price'] == 5000.0
        assert params['max_price'] == 50000.0
        assert params['min_acreage'] == 10.0
        assert params['max_acreage'] == 100.0
        assert params['water_features'] is True
        assert params['county'] == 'Mobile'
        assert params['sort_by'] == 'amount ASC'
        assert params['min_investment_score'] == 50.0
