#!/usr/bin/env python3
"""
Database Optimization Script for Alabama Auction Watcher

This script applies comprehensive database optimizations to prepare for
handling 50,000+ properties efficiently.
"""

import sys
import sqlite3
from pathlib import Path
import logging

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def optimize_sqlite_database(db_path: str = "alabama_auction_watcher.db"):
    """
    Apply SQLite-specific optimizations for better performance.
    """
    try:
        logger.info(f"Starting SQLite database optimization for {db_path}")

        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Apply SQLite optimizations
        optimizations = [
            # 1. Create indexes for common query patterns
            "CREATE INDEX IF NOT EXISTS idx_properties_county ON properties (county)",
            "CREATE INDEX IF NOT EXISTS idx_properties_amount ON properties (amount)",
            "CREATE INDEX IF NOT EXISTS idx_properties_acreage ON properties (acreage)",
            "CREATE INDEX IF NOT EXISTS idx_properties_investment_score ON properties (investment_score)",
            "CREATE INDEX IF NOT EXISTS idx_properties_water_score ON properties (water_score)",
            "CREATE INDEX IF NOT EXISTS idx_properties_year_sold ON properties (year_sold)",
            "CREATE INDEX IF NOT EXISTS idx_properties_parcel_id ON properties (parcel_id)",

            # 2. Composite indexes for common filter combinations
            "CREATE INDEX IF NOT EXISTS idx_properties_county_amount ON properties (county, amount)",
            "CREATE INDEX IF NOT EXISTS idx_properties_county_acreage ON properties (county, acreage)",
            "CREATE INDEX IF NOT EXISTS idx_properties_county_investment ON properties (county, investment_score)",
            "CREATE INDEX IF NOT EXISTS idx_properties_amount_acreage ON properties (amount, acreage)",
            "CREATE INDEX IF NOT EXISTS idx_properties_investment_water ON properties (investment_score, water_score)",

            # 3. Sorting optimization indexes
            "CREATE INDEX IF NOT EXISTS idx_properties_investment_desc ON properties (investment_score DESC)",
            "CREATE INDEX IF NOT EXISTS idx_properties_amount_desc ON properties (amount DESC)",

            # 4. Full-text search support (SQLite FTS)
            "CREATE VIRTUAL TABLE IF NOT EXISTS properties_fts USING fts5(description, owner_name, parcel_id, content=properties, content_rowid=id)",

            # 5. Update database statistics
            "ANALYZE",

            # 6. Vacuum to reclaim space and reorganize data
            "VACUUM",
        ]

        # Apply each optimization
        for i, sql in enumerate(optimizations, 1):
            try:
                logger.info(f"Applying optimization {i}/{len(optimizations)}: {sql[:50]}...")
                cursor.execute(sql)
                conn.commit()
                logger.info(f"✅ Optimization {i} completed successfully")
            except Exception as e:
                logger.warning(f"⚠️ Optimization {i} failed (may already exist): {e}")
                continue

        # Get final database statistics
        cursor.execute("SELECT COUNT(*) FROM properties")
        row_count = cursor.fetchone()[0]

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='properties'")
        indexes = cursor.fetchall()

        logger.info(f"Database optimization complete!")
        logger.info(f"📊 Total properties: {row_count:,}")
        logger.info(f"📇 Total indexes: {len(indexes)}")
        logger.info(f"💾 Database file: {db_path}")

        # Close connection
        conn.close()

        return True

    except Exception as e:
        logger.error(f"❌ Database optimization failed: {e}")
        return False

def verify_database_performance(db_path: str = "alabama_auction_watcher.db"):
    """
    Verify database performance and provide recommendations.
    """
    try:
        logger.info("Verifying database performance...")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check table statistics
        cursor.execute("SELECT COUNT(*) FROM properties")
        total_properties = cursor.fetchone()[0]

        # Check index usage
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='properties'")
        indexes = [row[0] for row in cursor.fetchall()]

        # Test query performance (simplified)
        import time

        start_time = time.time()
        cursor.execute("SELECT * FROM properties WHERE county = 'Jefferson' ORDER BY investment_score DESC LIMIT 100")
        results = cursor.fetchall()
        query_time = time.time() - start_time

        logger.info("🔍 Performance Analysis:")
        logger.info(f"   • Total Properties: {total_properties:,}")
        logger.info(f"   • Available Indexes: {len(indexes)}")
        logger.info(f"   • Sample Query Time: {query_time:.3f}s")
        logger.info(f"   • Query Result Count: {len(results)}")

        # Performance recommendations
        if total_properties > 50000:
            logger.info("📈 Recommendations for large dataset:")
            logger.info("   • Enable WAL mode for better concurrency")
            logger.info("   • Consider partitioning by county")
            logger.info("   • Implement query result caching")

        if query_time > 1.0:
            logger.warning("⚠️ Slow query detected - consider adding more specific indexes")
        else:
            logger.info("✅ Query performance looks good")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"❌ Performance verification failed: {e}")
        return False

def enable_wal_mode(db_path: str = "alabama_auction_watcher.db"):
    """
    Enable WAL (Write-Ahead Logging) mode for better performance.
    """
    try:
        logger.info("Enabling WAL mode for better concurrency...")

        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=memory")
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB

        result = conn.execute("PRAGMA journal_mode").fetchone()
        logger.info(f"✅ WAL mode enabled: {result[0]}")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"❌ Failed to enable WAL mode: {e}")
        return False

def main():
    """Main optimization routine."""
    print("Alabama Auction Watcher - Database Optimization")
    print("=" * 60)
    print("This will optimize the database for handling 50,000+ properties efficiently.")
    print()

    # Find database file
    db_candidates = [
        "alabama_auction_watcher.db",
        "streamlit_app/alabama_auction_watcher.db",
        "streamlit_app/components/alabama_auction_watcher.db"
    ]

    db_path = None
    for candidate in db_candidates:
        if Path(candidate).exists():
            db_path = candidate
            break

    if not db_path:
        logger.error("❌ Database file not found. Please run the scraping first.")
        return False

    logger.info(f"🎯 Found database: {db_path}")

    # Apply optimizations
    success = True

    # 1. Enable WAL mode
    if enable_wal_mode(db_path):
        logger.info("✅ WAL mode configuration complete")
    else:
        success = False

    # 2. Create indexes and optimize
    if optimize_sqlite_database(db_path):
        logger.info("✅ Database indexes and optimizations complete")
    else:
        success = False

    # 3. Verify performance
    if verify_database_performance(db_path):
        logger.info("✅ Performance verification complete")
    else:
        success = False

    if success:
        print()
        print("🎉 Database optimization completed successfully!")
        print("💡 Your database is now ready to handle large datasets efficiently.")
        print()
        print("Next steps:")
        print("1. Import new scraped data: python scripts/import_data.py")
        print("2. Run the application: streamlit run streamlit_app/app.py")
        print("3. Test performance with expanded dataset")
    else:
        print()
        print("⚠️ Some optimizations failed. Check the logs above.")
        print("The application should still work, but performance may be suboptimal.")

    return success

if __name__ == "__main__":
    main()