"""
Centralized Property Filter Specifications.

This module provides a single source of truth for property filtering logic
that can be used by both the API backend and Streamlit UI.

Key Design Principles:
1. Filter specifications are framework-agnostic
2. Validation happens at the core layer
3. Both SQL and API queries can be built from the same spec
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum


# =============================================================================
# CONSTANTS
# =============================================================================

# Columns allowed for sorting (prevents SQL injection)
ALLOWED_SORT_COLUMNS = frozenset({
    "investment_score",
    "amount",
    "acreage",
    "price_per_acre",
    "water_score",
    "assessed_value_ratio",
    "county",
    "year_sold",
    "created_at",
    "updated_at",
    "county_market_score",
    "geographic_score",
    "market_timing_score",
    "total_description_score",
    "road_access_score",
})

# Score-based filter columns (minimum value filters)
SCORE_FILTER_COLUMNS = frozenset({
    "investment_score",
    "county_market_score",
    "geographic_score",
    "market_timing_score",
    "total_description_score",
    "road_access_score",
    "water_score",
})

# Default pagination values
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000


class SortOrder(str, Enum):
    """Sort direction enumeration."""
    ASC = "asc"
    DESC = "desc"


# =============================================================================
# FILTER SPECIFICATIONS
# =============================================================================

@dataclass
class PropertyFilterSpec:
    """
    Specification for property filtering.

    This is a framework-agnostic representation of filter criteria
    that can be converted to either SQL WHERE clauses or API query parameters.
    """
    # Price filters
    min_price: Optional[float] = None
    max_price: Optional[float] = None

    # Acreage filters
    min_acreage: Optional[float] = None
    max_acreage: Optional[float] = None

    # Categorical filters
    county: Optional[str] = None
    year_sold: Optional[str] = None

    # Feature filters
    water_features: Optional[bool] = None

    # Score filters
    min_investment_score: Optional[float] = None
    max_investment_score: Optional[float] = None
    min_county_market_score: Optional[float] = None
    min_geographic_score: Optional[float] = None
    min_market_timing_score: Optional[float] = None
    min_total_description_score: Optional[float] = None
    min_road_access_score: Optional[float] = None

    # Search
    search_query: Optional[str] = None

    def has_any_filter(self) -> bool:
        """Check if any filter is active."""
        return any([
            self.min_price is not None,
            self.max_price is not None,
            self.min_acreage is not None,
            self.max_acreage is not None,
            self.county is not None and self.county != "All",
            self.year_sold is not None,
            self.water_features is not None,
            self.min_investment_score is not None,
            self.max_investment_score is not None,
            self.min_county_market_score is not None,
            self.min_geographic_score is not None,
            self.min_market_timing_score is not None,
            self.min_total_description_score is not None,
            self.min_road_access_score is not None,
            self.search_query is not None,
        ])

    def get_active_filters(self) -> Dict[str, Any]:
        """Return dictionary of only active filters."""
        active = {}
        for field_name, value in self.__dict__.items():
            if value is not None:
                if field_name == "county" and value == "All":
                    continue
                active[field_name] = value
        return active

    @classmethod
    def from_ui_filters(cls, filters: Dict[str, Any]) -> "PropertyFilterSpec":
        """
        Create filter spec from UI filter dictionary.

        This handles the format used by the Streamlit UI.
        """
        spec = cls()

        # Price range (tuple)
        if "price_range" in filters and filters["price_range"]:
            min_price, max_price = filters["price_range"]
            spec.min_price = min_price if min_price > 0 else None
            spec.max_price = max_price if max_price < 1_000_000 else None

        # Acreage range (tuple)
        if "acreage_range" in filters and filters["acreage_range"]:
            min_acreage, max_acreage = filters["acreage_range"]
            spec.min_acreage = min_acreage if min_acreage > 0 else None
            spec.max_acreage = max_acreage if max_acreage < 1000 else None

        # County filter
        if filters.get("county") and filters["county"] != "All":
            spec.county = filters["county"]

        # Water features
        if filters.get("water_only"):
            spec.water_features = True

        # Score filters
        score_mappings = {
            "min_investment_score": "min_investment_score",
            "min_county_market_score": "min_county_market_score",
            "min_geographic_score": "min_geographic_score",
            "min_market_timing_score": "min_market_timing_score",
            "min_total_description_score": "min_total_description_score",
            "min_road_access_score": "min_road_access_score",
        }

        for ui_key, spec_key in score_mappings.items():
            if filters.get(ui_key, 0) > 0:
                setattr(spec, spec_key, filters[ui_key])

        # Search query
        if filters.get("search_query"):
            spec.search_query = filters["search_query"]

        return spec

    @classmethod
    def from_api_model(cls, model: Any) -> "PropertyFilterSpec":
        """
        Create filter spec from API Pydantic model.

        This handles PropertyFilters from the API models.
        """
        spec = cls()

        # Direct field mappings
        if hasattr(model, "min_price") and model.min_price is not None:
            spec.min_price = model.min_price
        if hasattr(model, "max_price") and model.max_price is not None:
            spec.max_price = model.max_price
        if hasattr(model, "min_acreage") and model.min_acreage is not None:
            spec.min_acreage = model.min_acreage
        if hasattr(model, "max_acreage") and model.max_acreage is not None:
            spec.max_acreage = model.max_acreage
        if hasattr(model, "county") and model.county:
            spec.county = model.county
        if hasattr(model, "year_sold") and model.year_sold:
            spec.year_sold = model.year_sold
        if hasattr(model, "water_features") and model.water_features is not None:
            spec.water_features = model.water_features
        if hasattr(model, "min_investment_score") and model.min_investment_score is not None:
            spec.min_investment_score = model.min_investment_score
        if hasattr(model, "max_investment_score") and model.max_investment_score is not None:
            spec.max_investment_score = model.max_investment_score
        if hasattr(model, "search_query") and model.search_query:
            spec.search_query = model.search_query

        # Intelligence score filters
        for attr in ["min_county_market_score", "min_geographic_score",
                     "min_market_timing_score", "min_total_description_score",
                     "min_road_access_score"]:
            if hasattr(model, attr) and getattr(model, attr) is not None:
                setattr(spec, attr, getattr(model, attr))

        return spec


@dataclass
class PropertySortSpec:
    """
    Specification for property sorting.
    """
    column: str = "investment_score"
    order: SortOrder = SortOrder.DESC

    def __post_init__(self):
        """Validate sort column."""
        if self.column not in ALLOWED_SORT_COLUMNS:
            self.column = "investment_score"
        if isinstance(self.order, str):
            self.order = SortOrder(self.order.lower())

    @property
    def is_ascending(self) -> bool:
        """Check if sort is ascending."""
        return self.order == SortOrder.ASC

    @classmethod
    def from_ui_tuple(cls, sort_tuple: Tuple[str, bool]) -> "PropertySortSpec":
        """
        Create sort spec from UI tuple format.

        UI uses (column_name, is_ascending) format.
        """
        column, is_asc = sort_tuple
        return cls(
            column=column if column in ALLOWED_SORT_COLUMNS else "investment_score",
            order=SortOrder.ASC if is_asc else SortOrder.DESC
        )

    @classmethod
    def from_api_params(cls, sort_by: str, sort_order: str) -> "PropertySortSpec":
        """Create sort spec from API parameters."""
        return cls(
            column=sort_by if sort_by in ALLOWED_SORT_COLUMNS else "investment_score",
            order=SortOrder(sort_order.lower()) if sort_order else SortOrder.DESC
        )


@dataclass
class PaginationSpec:
    """
    Specification for pagination.
    """
    page: int = DEFAULT_PAGE
    page_size: int = DEFAULT_PAGE_SIZE

    def __post_init__(self):
        """Validate pagination values."""
        if self.page < 1:
            self.page = DEFAULT_PAGE
        if self.page_size < 1:
            self.page_size = DEFAULT_PAGE_SIZE
        if self.page_size > MAX_PAGE_SIZE:
            self.page_size = MAX_PAGE_SIZE

    @property
    def offset(self) -> int:
        """Calculate offset for SQL queries."""
        return (self.page - 1) * self.page_size

    def calculate_total_pages(self, total_count: int) -> int:
        """Calculate total pages from total count."""
        if total_count == 0:
            return 0
        return (total_count + self.page_size - 1) // self.page_size


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def build_filter_params(filter_spec: PropertyFilterSpec) -> Dict[str, Any]:
    """
    Build API query parameters from filter specification.

    Returns a dictionary suitable for API requests.
    """
    params = {}

    if filter_spec.county:
        params["county"] = filter_spec.county
    if filter_spec.min_price is not None:
        params["min_price"] = filter_spec.min_price
    if filter_spec.max_price is not None:
        params["max_price"] = filter_spec.max_price
    if filter_spec.min_acreage is not None:
        params["min_acreage"] = filter_spec.min_acreage
    if filter_spec.max_acreage is not None:
        params["max_acreage"] = filter_spec.max_acreage
    if filter_spec.water_features is not None:
        params["water_features"] = filter_spec.water_features
    if filter_spec.min_investment_score is not None:
        params["min_investment_score"] = filter_spec.min_investment_score
    if filter_spec.max_investment_score is not None:
        params["max_investment_score"] = filter_spec.max_investment_score
    if filter_spec.year_sold:
        params["year_sold"] = filter_spec.year_sold
    if filter_spec.search_query:
        params["search_query"] = filter_spec.search_query

    # Intelligence filters
    for attr in ["min_county_market_score", "min_geographic_score",
                 "min_market_timing_score", "min_total_description_score",
                 "min_road_access_score"]:
        value = getattr(filter_spec, attr)
        if value is not None:
            params[attr] = value

    return params


def build_sql_where_clause(
    filter_spec: PropertyFilterSpec
) -> Tuple[str, List[Any]]:
    """
    Build SQL WHERE clause from filter specification.

    Returns (where_clause, params) tuple.
    This is safe from SQL injection as column names are validated.
    """
    conditions = []
    params = []

    # Price filters
    if filter_spec.min_price is not None:
        conditions.append("amount >= ?")
        params.append(filter_spec.min_price)
    if filter_spec.max_price is not None:
        conditions.append("amount <= ?")
        params.append(filter_spec.max_price)

    # Acreage filters
    if filter_spec.min_acreage is not None:
        conditions.append("acreage >= ?")
        params.append(filter_spec.min_acreage)
    if filter_spec.max_acreage is not None:
        conditions.append("acreage <= ?")
        params.append(filter_spec.max_acreage)

    # County filter
    if filter_spec.county and filter_spec.county != "All":
        conditions.append("county = ?")
        params.append(filter_spec.county)

    # Water features
    if filter_spec.water_features is True:
        conditions.append("water_score > 0")
    elif filter_spec.water_features is False:
        conditions.append("water_score = 0")

    # Year sold
    if filter_spec.year_sold:
        conditions.append("year_sold = ?")
        params.append(filter_spec.year_sold)

    # Score filters
    score_columns = [
        ("min_investment_score", "investment_score"),
        ("max_investment_score", "investment_score"),
        ("min_county_market_score", "county_market_score"),
        ("min_geographic_score", "geographic_score"),
        ("min_market_timing_score", "market_timing_score"),
        ("min_total_description_score", "total_description_score"),
        ("min_road_access_score", "road_access_score"),
    ]

    for attr, column in score_columns:
        value = getattr(filter_spec, attr)
        if value is not None:
            if attr.startswith("max_"):
                conditions.append(f"{column} <= ?")
            else:
                conditions.append(f"{column} >= ?")
            params.append(value)

    # Search query
    if filter_spec.search_query:
        search_term = f"%{filter_spec.search_query}%"
        conditions.append("(description LIKE ? OR owner_name LIKE ? OR parcel_id LIKE ?)")
        params.extend([search_term, search_term, search_term])

    # Build WHERE clause
    if conditions:
        where_clause = " AND ".join(conditions)
    else:
        where_clause = "1=1"

    return where_clause, params


def validate_filter_values(filters: Dict[str, Any]) -> List[str]:
    """
    Validate filter values and return list of validation errors.

    Returns empty list if all validations pass.
    """
    errors = []

    # Price range validation
    if "price_range" in filters:
        min_p, max_p = filters["price_range"]
        if min_p < 0:
            errors.append("Minimum price cannot be negative")
        if max_p < min_p:
            errors.append("Maximum price cannot be less than minimum price")

    # Acreage range validation
    if "acreage_range" in filters:
        min_a, max_a = filters["acreage_range"]
        if min_a < 0:
            errors.append("Minimum acreage cannot be negative")
        if max_a < min_a:
            errors.append("Maximum acreage cannot be less than minimum acreage")

    # Score validation (must be 0-100 for investment score)
    if filters.get("min_investment_score", 0) < 0:
        errors.append("Minimum investment score cannot be negative")
    if filters.get("min_investment_score", 0) > 100:
        errors.append("Minimum investment score cannot exceed 100")

    # Sort column validation
    if "sort_by" in filters:
        sort_val = filters["sort_by"]
        if isinstance(sort_val, tuple):
            column = sort_val[0]
        else:
            column = sort_val
        if column not in ALLOWED_SORT_COLUMNS:
            errors.append(f"Invalid sort column: {column}")

    return errors
