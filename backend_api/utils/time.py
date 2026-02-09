"""
Centralized time utilities for consistent timezone handling.

CRITICAL: All datetime operations in the sync module should use these utilities
to ensure timezone-aware datetimes and prevent drift between client/server timestamps.

Why this matters:
- datetime.utcnow() returns naive datetime (no timezone info) - DEPRECATED in Python 3.12
- func.now() uses database server time which may drift from application server
- Clients send timezone-aware UTC timestamps
- Comparing naive vs aware datetimes raises TypeError in Python 3.x

Usage:
    from backend_api.utils import utc_now

    # Instead of: datetime.utcnow()
    timestamp = utc_now()

    # For SQLAlchemy model defaults, use the callable:
    created_at = Column(DateTime(timezone=True), default=utc_now)
"""

from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """
    Returns the current UTC time as a timezone-aware datetime.

    This is the single source of truth for timestamps in the application.
    Always use this instead of datetime.utcnow() or datetime.now().

    Returns:
        datetime: Current UTC time with timezone info (tzinfo=timezone.utc)

    Example:
        >>> ts = utc_now()
        >>> ts.tzinfo
        datetime.timezone.utc
    """
    return datetime.now(timezone.utc)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensures a datetime is timezone-aware UTC.

    - If None, returns None
    - If naive (no tzinfo), assumes UTC and adds timezone
    - If aware but different timezone, converts to UTC
    - If already UTC, returns as-is

    Args:
        dt: A datetime object (naive or aware) or None

    Returns:
        Timezone-aware UTC datetime or None

    Example:
        >>> naive = datetime(2024, 1, 1, 12, 0, 0)
        >>> aware = ensure_utc(naive)
        >>> aware.tzinfo
        datetime.timezone.utc
    """
    if dt is None:
        return None

    if dt.tzinfo is None:
        # Naive datetime - assume UTC
        return dt.replace(tzinfo=timezone.utc)
    elif dt.tzinfo != timezone.utc:
        # Different timezone - convert to UTC
        return dt.astimezone(timezone.utc)
    else:
        # Already UTC
        return dt


def format_iso(dt: Optional[datetime]) -> Optional[str]:
    """
    Formats a datetime as ISO 8601 string with UTC timezone.

    Args:
        dt: A datetime object or None

    Returns:
        ISO 8601 formatted string (e.g., "2024-01-01T12:00:00+00:00") or None
    """
    if dt is None:
        return None

    utc_dt = ensure_utc(dt)
    return utc_dt.isoformat()
