"""
Database connection management for Alabama Auction Watcher API
Async database connections with SQLAlchemy and proper connection pooling
"""

import logging
from databases import Database
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ..config import settings

logger = logging.getLogger(__name__)

# Database configuration from centralized settings
DATABASE_URL = settings.resolved_database_url

# Validate database URL scheme for security
ALLOWED_DB_SCHEMES = (
    "sqlite://",           # Sync SQLite
    "sqlite+aiosqlite://", # Async SQLite (testing)
    "postgresql://",       # Sync PostgreSQL
    "postgresql+asyncpg://", # Async PostgreSQL
)
if not any(DATABASE_URL.startswith(scheme) for scheme in ALLOWED_DB_SCHEMES):
    raise ValueError(
        f"Unsupported database scheme in DATABASE_URL. "
        f"Allowed schemes: {', '.join(ALLOWED_DB_SCHEMES)}"
    )

# For production PostgreSQL, use format:
# postgresql://username:password@localhost/dbname

# Database instance for async operations
database = Database(DATABASE_URL)

# SQLAlchemy engine for sync operations
if DATABASE_URL.startswith("sqlite"):
    # SQLite configuration with thread safety
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.resolved_sql_echo
    )
else:
    # PostgreSQL configuration
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=settings.resolved_sql_echo
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy models
Base = declarative_base()

# Metadata for table creation
metadata = MetaData()

async def connect_db():
    """Connect to the database."""
    try:
        await database.connect()
        logger.info(f" Database connected: {DATABASE_URL}")
    except Exception as e:
        logger.error(f"L Database connection failed: {str(e)}")
        raise

async def disconnect_db():
    """Disconnect from the database."""
    try:
        await database.disconnect()
        logger.info(" Database disconnected successfully")
    except Exception as e:
        logger.error(f"L Database disconnection failed: {str(e)}")
        raise

def get_db():
    """
    Dependency function to get database session.
    Use this with FastAPI Depends() for automatic session management.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def create_tables():
    """Create all database tables."""
    try:
        # Import models to ensure they're registered with SQLAlchemy
        from .models import Property, County, SyncLog, UserProfile, PropertyApplication, ApplicationBatch, ApplicationNotification

        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info(" Database tables created successfully")
    except Exception as e:
        logger.error(f"L Table creation failed: {str(e)}")
        raise

async def get_database():
    """Get async database instance for direct queries."""
    return database

def get_engine():
    """Get SQLAlchemy engine instance."""
    return engine

# Health check function
async def check_database_health():
    """Check database connectivity and return status."""
    try:
        if database.is_connected:
            # Simple query to test connectivity
            await database.fetch_one("SELECT 1 as health_check")
            return {"status": "healthy", "connected": True}
        else:
            return {"status": "disconnected", "connected": False}
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {"status": "unhealthy", "connected": False, "error": str(e)}