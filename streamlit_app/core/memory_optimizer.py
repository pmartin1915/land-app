"""
Memory Optimization System for Streamlit App - Alabama Auction Watcher

This module provides intelligent memory management, data structure optimization,
and memory-efficient operations for handling large datasets in Streamlit.
"""

import pandas as pd
import numpy as np
import streamlit as st
import gc
import psutil
import sys
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from streamlit_app.core.performance_monitor import get_performance_monitor, performance_context

logger = logging.getLogger(__name__)


@dataclass
class MemoryStats:
    """Memory usage statistics."""
    total_mb: float
    available_mb: float
    used_mb: float
    used_percentage: float
    process_mb: float
    dataframe_mb: float


class DataFrameOptimizer:
    """
    Optimizes pandas DataFrames for memory efficiency.
    Includes column type optimization, data compression, and lazy loading.
    """

    def __init__(self):
        self.type_mappings = {
            'integer': {
                'int64': ['int8', 'int16', 'int32'],
                'uint64': ['uint8', 'uint16', 'uint32']
            },
            'float': {
                'float64': ['float32']
            }
        }

    def optimize_dataframe(self, df: pd.DataFrame, aggressive: bool = False) -> pd.DataFrame:
        """
        Optimize DataFrame memory usage.

        Args:
            df: DataFrame to optimize
            aggressive: Whether to use aggressive optimization (may lose precision)

        Returns:
            Optimized DataFrame
        """
        if df.empty:
            return df

        with performance_context("memory_optimizer", "dataframe_optimization"):
            original_memory = df.memory_usage(deep=True).sum()

            # Create optimized copy
            optimized_df = df.copy()

            # Optimize numeric columns
            optimized_df = self._optimize_numeric_columns(optimized_df, aggressive)

            # Optimize object columns
            optimized_df = self._optimize_object_columns(optimized_df)

            # Optimize categorical columns
            optimized_df = self._optimize_categorical_columns(optimized_df)

            final_memory = optimized_df.memory_usage(deep=True).sum()
            memory_saved = original_memory - final_memory
            memory_reduction = (memory_saved / original_memory) * 100

            logger.info(f"DataFrame optimized: {memory_reduction:.1f}% memory reduction")

            return optimized_df

    def _optimize_numeric_columns(self, df: pd.DataFrame, aggressive: bool) -> pd.DataFrame:
        """Optimize numeric column types."""
        for column in df.select_dtypes(include=['int64', 'float64']).columns:
            col_series = df[column]

            # Skip if contains NaN (unless aggressive)
            if col_series.isnull().any() and not aggressive:
                continue

            try:
                if col_series.dtype == 'int64':
                    # Find the smallest integer type that can hold the data
                    min_val, max_val = col_series.min(), col_series.max()

                    if min_val >= 0:  # Unsigned integers
                        if max_val <= np.iinfo(np.uint8).max:
                            df[column] = col_series.astype('uint8')
                        elif max_val <= np.iinfo(np.uint16).max:
                            df[column] = col_series.astype('uint16')
                        elif max_val <= np.iinfo(np.uint32).max:
                            df[column] = col_series.astype('uint32')
                    else:  # Signed integers
                        if (min_val >= np.iinfo(np.int8).min and
                            max_val <= np.iinfo(np.int8).max):
                            df[column] = col_series.astype('int8')
                        elif (min_val >= np.iinfo(np.int16).min and
                              max_val <= np.iinfo(np.int16).max):
                            df[column] = col_series.astype('int16')
                        elif (min_val >= np.iinfo(np.int32).min and
                              max_val <= np.iinfo(np.int32).max):
                            df[column] = col_series.astype('int32')

                elif col_series.dtype == 'float64':
                    # Convert to float32 if precision loss is acceptable
                    if aggressive or self._can_convert_to_float32(col_series):
                        df[column] = col_series.astype('float32')

            except (ValueError, OverflowError):
                # Keep original type if conversion fails
                continue

        return df

    def _can_convert_to_float32(self, series: pd.Series) -> bool:
        """Check if float64 series can be safely converted to float32."""
        if series.isnull().all():
            return True

        try:
            # Check if conversion preserves data integrity
            converted = series.astype('float32')
            return np.allclose(series.dropna(), converted.dropna(), rtol=1e-6)
        except:
            return False

    def _optimize_object_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Optimize object columns by converting to category where appropriate."""
        for column in df.select_dtypes(include=['object']).columns:
            col_series = df[column]

            # Skip if column is mostly NaN
            if col_series.isnull().sum() / len(col_series) > 0.9:
                continue

            # Convert to category if it reduces memory usage
            unique_count = col_series.nunique()
            total_count = len(col_series)

            # Use categorical if less than 50% unique values or absolute threshold
            if (unique_count / total_count < 0.5) or (unique_count < 100):
                try:
                    df[column] = col_series.astype('category')
                except:
                    continue

        return df

    def _optimize_categorical_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Optimize existing categorical columns."""
        for column in df.select_dtypes(include=['category']).columns:
            # Remove unused categories
            df[column] = df[column].cat.remove_unused_categories()

        return df

    def get_memory_usage_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get detailed memory usage summary for a DataFrame."""
        if df.empty:
            return {"total_mb": 0, "columns": {}}

        memory_usage = df.memory_usage(deep=True)
        total_bytes = memory_usage.sum()

        summary = {
            "total_mb": total_bytes / (1024 * 1024),
            "total_bytes": total_bytes,
            "row_count": len(df),
            "column_count": len(df.columns),
            "bytes_per_row": total_bytes / len(df) if len(df) > 0 else 0,
            "columns": {}
        }

        # Per-column breakdown
        for column in df.columns:
            col_memory = memory_usage[column]
            summary["columns"][column] = {
                "mb": col_memory / (1024 * 1024),
                "bytes": col_memory,
                "dtype": str(df[column].dtype),
                "percentage": (col_memory / total_bytes) * 100
            }

        return summary


class MemoryManager:
    """
    Comprehensive memory management for Streamlit applications.
    Monitors memory usage, triggers garbage collection, and optimizes data structures.
    """

    def __init__(self, memory_threshold_mb: int = 500):
        self.memory_threshold_mb = memory_threshold_mb
        self.dataframe_optimizer = DataFrameOptimizer()
        self.performance_monitor = get_performance_monitor()

        # Memory usage tracking
        self.memory_history: List[MemoryStats] = []
        self.max_history = 100

    def get_memory_stats(self) -> MemoryStats:
        """Get current memory usage statistics."""
        # System memory
        memory = psutil.virtual_memory()

        # Process memory
        process = psutil.Process()
        process_memory = process.memory_info().rss

        # DataFrame memory (estimate from session state)
        dataframe_memory = self._estimate_dataframe_memory()

        stats = MemoryStats(
            total_mb=memory.total / (1024 * 1024),
            available_mb=memory.available / (1024 * 1024),
            used_mb=memory.used / (1024 * 1024),
            used_percentage=memory.percent,
            process_mb=process_memory / (1024 * 1024),
            dataframe_mb=dataframe_memory
        )

        # Track history
        self.memory_history.append(stats)
        if len(self.memory_history) > self.max_history:
            self.memory_history.pop(0)

        return stats

    def _estimate_dataframe_memory(self) -> float:
        """Estimate memory usage of DataFrames in session state."""
        total_memory = 0

        try:
            if hasattr(st, 'session_state'):
                for key, value in st.session_state.items():
                    if isinstance(value, pd.DataFrame):
                        total_memory += value.memory_usage(deep=True).sum()
                    elif isinstance(value, dict):
                        # Check for DataFrames in nested dictionaries
                        for nested_value in value.values():
                            if isinstance(nested_value, pd.DataFrame):
                                total_memory += nested_value.memory_usage(deep=True).sum()
        except:
            pass

        return total_memory / (1024 * 1024)  # Convert to MB

    def optimize_session_dataframes(self):
        """Optimize all DataFrames stored in session state."""
        if not hasattr(st, 'session_state'):
            return

        optimized_count = 0
        memory_saved = 0

        try:
            for key, value in st.session_state.items():
                if isinstance(value, pd.DataFrame) and not value.empty:
                    original_memory = value.memory_usage(deep=True).sum()
                    optimized_df = self.dataframe_optimizer.optimize_dataframe(value)

                    # Update session state with optimized DataFrame
                    st.session_state[key] = optimized_df

                    new_memory = optimized_df.memory_usage(deep=True).sum()
                    memory_saved += (original_memory - new_memory)
                    optimized_count += 1

        except Exception as e:
            logger.warning(f"Failed to optimize session DataFrames: {e}")

        if optimized_count > 0:
            logger.info(f"Optimized {optimized_count} DataFrames, saved {memory_saved / (1024*1024):.1f} MB")

    def trigger_garbage_collection(self):
        """Trigger garbage collection and memory cleanup."""
        with performance_context("memory_manager", "garbage_collection"):
            # Force garbage collection
            collected = gc.collect()

            # Log memory cleanup
            self.performance_monitor.record_metric(
                "memory_manager",
                "garbage_collected_objects",
                collected
            )

        logger.info(f"Garbage collection freed {collected} objects")

    def check_memory_pressure(self) -> bool:
        """Check if system is under memory pressure."""
        stats = self.get_memory_stats()

        # Check if process memory exceeds threshold
        if stats.process_mb > self.memory_threshold_mb:
            return True

        # Check if system memory usage is high
        if stats.used_percentage > 85:
            return True

        return False

    def handle_memory_pressure(self):
        """Handle memory pressure by optimizing and cleaning up."""
        logger.warning("Memory pressure detected, initiating cleanup...")

        # Optimize session DataFrames
        self.optimize_session_dataframes()

        # Clear caches if available
        try:
            from streamlit_app.core.cache_manager import get_cache_manager
            cache_manager = get_cache_manager()

            # Clear least recently used cache entries
            if hasattr(cache_manager, 'memory_cache'):
                entries_to_remove = []
                for key, entry in cache_manager.memory_cache.items():
                    if entry.cache_type in ['computed_result', 'visualization']:
                        entries_to_remove.append(key)

                for key in entries_to_remove[:10]:  # Remove up to 10 entries
                    cache_manager.memory_cache.pop(key, None)

        except Exception as e:
            logger.warning(f"Failed to clear caches during memory pressure: {e}")

        # Trigger garbage collection
        self.trigger_garbage_collection()

        logger.info("Memory pressure handling completed")

    def get_optimization_recommendations(self, df: pd.DataFrame) -> List[str]:
        """Get memory optimization recommendations for a DataFrame."""
        if df.empty:
            return []

        recommendations = []
        memory_summary = self.dataframe_optimizer.get_memory_usage_summary(df)

        # Check for large object columns
        for column, info in memory_summary["columns"].items():
            if info["dtype"] == "object" and info["percentage"] > 20:
                unique_ratio = df[column].nunique() / len(df)
                if unique_ratio < 0.5:
                    recommendations.append(
                        f"Convert '{column}' to categorical type (current: {info['mb']:.1f}MB)"
                    )

        # Check for oversized numeric types
        for column in df.select_dtypes(include=['int64', 'float64']).columns:
            col_info = memory_summary["columns"][column]
            if col_info["percentage"] > 15:
                recommendations.append(
                    f"Consider downcasting '{column}' to smaller numeric type"
                )

        # Check overall DataFrame size
        if memory_summary["total_mb"] > 50:
            recommendations.append(
                "DataFrame is large (>50MB) - consider data filtering or pagination"
            )

        # Check for duplicate data
        if len(df) != len(df.drop_duplicates()):
            duplicate_count = len(df) - len(df.drop_duplicates())
            recommendations.append(
                f"Remove {duplicate_count} duplicate rows to save memory"
            )

        return recommendations


class LazyDataFrame:
    """
    Lazy-loading DataFrame wrapper for handling large datasets.
    Loads data in chunks and provides transparent access.
    """

    def __init__(self, data_loader: callable, chunk_size: int = 1000):
        self.data_loader = data_loader
        self.chunk_size = chunk_size
        self._cache = {}
        self._total_rows = None

    def __len__(self):
        if self._total_rows is None:
            # Load first chunk to determine size
            self._load_chunk(0)
        return self._total_rows or 0

    def _load_chunk(self, start_index: int) -> pd.DataFrame:
        """Load a chunk of data."""
        chunk_key = start_index // self.chunk_size

        if chunk_key not in self._cache:
            # Load chunk from data source
            chunk_data = self.data_loader(start_index, self.chunk_size)
            self._cache[chunk_key] = chunk_data

            # Update total rows estimate
            if self._total_rows is None and hasattr(chunk_data, '__len__'):
                self._total_rows = len(chunk_data)

        return self._cache[chunk_key]

    def iloc(self, start: int, end: int = None) -> pd.DataFrame:
        """Get rows by integer location."""
        if end is None:
            end = start + 1

        # Determine which chunks we need
        start_chunk = start // self.chunk_size
        end_chunk = (end - 1) // self.chunk_size

        # Load all required chunks
        result_chunks = []
        for chunk_idx in range(start_chunk, end_chunk + 1):
            chunk_start = chunk_idx * self.chunk_size
            chunk = self._load_chunk(chunk_start)
            result_chunks.append(chunk)

        # Combine chunks and slice to exact range
        if result_chunks:
            combined = pd.concat(result_chunks, ignore_index=True)
            local_start = start % self.chunk_size
            local_end = local_start + (end - start)
            return combined.iloc[local_start:local_end]

        return pd.DataFrame()


# Global memory manager instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get the global memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


def optimize_dataframe(df: pd.DataFrame, aggressive: bool = False) -> pd.DataFrame:
    """Optimize DataFrame memory usage."""
    manager = get_memory_manager()
    return manager.dataframe_optimizer.optimize_dataframe(df, aggressive)


def check_memory_and_optimize():
    """Check memory usage and optimize if needed."""
    manager = get_memory_manager()

    if manager.check_memory_pressure():
        manager.handle_memory_pressure()


def display_memory_info():
    """Display memory usage information in Streamlit."""
    manager = get_memory_manager()
    stats = manager.get_memory_stats()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Process Memory", f"{stats.process_mb:.1f} MB")
        st.metric("System Memory", f"{stats.used_percentage:.1f}%")

    with col2:
        st.metric("Available Memory", f"{stats.available_mb:.1f} MB")
        st.metric("DataFrame Memory", f"{stats.dataframe_mb:.1f} MB")

    with col3:
        memory_pressure = manager.check_memory_pressure()
        pressure_color = "🔴" if memory_pressure else "🟢"
        st.metric("Memory Pressure", f"{pressure_color} {'High' if memory_pressure else 'Normal'}")

    # Memory optimization controls
    if st.button("Optimize Memory"):
        with st.spinner("Optimizing memory usage..."):
            manager.optimize_session_dataframes()
            manager.trigger_garbage_collection()
        st.success("Memory optimization completed!")
        st.rerun()


def memory_efficient_dataframe_operation(operation: str):
    """Decorator for memory-efficient DataFrame operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check memory before operation
            check_memory_and_optimize()

            # Execute operation
            result = func(*args, **kwargs)

            # Optimize result if it's a DataFrame
            if isinstance(result, pd.DataFrame):
                result = optimize_dataframe(result)

            return result
        return wrapper
    return decorator