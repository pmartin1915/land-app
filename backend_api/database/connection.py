"""
Database connection management for Auction Watcher API
Async database connections with SQLAlchemy and proper connection pooling
"""

import logging
from databases import Database
from sqlalchemy import create_engine, MetaData
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import declarative_base, sessionmaker
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

# CRITICAL: Prevent SQLite from running in production
# SQLite is not suitable for production due to:
# - No concurrent write support (StaticPool uses single connection)
# - No network access (can't scale horizontally)
# - File-based storage (data loss risk, no replication)
if settings.is_production and DATABASE_URL.startswith("sqlite"):
    raise ValueError(
        "SQLite is not allowed in production. "
        "Set DATABASE_URL to a PostgreSQL connection string: "
        "postgresql://username:password@host:5432/dbname"
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

# Base class for SQLAlchemy models with auto-serialization
class _BaseModel:
    """Mixin providing generic to_dict() for all SQLAlchemy models."""

    def to_dict(self):
        result = {}
        for col in sa_inspect(type(self)).mapper.column_attrs:
            value = getattr(self, col.key)
            if hasattr(value, 'isoformat'):
                value = value.isoformat()
            result[col.key] = value
        return result

Base = declarative_base(cls=_BaseModel)

# Metadata for table creation
metadata = MetaData()


def _redact_database_url(url: str) -> str:
    """Redact password from database URL for safe logging."""
    # Pattern: protocol://user:password@host/db -> protocol://user:***@host/db
    if "@" in url and "://" in url:
        prefix = url.split("://")[0]  # postgresql or sqlite
        rest = url.split("://")[1]    # user:password@host/db
        if "@" in rest:
            creds_part, host_part = rest.split("@", 1)
            if ":" in creds_part:
                user = creds_part.split(":")[0]
                return f"{prefix}://{user}:***@{host_part}"
    return url


async def connect_db():
    """Connect to the database."""
    try:
        await database.connect()
        logger.info(f"Database connected: {_redact_database_url(DATABASE_URL)}")
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise

async def disconnect_db():
    """Disconnect from the database."""
    try:
        await database.disconnect()
        logger.info("Database disconnected successfully")
    except Exception as e:
        logger.error(f"Database disconnection failed: {str(e)}")
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
        # IMPORTANT: Include ALL models to ensure tables are created
        from .models import (
            Property, County, SyncLog, UserProfile, PropertyApplication,
            ApplicationBatch, ApplicationNotification, StateConfig,
            UserPreference, PropertyInteraction, ScrapeJob, WholesalePipeline
        )

        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Table creation failed: {str(e)}")
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
