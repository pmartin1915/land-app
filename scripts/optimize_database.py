"""
Database Optimization Script for Alabama Auction Watcher

This script applies comprehensive database optimizations including:
- Creating performance indexes
- Analyzing query patterns
- Implementing full-text search
- Setting up monitoring for continued optimization
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, Any
import time

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend_api.database.connection import SessionLocal
from config.database_optimization import DatabaseOptimizer
from sqlalchemy import text

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseOptimizationManager:
    """Manage the complete database optimization process."""

    def __init__(self, db_session):
        self.db = db_session
        self.optimizer = DatabaseOptimizer(db_session)
        self.optimization_results = {}

    def run_full_optimization(self, force: bool = False) -> Dict[str, Any]:
        """Run complete database optimization process."""
        logger.info("Starting comprehensive database optimization...")

        results = {
            "timestamp": time.time(),
            "status": "in_progress",
            "steps_completed": [],
            "errors": [],
            "performance_before": {},
            "performance_after": {},
            "recommendations": []
        }

        try:
            # Step 1: Analyze current performance
            logger.info("Step 1: Analyzing current database performance...")
            results["performance_before"] = self._analyze_current_performance()
            results["steps_completed"].append("performance_analysis")

            # Step 2: Create critical indexes
            logger.info("Step 2: Creating performance indexes...")
            index_results = self._create_performance_indexes(force)
            results["index_creation"] = index_results
            results["steps_completed"].append("index_creation")

            # Step 3: Optimize existing queries
            logger.info("Step 3: Optimizing existing queries...")
            query_optimization_results = self._optimize_queries()
            results["query_optimization"] = query_optimization_results
            results["steps_completed"].append("query_optimization")

            # Step 4: Set up full-text search
            logger.info("Step 4: Setting up full-text search...")
            fulltext_results = self._setup_fulltext_search()
            results["fulltext_search"] = fulltext_results
            results["steps_completed"].append("fulltext_search")

            # Step 5: Update table statistics
            logger.info("Step 5: Updating table statistics...")
            self._update_table_statistics()
            results["steps_completed"].append("statistics_update")

            # Step 6: Analyze performance after optimization
            logger.info("Step 6: Analyzing performance after optimization...")
            results["performance_after"] = self._analyze_current_performance()
            results["steps_completed"].append("post_optimization_analysis")

            # Step 7: Generate recommendations
            logger.info("Step 7: Generating optimization recommendations...")
            results["recommendations"] = self.optimizer.get_optimization_recommendations()
            results["steps_completed"].append("recommendations")

            results["status"] = "completed"
            logger.info("Database optimization completed successfully!")

            # Print summary
            self._print_optimization_summary(results)

            return results

        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            results["status"] = "failed"
            results["errors"].append(str(e))
            return results

    def _analyze_current_performance(self) -> Dict[str, Any]:
        """Analyze current database performance."""
        try:
            # Get basic table statistics
            stats = self.optimizer.analyze_table_statistics()

            # Test query performance
            query_performance = self._benchmark_common_queries()
            stats["query_benchmarks"] = query_performance

            return stats

        except Exception as e:
            logger.error(f"Error analyzing performance: {e}")
            return {"error": str(e)}

    def _benchmark_common_queries(self) -> Dict[str, float]:
        """Benchmark common query patterns."""
        benchmarks = {}

        common_queries = [
            ("count_all", "SELECT COUNT(*) FROM properties WHERE is_deleted = FALSE"),
            ("filter_by_county", "SELECT COUNT(*) FROM properties WHERE is_deleted = FALSE AND county = 'Baldwin'"),
            ("filter_by_price", "SELECT COUNT(*) FROM properties WHERE is_deleted = FALSE AND amount BETWEEN 10000 AND 50000"),
            ("filter_by_investment", "SELECT COUNT(*) FROM properties WHERE is_deleted = FALSE AND investment_score > 50"),
            ("complex_filter", """
                SELECT COUNT(*) FROM properties
                WHERE is_deleted = FALSE
                AND county = 'Baldwin'
                AND amount BETWEEN 10000 AND 50000
                AND investment_score > 40
            """),
            ("text_search", """
                SELECT COUNT(*) FROM properties
                WHERE is_deleted = FALSE
                AND (description ILIKE '%creek%' OR owner_name ILIKE '%smith%')
            """)
        ]

        for query_name, sql in common_queries:
            try:
                start_time = time.time()
                result = self.db.execute(text(sql)).scalar()
                execution_time = time.time() - start_time

                benchmarks[query_name] = {
                    "execution_time": execution_time,
                    "result_count": result
                }

                logger.info(f"Query '{query_name}': {execution_time:.3f}s ({result} rows)")

            except Exception as e:
                logger.warning(f"Failed to benchmark query '{query_name}': {e}")
                benchmarks[query_name] = {"error": str(e)}

        return benchmarks

    def _create_performance_indexes(self, force: bool = False) -> Dict[str, Any]:
        """Create all performance indexes."""
        try:
            logger.info("Creating performance indexes...")

            # Check if indexes already exist
            if not force and self._indexes_already_exist():
                logger.info("Indexes already exist. Use --force to recreate.")
                return {"status": "skipped", "reason": "indexes_exist"}

            # Create indexes
            index_results = self.optimizer.create_all_indexes()

            successful_indexes = [name for name, success in index_results.items() if success]
            failed_indexes = [name for name, success in index_results.items() if not success]

            logger.info(f"Successfully created {len(successful_indexes)} indexes")
            if failed_indexes:
                logger.warning(f"Failed to create {len(failed_indexes)} indexes: {failed_indexes}")

            return {
                "status": "completed",
                "successful_indexes": successful_indexes,
                "failed_indexes": failed_indexes,
                "total_created": len(successful_indexes)
            }

        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            return {"status": "failed", "error": str(e)}

    def _indexes_already_exist(self) -> bool:
        """Check if critical indexes already exist."""
        try:
            critical_indexes = ["idx_properties_county", "idx_properties_amount", "idx_properties_investment_score"]

            for index_name in critical_indexes:
                if not self.optimizer._index_exists(index_name):
                    return False

            return True

        except Exception:
            return False

    def _optimize_queries(self) -> Dict[str, Any]:
        """Optimize existing query patterns."""
        try:
            optimizations = []

            # Update query hints for PostgreSQL
            if self.optimizer._is_postgresql():
                # Enable query planner to use indexes
                self.db.execute(text("SET enable_seqscan = false"))
                optimizations.append("Disabled sequential scans")

                # Increase work memory for better sorting
                self.db.execute(text("SET work_mem = '256MB'"))
                optimizations.append("Increased work memory")

                # Enable parallel query execution
                self.db.execute(text("SET max_parallel_workers_per_gather = 4"))
                optimizations.append("Enabled parallel queries")

            return {
                "status": "completed",
                "optimizations_applied": optimizations
            }

        except Exception as e:
            logger.error(f"Error optimizing queries: {e}")
            return {"status": "failed", "error": str(e)}

    def _setup_fulltext_search(self) -> Dict[str, Any]:
        """Set up full-text search capabilities."""
        try:
            if not self.optimizer._is_postgresql():
                return {
                    "status": "skipped",
                    "reason": "Full-text search optimization only available for PostgreSQL"
                }

            # Create text search configuration
            self.db.execute(text("""
                CREATE TEXT SEARCH CONFIGURATION IF NOT EXISTS english_property (COPY = english);
            """))

            # Create full-text search function
            self.db.execute(text("""
                CREATE OR REPLACE FUNCTION search_properties(search_term text)
                RETURNS TABLE(
                    id text,
                    parcel_id text,
                    amount float,
                    description text,
                    rank float
                ) AS $$
                BEGIN
                    RETURN QUERY
                    SELECT
                        p.id,
                        p.parcel_id,
                        p.amount,
                        p.description,
                        ts_rank_cd(
                            to_tsvector('english', p.description || ' ' || COALESCE(p.owner_name, '') || ' ' || p.parcel_id),
                            plainto_tsquery('english', search_term)
                        ) as rank
                    FROM properties p
                    WHERE p.is_deleted = FALSE
                    AND to_tsvector('english', p.description || ' ' || COALESCE(p.owner_name, '') || ' ' || p.parcel_id)
                        @@ plainto_tsquery('english', search_term)
                    ORDER BY rank DESC;
                END;
                $$ LANGUAGE plpgsql;
            """))

            self.db.commit()

            return {
                "status": "completed",
                "features_created": ["text_search_config", "search_function"]
            }

        except Exception as e:
            logger.error(f"Error setting up full-text search: {e}")
            self.db.rollback()
            return {"status": "failed", "error": str(e)}

    def _update_table_statistics(self):
        """Update table statistics for query planner."""
        try:
            if self.optimizer._is_postgresql():
                # Analyze table to update statistics
                self.db.execute(text("ANALYZE properties"))
                logger.info("Updated PostgreSQL table statistics")
            else:
                # SQLite analyze
                self.db.execute(text("ANALYZE properties"))
                logger.info("Updated SQLite table statistics")

            self.db.commit()

        except Exception as e:
            logger.warning(f"Failed to update table statistics: {e}")

    def _print_optimization_summary(self, results: Dict[str, Any]):
        """Print a summary of optimization results."""
        print("\n" + "="*60)
        print("DATABASE OPTIMIZATION SUMMARY")
        print("="*60)

        print(f"Status: {results['status'].upper()}")
        print(f"Steps completed: {len(results['steps_completed'])}")

        if results.get('index_creation'):
            index_info = results['index_creation']
            if index_info.get('successful_indexes'):
                print(f"Indexes created: {index_info['total_created']}")

        # Performance comparison
        before = results.get('performance_before', {}).get('query_benchmarks', {})
        after = results.get('performance_after', {}).get('query_benchmarks', {})

        if before and after:
            print("\nPerformance Improvements:")
            for query_name in before.keys():
                if query_name in after and 'execution_time' in before[query_name] and 'execution_time' in after[query_name]:
                    before_time = before[query_name]['execution_time']
                    after_time = after[query_name]['execution_time']
                    improvement = ((before_time - after_time) / before_time * 100) if before_time > 0 else 0
                    print(f"  {query_name}: {before_time:.3f}s → {after_time:.3f}s ({improvement:+.1f}%)")

        # Recommendations
        if results.get('recommendations'):
            print(f"\nOptimization Recommendations: {len(results['recommendations'])}")
            for rec in results['recommendations'][:3]:  # Show top 3
                print(f"  - {rec.get('action', 'N/A')} (Priority: {rec.get('priority', 'medium')})")

        print("="*60)


def main():
    """Main script execution."""
    parser = argparse.ArgumentParser(description="Optimize Alabama Auction Watcher database")
    parser.add_argument("--force", action="store_true", help="Force recreate existing indexes")
    parser.add_argument("--dry-run", action="store_true", help="Analyze only, don't make changes")
    parser.add_argument("--benchmark-only", action="store_true", help="Run performance benchmarks only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create database session
    db = SessionLocal()

    try:
        optimizer_manager = DatabaseOptimizationManager(db)

        if args.benchmark_only:
            # Run benchmarks only
            logger.info("Running performance benchmarks...")
            performance = optimizer_manager._analyze_current_performance()
            print("\nCurrent Performance:")
            for query_name, metrics in performance.get('query_benchmarks', {}).items():
                if 'execution_time' in metrics:
                    print(f"  {query_name}: {metrics['execution_time']:.3f}s")

        elif args.dry_run:
            # Analyze only
            logger.info("Running dry-run analysis...")
            performance = optimizer_manager._analyze_current_performance()
            recommendations = optimizer_manager.optimizer.get_optimization_recommendations()

            print("\nRecommendations:")
            for rec in recommendations:
                print(f"  - {rec.get('action', 'N/A')} (Priority: {rec.get('priority', 'medium')})")

        else:
            # Run full optimization
            results = optimizer_manager.run_full_optimization(force=args.force)

            if results["status"] == "failed":
                sys.exit(1)

    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()