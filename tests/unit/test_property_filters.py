"""
Unit tests for Core Property Filter Services.

Tests cover:
- PropertyFilterSpec: Filter specification creation and conversion
- PropertySortSpec: Sort specification and validation
- PaginationSpec: Pagination handling
- SQL and API parameter builders
"""

import pytest
from core.services.property_filters import (
    PropertyFilterSpec,
    PropertySortSpec,
    PaginationSpec,
    SortOrder,
    build_filter_params,
    build_sql_where_clause,
    validate_filter_values,
    ALLOWED_SORT_COLUMNS,
    SCORE_FILTER_COLUMNS,
)


# =============================================================================
# PROPERTY FILTER SPEC TESTS
# =============================================================================

class TestPropertyFilterSpec:
    """Test suite for PropertyFilterSpec."""

    # -------------------------------------------------------------------------
    # Basic Construction
    # -------------------------------------------------------------------------

    def test_default_construction(self):
        """Test default filter spec has no active filters."""
        spec = PropertyFilterSpec()
        assert spec.min_price is None
        assert spec.max_price is None
        assert spec.county is None
        assert spec.water_features is None

    def test_construction_with_values(self):
        """Test filter spec with explicit values."""
        spec = PropertyFilterSpec(
            min_price=1000,
            max_price=50000,
            county="Baldwin"
        )
        assert spec.min_price == 1000
        assert spec.max_price == 50000
        assert spec.county == "Baldwin"

    # -------------------------------------------------------------------------
    # has_any_filter Method
    # -------------------------------------------------------------------------

    def test_has_any_filter_empty(self):
        """Test has_any_filter returns False for default spec."""
        spec = PropertyFilterSpec()
        assert spec.has_any_filter() is False

    def test_has_any_filter_with_price(self):
        """Test has_any_filter detects price filters."""
        spec = PropertyFilterSpec(min_price=1000)
        assert spec.has_any_filter() is True

    def test_has_any_filter_with_county(self):
        """Test has_any_filter detects county filter."""
        spec = PropertyFilterSpec(county="Baldwin")
        assert spec.has_any_filter() is True

    def test_has_any_filter_ignores_all_county(self):
        """Test has_any_filter ignores 'All' county."""
        spec = PropertyFilterSpec(county="All")
        assert spec.has_any_filter() is False

    def test_has_any_filter_with_water_features(self):
        """Test has_any_filter detects water features filter."""
        spec = PropertyFilterSpec(water_features=True)
        assert spec.has_any_filter() is True

    def test_has_any_filter_with_search_query(self):
        """Test has_any_filter detects search query."""
        spec = PropertyFilterSpec(search_query="creek")
        assert spec.has_any_filter() is True

    # -------------------------------------------------------------------------
    # get_active_filters Method
    # -------------------------------------------------------------------------

    def test_get_active_filters_empty(self):
        """Test get_active_filters returns empty dict for default spec."""
        spec = PropertyFilterSpec()
        assert spec.get_active_filters() == {}

    def test_get_active_filters_excludes_none(self):
        """Test get_active_filters excludes None values."""
        spec = PropertyFilterSpec(min_price=1000, max_price=None)
        active = spec.get_active_filters()
        assert "min_price" in active
        assert "max_price" not in active

    def test_get_active_filters_excludes_all_county(self):
        """Test get_active_filters excludes 'All' county."""
        spec = PropertyFilterSpec(county="All")
        active = spec.get_active_filters()
        assert "county" not in active

    def test_get_active_filters_includes_non_all_county(self):
        """Test get_active_filters includes specific county."""
        spec = PropertyFilterSpec(county="Baldwin")
        active = spec.get_active_filters()
        assert active["county"] == "Baldwin"

    # -------------------------------------------------------------------------
    # from_ui_filters Factory
    # -------------------------------------------------------------------------

    def test_from_ui_filters_price_range(self):
        """Test creating spec from UI price range tuple."""
        filters = {"price_range": (500, 10000)}
        spec = PropertyFilterSpec.from_ui_filters(filters)
        assert spec.min_price == 500
        assert spec.max_price == 10000

    def test_from_ui_filters_price_range_zero_min(self):
        """Test zero minimum price is ignored."""
        filters = {"price_range": (0, 10000)}
        spec = PropertyFilterSpec.from_ui_filters(filters)
        assert spec.min_price is None
        assert spec.max_price == 10000

    def test_from_ui_filters_price_range_max_at_limit(self):
        """Test maximum at 1M is ignored."""
        filters = {"price_range": (500, 1000000)}
        spec = PropertyFilterSpec.from_ui_filters(filters)
        assert spec.min_price == 500
        assert spec.max_price is None

    def test_from_ui_filters_acreage_range(self):
        """Test creating spec from UI acreage range tuple."""
        filters = {"acreage_range": (1.0, 50.0)}
        spec = PropertyFilterSpec.from_ui_filters(filters)
        assert spec.min_acreage == 1.0
        assert spec.max_acreage == 50.0

    def test_from_ui_filters_county(self):
        """Test creating spec from UI county filter."""
        filters = {"county": "Mobile"}
        spec = PropertyFilterSpec.from_ui_filters(filters)
        assert spec.county == "Mobile"

    def test_from_ui_filters_county_all_ignored(self):
        """Test 'All' county is ignored."""
        filters = {"county": "All"}
        spec = PropertyFilterSpec.from_ui_filters(filters)
        assert spec.county is None

    def test_from_ui_filters_water_only(self):
        """Test water_only flag."""
        filters = {"water_only": True}
        spec = PropertyFilterSpec.from_ui_filters(filters)
        assert spec.water_features is True

    def test_from_ui_filters_score_filters(self):
        """Test score filters from UI."""
        filters = {
            "min_investment_score": 50,
            "min_county_market_score": 30,
        }
        spec = PropertyFilterSpec.from_ui_filters(filters)
        assert spec.min_investment_score == 50
        assert spec.min_county_market_score == 30

    def test_from_ui_filters_zero_score_ignored(self):
        """Test zero score filters are ignored."""
        filters = {"min_investment_score": 0}
        spec = PropertyFilterSpec.from_ui_filters(filters)
        assert spec.min_investment_score is None

    def test_from_ui_filters_search_query(self):
        """Test search query from UI."""
        filters = {"search_query": "waterfront"}
        spec = PropertyFilterSpec.from_ui_filters(filters)
        assert spec.search_query == "waterfront"


# =============================================================================
# PROPERTY SORT SPEC TESTS
# =============================================================================

class TestPropertySortSpec:
    """Test suite for PropertySortSpec."""

    def test_default_sort(self):
        """Test default sort is investment_score DESC."""
        spec = PropertySortSpec()
        assert spec.column == "investment_score"
        assert spec.order == SortOrder.DESC

    def test_custom_column(self):
        """Test custom sort column."""
        spec = PropertySortSpec(column="amount")
        assert spec.column == "amount"

    def test_invalid_column_defaults_to_investment_score(self):
        """Test invalid column defaults to investment_score."""
        spec = PropertySortSpec(column="invalid_column")
        assert spec.column == "investment_score"

    def test_ascending_order(self):
        """Test ascending sort order."""
        spec = PropertySortSpec(order=SortOrder.ASC)
        assert spec.is_ascending is True

    def test_descending_order(self):
        """Test descending sort order."""
        spec = PropertySortSpec(order=SortOrder.DESC)
        assert spec.is_ascending is False

    def test_order_from_string(self):
        """Test order can be set from string."""
        spec = PropertySortSpec(column="amount", order="asc")
        assert spec.order == SortOrder.ASC

    def test_from_ui_tuple_ascending(self):
        """Test creating from UI tuple with ascending."""
        spec = PropertySortSpec.from_ui_tuple(("amount", True))
        assert spec.column == "amount"
        assert spec.order == SortOrder.ASC

    def test_from_ui_tuple_descending(self):
        """Test creating from UI tuple with descending."""
        spec = PropertySortSpec.from_ui_tuple(("water_score", False))
        assert spec.column == "water_score"
        assert spec.order == SortOrder.DESC

    def test_from_api_params(self):
        """Test creating from API parameters."""
        spec = PropertySortSpec.from_api_params("price_per_acre", "asc")
        assert spec.column == "price_per_acre"
        assert spec.order == SortOrder.ASC


# =============================================================================
# PAGINATION SPEC TESTS
# =============================================================================

class TestPaginationSpec:
    """Test suite for PaginationSpec."""

    def test_default_values(self):
        """Test default pagination values."""
        spec = PaginationSpec()
        assert spec.page == 1
        assert spec.page_size == 100

    def test_custom_values(self):
        """Test custom pagination values."""
        spec = PaginationSpec(page=3, page_size=50)
        assert spec.page == 3
        assert spec.page_size == 50

    def test_negative_page_corrected(self):
        """Test negative page is corrected to 1."""
        spec = PaginationSpec(page=-1)
        assert spec.page == 1

    def test_zero_page_corrected(self):
        """Test zero page is corrected to 1."""
        spec = PaginationSpec(page=0)
        assert spec.page == 1

    def test_negative_page_size_corrected(self):
        """Test negative page size is corrected."""
        spec = PaginationSpec(page_size=-10)
        assert spec.page_size == 100

    def test_excessive_page_size_capped(self):
        """Test excessive page size is capped at MAX_PAGE_SIZE."""
        spec = PaginationSpec(page_size=5000)
        assert spec.page_size == 1000

    def test_offset_calculation(self):
        """Test offset calculation."""
        spec = PaginationSpec(page=3, page_size=50)
        assert spec.offset == 100  # (3-1) * 50

    def test_offset_first_page(self):
        """Test offset for first page is 0."""
        spec = PaginationSpec(page=1, page_size=100)
        assert spec.offset == 0

    def test_calculate_total_pages(self):
        """Test total pages calculation."""
        spec = PaginationSpec(page_size=10)
        assert spec.calculate_total_pages(95) == 10
        assert spec.calculate_total_pages(100) == 10
        assert spec.calculate_total_pages(101) == 11

    def test_calculate_total_pages_zero_count(self):
        """Test total pages for zero count."""
        spec = PaginationSpec(page_size=10)
        assert spec.calculate_total_pages(0) == 0


# =============================================================================
# BUILD FILTER PARAMS TESTS
# =============================================================================

class TestBuildFilterParams:
    """Test suite for build_filter_params function."""

    def test_empty_spec(self):
        """Test building params from empty spec."""
        spec = PropertyFilterSpec()
        params = build_filter_params(spec)
        assert params == {}

    def test_with_price_filters(self):
        """Test building params with price filters."""
        spec = PropertyFilterSpec(min_price=1000, max_price=50000)
        params = build_filter_params(spec)
        assert params["min_price"] == 1000
        assert params["max_price"] == 50000

    def test_with_county(self):
        """Test building params with county."""
        spec = PropertyFilterSpec(county="Baldwin")
        params = build_filter_params(spec)
        assert params["county"] == "Baldwin"

    def test_with_water_features(self):
        """Test building params with water features."""
        spec = PropertyFilterSpec(water_features=True)
        params = build_filter_params(spec)
        assert params["water_features"] is True

    def test_with_score_filters(self):
        """Test building params with score filters."""
        spec = PropertyFilterSpec(
            min_investment_score=50,
            min_county_market_score=30
        )
        params = build_filter_params(spec)
        assert params["min_investment_score"] == 50
        assert params["min_county_market_score"] == 30


# =============================================================================
# BUILD SQL WHERE CLAUSE TESTS
# =============================================================================

class TestBuildSQLWhereClause:
    """Test suite for build_sql_where_clause function."""

    def test_empty_spec(self):
        """Test building SQL from empty spec."""
        spec = PropertyFilterSpec()
        where, params = build_sql_where_clause(spec)
        assert where == "1=1"
        assert params == []

    def test_price_filters(self):
        """Test SQL with price filters."""
        spec = PropertyFilterSpec(min_price=1000, max_price=50000)
        where, params = build_sql_where_clause(spec)
        assert "amount >= ?" in where
        assert "amount <= ?" in where
        assert 1000 in params
        assert 50000 in params

    def test_county_filter(self):
        """Test SQL with county filter."""
        spec = PropertyFilterSpec(county="Baldwin")
        where, params = build_sql_where_clause(spec)
        assert "county = ?" in where
        assert "Baldwin" in params

    def test_county_all_ignored(self):
        """Test 'All' county is ignored in SQL."""
        spec = PropertyFilterSpec(county="All")
        where, params = build_sql_where_clause(spec)
        assert "county" not in where
        assert params == []

    def test_water_features_true(self):
        """Test SQL with water features = True."""
        spec = PropertyFilterSpec(water_features=True)
        where, params = build_sql_where_clause(spec)
        assert "water_score > 0" in where

    def test_water_features_false(self):
        """Test SQL with water features = False."""
        spec = PropertyFilterSpec(water_features=False)
        where, params = build_sql_where_clause(spec)
        assert "water_score = 0" in where

    def test_search_query(self):
        """Test SQL with search query."""
        spec = PropertyFilterSpec(search_query="creek")
        where, params = build_sql_where_clause(spec)
        assert "description LIKE ?" in where
        assert "owner_name LIKE ?" in where
        assert "parcel_id LIKE ?" in where
        assert "%creek%" in params

    def test_multiple_conditions_combined_with_and(self):
        """Test multiple conditions are combined with AND."""
        spec = PropertyFilterSpec(
            min_price=1000,
            county="Baldwin",
            water_features=True
        )
        where, params = build_sql_where_clause(spec)
        assert " AND " in where
        # Should have all three conditions
        assert where.count(" AND ") == 2


# =============================================================================
# VALIDATE FILTER VALUES TESTS
# =============================================================================

class TestValidateFilterValues:
    """Test suite for validate_filter_values function."""

    def test_valid_filters(self):
        """Test validation passes for valid filters."""
        filters = {
            "price_range": (1000, 50000),
            "acreage_range": (1.0, 100.0),
        }
        errors = validate_filter_values(filters)
        assert errors == []

    def test_negative_min_price(self):
        """Test validation fails for negative min price."""
        filters = {"price_range": (-100, 50000)}
        errors = validate_filter_values(filters)
        assert len(errors) == 1
        assert "negative" in errors[0].lower()

    def test_max_price_less_than_min(self):
        """Test validation fails when max < min price."""
        filters = {"price_range": (50000, 1000)}
        errors = validate_filter_values(filters)
        assert len(errors) == 1
        assert "less than" in errors[0].lower()

    def test_negative_min_acreage(self):
        """Test validation fails for negative min acreage."""
        filters = {"acreage_range": (-5.0, 100.0)}
        errors = validate_filter_values(filters)
        assert len(errors) == 1
        assert "negative" in errors[0].lower()

    def test_negative_investment_score(self):
        """Test validation fails for negative investment score."""
        filters = {"min_investment_score": -10}
        errors = validate_filter_values(filters)
        assert len(errors) == 1

    def test_investment_score_over_100(self):
        """Test validation fails for investment score over 100."""
        filters = {"min_investment_score": 150}
        errors = validate_filter_values(filters)
        assert len(errors) == 1

    def test_invalid_sort_column(self):
        """Test validation fails for invalid sort column."""
        filters = {"sort_by": "invalid_column"}
        errors = validate_filter_values(filters)
        assert len(errors) == 1
        assert "sort column" in errors[0].lower()

    def test_valid_sort_column_tuple(self):
        """Test validation passes for valid sort column tuple."""
        filters = {"sort_by": ("investment_score", False)}
        errors = validate_filter_values(filters)
        assert errors == []


# =============================================================================
# CONSTANTS TESTS
# =============================================================================

class TestConstants:
    """Test suite for module constants."""

    def test_allowed_sort_columns_is_frozenset(self):
        """Test ALLOWED_SORT_COLUMNS is immutable."""
        assert isinstance(ALLOWED_SORT_COLUMNS, frozenset)

    def test_allowed_sort_columns_contains_expected(self):
        """Test ALLOWED_SORT_COLUMNS has expected columns."""
        assert "investment_score" in ALLOWED_SORT_COLUMNS
        assert "amount" in ALLOWED_SORT_COLUMNS
        assert "water_score" in ALLOWED_SORT_COLUMNS

    def test_score_filter_columns_is_frozenset(self):
        """Test SCORE_FILTER_COLUMNS is immutable."""
        assert isinstance(SCORE_FILTER_COLUMNS, frozenset)

    def test_score_filter_columns_contains_expected(self):
        """Test SCORE_FILTER_COLUMNS has expected columns."""
        assert "investment_score" in SCORE_FILTER_COLUMNS
        assert "water_score" in SCORE_FILTER_COLUMNS
        assert "county_market_score" in SCORE_FILTER_COLUMNS
