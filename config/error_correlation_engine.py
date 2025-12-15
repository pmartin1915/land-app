"""
Error Correlation Engine for Alabama Auction Watcher
Advanced error correlation and pattern detection system that identifies
relationships between errors across different components and systems.

Features:
- Multi-dimensional error correlation analysis
- Temporal pattern recognition
- Cross-component dependency mapping
- Predictive error cascading detection
- Machine learning-inspired correlation algorithms
- Real-time correlation monitoring
"""

import time
import threading
import numpy as np
from collections import defaultdict, deque
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import json
import hashlib
import statistics
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.ai_logging import get_ai_logger, LogCategory
from config.ai_diagnostics import SystemComponent, HealthStatus, HealthMetrics
from scripts.ai_exceptions import ErrorSeverity, ErrorCategory, RecoveryAction


logger = get_ai_logger(__name__)


class CorrelationType(Enum):
    """Types of error correlations that can be detected."""
    TEMPORAL = "temporal"          # Errors occurring in time sequence
    CAUSAL = "causal"              # Direct cause-effect relationships
    DEPENDENCY = "dependency"      # Component dependency failures
    RESOURCE = "resource"          # Shared resource contention
    CASCADE = "cascade"            # Failure cascading across components
    PERIODIC = "periodic"          # Recurring pattern correlations
    ANOMALY = "anomaly"           # Correlated anomalous behavior
    CONFIGURATION = "configuration" # Configuration-related correlations


@dataclass
class ErrorEvent:
    """Structured error event for correlation analysis."""
    event_id: str
    timestamp: datetime
    component: str
    severity: ErrorSeverity
    category: ErrorCategory
    error_type: str
    error_message: str
    system_context: Dict[str, Any]
    metrics_snapshot: Optional[Dict[str, float]]
    recovery_attempted: bool
    correlation_signature: str  # Hash-based signature for similarity matching


@dataclass
class ErrorCorrelation:
    """Detected error correlation between components or events."""
    correlation_id: str
    correlation_type: CorrelationType
    primary_component: str
    secondary_component: str
    strength: float  # 0.0 to 1.0 correlation strength
    confidence: float  # 0.0 to 1.0 confidence in correlation
    time_window_seconds: float
    frequency: int  # How often this correlation has been observed
    last_observed: datetime
    impact_score: float  # Potential system impact (0.0 to 10.0)

    # Pattern details
    pattern_description: str
    trigger_conditions: List[str]
    predicted_effects: List[str]
    mitigation_strategies: List[str]

    # Statistical measures
    correlation_coefficient: float
    p_value: float  # Statistical significance
    temporal_delay_seconds: float  # Average delay between correlated events


class ErrorCorrelationEngine:
    """
    Advanced error correlation engine using machine learning-inspired techniques
    for detecting complex error patterns and relationships.
    """

    def __init__(self, max_history_size: int = 50000):
        self.logger = get_ai_logger(__name__)
        self.max_history_size = max_history_size

        # Core data structures
        self.error_history = deque(maxlen=max_history_size)
        self.correlation_cache = {}  # correlation_id -> ErrorCorrelation
        self.component_relationships = defaultdict(lambda: defaultdict(list))
        self.temporal_patterns = defaultdict(list)
        self.signature_clusters = defaultdict(list)

        # Configuration
        self.correlation_threshold = 0.7  # Minimum correlation strength to report
        self.confidence_threshold = 0.6   # Minimum confidence to report
        self.max_time_window_seconds = 3600  # 1 hour max correlation window
        self.min_observations = 3  # Minimum observations to establish correlation

        # Analysis windows
        self.analysis_windows = [
            30,    # 30 seconds - immediate cascading
            300,   # 5 minutes - quick propagation
            900,   # 15 minutes - medium-term effects
            3600   # 1 hour - long-term patterns
        ]

        # Thread-safe operations
        self.correlation_lock = threading.Lock()

        # Performance tracking
        self.analysis_stats = {
            'total_correlations_detected': 0,
            'correlations_by_type': defaultdict(int),
            'analysis_run_count': 0,
            'avg_analysis_time_ms': 0.0
        }

    def record_error_event(self, component: str, error_type: str, error_message: str,
                          severity: str = 'medium', category: str = 'system',
                          system_context: Optional[Dict[str, Any]] = None,
                          metrics_snapshot: Optional[Dict[str, float]] = None) -> str:
        """
        Record an error event for correlation analysis.

        Returns:
            str: Event ID for tracking
        """
        event_id = f"event_{int(time.time() * 1000)}_{hash(error_message) % 10000}"

        # Map string enums
        severity_enum = self._map_severity(severity)
        category_enum = self._map_category(category)

        # Generate correlation signature for similarity matching
        signature_data = f"{component}:{error_type}:{category}"
        correlation_signature = hashlib.md5(signature_data.encode()).hexdigest()

        error_event = ErrorEvent(
            event_id=event_id,
            timestamp=datetime.now(),
            component=component,
            severity=severity_enum,
            category=category_enum,
            error_type=error_type,
            error_message=error_message,
            system_context=system_context or {},
            metrics_snapshot=metrics_snapshot,
            recovery_attempted=False,
            correlation_signature=correlation_signature
        )

        # Add to history
        with self.correlation_lock:
            self.error_history.append(error_event)
            self.signature_clusters[correlation_signature].append(error_event)

        # Trigger real-time correlation analysis
        self._trigger_realtime_analysis(error_event)

        self.logger.info(
            f"Error event recorded: {component} - {error_type}",
            extra={
                "category": LogCategory.SYSTEM,
                "event_id": event_id,
                "component": component,
                "error_severity": severity,
                "correlation_signature": correlation_signature
            }
        )

        return event_id

    def _map_severity(self, severity: str) -> ErrorSeverity:
        """Map string severity to enum."""
        mapping = {
            'critical': ErrorSeverity.CRITICAL,
            'high': ErrorSeverity.HIGH,
            'medium': ErrorSeverity.MEDIUM,
            'low': ErrorSeverity.LOW
        }
        return mapping.get(severity.lower(), ErrorSeverity.MEDIUM)

    def _map_category(self, category: str) -> ErrorCategory:
        """Map string category to enum."""
        mapping = {
            'network': ErrorCategory.NETWORK,
            'parsing': ErrorCategory.PARSING,
            'validation': ErrorCategory.VALIDATION,
            'configuration': ErrorCategory.CONFIGURATION,
            'system': ErrorCategory.SYSTEM,
            'business_logic': ErrorCategory.BUSINESS_LOGIC,
            'external_service': ErrorCategory.EXTERNAL_SERVICE,
            'user_input': ErrorCategory.USER_INPUT
        }
        return mapping.get(category.lower(), ErrorCategory.SYSTEM)

    def _trigger_realtime_analysis(self, new_event: ErrorEvent):
        """Trigger real-time correlation analysis for immediate detection."""
        try:
            # Quick analysis for immediate correlations
            recent_events = [e for e in self.error_history
                           if (new_event.timestamp - e.timestamp).total_seconds() <= 300]  # 5 minutes

            if len(recent_events) >= 2:
                immediate_correlations = self._analyze_temporal_correlations(
                    recent_events, time_window_seconds=300
                )

                for correlation in immediate_correlations:
                    if (correlation.strength >= self.correlation_threshold and
                        correlation.confidence >= self.confidence_threshold):
                        self._add_correlation(correlation)

                        # Trigger alert for high-impact immediate correlations
                        if correlation.impact_score >= 7.0:
                            self._trigger_correlation_alert(correlation)

        except Exception as e:
            self.logger.error(f"Real-time correlation analysis failed: {e}")

    def run_comprehensive_analysis(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """
        Run comprehensive correlation analysis across multiple dimensions.

        Args:
            time_window_hours: Analysis time window in hours

        Returns:
            Dict containing analysis results and detected correlations
        """
        analysis_start = time.time()

        self.logger.info(
            f"Starting comprehensive correlation analysis (window: {time_window_hours}h)",
            extra={"category": LogCategory.SYSTEM}
        )

        analysis_results = {
            'analysis_timestamp': datetime.now().isoformat(),
            'time_window_hours': time_window_hours,
            'total_events_analyzed': 0,
            'correlations_detected': [],
            'correlation_summary': {},
            'component_impact_analysis': {},
            'recommendations': [],
            'analysis_performance': {}
        }

        try:
            # Filter events within time window
            cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
            relevant_events = [e for e in self.error_history if e.timestamp >= cutoff_time]
            analysis_results['total_events_analyzed'] = len(relevant_events)

            if len(relevant_events) < 2:
                analysis_results['message'] = 'Insufficient events for correlation analysis'
                return analysis_results

            # Multi-dimensional correlation analysis
            all_correlations = []

            # 1. Temporal correlation analysis
            for window in self.analysis_windows:
                temporal_correlations = self._analyze_temporal_correlations(
                    relevant_events, time_window_seconds=window
                )
                all_correlations.extend(temporal_correlations)

            # 2. Component dependency analysis
            dependency_correlations = self._analyze_dependency_correlations(relevant_events)
            all_correlations.extend(dependency_correlations)

            # 3. Resource contention analysis
            resource_correlations = self._analyze_resource_correlations(relevant_events)
            all_correlations.extend(resource_correlations)

            # 4. Cascade failure analysis
            cascade_correlations = self._analyze_cascade_patterns(relevant_events)
            all_correlations.extend(cascade_correlations)

            # 5. Periodic pattern analysis
            periodic_correlations = self._analyze_periodic_patterns(relevant_events)
            all_correlations.extend(periodic_correlations)

            # 6. Anomaly correlation analysis
            anomaly_correlations = self._analyze_anomaly_correlations(relevant_events)
            all_correlations.extend(anomaly_correlations)

            # Filter and deduplicate correlations
            significant_correlations = self._filter_and_rank_correlations(all_correlations)

            # Update correlation cache
            with self.correlation_lock:
                for correlation in significant_correlations:
                    self._add_correlation(correlation)

            # Generate analysis results
            analysis_results['correlations_detected'] = [
                self._correlation_to_dict(c) for c in significant_correlations
            ]
            analysis_results['correlation_summary'] = self._generate_correlation_summary(significant_correlations)
            analysis_results['component_impact_analysis'] = self._analyze_component_impacts(relevant_events, significant_correlations)
            analysis_results['recommendations'] = self._generate_correlation_recommendations(significant_correlations)

        except Exception as e:
            self.logger.error(f"Comprehensive correlation analysis failed: {e}")
            analysis_results['error'] = str(e)

        # Performance tracking
        analysis_time = time.time() - analysis_start
        analysis_results['analysis_performance'] = {
            'analysis_time_seconds': analysis_time,
            'events_per_second': analysis_results['total_events_analyzed'] / max(analysis_time, 0.001),
            'correlations_per_second': len(analysis_results['correlations_detected']) / max(analysis_time, 0.001)
        }

        # Update stats
        self.analysis_stats['analysis_run_count'] += 1
        current_avg = self.analysis_stats['avg_analysis_time_ms']
        new_time_ms = analysis_time * 1000
        self.analysis_stats['avg_analysis_time_ms'] = (
            (current_avg * (self.analysis_stats['analysis_run_count'] - 1) + new_time_ms)
            / self.analysis_stats['analysis_run_count']
        )

        self.logger.info(
            f"Correlation analysis completed: {len(significant_correlations)} correlations detected",
            extra={
                "category": LogCategory.SYSTEM,
                "analysis_time_seconds": analysis_time,
                "correlations_detected": len(significant_correlations)
            }
        )

        return analysis_results

    def _analyze_temporal_correlations(self, events: List[ErrorEvent],
                                     time_window_seconds: int) -> List[ErrorCorrelation]:
        """Analyze temporal correlations between error events."""
        correlations = []

        # Group events by component
        component_events = defaultdict(list)
        for event in events:
            component_events[event.component].append(event)

        components = list(component_events.keys())

        # Analyze correlations between each pair of components
        for i in range(len(components)):
            for j in range(i + 1, len(components)):
                comp1, comp2 = components[i], components[j]
                events1 = component_events[comp1]
                events2 = component_events[comp2]

                # Find temporal relationships
                temporal_pairs = []

                for e1 in events1:
                    for e2 in events2:
                        time_diff = abs((e2.timestamp - e1.timestamp).total_seconds())
                        if time_diff <= time_window_seconds:
                            temporal_pairs.append((e1, e2, time_diff))

                if len(temporal_pairs) >= self.min_observations:
                    # Calculate correlation strength
                    strength = self._calculate_temporal_strength(temporal_pairs, time_window_seconds)
                    confidence = self._calculate_temporal_confidence(temporal_pairs)

                    if strength >= self.correlation_threshold:
                        correlation = ErrorCorrelation(
                            correlation_id=f"temporal_{comp1}_{comp2}_{int(time.time())}",
                            correlation_type=CorrelationType.TEMPORAL,
                            primary_component=comp1,
                            secondary_component=comp2,
                            strength=strength,
                            confidence=confidence,
                            time_window_seconds=time_window_seconds,
                            frequency=len(temporal_pairs),
                            last_observed=max(e.timestamp for e, _, _ in temporal_pairs),
                            impact_score=self._calculate_impact_score(temporal_pairs),
                            pattern_description=f"Temporal correlation between {comp1} and {comp2} errors",
                            trigger_conditions=[f"{comp1} error occurrence"],
                            predicted_effects=[f"{comp2} error likely within {time_window_seconds}s"],
                            mitigation_strategies=self._generate_temporal_mitigations(comp1, comp2),
                            correlation_coefficient=strength,
                            p_value=max(0.01, 1.0 - confidence),  # Simplified p-value
                            temporal_delay_seconds=statistics.mean(time_diff for _, _, time_diff in temporal_pairs)
                        )
                        correlations.append(correlation)

        return correlations

    def _calculate_temporal_strength(self, temporal_pairs: List[Tuple],
                                   time_window_seconds: int) -> float:
        """Calculate temporal correlation strength."""
        if not temporal_pairs:
            return 0.0

        # Normalize by time window - closer events = stronger correlation
        avg_time_diff = statistics.mean(time_diff for _, _, time_diff in temporal_pairs)
        normalized_time = 1.0 - (avg_time_diff / time_window_seconds)

        # Factor in frequency - more observations = stronger correlation
        frequency_factor = min(1.0, len(temporal_pairs) / 10)  # Normalize to 10 observations

        return (normalized_time * 0.7) + (frequency_factor * 0.3)

    def _calculate_temporal_confidence(self, temporal_pairs: List[Tuple]) -> float:
        """Calculate confidence in temporal correlation."""
        if len(temporal_pairs) < 2:
            return 0.5

        # Higher confidence with more observations and consistent timing
        observation_factor = min(1.0, len(temporal_pairs) / 5)  # Normalize to 5 observations

        # Consistency in timing increases confidence
        time_diffs = [time_diff for _, _, time_diff in temporal_pairs]
        if len(time_diffs) > 1:
            std_dev = statistics.stdev(time_diffs)
            mean_time = statistics.mean(time_diffs)
            consistency_factor = 1.0 - min(1.0, std_dev / max(mean_time, 1))
        else:
            consistency_factor = 0.5

        return (observation_factor * 0.6) + (consistency_factor * 0.4)

    def _analyze_dependency_correlations(self, events: List[ErrorEvent]) -> List[ErrorCorrelation]:
        """Analyze error correlations based on component dependencies."""
        correlations = []

        # Define known component dependencies
        dependencies = self._get_component_dependencies()

        # Analyze errors in dependent components
        for primary, dependents in dependencies.items():
            primary_errors = [e for e in events if e.component == primary]

            for dependent in dependents:
                dependent_errors = [e for e in events if e.component == dependent]

                # Look for dependency-related error patterns
                dependency_pairs = []

                for p_error in primary_errors:
                    for d_error in dependent_errors:
                        time_diff = (d_error.timestamp - p_error.timestamp).total_seconds()
                        # Dependent errors should occur after primary errors
                        if 0 <= time_diff <= 1800:  # Within 30 minutes
                            dependency_pairs.append((p_error, d_error, time_diff))

                if len(dependency_pairs) >= self.min_observations:
                    strength = min(1.0, len(dependency_pairs) / len(primary_errors))
                    confidence = self._calculate_dependency_confidence(dependency_pairs)

                    if strength >= self.correlation_threshold:
                        correlation = ErrorCorrelation(
                            correlation_id=f"dependency_{primary}_{dependent}_{int(time.time())}",
                            correlation_type=CorrelationType.DEPENDENCY,
                            primary_component=primary,
                            secondary_component=dependent,
                            strength=strength,
                            confidence=confidence,
                            time_window_seconds=1800,
                            frequency=len(dependency_pairs),
                            last_observed=max(e.timestamp for e, _, _ in dependency_pairs),
                            impact_score=self._calculate_dependency_impact(dependency_pairs),
                            pattern_description=f"Dependency-based error propagation from {primary} to {dependent}",
                            trigger_conditions=[f"{primary} component failure"],
                            predicted_effects=[f"{dependent} errors due to dependency failure"],
                            mitigation_strategies=self._generate_dependency_mitigations(primary, dependent),
                            correlation_coefficient=strength,
                            p_value=max(0.01, 1.0 - confidence),
                            temporal_delay_seconds=statistics.mean(time_diff for _, _, time_diff in dependency_pairs)
                        )
                        correlations.append(correlation)

        return correlations

    def _get_component_dependencies(self) -> Dict[str, List[str]]:
        """Get known component dependency mappings."""
        return {
            'database': ['data_processor', 'api_server', 'web_scraper'],
            'network': ['web_scraper', 'external_services', 'api_server'],
            'file_system': ['csv_parser', 'data_processor', 'logging_system'],
            'memory': ['data_processor', 'performance_monitor'],
            'cpu': ['all_components'],
            'api_server': ['web_interface', 'mobile_app'],
            'authentication': ['api_server', 'web_interface', 'mobile_app']
        }

    def _calculate_dependency_confidence(self, dependency_pairs: List[Tuple]) -> float:
        """Calculate confidence in dependency correlation."""
        if not dependency_pairs:
            return 0.0

        # Higher confidence with consistent timing patterns
        time_diffs = [time_diff for _, _, time_diff in dependency_pairs]

        if len(time_diffs) > 1:
            # Consistent delays indicate strong dependency relationship
            std_dev = statistics.stdev(time_diffs)
            mean_time = statistics.mean(time_diffs)
            consistency = 1.0 - min(1.0, std_dev / max(mean_time, 1))
        else:
            consistency = 0.7

        # More observations = higher confidence
        observation_factor = min(1.0, len(dependency_pairs) / 3)

        return (consistency * 0.7) + (observation_factor * 0.3)

    def _calculate_dependency_impact(self, dependency_pairs: List[Tuple]) -> float:
        """Calculate impact score for dependency correlations."""
        if not dependency_pairs:
            return 0.0

        # Higher impact for more severe errors and critical components
        severity_scores = {
            ErrorSeverity.CRITICAL: 10.0,
            ErrorSeverity.HIGH: 7.5,
            ErrorSeverity.MEDIUM: 5.0,
            ErrorSeverity.LOW: 2.5
        }

        avg_severity = statistics.mean(
            severity_scores.get(primary.severity, 5.0)
            for primary, _, _ in dependency_pairs
        )

        # Scale by frequency
        frequency_factor = min(1.0, len(dependency_pairs) / 5)

        return avg_severity * frequency_factor

    def _analyze_resource_correlations(self, events: List[ErrorEvent]) -> List[ErrorCorrelation]:
        """Analyze correlations based on shared resource contention."""
        correlations = []

        # Group events by resource-related categories
        resource_events = defaultdict(list)

        for event in events:
            if event.metrics_snapshot:
                # Check for resource-related metrics
                for metric, value in event.metrics_snapshot.items():
                    if any(resource in metric.lower() for resource in ['memory', 'cpu', 'disk', 'network']):
                        resource_type = self._identify_resource_type(metric)
                        if value > self._get_resource_threshold(resource_type):
                            resource_events[resource_type].append(event)

        # Analyze correlations within resource groups
        for resource_type, res_events in resource_events.items():
            if len(res_events) >= self.min_observations:
                # Group by component
                component_groups = defaultdict(list)
                for event in res_events:
                    component_groups[event.component].append(event)

                # Find correlations between components sharing the resource
                components = list(component_groups.keys())
                for i in range(len(components)):
                    for j in range(i + 1, len(components)):
                        comp1, comp2 = components[i], components[j]

                        # Check for simultaneous resource issues
                        simultaneous_events = self._find_simultaneous_resource_events(
                            component_groups[comp1], component_groups[comp2]
                        )

                        if len(simultaneous_events) >= self.min_observations:
                            strength = len(simultaneous_events) / min(len(component_groups[comp1]), len(component_groups[comp2]))
                            confidence = self._calculate_resource_confidence(simultaneous_events, resource_type)

                            if strength >= self.correlation_threshold:
                                correlation = ErrorCorrelation(
                                    correlation_id=f"resource_{resource_type}_{comp1}_{comp2}_{int(time.time())}",
                                    correlation_type=CorrelationType.RESOURCE,
                                    primary_component=comp1,
                                    secondary_component=comp2,
                                    strength=strength,
                                    confidence=confidence,
                                    time_window_seconds=300,  # 5 minute window for resource contention
                                    frequency=len(simultaneous_events),
                                    last_observed=max(e1.timestamp for e1, _ in simultaneous_events),
                                    impact_score=self._calculate_resource_impact(simultaneous_events, resource_type),
                                    pattern_description=f"Resource contention correlation on {resource_type} between {comp1} and {comp2}",
                                    trigger_conditions=[f"High {resource_type} usage in {comp1}"],
                                    predicted_effects=[f"Resource contention affecting {comp2}"],
                                    mitigation_strategies=self._generate_resource_mitigations(resource_type),
                                    correlation_coefficient=strength,
                                    p_value=max(0.01, 1.0 - confidence),
                                    temporal_delay_seconds=0  # Simultaneous for resource contention
                                )
                                correlations.append(correlation)

        return correlations

    def _identify_resource_type(self, metric_name: str) -> str:
        """Identify resource type from metric name."""
        metric_lower = metric_name.lower()
        if 'memory' in metric_lower or 'ram' in metric_lower:
            return 'memory'
        elif 'cpu' in metric_lower or 'processor' in metric_lower:
            return 'cpu'
        elif 'disk' in metric_lower or 'storage' in metric_lower:
            return 'disk'
        elif 'network' in metric_lower or 'bandwidth' in metric_lower:
            return 'network'
        else:
            return 'unknown'

    def _get_resource_threshold(self, resource_type: str) -> float:
        """Get threshold values for resource contention detection."""
        thresholds = {
            'memory': 80.0,    # 80% memory usage
            'cpu': 85.0,       # 85% CPU usage
            'disk': 90.0,      # 90% disk usage
            'network': 1000.0, # 1000 ms latency
            'unknown': 75.0
        }
        return thresholds.get(resource_type, 75.0)

    def _find_simultaneous_resource_events(self, events1: List[ErrorEvent],
                                         events2: List[ErrorEvent]) -> List[Tuple[ErrorEvent, ErrorEvent]]:
        """Find events that occurred simultaneously (within resource contention window)."""
        simultaneous = []
        window_seconds = 60  # 1 minute window for resource correlation

        for e1 in events1:
            for e2 in events2:
                time_diff = abs((e2.timestamp - e1.timestamp).total_seconds())
                if time_diff <= window_seconds:
                    simultaneous.append((e1, e2))

        return simultaneous

    def _calculate_resource_confidence(self, simultaneous_events: List[Tuple], resource_type: str) -> float:
        """Calculate confidence in resource correlation."""
        base_confidence = min(1.0, len(simultaneous_events) / 5)

        # Higher confidence for critical resources
        resource_importance = {
            'memory': 0.9,
            'cpu': 0.9,
            'disk': 0.7,
            'network': 0.8,
            'unknown': 0.5
        }

        importance_factor = resource_importance.get(resource_type, 0.5)
        return base_confidence * importance_factor

    def _calculate_resource_impact(self, simultaneous_events: List[Tuple], resource_type: str) -> float:
        """Calculate impact score for resource correlations."""
        base_impact = len(simultaneous_events)

        # Scale by resource criticality
        resource_criticality = {
            'memory': 2.0,
            'cpu': 2.0,
            'disk': 1.5,
            'network': 1.8,
            'unknown': 1.0
        }

        return min(10.0, base_impact * resource_criticality.get(resource_type, 1.0))

    def _analyze_cascade_patterns(self, events: List[ErrorEvent]) -> List[ErrorCorrelation]:
        """Analyze cascade failure patterns."""
        correlations = []

        # Sort events by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp)

        # Look for cascade patterns (rapid succession of failures)
        cascade_window = 600  # 10 minutes

        for i, primary_event in enumerate(sorted_events):
            cascade_events = [primary_event]

            # Find subsequent events in cascade window
            for j in range(i + 1, len(sorted_events)):
                secondary_event = sorted_events[j]
                time_diff = (secondary_event.timestamp - primary_event.timestamp).total_seconds()

                if time_diff > cascade_window:
                    break  # Outside cascade window

                if secondary_event.component != primary_event.component:
                    cascade_events.append(secondary_event)

            # Analyze if this represents a significant cascade
            if len(cascade_events) >= 3:  # At least 3 components involved
                unique_components = list(set(e.component for e in cascade_events))

                if len(unique_components) >= 3:
                    strength = len(cascade_events) / 10  # Normalize by expected cascade size
                    confidence = self._calculate_cascade_confidence(cascade_events)

                    if strength >= self.correlation_threshold:
                        correlation = ErrorCorrelation(
                            correlation_id=f"cascade_{primary_event.component}_{int(time.time())}",
                            correlation_type=CorrelationType.CASCADE,
                            primary_component=primary_event.component,
                            secondary_component=','.join(unique_components[1:3]),  # Top affected components
                            strength=strength,
                            confidence=confidence,
                            time_window_seconds=cascade_window,
                            frequency=1,  # Each cascade is unique
                            last_observed=cascade_events[-1].timestamp,
                            impact_score=self._calculate_cascade_impact(cascade_events),
                            pattern_description=f"Cascade failure starting from {primary_event.component}",
                            trigger_conditions=[f"{primary_event.component} critical failure"],
                            predicted_effects=[f"System-wide cascade affecting {len(unique_components)} components"],
                            mitigation_strategies=self._generate_cascade_mitigations(),
                            correlation_coefficient=strength,
                            p_value=0.01,  # High significance for cascades
                            temporal_delay_seconds=statistics.mean(
                                (e.timestamp - primary_event.timestamp).total_seconds()
                                for e in cascade_events[1:]
                            )
                        )
                        correlations.append(correlation)

        return correlations

    def _calculate_cascade_confidence(self, cascade_events: List[ErrorEvent]) -> float:
        """Calculate confidence in cascade pattern."""
        # Higher confidence with more components and consistent timing
        component_factor = min(1.0, len(set(e.component for e in cascade_events)) / 5)

        # Check timing consistency
        if len(cascade_events) > 2:
            time_intervals = []
            for i in range(1, len(cascade_events)):
                interval = (cascade_events[i].timestamp - cascade_events[i-1].timestamp).total_seconds()
                time_intervals.append(interval)

            # Consistent intervals suggest real cascade vs random failures
            if time_intervals:
                std_dev = statistics.stdev(time_intervals) if len(time_intervals) > 1 else 0
                mean_interval = statistics.mean(time_intervals)
                timing_consistency = 1.0 - min(1.0, std_dev / max(mean_interval, 1))
            else:
                timing_consistency = 0.5
        else:
            timing_consistency = 0.5

        return (component_factor * 0.6) + (timing_consistency * 0.4)

    def _calculate_cascade_impact(self, cascade_events: List[ErrorEvent]) -> float:
        """Calculate impact score for cascade failures."""
        # Impact based on number of affected components and severity
        unique_components = len(set(e.component for e in cascade_events))
        avg_severity = statistics.mean([
            {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}.get(e.severity.value, 2)
            for e in cascade_events
        ])

        return min(10.0, unique_components * avg_severity * 0.8)

    def _analyze_periodic_patterns(self, events: List[ErrorEvent]) -> List[ErrorCorrelation]:
        """Analyze periodic error patterns."""
        correlations = []

        # Group events by component and error signature
        pattern_groups = defaultdict(list)

        for event in events:
            key = f"{event.component}:{event.correlation_signature}"
            pattern_groups[key].append(event)

        # Analyze each pattern group for periodicity
        for pattern_key, pattern_events in pattern_groups.items():
            if len(pattern_events) >= 4:  # Need minimum events to detect periodicity
                component = pattern_key.split(':')[0]

                # Calculate time intervals between events
                pattern_events.sort(key=lambda e: e.timestamp)
                intervals = []

                for i in range(1, len(pattern_events)):
                    interval = (pattern_events[i].timestamp - pattern_events[i-1].timestamp).total_seconds()
                    intervals.append(interval)

                # Check for periodic pattern
                if self._is_periodic_pattern(intervals):
                    avg_interval = statistics.mean(intervals)

                    # Calculate periodicity strength
                    std_dev = statistics.stdev(intervals) if len(intervals) > 1 else 0
                    strength = 1.0 - min(1.0, std_dev / avg_interval) if avg_interval > 0 else 0
                    confidence = min(1.0, len(intervals) / 10)  # More observations = higher confidence

                    if strength >= self.correlation_threshold:
                        correlation = ErrorCorrelation(
                            correlation_id=f"periodic_{component}_{int(time.time())}",
                            correlation_type=CorrelationType.PERIODIC,
                            primary_component=component,
                            secondary_component=component,  # Self-correlation
                            strength=strength,
                            confidence=confidence,
                            time_window_seconds=avg_interval,
                            frequency=len(pattern_events),
                            last_observed=pattern_events[-1].timestamp,
                            impact_score=self._calculate_periodic_impact(pattern_events),
                            pattern_description=f"Periodic error pattern in {component} (interval: {avg_interval:.0f}s)",
                            trigger_conditions=["Time-based trigger", "Scheduled process execution"],
                            predicted_effects=[f"Next occurrence expected around {avg_interval:.0f}s intervals"],
                            mitigation_strategies=self._generate_periodic_mitigations(avg_interval),
                            correlation_coefficient=strength,
                            p_value=max(0.05, 1.0 - confidence),
                            temporal_delay_seconds=avg_interval
                        )
                        correlations.append(correlation)

        return correlations

    def _is_periodic_pattern(self, intervals: List[float]) -> bool:
        """Check if intervals represent a periodic pattern."""
        if len(intervals) < 3:
            return False

        # Calculate coefficient of variation
        mean_interval = statistics.mean(intervals)
        std_dev = statistics.stdev(intervals)

        # Low coefficient of variation indicates periodicity
        cv = std_dev / mean_interval if mean_interval > 0 else float('inf')
        return cv < 0.3  # 30% variation threshold

    def _calculate_periodic_impact(self, pattern_events: List[ErrorEvent]) -> float:
        """Calculate impact score for periodic patterns."""
        # Impact based on frequency and severity
        frequency_factor = min(5.0, len(pattern_events) / 2)

        avg_severity = statistics.mean([
            {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}.get(e.severity.value, 2)
            for e in pattern_events
        ])

        return frequency_factor * avg_severity * 0.5

    def _analyze_anomaly_correlations(self, events: List[ErrorEvent]) -> List[ErrorCorrelation]:
        """Analyze correlations between anomalous behavior patterns."""
        correlations = []

        # Identify anomalous events (events with unusual patterns)
        anomalous_events = []

        for event in events:
            if self._is_anomalous_event(event):
                anomalous_events.append(event)

        if len(anomalous_events) < 2:
            return correlations

        # Group anomalous events by time windows
        time_window = 1800  # 30 minutes
        anomaly_clusters = []

        for event in anomalous_events:
            # Find other anomalous events in the same time window
            cluster = [event]
            for other_event in anomalous_events:
                if (event != other_event and
                    abs((other_event.timestamp - event.timestamp).total_seconds()) <= time_window):
                    cluster.append(other_event)

            if len(cluster) > 1:
                anomaly_clusters.append(cluster)

        # Analyze clusters for correlations
        for cluster in anomaly_clusters:
            if len(cluster) >= 3:
                components_involved = list(set(e.component for e in cluster))

                if len(components_involved) >= 2:
                    primary_comp = components_involved[0]
                    secondary_comp = components_involved[1]

                    strength = len(cluster) / 10  # Normalize by expected cluster size
                    confidence = self._calculate_anomaly_confidence(cluster)

                    if strength >= self.correlation_threshold:
                        correlation = ErrorCorrelation(
                            correlation_id=f"anomaly_{primary_comp}_{secondary_comp}_{int(time.time())}",
                            correlation_type=CorrelationType.ANOMALY,
                            primary_component=primary_comp,
                            secondary_component=secondary_comp,
                            strength=strength,
                            confidence=confidence,
                            time_window_seconds=time_window,
                            frequency=1,
                            last_observed=max(e.timestamp for e in cluster),
                            impact_score=self._calculate_anomaly_impact(cluster),
                            pattern_description=f"Correlated anomalous behavior between {primary_comp} and {secondary_comp}",
                            trigger_conditions=["Unusual system behavior", "Anomalous conditions"],
                            predicted_effects=["Correlated system anomalies", "Unusual error patterns"],
                            mitigation_strategies=self._generate_anomaly_mitigations(),
                            correlation_coefficient=strength,
                            p_value=0.05,  # Moderate significance
                            temporal_delay_seconds=statistics.mean(
                                abs((e.timestamp - cluster[0].timestamp).total_seconds())
                                for e in cluster[1:]
                            )
                        )
                        correlations.append(correlation)

        return correlations

    def _is_anomalous_event(self, event: ErrorEvent) -> bool:
        """Determine if an event represents anomalous behavior."""
        # Simple anomaly detection based on rarity and context
        signature_events = self.signature_clusters.get(event.correlation_signature, [])

        # Rare signatures are potentially anomalous
        if len(signature_events) <= 2:
            return True

        # Events with unusual timing patterns
        if len(signature_events) > 1:
            time_intervals = []
            sorted_events = sorted(signature_events, key=lambda e: e.timestamp)

            for i in range(1, len(sorted_events)):
                interval = (sorted_events[i].timestamp - sorted_events[i-1].timestamp).total_seconds()
                time_intervals.append(interval)

            if time_intervals:
                current_interval = (event.timestamp - sorted_events[-2].timestamp).total_seconds()
                mean_interval = statistics.mean(time_intervals)

                # Anomalous if significantly different from typical interval
                if abs(current_interval - mean_interval) > mean_interval * 2:
                    return True

        return False

    def _calculate_anomaly_confidence(self, cluster: List[ErrorEvent]) -> float:
        """Calculate confidence in anomaly correlation."""
        # Higher confidence with more components and diverse error types
        unique_components = len(set(e.component for e in cluster))
        unique_error_types = len(set(e.error_type for e in cluster))

        diversity_factor = (unique_components + unique_error_types) / (2 * len(cluster))
        cluster_size_factor = min(1.0, len(cluster) / 5)

        return (diversity_factor * 0.6) + (cluster_size_factor * 0.4)

    def _calculate_anomaly_impact(self, cluster: List[ErrorEvent]) -> float:
        """Calculate impact score for anomaly correlations."""
        # Impact based on cluster size and severity diversity
        size_factor = len(cluster)
        severity_diversity = len(set(e.severity.value for e in cluster))

        return min(10.0, size_factor * severity_diversity * 0.8)

    def _filter_and_rank_correlations(self, correlations: List[ErrorCorrelation]) -> List[ErrorCorrelation]:
        """Filter and rank correlations by significance and impact."""
        # Filter by thresholds
        significant_correlations = [
            c for c in correlations
            if (c.strength >= self.correlation_threshold and
                c.confidence >= self.confidence_threshold)
        ]

        # Remove duplicates (same component pair and type)
        unique_correlations = {}
        for correlation in significant_correlations:
            key = f"{correlation.correlation_type.value}:{correlation.primary_component}:{correlation.secondary_component}"

            if key not in unique_correlations or correlation.strength > unique_correlations[key].strength:
                unique_correlations[key] = correlation

        # Rank by combined score (strength * confidence * impact)
        ranked_correlations = sorted(
            unique_correlations.values(),
            key=lambda c: c.strength * c.confidence * (c.impact_score / 10),
            reverse=True
        )

        return ranked_correlations

    def _add_correlation(self, correlation: ErrorCorrelation):
        """Add correlation to cache and update statistics."""
        self.correlation_cache[correlation.correlation_id] = correlation
        self.analysis_stats['total_correlations_detected'] += 1
        self.analysis_stats['correlations_by_type'][correlation.correlation_type.value] += 1

    def _trigger_correlation_alert(self, correlation: ErrorCorrelation):
        """Trigger alert for high-impact correlations."""
        self.logger.warning(
            f"High-impact correlation detected: {correlation.pattern_description}",
            extra={
                "category": LogCategory.SYSTEM,
                "correlation_id": correlation.correlation_id,
                "correlation_type": correlation.correlation_type.value,
                "impact_score": correlation.impact_score,
                "strength": correlation.strength
            }
        )

    def _correlation_to_dict(self, correlation: ErrorCorrelation) -> Dict[str, Any]:
        """Convert correlation object to dictionary."""
        return {
            'correlation_id': correlation.correlation_id,
            'type': correlation.correlation_type.value,
            'primary_component': correlation.primary_component,
            'secondary_component': correlation.secondary_component,
            'strength': correlation.strength,
            'confidence': correlation.confidence,
            'impact_score': correlation.impact_score,
            'frequency': correlation.frequency,
            'last_observed': correlation.last_observed.isoformat(),
            'pattern_description': correlation.pattern_description,
            'trigger_conditions': correlation.trigger_conditions,
            'predicted_effects': correlation.predicted_effects,
            'mitigation_strategies': correlation.mitigation_strategies,
            'temporal_delay_seconds': correlation.temporal_delay_seconds
        }

    def _generate_correlation_summary(self, correlations: List[ErrorCorrelation]) -> Dict[str, Any]:
        """Generate summary of detected correlations."""
        if not correlations:
            return {}

        # Group by type
        by_type = defaultdict(list)
        for correlation in correlations:
            by_type[correlation.correlation_type.value].append(correlation)

        # Calculate summary statistics
        avg_strength = statistics.mean(c.strength for c in correlations)
        avg_confidence = statistics.mean(c.confidence for c in correlations)
        avg_impact = statistics.mean(c.impact_score for c in correlations)

        # Identify most affected components
        component_involvement = defaultdict(int)
        for correlation in correlations:
            component_involvement[correlation.primary_component] += 1
            component_involvement[correlation.secondary_component] += 1

        most_affected = sorted(component_involvement.items(),
                             key=lambda x: x[1], reverse=True)[:5]

        return {
            'total_correlations': len(correlations),
            'correlations_by_type': {k: len(v) for k, v in by_type.items()},
            'average_strength': round(avg_strength, 3),
            'average_confidence': round(avg_confidence, 3),
            'average_impact_score': round(avg_impact, 2),
            'most_affected_components': most_affected,
            'high_impact_correlations': len([c for c in correlations if c.impact_score >= 7.0])
        }

    def _analyze_component_impacts(self, events: List[ErrorEvent],
                                 correlations: List[ErrorCorrelation]) -> Dict[str, Any]:
        """Analyze impact of correlations on individual components."""
        component_analysis = {}

        # Get all unique components
        all_components = set(e.component for e in events)

        for component in all_components:
            # Count component involvement in correlations
            as_primary = sum(1 for c in correlations if c.primary_component == component)
            as_secondary = sum(1 for c in correlations if c.secondary_component == component)

            # Calculate risk factors
            total_errors = len([e for e in events if e.component == component])
            correlation_involvement = as_primary + as_secondary

            risk_score = (correlation_involvement / max(1, len(correlations))) * 10

            component_analysis[component] = {
                'total_errors': total_errors,
                'correlation_involvement': correlation_involvement,
                'as_primary_cause': as_primary,
                'as_secondary_effect': as_secondary,
                'risk_score': round(risk_score, 2),
                'risk_level': 'high' if risk_score >= 7 else 'medium' if risk_score >= 4 else 'low'
            }

        return component_analysis

    def _generate_correlation_recommendations(self, correlations: List[ErrorCorrelation]) -> List[str]:
        """Generate actionable recommendations based on detected correlations."""
        recommendations = []

        if not correlations:
            recommendations.append("Continue monitoring for error patterns")
            return recommendations

        # High-impact correlations
        high_impact = [c for c in correlations if c.impact_score >= 7.0]
        if high_impact:
            recommendations.append(
                f"URGENT: Address {len(high_impact)} high-impact error correlations immediately"
            )

        # Cascade failures
        cascade_correlations = [c for c in correlations if c.correlation_type == CorrelationType.CASCADE]
        if cascade_correlations:
            recommendations.append(
                "Implement circuit breakers to prevent cascade failures"
            )
            recommendations.append(
                "Review component isolation and fault tolerance"
            )

        # Resource correlations
        resource_correlations = [c for c in correlations if c.correlation_type == CorrelationType.RESOURCE]
        if resource_correlations:
            recommendations.append(
                "Investigate resource contention and consider resource scaling"
            )

        # Dependency correlations
        dependency_correlations = [c for c in correlations if c.correlation_type == CorrelationType.DEPENDENCY]
        if dependency_correlations:
            recommendations.append(
                "Review component dependencies and implement graceful degradation"
            )

        # Periodic patterns
        periodic_correlations = [c for c in correlations if c.correlation_type == CorrelationType.PERIODIC]
        if periodic_correlations:
            recommendations.append(
                "Investigate periodic error patterns - may indicate scheduled processes or external factors"
            )

        # Component-specific recommendations
        most_involved_components = self._get_most_involved_components(correlations)
        for component, involvement_count in most_involved_components[:3]:
            recommendations.append(
                f"Focus monitoring and improvement efforts on {component} (involved in {involvement_count} correlations)"
            )

        return recommendations

    def _get_most_involved_components(self, correlations: List[ErrorCorrelation]) -> List[Tuple[str, int]]:
        """Get components most involved in correlations."""
        involvement = defaultdict(int)

        for correlation in correlations:
            involvement[correlation.primary_component] += 1
            involvement[correlation.secondary_component] += 1

        return sorted(involvement.items(), key=lambda x: x[1], reverse=True)

    def _generate_temporal_mitigations(self, comp1: str, comp2: str) -> List[str]:
        """Generate mitigation strategies for temporal correlations."""
        return [
            f"Monitor {comp1} for early warning signs",
            f"Implement proactive health checks for {comp2}",
            "Add circuit breakers between correlated components",
            "Consider load balancing to reduce correlation"
        ]

    def _generate_dependency_mitigations(self, primary: str, dependent: str) -> List[str]:
        """Generate mitigation strategies for dependency correlations."""
        return [
            f"Implement graceful degradation in {dependent}",
            f"Add redundancy for {primary} component",
            "Implement health checks with automatic failover",
            "Consider service mesh for dependency management"
        ]

    def _generate_resource_mitigations(self, resource_type: str) -> List[str]:
        """Generate mitigation strategies for resource correlations."""
        return [
            f"Scale {resource_type} resources",
            f"Implement {resource_type} usage monitoring",
            "Add resource isolation between components",
            f"Optimize {resource_type} consumption"
        ]

    def _generate_cascade_mitigations(self) -> List[str]:
        """Generate mitigation strategies for cascade failures."""
        return [
            "Implement comprehensive circuit breaker pattern",
            "Add bulkhead isolation between critical components",
            "Implement graceful degradation strategies",
            "Add system-wide health monitoring",
            "Consider chaos engineering testing"
        ]

    def _generate_periodic_mitigations(self, interval_seconds: float) -> List[str]:
        """Generate mitigation strategies for periodic patterns."""
        return [
            f"Investigate processes running every {interval_seconds:.0f} seconds",
            "Review scheduled tasks and cron jobs",
            "Implement staggered execution to reduce load spikes",
            "Add monitoring for periodic resource usage"
        ]

    def _generate_anomaly_mitigations(self) -> List[str]:
        """Generate mitigation strategies for anomaly correlations."""
        return [
            "Implement advanced anomaly detection",
            "Add alerting for unusual error patterns",
            "Review system changes that might cause anomalies",
            "Implement automated anomaly response"
        ]

    def get_correlation_statistics(self) -> Dict[str, Any]:
        """Get comprehensive correlation engine statistics."""
        with self.correlation_lock:
            active_correlations = len(self.correlation_cache)

            # Group by type
            by_type = defaultdict(int)
            impact_scores = []
            strengths = []

            for correlation in self.correlation_cache.values():
                by_type[correlation.correlation_type.value] += 1
                impact_scores.append(correlation.impact_score)
                strengths.append(correlation.strength)

            return {
                'total_events_recorded': len(self.error_history),
                'active_correlations': active_correlations,
                'correlations_by_type': dict(by_type),
                'average_impact_score': statistics.mean(impact_scores) if impact_scores else 0,
                'average_strength': statistics.mean(strengths) if strengths else 0,
                'analysis_statistics': self.analysis_stats.copy(),
                'signature_clusters': len(self.signature_clusters),
                'configuration': {
                    'correlation_threshold': self.correlation_threshold,
                    'confidence_threshold': self.confidence_threshold,
                    'max_time_window_seconds': self.max_time_window_seconds,
                    'min_observations': self.min_observations
                }
            }

    def get_active_correlations(self,
                              correlation_type: Optional[str] = None,
                              min_impact_score: float = 0.0) -> List[Dict[str, Any]]:
        """Get active correlations with optional filtering."""
        with self.correlation_lock:
            correlations = list(self.correlation_cache.values())

        # Apply filters
        if correlation_type:
            correlations = [c for c in correlations if c.correlation_type.value == correlation_type]

        if min_impact_score > 0:
            correlations = [c for c in correlations if c.impact_score >= min_impact_score]

        # Sort by impact score (descending)
        correlations.sort(key=lambda c: c.impact_score, reverse=True)

        return [self._correlation_to_dict(c) for c in correlations]


# Global error correlation engine instance
_error_correlation_engine: Optional[ErrorCorrelationEngine] = None


def get_error_correlation_engine() -> ErrorCorrelationEngine:
    """Get the global error correlation engine instance."""
    global _error_correlation_engine
    if _error_correlation_engine is None:
        _error_correlation_engine = ErrorCorrelationEngine()
    return _error_correlation_engine


def record_error_for_correlation(component: str, error_type: str, error_message: str,
                                severity: str = 'medium', category: str = 'system',
                                system_context: Optional[Dict[str, Any]] = None,
                                metrics_snapshot: Optional[Dict[str, float]] = None) -> str:
    """
    Convenience function to record an error event for correlation analysis.

    Returns:
        str: Event ID for tracking
    """
    engine = get_error_correlation_engine()
    return engine.record_error_event(
        component=component,
        error_type=error_type,
        error_message=error_message,
        severity=severity,
        category=category,
        system_context=system_context,
        metrics_snapshot=metrics_snapshot
    )


async def analyze_error_correlations(time_window_hours: int = 24) -> Dict[str, Any]:
    """
    Run comprehensive error correlation analysis.

    Args:
        time_window_hours: Analysis time window in hours

    Returns:
        Dict containing analysis results and detected correlations
    """
    engine = get_error_correlation_engine()
    return engine.run_comprehensive_analysis(time_window_hours)