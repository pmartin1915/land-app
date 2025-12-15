"""
Asynchronous Data Loading System for Streamlit App - Alabama Auction Watcher

This module provides concurrent data loading, progressive rendering, and background
data refresh capabilities to dramatically improve Streamlit app performance.
"""

import asyncio
import streamlit as st
import pandas as pd
import requests
import threading
import time
import sqlite3
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.security import get_security_config, create_secure_headers
from streamlit_app.core.performance_monitor import get_performance_monitor, performance_context
from streamlit_app.core.cache_manager import get_cache_manager


@dataclass
class DataLoadRequest:
    """Data loading request specification."""
    endpoint: str
    params: Dict[str, Any]
    priority: int = 1  # 1=highest, 10=lowest
    cache_key: str = None
    timeout: int = 30
    retry_count: int = 3
    callback: Optional[Callable] = None


@dataclass
class LoadResult:
    """Result of a data loading operation."""
    request: DataLoadRequest
    data: Any
    success: bool
    error: Optional[str]
    load_time: float
    from_cache: bool


class AsyncDataLoader:
    """
    Asynchronous data loading system with intelligent features:
    - Concurrent API calls
    - Progressive data loading
    - Background refresh
    - Priority-based loading
    - Automatic retry logic
    """

    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_requests: Dict[str, threading.Event] = {}
        self.request_queue: List[DataLoadRequest] = []
        self.cache_manager = get_cache_manager()
        self.performance_monitor = get_performance_monitor()

        # Background refresh settings
        self.background_refresh_enabled = True
        self.refresh_interval_seconds = 300  # 5 minutes
        self.last_refresh_time = {}

        # Start background refresh thread
        self._start_background_refresh()

    def load_data_sync(self, request: DataLoadRequest) -> LoadResult:
        """Synchronously load data (blocking call)."""
        return self._execute_single_request(request)

    def load_data_async(self, requests: List[DataLoadRequest]) -> List[LoadResult]:
        """Load multiple data requests asynchronously."""
        if not requests:
            return []

        # Sort by priority
        requests.sort(key=lambda x: x.priority)

        # Submit all requests to thread pool
        future_to_request = {}
        for request in requests:
            future = self.executor.submit(self._execute_single_request, request)
            future_to_request[future] = request

        # Collect results as they complete
        results = []
        for future in as_completed(future_to_request.keys()):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                # Create error result
                request = future_to_request[future]
                error_result = LoadResult(
                    request=request,
                    data=None,
                    success=False,
                    error=str(e),
                    load_time=0.0,
                    from_cache=False
                )
                results.append(error_result)

        return results

    def _execute_single_request(self, request: DataLoadRequest) -> LoadResult:
        """Execute a single data loading request."""
        start_time = time.time()

        # Check cache first
        if request.cache_key:
            cached_data = self.cache_manager.get(request.cache_key)
            if cached_data is not None:
                return LoadResult(
                    request=request,
                    data=cached_data,
                    success=True,
                    error=None,
                    load_time=time.time() - start_time,
                    from_cache=True
                )

        # Execute API call with retries
        for attempt in range(request.retry_count):
            try:
                with performance_context("async_loader", f"api_call_{request.endpoint}"):
                    data = self._make_api_call(request)

                # Cache the result
                if request.cache_key:
                    self.cache_manager.set(
                        request.cache_key,
                        data,
                        ttl_seconds=300,
                        cache_type="api_data"
                    )

                # Execute callback if provided
                if request.callback:
                    request.callback(data)

                return LoadResult(
                    request=request,
                    data=data,
                    success=True,
                    error=None,
                    load_time=time.time() - start_time,
                    from_cache=False
                )

            except Exception as e:
                if attempt == request.retry_count - 1:
                    # Final attempt failed
                    return LoadResult(
                        request=request,
                        data=None,
                        success=False,
                        error=str(e),
                        load_time=time.time() - start_time,
                        from_cache=False
                    )
                else:
                    # Wait before retry
                    time.sleep(2 ** attempt)  # Exponential backoff

    def _make_api_call(self, request: DataLoadRequest) -> Any:
        """Make the actual API call."""
        security_config = get_security_config()
        base_url = security_config.api_base_url
        url = f"{base_url}/{request.endpoint.lstrip('/')}"

        headers = create_secure_headers()

        response = requests.get(
            url,
            params=request.params,
            headers=headers,
            timeout=request.timeout
        )
        response.raise_for_status()

        return response.json()

    def _start_background_refresh(self):
        """Start background data refresh thread."""
        def refresh_loop():
            while True:
                try:
                    if self.background_refresh_enabled:
                        self._refresh_stale_data()
                    time.sleep(60)  # Check every minute
                except Exception:
                    time.sleep(300)  # Wait longer on error

        refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
        refresh_thread.start()

    def _refresh_stale_data(self):
        """Refresh data that's becoming stale."""
        # This would implement background refresh logic
        # For now, it's a placeholder
        pass

    def create_property_load_requests(self, filters: Dict[str, Any]) -> List[DataLoadRequest]:
        """Create optimized load requests for property data."""
        requests = []

        # Primary data request
        main_request = DataLoadRequest(
            endpoint="properties/",
            params=self._build_api_params(filters),
            priority=1,
            cache_key=self.cache_manager._generate_cache_key("properties", **filters),
            timeout=30
        )
        requests.append(main_request)

        # Summary metrics request (lower priority)
        if len(requests) == 1:  # Only if we're loading main data
            summary_request = DataLoadRequest(
                endpoint="properties/metrics",
                params={},
                priority=2,
                cache_key=self.cache_manager._generate_cache_key("metrics"),
                timeout=15
            )
            requests.append(summary_request)

        return requests

    def _build_api_params(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Build API parameters from filters."""
        params = {
            "page_size": 10000  # Fetch all data in single request
        }

        # Map filter values to API parameters
        if 'price_range' in filters and filters['price_range']:
            min_price, max_price = filters['price_range']
            if min_price > 0:
                params['min_price'] = min_price
            if max_price < 1000000:  # Only set if not at maximum
                params['max_price'] = max_price

        if 'acreage_range' in filters and filters['acreage_range']:
            min_acreage, max_acreage = filters['acreage_range']
            if min_acreage > 0:
                params['min_acreage'] = min_acreage
            if max_acreage < 1000:  # Only set if not at maximum
                params['max_acreage'] = max_acreage

        if filters.get('water_only'):
            params['water_features'] = True

        if filters.get('county') and filters['county'] != 'All':
            params['county'] = filters['county']

        # Intelligence score filters
        for score_filter in ['min_investment_score', 'min_county_market_score',
                           'min_geographic_score', 'min_market_timing_score',
                           'min_total_description_score', 'min_road_access_score']:
            if filters.get(score_filter, 0) > 0:
                params[score_filter] = filters[score_filter]

        return params


class ProgressiveDataLoader:
    """
    Progressive data loading for better user experience.
    Loads data in chunks and updates UI progressively.
    """

    def __init__(self, async_loader: AsyncDataLoader):
        self.async_loader = async_loader

    def load_with_progress(self, requests: List[DataLoadRequest],
                         progress_callback: Optional[Callable] = None) -> List[LoadResult]:
        """Load data with progress updates."""

        if not requests:
            return []

        # Sort by priority
        requests.sort(key=lambda x: x.priority)

        results = []
        total_requests = len(requests)

        # Create progress indicator if callback provided
        if progress_callback:
            progress_callback(0, "Starting data load...")

        # Load requests in order of priority
        for i, request in enumerate(requests):
            if progress_callback:
                progress_callback(
                    int((i / total_requests) * 100),
                    f"Loading {request.endpoint}..."
                )

            result = self.async_loader.load_data_sync(request)
            results.append(result)

            # Update progress
            if progress_callback:
                status = "✓" if result.success else "✗"
                cache_status = " (cached)" if result.from_cache else ""
                progress_callback(
                    int(((i + 1) / total_requests) * 100),
                    f"{status} {request.endpoint}{cache_status}"
                )

        return results


class StreamlitDataLoader:
    """
    Streamlit-specific data loader with UI integration.
    Provides seamless integration with Streamlit's reactive model.
    """

    def __init__(self):
        self.async_loader = AsyncDataLoader()
        self.progressive_loader = ProgressiveDataLoader(self.async_loader)

    def load_properties_with_ui(self, filters: Dict[str, Any]) -> pd.DataFrame:
        """Load properties data with Streamlit UI integration and database fallback."""

        # Try API first
        try:
            # Create loading requests
            requests = self.async_loader.create_property_load_requests(filters)

            # Show loading indicator
            with st.spinner("Loading property data from API..."):
                # Use progressive loading for better UX
                results = self.progressive_loader.load_with_progress(requests)

            # Process results
            property_data = None
            for result in results:
                if result.request.endpoint == "properties/" and result.success:
                    property_data = result.data.get('properties', [])
                    break

            if property_data:
                df = pd.DataFrame(property_data)
                return self._process_properties_data(df)

        except Exception as e:
            st.warning(f"API unavailable: {str(e)}. Falling back to direct database access...")

        # Fallback to direct database access
        try:
            with st.spinner("Loading property data from database..."):
                df = self._load_from_database_direct(filters)
                if not df.empty:
                    st.success(f"Loaded {len(df)} properties from database")
                    return self._process_properties_data(df)
        except Exception as e:
            st.error(f"Failed to load data from database: {str(e)}")

        return pd.DataFrame()

    def _load_from_database_direct(self, filters: Dict[str, Any]) -> pd.DataFrame:
        """Load data directly from the database as a fallback."""
        # Database path - use the same path as the corrected API backend
        db_path = Path(__file__).parent.parent.parent / "alabama_auction_watcher.db"

        if not db_path.exists():
            raise FileNotFoundError(f"Database not found at {db_path}")

        # Connect and query
        conn = sqlite3.connect(str(db_path))

        try:
            # Build the base query
            query = """
            SELECT * FROM properties
            WHERE 1=1
            """
            params = []

            # Apply filters
            if 'price_range' in filters and filters['price_range']:
                min_price, max_price = filters['price_range']
                if min_price > 0:
                    query += " AND amount >= ?"
                    params.append(min_price)
                if max_price < 1000000:  # Only set if not at maximum
                    query += " AND amount <= ?"
                    params.append(max_price)

            if 'acreage_range' in filters and filters['acreage_range']:
                min_acreage, max_acreage = filters['acreage_range']
                if min_acreage > 0:
                    query += " AND acreage >= ?"
                    params.append(min_acreage)
                if max_acreage < 1000:
                    query += " AND acreage <= ?"
                    params.append(max_acreage)

            if filters.get('water_only'):
                query += " AND water_score > 0"

            if filters.get('county') and filters['county'] != 'All':
                query += " AND county = ?"
                params.append(filters['county'])

            # Intelligence score filters
            score_filters = ['min_investment_score', 'min_county_market_score',
                           'min_geographic_score', 'min_market_timing_score',
                           'min_total_description_score', 'min_road_access_score']

            for score_filter in score_filters:
                if filters.get(score_filter, 0) > 0:
                    column_name = score_filter.replace('min_', '')
                    query += f" AND {column_name} >= ?"
                    params.append(filters[score_filter])

            # Order by investment score for consistent results
            query += " ORDER BY investment_score DESC"

            # Execute query and return DataFrame
            df = pd.read_sql_query(query, conn, params=params)
            return df

        finally:
            conn.close()

    def _process_properties_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process and clean properties data."""
        if df.empty:
            return df

        # Ensure required columns exist
        required_columns = {
            'rank': 0, 'parcel_id': 'Unknown', 'amount': 0.0, 'acreage': 0.0,
            'price_per_acre': 0.0, 'water_score': 0.0, 'investment_score': 0.0,
            'description': 'No description', 'county': 'Unknown'
        }
        for col, default in required_columns.items():
            if col not in df.columns:
                df[col] = default

        # Calculate price per acre if missing
        if 'price_per_acre' not in df.columns or df['price_per_acre'].isna().any():
            df['price_per_acre'] = df.apply(
                lambda row: row['amount'] / row['acreage'] if row['acreage'] > 0 else 0,
                axis=1
            )

        return df

    def load_component_data(self, component_name: str, data_type: str,
                          params: Dict[str, Any] = None) -> Any:
        """Load data for a specific component asynchronously."""

        endpoint_mapping = {
            'analytics': 'properties/metrics',
            'counties': 'counties/',
            'comparison': 'properties/',
        }

        endpoint = endpoint_mapping.get(data_type, data_type)

        request = DataLoadRequest(
            endpoint=endpoint,
            params=params or {},
            priority=2,  # Lower priority than main data
            cache_key=self.async_loader.cache_manager._generate_cache_key(
                f"{component_name}_{data_type}", **(params or {})
            )
        )

        result = self.async_loader.load_data_sync(request)

        if result.success:
            return result.data
        else:
            st.error(f"Failed to load {data_type} data: {result.error}")
            return None


# Global loader instances
_async_loader: Optional[AsyncDataLoader] = None
_streamlit_loader: Optional[StreamlitDataLoader] = None


def get_async_loader() -> AsyncDataLoader:
    """Get the global async data loader instance."""
    global _async_loader
    if _async_loader is None:
        _async_loader = AsyncDataLoader()
    return _async_loader


def get_streamlit_loader() -> StreamlitDataLoader:
    """Get the global Streamlit data loader instance."""
    global _streamlit_loader
    if _streamlit_loader is None:
        _streamlit_loader = StreamlitDataLoader()
    return _streamlit_loader


# Utility functions for common loading patterns

def async_load_properties(filters: Dict[str, Any]) -> pd.DataFrame:
    """Async load properties with caching and error handling."""
    loader = get_streamlit_loader()
    return loader.load_properties_with_ui(filters)


def background_refresh_data():
    """Trigger background data refresh."""
    loader = get_async_loader()
    # This would trigger a background refresh of commonly accessed data
    pass


class DataLoadingProgress:
    """Context manager for showing data loading progress."""

    def __init__(self, title: str = "Loading data..."):
        self.title = title
        self.progress_bar = None
        self.status_text = None

    def __enter__(self):
        self.progress_bar = st.progress(0)
        self.status_text = st.empty()
        self.status_text.text(self.title)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.progress_bar:
            self.progress_bar.empty()
        if self.status_text:
            self.status_text.empty()

    def update(self, progress: int, message: str):
        """Update progress and message."""
        if self.progress_bar:
            self.progress_bar.progress(progress)
        if self.status_text:
            self.status_text.text(message)


def with_loading_progress(title: str = "Loading..."):
    """Decorator to add loading progress to functions."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            with DataLoadingProgress(title):
                return func(*args, **kwargs)
        return wrapper
    return decorator


@with_loading_progress("Loading property data...")
def load_and_cache_properties(filters: Dict[str, Any]) -> pd.DataFrame:
    """Load properties with automatic progress indication."""
    return async_load_properties(filters)