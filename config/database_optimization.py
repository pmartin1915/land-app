"""
Database Query Optimization Strategy for Alabama Auction Watcher

This module provides comprehensive database optimization including indexing strategies,
query optimizations, and performance monitoring for optimal application performance.
"""

import logging
from typing import Dict, List, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from dataclasses import dataclass
from datetime import datetime
import time

logger = logging.getLogger(__name__)


@dataclass
class QueryPerformance:
    """Track query performance metrics."""
    query_type: str
    execution_time: float
    rows_examined: int
    rows_returned: int
    index_used: bool
    cost_estimate: float
    timestamp: datetime


class DatabaseOptimizer:
    """Comprehensive database optimization system."""

    # Critical indexes for property queries
    PROPERTY_INDEXES = [
        # Single column indexes for common filters
        ("idx_properties_county", ["county"]),
        ("idx_properties_amount", ["amount"]),
        ("idx_properties_acreage", ["acreage"]),
        ("idx_properties_investment_score", ["investment_score"]),
        ("idx_properties_water_score", ["water_score"]),
        ("idx_properties_year_sold", ["year_sold"]),
        ("idx_properties_is_deleted", ["is_deleted"]),
        ("idx_properties_created_at", ["created_at"]),
        ("idx_properties_updated_at", ["updated_at"]),

        # Composite indexes for common filter combinations
        ("idx_properties_county_amount", ["county", "amount"]),
        ("idx_properties_county_acreage", ["county", "acreage"]),
        ("idx_properties_county_investment", ["county", "investment_score"]),
        ("idx_properties_active_investment", ["is_deleted", "investment_score"]),
        ("idx_properties_active_county", ["is_deleted", "county"]),
        ("idx_properties_active_amount", ["is_deleted", "amount"]),
        ("idx_properties_water_investment", ["water_score", "investment_score"]),

        # Range query optimizations
        ("idx_properties_amount_acreage", ["amount", "acreage"]),
        ("idx_properties_price_per_acre", ["price_per_acre"]),

        # Enhanced intelligence score indexes
        ("idx_properties_county_market", ["county_market_score"]),
        ("idx_properties_geographic", ["geographic_score"]),
        ("idx_properties_market_timing", ["market_timing_score"]),
        ("idx_properties_description_score", ["total_description_score"]),
        ("idx_properties_road_access", ["road_access_score"]),

        # Sorting optimization indexes
        ("idx_properties_active_investment_desc", ["is_deleted", "investment_score DESC"]),
        ("idx_properties_active_amount_desc", ["is_deleted", "amount DESC"]),
        ("idx_properties_active_created_desc", ["is_deleted", "created_at DESC"]),
    ]

    # Full-text search indexes (PostgreSQL specific)
    FULLTEXT_INDEXES = [
        # GIN indexes for text search
        ("idx_properties_description_gin", "description", "gin"),
        ("idx_properties_owner_name_gin", "owner_name", "gin"),
        ("idx_properties_parcel_id_gin", "parcel_id", "gin"),

        # Combined text search index
        ("idx_properties_search_combined", "description || ' ' || COALESCE(owner_name, '') || ' ' || parcel_id", "gin"),
    ]

    # Partial indexes for specific scenarios
    PARTIAL_INDEXES = [
        # Active properties only (most common queries)
        ("idx_properties_active_only", ["investment_score"], "is_deleted = FALSE"),
        ("idx_properties_water_active", ["water_score"], "is_deleted = FALSE AND water_score > 0"),
        ("idx_properties_recent", ["created_at"], "created_at > NOW() - INTERVAL '30 days'"),
        ("idx_properties_high_value", ["amount", "acreage"], "amount > 10000 AND acreage > 1"),
    ]

    def __init__(self, db_session: Session):
        self.db = db_session
        self.performance_log: List[QueryPerformance] = []

    def create_all_indexes(self) -> Dict[str, bool]:
        """Create all recommended indexes."""
        results = {}

        try:
            # Create standard indexes
            for index_name, columns in self.PROPERTY_INDEXES:
                try:
                    success = self._create_standard_index(index_name, columns)
                    results[index_name] = success
                except Exception as e:
                    logger.error(f"Failed to create index {index_name}: {e}")
                    results[index_name] = False

            # Create full-text indexes (PostgreSQL)
            if self._is_postgresql():
                for index_name, expression, index_type in self.FULLTEXT_INDEXES:
                    try:
                        success = self._create_fulltext_index(index_name, expression, index_type)
                        results[index_name] = success
                    except Exception as e:
                        logger.error(f"Failed to create fulltext index {index_name}: {e}")
                        results[index_name] = False

            # Create partial indexes
            for index_name, columns, condition in self.PARTIAL_INDEXES:
                try:
                    success = self._create_partial_index(index_name, columns, condition)
                    results[index_name] = success
                except Exception as e:
                    logger.error(f"Failed to create partial index {index_name}: {e}")
                    results[index_name] = False

            return results

        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            return results

    def _create_standard_index(self, index_name: str, columns: List[str]) -> bool:
        """Create a standard B-tree index."""
        try:
            # Check if index already exists
            if self._index_exists(index_name):
                logger.info(f"Index {index_name} already exists")
                return True

            # Build CREATE INDEX statement
            columns_str = ", ".join(columns)
            sql = f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name} ON properties ({columns_str})"

            self.db.execute(text(sql))
            self.db.commit()

            logger.info(f"Created index: {index_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {e}")
            self.db.rollback()
            return False

    def _create_fulltext_index(self, index_name: str, expression: str, index_type: str) -> bool:
        """Create a full-text search index (PostgreSQL GIN)."""
        try:
            if self._index_exists(index_name):
                logger.info(f"Fulltext index {index_name} already exists")
                return True

            # Create GIN index for full-text search
            if index_type == "gin":
                sql = f"""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name}
                    ON properties USING gin(to_tsvector('english', {expression}))
                """
            else:
                sql = f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name} ON properties USING {index_type} ({expression})"

            self.db.execute(text(sql))
            self.db.commit()

            logger.info(f"Created fulltext index: {index_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create fulltext index {index_name}: {e}")
            self.db.rollback()
            return False

    def _create_partial_index(self, index_name: str, columns: List[str], condition: str) -> bool:
        """Create a partial index with WHERE condition."""
        try:
            if self._index_exists(index_name):
                logger.info(f"Partial index {index_name} already exists")
                return True

            columns_str = ", ".join(columns)
            sql = f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name}
                ON properties ({columns_str})
                WHERE {condition}
            """

            self.db.execute(text(sql))
            self.db.commit()

            logger.info(f"Created partial index: {index_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create partial index {index_name}: {e}")
            self.db.rollback()
            return False

    def _index_exists(self, index_name: str) -> bool:
        """Check if an index already exists."""
        try:
            if self._is_postgresql():
                sql = """
                    SELECT 1 FROM pg_indexes
                    WHERE indexname = :index_name
                """
            else:
                # SQLite
                sql = """
                    SELECT 1 FROM sqlite_master
                    WHERE type = 'index' AND name = :index_name
                """

            result = self.db.execute(text(sql), {"index_name": index_name}).fetchone()
            return result is not None

        except Exception:
            return False

    def _is_postgresql(self) -> bool:
        """Check if the database is PostgreSQL."""
        try:
            return "postgresql" in str(self.db.bind.url)
        except:
            return False

    def analyze_table_statistics(self) -> Dict[str, Any]:
        """Analyze table statistics for optimization insights."""
        try:
            stats = {}

            # Get table size and row count
            if self._is_postgresql():
                size_query = """
                    SELECT
                        pg_size_pretty(pg_total_relation_size('properties')) as table_size,
                        pg_size_pretty(pg_relation_size('properties')) as data_size,
                        (SELECT COUNT(*) FROM properties) as row_count
                """
            else:
                size_query = "SELECT COUNT(*) as row_count FROM properties"

            result = self.db.execute(text(size_query)).fetchone()
            stats.update(dict(result._mapping))

            # Get column statistics
            stats["column_stats"] = self._get_column_statistics()

            # Get index usage statistics
            stats["index_usage"] = self._get_index_usage_stats()

            # Get slow query analysis
            stats["performance_issues"] = self._identify_performance_issues()

            return stats

        except Exception as e:
            logger.error(f"Error analyzing table statistics: {e}")
            return {}

    def _get_column_statistics(self) -> Dict[str, Any]:
        """Get statistics for each column."""
        try:
            stats = {}

            # Common columns to analyze
            columns = ["county", "amount", "acreage", "investment_score", "water_score", "year_sold"]

            for column in columns:
                try:
                    # Get basic statistics
                    query = f"""
                        SELECT
                            COUNT(*) as total_count,
                            COUNT({column}) as non_null_count,
                            COUNT(DISTINCT {column}) as distinct_count,
                            MIN({column}) as min_value,
                            MAX({column}) as max_value,
                            AVG({column}) as avg_value
                        FROM properties
                        WHERE is_deleted = FALSE
                    """

                    if column in ["county", "year_sold"]:
                        # String columns - exclude numeric aggregations
                        query = f"""
                            SELECT
                                COUNT(*) as total_count,
                                COUNT({column}) as non_null_count,
                                COUNT(DISTINCT {column}) as distinct_count
                            FROM properties
                            WHERE is_deleted = FALSE
                        """

                    result = self.db.execute(text(query)).fetchone()
                    stats[column] = dict(result._mapping)

                except Exception as e:
                    logger.warning(f"Failed to get stats for column {column}: {e}")

            return stats

        except Exception as e:
            logger.error(f"Error getting column statistics: {e}")
            return {}

    def _get_index_usage_stats(self) -> Dict[str, Any]:
        """Get index usage statistics (PostgreSQL specific)."""
        try:
            if not self._is_postgresql():
                return {"message": "Index usage stats only available for PostgreSQL"}

            query = """
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    idx_tup_read,
                    idx_tup_fetch,
                    idx_scan
                FROM pg_stat_user_indexes
                WHERE tablename = 'properties'
                ORDER BY idx_scan DESC
            """

            results = self.db.execute(text(query)).fetchall()
            return {
                "indexes": [dict(row._mapping) for row in results],
                "total_indexes": len(results),
                "unused_indexes": len([r for r in results if r.idx_scan == 0])
            }

        except Exception as e:
            logger.error(f"Error getting index usage stats: {e}")
            return {}

    def _identify_performance_issues(self) -> List[Dict[str, Any]]:
        """Identify potential performance issues."""
        issues = []

        try:
            # Check for missing indexes on frequently filtered columns
            common_filters = ["county", "amount", "acreage", "investment_score"]

            for column in common_filters:
                if not self._column_has_index(column):
                    issues.append({
                        "type": "missing_index",
                        "column": column,
                        "severity": "high",
                        "recommendation": f"Create index on {column} column for better filter performance"
                    })

            # Check for full table scans
            if self._has_full_table_scans():
                issues.append({
                    "type": "full_table_scan",
                    "severity": "medium",
                    "recommendation": "Queries performing full table scans detected - review query patterns"
                })

            # Check table size vs performance
            row_count = self.db.execute(text("SELECT COUNT(*) FROM properties")).scalar()
            if row_count > 100000:
                issues.append({
                    "type": "large_table",
                    "row_count": row_count,
                    "severity": "medium",
                    "recommendation": "Large table detected - consider partitioning or archiving old data"
                })

            return issues

        except Exception as e:
            logger.error(f"Error identifying performance issues: {e}")
            return []

    def _column_has_index(self, column: str) -> bool:
        """Check if a column has an index."""
        try:
            if self._is_postgresql():
                query = """
                    SELECT 1 FROM pg_indexes
                    WHERE tablename = 'properties'
                    AND indexdef ILIKE %s
                """
                pattern = f"%{column}%"
            else:
                query = """
                    SELECT 1 FROM sqlite_master
                    WHERE type = 'index'
                    AND tbl_name = 'properties'
                    AND sql LIKE ?
                """
                pattern = f"%{column}%"

            result = self.db.execute(text(query), [pattern]).fetchone()
            return result is not None

        except Exception:
            return False

    def _has_full_table_scans(self) -> bool:
        """Check if queries are performing full table scans."""
        # This is a simplified check - in production, you'd want to analyze
        # actual query execution plans
        return False

    def optimize_property_queries(self, query_builder) -> Any:
        """Optimize property list queries for better performance."""

        class OptimizedQueryBuilder:
            """Wrapper to add query optimizations."""

            def __init__(self, original_query, db_session):
                self.query = original_query
                self.db = db_session
                self._filters_applied = []

            def filter_by_county(self, county: str):
                """Optimized county filtering."""
                if county:
                    self._filters_applied.append("county")
                    # Use index hint if PostgreSQL
                    if self._is_postgresql():
                        # PostgreSQL will automatically use the index
                        self.query = self.query.filter(text("county = :county")).params(county=county)
                    else:
                        self.query = self.query.filter_by(county=county)
                return self

            def filter_by_price_range(self, min_price: float = None, max_price: float = None):
                """Optimized price range filtering."""
                if min_price is not None or max_price is not None:
                    self._filters_applied.append("amount")

                    if min_price is not None and max_price is not None:
                        # Use BETWEEN for range queries
                        self.query = self.query.filter(text("amount BETWEEN :min_price AND :max_price")).params(
                            min_price=min_price, max_price=max_price
                        )
                    elif min_price is not None:
                        self.query = self.query.filter(text("amount >= :min_price")).params(min_price=min_price)
                    elif max_price is not None:
                        self.query = self.query.filter(text("amount <= :max_price")).params(max_price=max_price)
                return self

            def filter_by_acreage_range(self, min_acreage: float = None, max_acreage: float = None):
                """Optimized acreage range filtering."""
                if min_acreage is not None or max_acreage is not None:
                    self._filters_applied.append("acreage")

                    if min_acreage is not None and max_acreage is not None:
                        self.query = self.query.filter(text("acreage BETWEEN :min_acreage AND :max_acreage")).params(
                            min_acreage=min_acreage, max_acreage=max_acreage
                        )
                    elif min_acreage is not None:
                        self.query = self.query.filter(text("acreage >= :min_acreage")).params(min_acreage=min_acreage)
                    elif max_acreage is not None:
                        self.query = self.query.filter(text("acreage <= :max_acreage")).params(max_acreage=max_acreage)
                return self

            def search_text_optimized(self, search_term: str):
                """Optimized text search using full-text search if available."""
                if search_term:
                    if self._is_postgresql():
                        # Use PostgreSQL full-text search
                        self.query = self.query.filter(
                            text("""
                                to_tsvector('english', description || ' ' || COALESCE(owner_name, '') || ' ' || parcel_id)
                                @@ plainto_tsquery('english', :search_term)
                            """).params(search_term=search_term)
                        )
                    else:
                        # Fallback to LIKE for other databases
                        search_pattern = f"%{search_term}%"
                        self.query = self.query.filter(
                            text("""
                                (description LIKE :pattern OR
                                 owner_name LIKE :pattern OR
                                 parcel_id LIKE :pattern)
                            """).params(pattern=search_pattern)
                        )
                return self

            def _is_postgresql(self) -> bool:
                """Check if database is PostgreSQL."""
                try:
                    return "postgresql" in str(self.db.bind.url)
                except:
                    return False

            def execute_with_performance_tracking(self):
                """Execute query with performance tracking."""
                start_time = time.time()

                try:
                    result = self.query.all()
                    execution_time = time.time() - start_time

                    # Log performance metrics
                    logger.info(f"Query executed in {execution_time:.3f}s, filters: {self._filters_applied}")

                    return result

                except Exception as e:
                    execution_time = time.time() - start_time
                    logger.error(f"Query failed after {execution_time:.3f}s: {e}")
                    raise

        return OptimizedQueryBuilder(query_builder, self.db)

    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get optimization recommendations based on current state."""
        recommendations = []

        try:
            # Analyze current performance
            stats = self.analyze_table_statistics()

            # Recommend indexes based on table size
            row_count = stats.get("row_count", 0)

            if row_count > 10000:
                recommendations.append({
                    "type": "indexing",
                    "priority": "high",
                    "action": "Create composite indexes for common filter combinations",
                    "benefit": "Significantly faster query performance for large datasets"
                })

            if row_count > 100000:
                recommendations.append({
                    "type": "query_optimization",
                    "priority": "high",
                    "action": "Implement query result caching",
                    "benefit": "Reduce database load for repeated queries"
                })

            # Check for missing critical indexes
            critical_indexes = ["county", "amount", "investment_score"]
            for column in critical_indexes:
                if not self._column_has_index(column):
                    recommendations.append({
                        "type": "indexing",
                        "priority": "critical",
                        "action": f"Create index on {column} column",
                        "benefit": f"Essential for {column} filtering performance"
                    })

            return recommendations

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []


def create_database_optimizer(db_session: Session) -> DatabaseOptimizer:
    """Factory function to create database optimizer."""
    return DatabaseOptimizer(db_session)