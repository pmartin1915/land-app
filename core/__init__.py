"""
Core Module - Shared business logic for Alabama Auction Watcher.

This module provides shared functionality that can be used by:
- Backend API
- Streamlit UI
- CLI tools
- Tests

Submodules:
- services: Filter specifications, business rules
- guardrails: Input validation and security
- models: Shared data models
"""

from .services import (
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
