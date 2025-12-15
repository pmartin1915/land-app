"""
Streamlit Performance Monitoring Framework for Alabama Auction Watcher

This module provides comprehensive performance monitoring for Streamlit components,
including real-time metrics collection, AI-testable reporting, and automated
performance regression detection.
"""

import time
import psutil
import streamlit as st
import pandas as pd
import threading
import functools
import logging
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from contextlib import contextmanager
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.ai_logging import get_ai_logger, LogCategory
from config.ai_diagnostics import SystemComponent, HealthStatus

logger = get_ai_logger(__name__)


@dataclass
class PerformanceMetric:
    """Individual performance metric data structure."""
    component_name: str
    metric_type: str  # 'execution_time', 'memory_usage', 'api_call', 'render_time'
    value: float
    timestamp: datetime
    session_id: str
    user_context: Dict[str, Any]
    additional_data: Dict[str, Any] = None


@dataclass
class ComponentProfile:
    """Performance profile for a Streamlit component."""
    name: str
    total_executions: int
    total_execution_time: float
    average_execution_time: float
    min_execution_time: float
    max_execution_time: float
    memory_usage_mb: float
    render_count: int
    error_count: int
    last_execution: datetime
    performance_score: float  # 0-100 scale


class StreamlitPerformanceMonitor:
    """
    Comprehensive performance monitoring system for Streamlit applications.

    Features:
    - Real-time performance metrics collection
    - Component-level performance tracking
    - Memory usage monitoring
    - AI-testable performance reporting
    - Automated regression detection
    """

    def __init__(self, max_metrics_history: int = 10000):
        self.max_metrics_history = max_metrics_history
        self.metrics_history: deque = deque(maxlen=max_metrics_history)
        self.component_profiles: Dict[str, ComponentProfile] = {}
        self.session_metrics: Dict[str, List[PerformanceMetric]] = defaultdict(list)

        # Performance thresholds for alerting
        self.performance_thresholds = {
            'execution_time_warning': 2.0,  # seconds
            'execution_time_critical': 5.0,  # seconds
            'memory_usage_warning': 100.0,  # MB
            'memory_usage_critical': 250.0,  # MB
            'render_time_warning': 1.0,     # seconds
            'render_time_critical': 3.0     # seconds
        }

        # Background monitoring thread
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        self.start_background_monitoring()

    def get_session_id(self) -> str:
        """Get current Streamlit session ID."""
        try:
            from streamlit.runtime.scriptrunner import get_script_run_ctx
            ctx = get_script_run_ctx()
            return ctx.session_id if ctx else "unknown"
        except:
            return "unknown"

    def record_metric(self, component_name: str, metric_type: str, value: float,
                     additional_data: Dict[str, Any] = None):
        """Record a performance metric."""
        session_id = self.get_session_id()

        metric = PerformanceMetric(
            component_name=component_name,
            metric_type=metric_type,
            value=value,
            timestamp=datetime.now(),
            session_id=session_id,
            user_context=self._get_user_context(),
            additional_data=additional_data or {}
        )

        self.metrics_history.append(metric)
        self.session_metrics[session_id].append(metric)

        # Update component profile
        self._update_component_profile(component_name, metric)

        # Check for performance issues
        self._check_performance_thresholds(metric)

    def _get_user_context(self) -> Dict[str, Any]:
        """Get current user context from Streamlit session state."""
        context = {
            "timestamp": datetime.now().isoformat(),
            "page": "unknown"
        }

        try:
            if hasattr(st, 'session_state'):
                # Extract relevant context from session state
                if hasattr(st.session_state, 'current_filters'):
                    context['filters'] = st.session_state.current_filters
                if hasattr(st.session_state, 'current_page'):
                    context['page'] = st.session_state.current_page
                if hasattr(st.session_state, 'data_size'):
                    context['data_size'] = st.session_state.data_size
        except Exception as e:
            logger.warning(f"Failed to extract user context: {e}")

        return context

    def _update_component_profile(self, component_name: str, metric: PerformanceMetric):
        """Update component performance profile."""
        if component_name not in self.component_profiles:
            self.component_profiles[component_name] = ComponentProfile(
                name=component_name,
                total_executions=0,
                total_execution_time=0.0,
                average_execution_time=0.0,
                min_execution_time=float('inf'),
                max_execution_time=0.0,
                memory_usage_mb=0.0,
                render_count=0,
                error_count=0,
                last_execution=datetime.now(),
                performance_score=100.0
            )

        profile = self.component_profiles[component_name]

        if metric.metric_type == 'execution_time':
            profile.total_executions += 1
            profile.total_execution_time += metric.value
            profile.average_execution_time = profile.total_execution_time / profile.total_executions
            profile.min_execution_time = min(profile.min_execution_time, metric.value)
            profile.max_execution_time = max(profile.max_execution_time, metric.value)
            profile.last_execution = metric.timestamp

        elif metric.metric_type == 'memory_usage':
            profile.memory_usage_mb = metric.value

        elif metric.metric_type == 'render_time':
            profile.render_count += 1

        elif metric.metric_type == 'error':
            profile.error_count += 1

        # Calculate performance score (0-100)
        profile.performance_score = self._calculate_performance_score(profile)

    def _calculate_performance_score(self, profile: ComponentProfile) -> float:
        """Calculate a performance score for a component (0-100 scale)."""
        score = 100.0

        # Penalize slow execution times
        if profile.average_execution_time > self.performance_thresholds['execution_time_warning']:
            score -= 20
        if profile.average_execution_time > self.performance_thresholds['execution_time_critical']:
            score -= 30

        # Penalize high memory usage
        if profile.memory_usage_mb > self.performance_thresholds['memory_usage_warning']:
            score -= 15
        if profile.memory_usage_mb > self.performance_thresholds['memory_usage_critical']:
            score -= 25

        # Penalize errors
        if profile.error_count > 0 and profile.total_executions > 0:
            error_rate = profile.error_count / profile.total_executions
            score -= error_rate * 50

        return max(0.0, score)

    def _check_performance_thresholds(self, metric: PerformanceMetric):
        """Check if metric exceeds performance thresholds and alert if necessary."""
        component = metric.component_name
        value = metric.value
        metric_type = metric.metric_type

        alert_level = None

        if metric_type == 'execution_time':
            if value > self.performance_thresholds['execution_time_critical']:
                alert_level = 'critical'
            elif value > self.performance_thresholds['execution_time_warning']:
                alert_level = 'warning'

        elif metric_type == 'memory_usage':
            if value > self.performance_thresholds['memory_usage_critical']:
                alert_level = 'critical'
            elif value > self.performance_thresholds['memory_usage_warning']:
                alert_level = 'warning'

        if alert_level:
            self._send_performance_alert(metric, alert_level)

    def _send_performance_alert(self, metric: PerformanceMetric, level: str):
        """Send performance alert through AI logging system."""
        alert_data = {
            "alert_type": "performance_threshold_exceeded",
            "component": metric.component_name,
            "metric_type": metric.metric_type,
            "value": metric.value,
            "threshold_level": level,
            "session_id": metric.session_id,
            "user_context": metric.user_context,
            "timestamp": metric.timestamp.isoformat(),
            "additional_data": metric.additional_data
        }

        if level == 'critical':
            logger.error(
                f"Critical performance issue in {metric.component_name}",
                extra={
                    "category": LogCategory.PERFORMANCE,
                    "ai_actionable": True,
                    "recovery_suggestions": [
                        "Check component implementation for efficiency",
                        "Consider caching strategies",
                        "Review data size and processing complexity"
                    ],
                    **alert_data
                }
            )
        else:
            logger.warning(
                f"Performance warning in {metric.component_name}",
                extra={
                    "category": LogCategory.PERFORMANCE,
                    "ai_actionable": True,
                    **alert_data
                }
            )

    def start_background_monitoring(self):
        """Start background system monitoring."""
        if self._monitoring_thread is None or not self._monitoring_thread.is_alive():
            self._stop_monitoring.clear()
            self._monitoring_thread = threading.Thread(
                target=self._background_monitoring_loop,
                daemon=True
            )
            self._monitoring_thread.start()

    def _background_monitoring_loop(self):
        """Background monitoring loop for system metrics."""
        while not self._stop_monitoring.is_set():
            try:
                # Record system metrics
                process = psutil.Process()

                # Memory usage
                memory_mb = process.memory_info().rss / 1024 / 1024
                self.record_metric("system", "memory_usage", memory_mb)

                # CPU usage
                cpu_percent = process.cpu_percent()
                self.record_metric("system", "cpu_usage", cpu_percent)

                # Sleep for monitoring interval
                self._stop_monitoring.wait(10)  # 10-second intervals

            except Exception as e:
                logger.error(f"Background monitoring error: {e}")
                self._stop_monitoring.wait(30)  # Wait longer on error

    def stop_monitoring(self):
        """Stop background monitoring."""
        self._stop_monitoring.set()
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary for AI analysis."""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_metrics": len(self.metrics_history),
            "active_sessions": len(self.session_metrics),
            "component_count": len(self.component_profiles),
            "components": {}
        }

        # Component summaries
        for name, profile in self.component_profiles.items():
            summary["components"][name] = asdict(profile)

        # Recent performance trends
        recent_metrics = [m for m in self.metrics_history
                         if m.timestamp > datetime.now() - timedelta(minutes=30)]

        if recent_metrics:
            # Calculate trend statistics
            execution_times = [m.value for m in recent_metrics if m.metric_type == 'execution_time']
            memory_usage = [m.value for m in recent_metrics if m.metric_type == 'memory_usage']

            summary["recent_trends"] = {
                "avg_execution_time": sum(execution_times) / len(execution_times) if execution_times else 0,
                "max_execution_time": max(execution_times) if execution_times else 0,
                "avg_memory_usage": sum(memory_usage) / len(memory_usage) if memory_usage else 0,
                "max_memory_usage": max(memory_usage) if memory_usage else 0
            }

        return summary

    def get_metrics_dataframe(self, component_name: Optional[str] = None,
                             hours: int = 24) -> pd.DataFrame:
        """Get metrics as a pandas DataFrame for analysis."""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        # Filter metrics
        filtered_metrics = [
            m for m in self.metrics_history
            if m.timestamp > cutoff_time and (
                component_name is None or m.component_name == component_name
            )
        ]

        if not filtered_metrics:
            return pd.DataFrame()

        # Convert to DataFrame
        data = []
        for metric in filtered_metrics:
            row = {
                'component_name': metric.component_name,
                'metric_type': metric.metric_type,
                'value': metric.value,
                'timestamp': metric.timestamp,
                'session_id': metric.session_id
            }
            # Add user context as separate columns
            for key, value in metric.user_context.items():
                row[f'context_{key}'] = value

            data.append(row)

        return pd.DataFrame(data)

    def generate_performance_report(self) -> str:
        """Generate AI-readable performance report."""
        summary = self.get_performance_summary()

        report_lines = [
            "=== STREAMLIT PERFORMANCE REPORT ===",
            f"Generated: {summary['timestamp']}",
            f"Total Metrics Collected: {summary['total_metrics']:,}",
            f"Active Sessions: {summary['active_sessions']}",
            f"Components Monitored: {summary['component_count']}",
            "",
            "=== COMPONENT PERFORMANCE SUMMARY ==="
        ]

        # Sort components by performance score
        components = list(summary['components'].items())
        components.sort(key=lambda x: x[1]['performance_score'], reverse=True)

        for name, profile in components:
            report_lines.extend([
                f"Component: {name}",
                f"  Performance Score: {profile['performance_score']:.1f}/100",
                f"  Avg Execution Time: {profile['average_execution_time']:.3f}s",
                f"  Memory Usage: {profile['memory_usage_mb']:.1f}MB",
                f"  Total Executions: {profile['total_executions']}",
                f"  Error Count: {profile['error_count']}",
                ""
            ])

        if "recent_trends" in summary:
            trends = summary["recent_trends"]
            report_lines.extend([
                "=== RECENT PERFORMANCE TRENDS (30 min) ===",
                f"Avg Execution Time: {trends['avg_execution_time']:.3f}s",
                f"Max Execution Time: {trends['max_execution_time']:.3f}s",
                f"Avg Memory Usage: {trends['avg_memory_usage']:.1f}MB",
                f"Max Memory Usage: {trends['max_memory_usage']:.1f}MB"
            ])

        return "\n".join(report_lines)

    def get_component_profile(self, component_name: str) -> Optional[ComponentProfile]:
        """Get component performance profile."""
        return self.component_profiles.get(component_name)

    def check_component_health(self, component_name: str):
        """Check component health status."""
        from config.ai_diagnostics import HealthStatus

        profile = self.get_component_profile(component_name)
        if not profile:
            return type('HealthCheck', (), {'status': HealthStatus.UNKNOWN})()

        # Simple health check based on performance score
        if profile.performance_score > 80:
            status = HealthStatus.HEALTHY
        elif profile.performance_score > 60:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.CRITICAL

        return type('HealthCheck', (), {'status': status})()

    @contextmanager
    def monitor_context(self, component_name: str, operation: str = "operation"):
        """Context manager for monitoring performance of code blocks."""
        start_time = time.time()

        # Record memory before
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024

        try:
            yield

            # Record successful execution
            execution_time = time.time() - start_time
            self.record_metric(f"{component_name}_{operation}", "execution_time", execution_time)

            # Record memory usage
            memory_after = process.memory_info().rss / 1024 / 1024
            memory_delta = memory_after - memory_before
            self.record_metric(f"{component_name}_{operation}", "memory_usage", memory_after)
            self.record_metric(f"{component_name}_{operation}", "memory_delta", memory_delta)

        except Exception as e:
            # Record error
            execution_time = time.time() - start_time
            self.record_metric(f"{component_name}_{operation}", "error", 1, {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "execution_time": execution_time
            })
            raise

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics for launcher integration."""
        try:
            # Get current system metrics
            memory_info = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # Calculate recent component performance
            recent_metrics = []
            cutoff_time = datetime.now() - timedelta(minutes=5)

            for metric in self.metrics_history:
                if metric.timestamp >= cutoff_time:
                    recent_metrics.append(metric)

            # Component-level aggregations
            component_stats = defaultdict(lambda: {'count': 0, 'total_time': 0.0, 'errors': 0})

            for metric in recent_metrics:
                component_stats[metric.component_name]['count'] += 1
                if metric.metric_type == 'execution_time':
                    component_stats[metric.component_name]['total_time'] += metric.value
                elif metric.metric_type == 'error':
                    component_stats[metric.component_name]['errors'] += 1

            # Overall system health score (0-100)
            health_score = 100.0
            if cpu_percent > 80:
                health_score -= 20
            if memory_info.percent > 85:
                health_score -= 20
            if any(stats['errors'] > 0 for stats in component_stats.values()):
                health_score -= 10

            return {
                'system_memory_percent': memory_info.percent,
                'system_memory_mb': memory_info.used / (1024 * 1024),
                'system_cpu_percent': cpu_percent,
                'total_metrics_collected': len(self.metrics_history),
                'recent_metrics_count': len(recent_metrics),
                'active_components': len(component_stats),
                'components_with_errors': sum(1 for stats in component_stats.values() if stats['errors'] > 0),
                'avg_execution_time': sum(stats['total_time'] / max(stats['count'], 1) for stats in component_stats.values() if stats['count'] > 0) / max(len(component_stats), 1) if component_stats else 0.0,
                'health_score': max(0, health_score),
                'last_measurement': datetime.now().isoformat(),
                'component_profiles': {name: {
                    'executions': stats['count'],
                    'avg_time': stats['total_time'] / max(stats['count'], 1),
                    'error_count': stats['errors']
                } for name, stats in component_stats.items()},
                'status': 'active' if recent_metrics else 'inactive'
            }

        except Exception as e:
            logger.error(f"Error getting current metrics: {e}")
            return {
                'system_memory_percent': 0,
                'system_memory_mb': 0,
                'system_cpu_percent': 0,
                'total_metrics_collected': 0,
                'recent_metrics_count': 0,
                'active_components': 0,
                'components_with_errors': 0,
                'avg_execution_time': 0.0,
                'health_score': 0,
                'last_measurement': datetime.now().isoformat(),
                'component_profiles': {},
                'status': 'error'
            }


# Global monitor instance
_performance_monitor: Optional[StreamlitPerformanceMonitor] = None


def get_performance_monitor() -> StreamlitPerformanceMonitor:
    """Get the global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = StreamlitPerformanceMonitor()
    return _performance_monitor


def monitor_performance(component_name: str = None, include_memory: bool = True):
    """
    Decorator to monitor the performance of Streamlit functions.

    Args:
        component_name: Name of the component (auto-detected if None)
        include_memory: Whether to include memory usage monitoring
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            comp_name = component_name or func.__name__

            # Record memory before execution
            if include_memory:
                process = psutil.Process()
                memory_before = process.memory_info().rss / 1024 / 1024

            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                # Record successful execution
                execution_time = time.time() - start_time
                monitor.record_metric(comp_name, "execution_time", execution_time)

                # Record memory usage
                if include_memory:
                    memory_after = process.memory_info().rss / 1024 / 1024
                    memory_delta = memory_after - memory_before
                    monitor.record_metric(comp_name, "memory_usage", memory_after)
                    monitor.record_metric(comp_name, "memory_delta", memory_delta)

                return result

            except Exception as e:
                # Record error
                execution_time = time.time() - start_time
                monitor.record_metric(comp_name, "error", 1, {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "execution_time": execution_time
                })
                raise

        return wrapper
    return decorator


@contextmanager
def performance_context(component_name: str, operation: str = "operation"):
    """Context manager for monitoring performance of code blocks."""
    monitor = get_performance_monitor()
    start_time = time.time()

    # Record memory before
    process = psutil.Process()
    memory_before = process.memory_info().rss / 1024 / 1024

    try:
        yield

        # Record successful execution
        execution_time = time.time() - start_time
        monitor.record_metric(f"{component_name}_{operation}", "execution_time", execution_time)

        # Record memory usage
        memory_after = process.memory_info().rss / 1024 / 1024
        memory_delta = memory_after - memory_before
        monitor.record_metric(f"{component_name}_{operation}", "memory_usage", memory_after)
        monitor.record_metric(f"{component_name}_{operation}", "memory_delta", memory_delta)

    except Exception as e:
        # Record error
        execution_time = time.time() - start_time
        monitor.record_metric(f"{component_name}_{operation}", "error", 1, {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "execution_time": execution_time
        })
        raise


def display_performance_metrics():
    """Display performance metrics in Streamlit sidebar (for debugging)."""
    if st.sidebar.checkbox("Show Performance Metrics", value=False):
        monitor = get_performance_monitor()

        with st.sidebar.expander("Performance Dashboard"):
            summary = monitor.get_performance_summary()

            st.subheader("System Status")
            st.metric("Total Metrics", summary["total_metrics"])
            st.metric("Active Sessions", summary["active_sessions"])
            st.metric("Components", summary["component_count"])

            # Component performance
            if summary["components"]:
                st.subheader("Component Performance")
                components_df = pd.DataFrame([
                    {
                        "Component": name,
                        "Score": profile["performance_score"],
                        "Avg Time (s)": profile["average_execution_time"],
                        "Memory (MB)": profile["memory_usage_mb"],
                        "Executions": profile["total_executions"]
                    }
                    for name, profile in summary["components"].items()
                ])
                st.dataframe(components_df, use_container_width=True)

            # Download performance report
            if st.button("Download Performance Report"):
                report = monitor.generate_performance_report()
                st.download_button(
                    label="Download Report",
                    data=report,
                    file_name=f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )