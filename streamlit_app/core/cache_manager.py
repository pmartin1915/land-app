"""
Advanced Caching System for Streamlit App - Alabama Auction Watcher

This module provides intelligent caching with multi-tier strategy, predictive loading,
context-aware invalidation, and AI-optimized performance for Streamlit components.
"""

import streamlit as st
import pandas as pd
import hashlib
import pickle
import time
import threading
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from functools import wraps
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.caching import get_cache_manager as get_backend_cache_manager
from streamlit_app.core.performance_monitor import get_performance_monitor, performance_context


@dataclass
class CacheEntry:
    """Enhanced cache entry with metadata."""
    key: str
    data: Any
    timestamp: datetime
    access_count: int
    last_access: datetime
    size_bytes: int
    cache_type: str  # 'api_data', 'computed_result', 'visualization'
    dependencies: List[str]  # Keys this entry depends on
    user_context: Dict[str, Any]
    ttl_seconds: int


class SmartCacheManager:
    """
    Advanced caching system with intelligent features:
    - Multi-tier caching (memory, session, backend)
    - Predictive data loading
    - Context-aware cache invalidation
    - Performance-optimized operations
    """

    def __init__(self):
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'invalidations': 0
        }
        self.max_memory_size = 100 * 1024 * 1024  # 100MB
        self.current_memory_usage = 0

        # Access patterns for predictive loading
        self.access_patterns: Dict[str, List[datetime]] = {}

        # Cache invalidation patterns
        self.invalidation_rules: Dict[str, List[str]] = {
            'filter_change': ['api_data', 'summary_metrics', 'visualizations'],
            'data_refresh': ['api_data', 'summary_metrics', 'visualizations', 'computed_results'],
            'user_selection': ['selected_properties', 'comparison_data']
        }

        # Background cache maintenance
        self._start_maintenance_thread()

    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate deterministic cache key."""
        # Include session context for user-specific caching
        session_context = self._get_session_context()

        key_data = {
            'prefix': prefix,
            'args': args,
            'kwargs': sorted(kwargs.items()) if kwargs else {},
            'session_context': session_context
        }

        key_string = str(key_data)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"streamlit:{prefix}:{key_hash[:12]}"

    def _get_session_context(self) -> Dict[str, Any]:
        """Get relevant session context for cache key generation."""
        context = {}

        try:
            # Get current filters from session state
            if hasattr(st, 'session_state'):
                if hasattr(st.session_state, 'filters'):
                    # Only include stable filter values in cache key
                    stable_filters = {
                        k: v for k, v in st.session_state.filters.items()
                        if k in ['county', 'price_range', 'acreage_range', 'water_only']
                    }
                    context['filters'] = stable_filters

                if hasattr(st.session_state, 'sort_order'):
                    context['sort_order'] = st.session_state.sort_order

        except Exception:
            # Fallback to empty context if session state is not available
            pass

        return context

    def _calculate_data_size(self, data: Any) -> int:
        """Calculate approximate size of data in bytes."""
        try:
            if isinstance(data, pd.DataFrame):
                return data.memory_usage(deep=True).sum()
            elif isinstance(data, (dict, list)):
                return len(pickle.dumps(data))
            else:
                return len(str(data).encode('utf-8'))
        except:
            return 1024  # Default size estimate

    def get(self, key: str, cache_type: str = None) -> Optional[Any]:
        """Get value from cache with intelligent access tracking."""
        # Check memory cache first
        if key in self.memory_cache:
            entry = self.memory_cache[key]

            # Check TTL
            if datetime.now() - entry.timestamp < timedelta(seconds=entry.ttl_seconds):
                # Update access metadata
                entry.access_count += 1
                entry.last_access = datetime.now()

                # Track access pattern
                self._track_access_pattern(key)

                self.cache_stats['hits'] += 1
                return entry.data
            else:
                # Expired entry
                del self.memory_cache[key]
                self.current_memory_usage -= entry.size_bytes

        # Check Streamlit session cache
        session_data = self._get_from_session_cache(key)
        if session_data is not None:
            self.cache_stats['hits'] += 1
            return session_data

        # Check backend cache
        backend_cache = get_backend_cache_manager()
        backend_data = backend_cache.get(key)
        if backend_data is not None:
            self.cache_stats['hits'] += 1
            return backend_data

        self.cache_stats['misses'] += 1
        return None

    def set(self, key: str, data: Any, ttl_seconds: int = 300,
            cache_type: str = 'computed_result', dependencies: List[str] = None):
        """Set value in cache with intelligent storage strategy."""

        data_size = self._calculate_data_size(data)

        # Check if we need to evict entries
        self._ensure_memory_space(data_size)

        # Create cache entry
        entry = CacheEntry(
            key=key,
            data=data,
            timestamp=datetime.now(),
            access_count=1,
            last_access=datetime.now(),
            size_bytes=data_size,
            cache_type=cache_type,
            dependencies=dependencies or [],
            user_context=self._get_session_context(),
            ttl_seconds=ttl_seconds
        )

        # Store in memory cache
        self.memory_cache[key] = entry
        self.current_memory_usage += data_size

        # Also store in session cache for large datasets
        if data_size > 1024 * 1024:  # > 1MB
            self._set_session_cache(key, data, ttl_seconds)

        # Store in backend cache for cross-session sharing
        if cache_type == 'api_data':
            backend_cache = get_backend_cache_manager()
            backend_cache.set(key, data, ttl_seconds)

    def _ensure_memory_space(self, required_bytes: int):
        """Ensure enough memory space is available."""
        while (self.current_memory_usage + required_bytes > self.max_memory_size
               and self.memory_cache):

            # Find least recently used entry
            lru_key = min(
                self.memory_cache.keys(),
                key=lambda k: self.memory_cache[k].last_access
            )

            # Evict LRU entry
            evicted_entry = self.memory_cache.pop(lru_key)
            self.current_memory_usage -= evicted_entry.size_bytes
            self.cache_stats['evictions'] += 1

    def invalidate(self, pattern: str):
        """Invalidate cache entries based on pattern."""
        if pattern in self.invalidation_rules:
            cache_types_to_invalidate = self.invalidation_rules[pattern]

            keys_to_remove = []
            for key, entry in self.memory_cache.items():
                if entry.cache_type in cache_types_to_invalidate:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                entry = self.memory_cache.pop(key)
                self.current_memory_usage -= entry.size_bytes
                self.cache_stats['invalidations'] += 1

        # Also clear session cache
        self._clear_session_cache_pattern(pattern)

    def _track_access_pattern(self, key: str):
        """Track access patterns for predictive loading."""
        if key not in self.access_patterns:
            self.access_patterns[key] = []

        self.access_patterns[key].append(datetime.now())

        # Keep only recent access history (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.access_patterns[key] = [
            t for t in self.access_patterns[key] if t > cutoff_time
        ]

    def predict_next_access(self, key: str) -> Optional[datetime]:
        """Predict when a key might be accessed next."""
        if key not in self.access_patterns or len(self.access_patterns[key]) < 2:
            return None

        accesses = self.access_patterns[key]
        intervals = []

        for i in range(1, len(accesses)):
            interval = (accesses[i] - accesses[i-1]).total_seconds()
            intervals.append(interval)

        # Calculate average interval
        avg_interval = sum(intervals) / len(intervals)

        # Predict next access
        last_access = accesses[-1]
        predicted_next = last_access + timedelta(seconds=avg_interval)

        return predicted_next

    def _get_from_session_cache(self, key: str) -> Optional[Any]:
        """Get data from Streamlit session cache."""
        try:
            if hasattr(st, 'session_state') and hasattr(st.session_state, 'cache_data'):
                return st.session_state.cache_data.get(key)
        except:
            pass
        return None

    def _set_session_cache(self, key: str, data: Any, ttl_seconds: int):
        """Set data in Streamlit session cache."""
        try:
            if not hasattr(st, 'session_state'):
                return

            if not hasattr(st.session_state, 'cache_data'):
                st.session_state.cache_data = {}

            if not hasattr(st.session_state, 'cache_metadata'):
                st.session_state.cache_metadata = {}

            st.session_state.cache_data[key] = data
            st.session_state.cache_metadata[key] = {
                'timestamp': datetime.now(),
                'ttl_seconds': ttl_seconds
            }
        except:
            pass

    def _clear_session_cache_pattern(self, pattern: str):
        """Clear session cache entries matching pattern."""
        try:
            if (hasattr(st, 'session_state') and
                hasattr(st.session_state, 'cache_data')):

                keys_to_remove = []
                for key in st.session_state.cache_data.keys():
                    if pattern in key:
                        keys_to_remove.append(key)

                for key in keys_to_remove:
                    del st.session_state.cache_data[key]
                    if hasattr(st.session_state, 'cache_metadata'):
                        st.session_state.cache_metadata.pop(key, None)
        except:
            pass

    def _start_maintenance_thread(self):
        """Start background maintenance thread."""
        def maintenance_loop():
            while True:
                try:
                    self._cleanup_expired_entries()
                    self._preload_predicted_data()
                    time.sleep(60)  # Run every minute
                except Exception:
                    time.sleep(300)  # Wait longer on error

        maintenance_thread = threading.Thread(target=maintenance_loop, daemon=True)
        maintenance_thread.start()

    def _cleanup_expired_entries(self):
        """Clean up expired cache entries."""
        current_time = datetime.now()
        expired_keys = []

        for key, entry in self.memory_cache.items():
            if current_time - entry.timestamp > timedelta(seconds=entry.ttl_seconds):
                expired_keys.append(key)

        for key in expired_keys:
            entry = self.memory_cache.pop(key)
            self.current_memory_usage -= entry.size_bytes

    def _preload_predicted_data(self):
        """Preload data that's predicted to be accessed soon."""
        # This is a placeholder for predictive loading logic
        # In a full implementation, this would use ML models to predict data needs
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = self.cache_stats['hits'] / total_requests if total_requests > 0 else 0

        return {
            'memory_usage_mb': self.current_memory_usage / (1024 * 1024),
            'memory_limit_mb': self.max_memory_size / (1024 * 1024),
            'entries_count': len(self.memory_cache),
            'hit_rate': hit_rate,
            'total_hits': self.cache_stats['hits'],
            'total_misses': self.cache_stats['misses'],
            'total_evictions': self.cache_stats['evictions'],
            'total_invalidations': self.cache_stats['invalidations'],
            'access_patterns_tracked': len(self.access_patterns)
        }

    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics (alias for get_stats)."""
        return self.get_stats()


# Global cache manager instance
_cache_manager: Optional[SmartCacheManager] = None


def get_cache_manager() -> SmartCacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = SmartCacheManager()
    return _cache_manager


def smart_cache(key_prefix: str = None, ttl_seconds: int = 300,
                cache_type: str = 'computed_result',
                dependencies: List[str] = None,
                invalidate_on: List[str] = None):
    """
    Smart caching decorator for Streamlit functions.

    Args:
        key_prefix: Prefix for cache key (auto-detected if None)
        ttl_seconds: Time to live in seconds
        cache_type: Type of cached data ('api_data', 'computed_result', 'visualization')
        dependencies: List of cache keys this depends on
        invalidate_on: List of patterns that should invalidate this cache
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()
            monitor = get_performance_monitor()

            # Generate cache key
            prefix = key_prefix or func.__name__
            cache_key = cache_manager._generate_cache_key(prefix, *args, **kwargs)

            # Try to get from cache
            with performance_context(f"cache_{prefix}", "lookup"):
                cached_result = cache_manager.get(cache_key)

            if cached_result is not None:
                monitor.record_metric(f"cache_{prefix}", "cache_hit", 1)
                return cached_result

            # Cache miss - execute function
            monitor.record_metric(f"cache_{prefix}", "cache_miss", 1)

            with performance_context(f"compute_{prefix}", "execution"):
                result = func(*args, **kwargs)

            # Store result in cache
            with performance_context(f"cache_{prefix}", "store"):
                cache_manager.set(
                    cache_key,
                    result,
                    ttl_seconds=ttl_seconds,
                    cache_type=cache_type,
                    dependencies=dependencies
                )

            return result

        # Add cache control methods
        wrapper.invalidate_cache = lambda *args, **kwargs: cache_manager.invalidate(
            cache_manager._generate_cache_key(key_prefix or func.__name__, *args, **kwargs)
        )
        wrapper.cache_info = lambda: cache_manager.get_stats()

        return wrapper
    return decorator


@smart_cache("api_data_loader", ttl_seconds=300, cache_type="api_data")
def cached_api_call(url: str, params: Dict[str, Any], headers: Dict[str, str]):
    """Cached API call with automatic invalidation."""
    import requests

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        # Don't cache errors
        raise


@smart_cache("dataframe_processor", ttl_seconds=600, cache_type="computed_result")
def cached_dataframe_processing(df: pd.DataFrame, operation: str, **kwargs):
    """Cache expensive DataFrame operations."""
    if operation == 'summary_stats':
        return {
            'count': len(df),
            'mean_price': df['amount'].mean() if 'amount' in df.columns else 0,
            'mean_acreage': df['acreage'].mean() if 'acreage' in df.columns else 0,
            'water_properties': (df['water_score'] > 0).sum() if 'water_score' in df.columns else 0
        }
    elif operation == 'filter':
        # Apply filters
        filtered_df = df.copy()
        for column, value in kwargs.items():
            if column in filtered_df.columns:
                if isinstance(value, (list, tuple)) and len(value) == 2:
                    # Range filter
                    filtered_df = filtered_df[
                        (filtered_df[column] >= value[0]) &
                        (filtered_df[column] <= value[1])
                    ]
                else:
                    # Exact match filter
                    filtered_df = filtered_df[filtered_df[column] == value]
        return filtered_df

    return df


def invalidate_cache_on_filter_change():
    """Invalidate relevant caches when filters change."""
    cache_manager = get_cache_manager()
    cache_manager.invalidate('filter_change')


def invalidate_cache_on_data_refresh():
    """Invalidate all data caches when refreshing."""
    cache_manager = get_cache_manager()
    cache_manager.invalidate('data_refresh')


def display_cache_info():
    """Display cache information in Streamlit (for debugging)."""
    cache_manager = get_cache_manager()
    stats = cache_manager.get_stats()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Cache Hit Rate", f"{stats['hit_rate']:.1%}")
        st.metric("Memory Usage", f"{stats['memory_usage_mb']:.1f}MB")

    with col2:
        st.metric("Cache Entries", stats['entries_count'])
        st.metric("Total Hits", stats['total_hits'])

    with col3:
        st.metric("Total Misses", stats['total_misses'])
        st.metric("Evictions", stats['total_evictions'])

    # Cache management controls
    if st.button("Clear All Caches"):
        cache_manager.memory_cache.clear()
        cache_manager.current_memory_usage = 0
        st.success("All caches cleared!")
        st.rerun()


class CachePreloader:
    """Intelligent cache preloading based on user patterns."""

    def __init__(self, cache_manager: SmartCacheManager):
        self.cache_manager = cache_manager

    def preload_common_queries(self, user_filters: Dict[str, Any]):
        """Preload data for common query patterns."""
        # This would implement predictive loading based on user behavior
        # For now, it's a placeholder for the concept
        pass