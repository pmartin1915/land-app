"""
Unit tests for database optimization system.

This module tests the database optimization functionality to ensure
proper index creation, query optimization, and performance monitoring.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config.database_optimization import DatabaseOptimizer, QueryPerformance


class TestDatabaseOptimizer:
    """Test suite for DatabaseOptimizer."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = Mock()
        session.execute.return_value.fetchone.return_value = None
        session.execute.return_value.fetchall.return_value = []
        session.execute.return_value.scalar.return_value = 0
        session.bind.url = "postgresql://test"
        return session

    @pytest.fixture
    def optimizer(self, mock_db_session):
        """Create a DatabaseOptimizer instance for testing."""
        return DatabaseOptimizer(mock_db_session)

    def test_optimizer_initialization(self, optimizer):
        """Test optimizer initialization."""
        assert optimizer is not None
        assert optimizer.PROPERTY_INDEXES is not None
        assert len(optimizer.PROPERTY_INDEXES) > 0
        assert optimizer.FULLTEXT_INDEXES is not None
        assert optimizer.PARTIAL_INDEXES is not None

    def test_is_postgresql_detection(self, optimizer):
        """Test PostgreSQL database detection."""
        # Test PostgreSQL detection
        assert optimizer._is_postgresql() == True

        # Test with SQLite URL
        optimizer.db.bind.url = "sqlite:///test.db"
        assert optimizer._is_postgresql() == False

    def test_index_definitions_structure(self, optimizer):
        """Test that index definitions have correct structure."""
        # Test standard indexes
        for index_name, columns in optimizer.PROPERTY_INDEXES:
            assert isinstance(index_name, str)
            assert isinstance(columns, list)
            assert len(columns) > 0
            assert all(isinstance(col, str) for col in columns)

        # Test fulltext indexes
        for index_name, expression, index_type in optimizer.FULLTEXT_INDEXES:
            assert isinstance(index_name, str)
            assert isinstance(expression, str)
            assert isinstance(index_type, str)

        # Test partial indexes
        for index_name, columns, condition in optimizer.PARTIAL_INDEXES:
            assert isinstance(index_name, str)
            assert isinstance(columns, list)
            assert isinstance(condition, str)

    def test_index_exists_check(self, optimizer):
        """Test index existence checking."""
        # Mock index exists
        optimizer.db.execute.return_value.fetchone.return_value = Mock()
        assert optimizer._index_exists("test_index") == True

        # Mock index doesn't exist
        optimizer.db.execute.return_value.fetchone.return_value = None
        assert optimizer._index_exists("nonexistent_index") == False

    def test_create_standard_index_success(self, optimizer):
        """Test successful standard index creation."""
        # Mock index doesn't exist
        optimizer._index_exists = Mock(return_value=False)

        result = optimizer._create_standard_index("test_index", ["column1", "column2"])

        assert result == True
        optimizer.db.execute.assert_called()
        optimizer.db.commit.assert_called()

    def test_create_standard_index_already_exists(self, optimizer):
        """Test standard index creation when index already exists."""
        # Mock index already exists
        optimizer._index_exists = Mock(return_value=True)

        result = optimizer._create_standard_index("existing_index", ["column1"])

        assert result == True
        # Should not execute CREATE INDEX
        assert optimizer.db.execute.call_count == 0

    def test_create_standard_index_failure(self, optimizer):
        """Test standard index creation failure."""
        # Mock index doesn't exist
        optimizer._index_exists = Mock(return_value=False)
        optimizer.db.execute.side_effect = Exception("Database error")

        result = optimizer._create_standard_index("test_index", ["column1"])

        assert result == False
        optimizer.db.rollback.assert_called()

    def test_create_fulltext_index_postgresql(self, optimizer):
        """Test full-text index creation for PostgreSQL."""
        optimizer._index_exists = Mock(return_value=False)

        result = optimizer._create_fulltext_index("test_gin_index", "description", "gin")

        assert result == True
        optimizer.db.execute.assert_called()
        optimizer.db.commit.assert_called()

    def test_create_partial_index_success(self, optimizer):
        """Test partial index creation."""
        optimizer._index_exists = Mock(return_value=False)

        result = optimizer._create_partial_index("test_partial", ["column1"], "column1 > 0")

        assert result == True
        optimizer.db.execute.assert_called()
        optimizer.db.commit.assert_called()

    def test_create_all_indexes(self, optimizer):
        """Test creating all indexes."""
        # Mock all index creation methods
        optimizer._create_standard_index = Mock(return_value=True)
        optimizer._create_fulltext_index = Mock(return_value=True)
        optimizer._create_partial_index = Mock(return_value=True)

        results = optimizer.create_all_indexes()

        assert isinstance(results, dict)
        assert len(results) > 0

        # Check that creation methods were called
        assert optimizer._create_standard_index.call_count > 0
        assert optimizer._create_fulltext_index.call_count > 0
        assert optimizer._create_partial_index.call_count > 0

    def test_column_statistics_analysis(self, optimizer):
        """Test column statistics analysis."""
        # Mock database results
        mock_result = Mock()
        mock_result._mapping = {
            "total_count": 1000,
            "non_null_count": 950,
            "distinct_count": 67,
            "min_value": 1000,
            "max_value": 50000,
            "avg_value": 15000
        }
        optimizer.db.execute.return_value.fetchone.return_value = mock_result

        stats = optimizer._get_column_statistics()

        assert isinstance(stats, dict)
        # Should have stats for multiple columns
        assert len(stats) > 0

    def test_index_usage_stats_postgresql(self, optimizer):
        """Test index usage statistics for PostgreSQL."""
        # Mock PostgreSQL index usage results
        mock_results = [
            Mock(_mapping={"indexname": "idx_test", "idx_scan": 100, "idx_tup_read": 1000}),
            Mock(_mapping={"indexname": "idx_unused", "idx_scan": 0, "idx_tup_read": 0})
        ]
        optimizer.db.execute.return_value.fetchall.return_value = mock_results

        stats = optimizer._get_index_usage_stats()

        assert isinstance(stats, dict)
        assert "indexes" in stats
        assert stats["total_indexes"] == 2
        assert stats["unused_indexes"] == 1

    def test_index_usage_stats_non_postgresql(self, optimizer):
        """Test index usage statistics for non-PostgreSQL databases."""
        optimizer.db.bind.url = "sqlite:///test.db"

        stats = optimizer._get_index_usage_stats()

        assert isinstance(stats, dict)
        assert "message" in stats

    def test_performance_issue_identification(self, optimizer):
        """Test performance issue identification."""
        # Mock column index checks
        optimizer._column_has_index = Mock(return_value=False)
        optimizer._has_full_table_scans = Mock(return_value=True)
        optimizer.db.execute.return_value.scalar.return_value = 150000  # Large table

        issues = optimizer._identify_performance_issues()

        assert isinstance(issues, list)
        assert len(issues) > 0

        # Should identify missing indexes
        missing_index_issues = [i for i in issues if i["type"] == "missing_index"]
        assert len(missing_index_issues) > 0

        # Should identify large table
        large_table_issues = [i for i in issues if i["type"] == "large_table"]
        assert len(large_table_issues) > 0

    def test_optimization_recommendations(self, optimizer):
        """Test optimization recommendations generation."""
        # Mock analysis results
        optimizer.analyze_table_statistics = Mock(return_value={"row_count": 50000})
        optimizer._column_has_index = Mock(return_value=False)

        recommendations = optimizer.get_optimization_recommendations()

        assert isinstance(recommendations, list)
        # Should have recommendations for missing indexes
        assert len(recommendations) > 0

        # Check recommendation structure
        for rec in recommendations:
            assert "type" in rec
            assert "priority" in rec
            assert "action" in rec
            assert "benefit" in rec

    def test_query_performance_tracking(self, optimizer):
        """Test query performance tracking."""
        performance = QueryPerformance(
            query_type="list_properties",
            execution_time=0.15,
            rows_examined=1000,
            rows_returned=50,
            index_used=True,
            cost_estimate=5.2,
            timestamp=time.time()
        )

        optimizer.performance_log.append(performance)

        assert len(optimizer.performance_log) == 1
        assert optimizer.performance_log[0].query_type == "list_properties"
        assert optimizer.performance_log[0].execution_time == 0.15

    def test_optimized_query_builder(self, optimizer):
        """Test optimized query builder functionality."""
        # Mock query object
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []

        optimized_builder = optimizer.optimize_property_queries(mock_query)

        # Test chained operations
        result_builder = (optimized_builder
                         .filter_by_county("Baldwin")
                         .filter_by_price_range(10000, 50000)
                         .filter_by_acreage_range(1.0, 5.0))

        assert result_builder is not None

    def test_table_statistics_analysis(self, optimizer):
        """Test comprehensive table statistics analysis."""
        # Mock database responses
        size_result = Mock()
        size_result._mapping = {
            "table_size": "1024 MB",
            "data_size": "800 MB",
            "row_count": 50000
        }
        optimizer.db.execute.return_value.fetchone.return_value = size_result

        # Mock column statistics
        optimizer._get_column_statistics = Mock(return_value={"county": {"distinct_count": 67}})
        optimizer._get_index_usage_stats = Mock(return_value={"total_indexes": 10})
        optimizer._identify_performance_issues = Mock(return_value=[])

        stats = optimizer.analyze_table_statistics()

        assert isinstance(stats, dict)
        assert stats["row_count"] == 50000


class TestOptimizedQueryBuilder:
    """Test suite for OptimizedQueryBuilder functionality."""

    @pytest.fixture
    def mock_query(self):
        """Create a mock SQLAlchemy query."""
        query = Mock()
        query.filter.return_value = query
        query.all.return_value = []
        return query

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = Mock()
        session.bind.url = "postgresql://test"
        return session

    @pytest.fixture
    def optimizer(self, mock_db_session):
        """Create optimizer with mock session."""
        return DatabaseOptimizer(mock_db_session)

    def test_optimized_county_filtering(self, optimizer, mock_query, mock_db_session):
        """Test optimized county filtering."""
        builder = optimizer.optimize_property_queries(mock_query)

        result = builder.filter_by_county("Baldwin")

        assert result is not None
        assert "county" in result._filters_applied

    def test_optimized_price_range_filtering(self, optimizer, mock_query, mock_db_session):
        """Test optimized price range filtering."""
        builder = optimizer.optimize_property_queries(mock_query)

        # Test with both min and max
        result = builder.filter_by_price_range(10000, 50000)
        assert "amount" in result._filters_applied

        # Test with only min
        result = builder.filter_by_price_range(min_price=10000)
        assert "amount" in result._filters_applied

        # Test with only max
        result = builder.filter_by_price_range(max_price=50000)
        assert "amount" in result._filters_applied

    def test_optimized_acreage_filtering(self, optimizer, mock_query, mock_db_session):
        """Test optimized acreage filtering."""
        builder = optimizer.optimize_property_queries(mock_query)

        result = builder.filter_by_acreage_range(1.0, 5.0)

        assert result is not None
        assert "acreage" in result._filters_applied

    def test_optimized_text_search_postgresql(self, optimizer, mock_query, mock_db_session):
        """Test optimized text search for PostgreSQL."""
        builder = optimizer.optimize_property_queries(mock_query)

        result = builder.search_text_optimized("creek property")

        assert result is not None
        # Should use PostgreSQL full-text search

    def test_optimized_text_search_fallback(self, optimizer, mock_query, mock_db_session):
        """Test text search fallback for non-PostgreSQL databases."""
        # Mock SQLite
        mock_db_session.bind.url = "sqlite:///test.db"
        builder = optimizer.optimize_property_queries(mock_query)

        result = builder.search_text_optimized("creek property")

        assert result is not None
        # Should use LIKE fallback

    def test_performance_tracking_execution(self, optimizer, mock_query, mock_db_session):
        """Test query execution with performance tracking."""
        builder = optimizer.optimize_property_queries(mock_query)

        # Mock successful execution
        mock_query.all.return_value = [Mock(), Mock(), Mock()]

        result = builder.execute_with_performance_tracking()

        assert result is not None
        assert len(result) == 3

    def test_query_builder_chaining(self, optimizer, mock_query, mock_db_session):
        """Test that query builder methods can be chained."""
        builder = optimizer.optimize_property_queries(mock_query)

        # Test method chaining
        result = (builder
                 .filter_by_county("Baldwin")
                 .filter_by_price_range(10000, 50000)
                 .filter_by_acreage_range(1.0, 5.0)
                 .search_text_optimized("creek"))

        assert result is not None
        assert len(result._filters_applied) >= 3


class TestDatabaseOptimizationErrors:
    """Test error handling in database optimization."""

    def test_index_creation_error_handling(self):
        """Test error handling during index creation."""
        session = Mock()
        session.execute.side_effect = Exception("Database connection error")
        session.bind.url = "postgresql://test"

        optimizer = DatabaseOptimizer(session)

        result = optimizer._create_standard_index("test_index", ["column1"])

        assert result == False
        session.rollback.assert_called()

    def test_statistics_analysis_error_handling(self):
        """Test error handling during statistics analysis."""
        session = Mock()
        session.execute.side_effect = Exception("Query failed")
        session.bind.url = "postgresql://test"

        optimizer = DatabaseOptimizer(session)

        stats = optimizer._get_column_statistics()

        assert isinstance(stats, dict)
        # Should return empty dict on error

    def test_create_all_indexes_partial_failure(self):
        """Test create_all_indexes with some failures."""
        session = Mock()
        session.bind.url = "postgresql://test"

        optimizer = DatabaseOptimizer(session)

        # Mock some successes and some failures
        def mock_create_standard(name, columns):
            return "fail" not in name

        def mock_create_fulltext(name, expr, type_):
            return "fail" not in name

        def mock_create_partial(name, columns, condition):
            return "fail" not in name

        optimizer._create_standard_index = mock_create_standard
        optimizer._create_fulltext_index = mock_create_fulltext
        optimizer._create_partial_index = mock_create_partial

        # Temporarily modify index lists to include some "fail" names
        original_indexes = optimizer.PROPERTY_INDEXES
        optimizer.PROPERTY_INDEXES = [("good_index", ["col1"]), ("fail_index", ["col2"])]

        results = optimizer.create_all_indexes()

        # Should have mixed results
        assert True in results.values()
        assert False in results.values()

        # Restore original indexes
        optimizer.PROPERTY_INDEXES = original_indexes


if __name__ == "__main__":
    pytest.main([__file__])