"""
Core Services Module - Centralized business logic for Alabama Auction Watcher.

This module provides shared services that can be used by both:
- Backend API (FastAPI routers and services)
- Frontend UI (Streamlit application)

This separation ensures:
1. Single source of truth for business logic
2. UI can be modified without breaking core functionality
3. Tests focus on core logic, not UI implementation
"""

from .property_filters import (
    PropertyFilterSpec,
    PropertySortSpec,
    build_filter_params,
    validate_filter_values,
    ALLOWED_SORT_COLUMNS,
    SCORE_FILTER_COLUMNS,
)

__all__ = [
    "PropertyFilterSpec",
    "PropertySortSpec",
    "build_filter_params",
    "validate_filter_values",
    "ALLOWED_SORT_COLUMNS",
    "SCORE_FILTER_COLUMNS",
]
