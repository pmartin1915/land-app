"""
Enhanced Error Detection Patterns for AI Testing Framework
Alabama Auction Watcher - Advanced Error Pattern Recognition

This module provides advanced error detection capabilities including:
- ML-based error pattern recognition
- Predictive failure analysis
- Cross-component error correlation
- Automated error classification and recovery suggestions

Author: Claude Code AI Assistant
Date: 2025-09-21
Version: 1.1.0
"""

import pandas as pd
import numpy as np
import time
import json
import hashlib
import threading
from typing import Dict, Any, List, Optional, Callable, Union, Tuple, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
import logging
from collections import defaultdict, deque
import re
import sys
from enum import Enum

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.ai_logging import get_ai_logger, LogCategory
from config.ai_diagnostics import SystemComponent, HealthStatus
from streamlit_app.core.performance_monitor import get_performance_monitor
from streamlit_app.testing.ai_testability import TestResult, TestScenario

logger = get_ai_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for classification."""
    CRITICAL = "critical"      # System breaking errors
    HIGH = "high"              # Component failure errors
    MEDIUM = "medium"          # Performance degradation
    LOW = "low"                # Minor issues
    INFO = "info"              # Informational patterns


class ErrorCategory(Enum):
    """Error categorization for pattern analysis."""
    PERFORMANCE = "performance"        # Slow execution, memory issues
    DATA_INTEGRITY = "data_integrity"  # Missing/corrupted data
    INTEGRATION = "integration"        # Component interaction issues
    USER_INPUT = "user_input"          # Input validation failures
    SYSTEM_RESOURCE = "system_resource" # Memory, CPU, disk issues
    NETWORK = "network"                # API, database connectivity
    CONFIGURATION = "configuration"    # Settings, environment issues
    UNKNOWN = "unknown"                # Unclassified errors


@dataclass
class ErrorPattern:
    """Detected error pattern with context."""
    pattern_id: str
    pattern_type: str
    description: str
    error_signature: str
    severity: ErrorSeverity
    category: ErrorCategory
    frequency: int
    first_seen: datetime
    last_seen: datetime
    affected_components: List[str]
    recovery_actions: List[str]
    prediction_confidence: float  # 0-1 how likely this pattern will recur


@dataclass
class PredictiveAlert:
    """Predictive failure alert based on pattern analysis."""
    alert_id: str
    predicted_failure_type: str
    confidence_score: float  # 0-1
    time_to_failure_estimate: timedelta
    affected_components: List[str]
    preventive_actions: List[str]
    risk_factors: List[str]
    generated_at: datetime


@dataclass
class ErrorAnalysisResult:
    """Result of comprehensive error analysis."""
    total_errors_analyzed: int
    patterns_identified: List[ErrorPattern]
    predictive_alerts: List[PredictiveAlert]
    component_health_scores: Dict[str, float]
    recommendations: List[str]
    analysis_timestamp: datetime


class EnhancedErrorDetector:
    """
    Advanced error detection system with ML-inspired pattern recognition.

    Features:
    - Real-time error pattern detection
    - Predictive failure analysis
    - Cross-component error correlation
    - Automated recovery suggestions
    - Error trend analysis
    """

    def __init__(self, history_window_hours: int = 24):
        self.history_window_hours = history_window_hours
        self.error_history: deque = deque(maxlen=10000)  # Store recent errors
        self.pattern_cache: Dict[str, ErrorPattern] = {}
        self.component_health_cache: Dict[str, float] = {}

        # Error signature patterns for classification
        self.error_signatures = {
            ErrorCategory.PERFORMANCE: [
                r"execution.*time.*exceed",
                r"timeout.*error",
                r"slow.*response",
                r"memory.*limit",
                r"cpu.*usage.*high"
            ],
            ErrorCategory.DATA_INTEGRITY: [
                r"missing.*column",
                r"null.*value",
                r"data.*corruption",
                r"validation.*failed",
                r"schema.*mismatch"
            ],
            ErrorCategory.INTEGRATION: [
                r"connection.*failed",
                r"api.*error",
                r"service.*unavailable",
                r"authentication.*failed",
                r"dependency.*missing"
            ],
            ErrorCategory.USER_INPUT: [
                r"invalid.*input",
                r"filter.*error",
                r"parameter.*invalid",
                r"format.*incorrect"
            ],
            ErrorCategory.SYSTEM_RESOURCE: [
                r"out.*of.*memory",
                r"disk.*space.*full",
                r"resource.*exhausted",
                r"quota.*exceeded"
            ],
            ErrorCategory.NETWORK: [
                r"network.*error",
                r"dns.*resolution",
                r"connection.*refused",
                r"request.*timeout"
            ],
            ErrorCategory.CONFIGURATION: [
                r"configuration.*error",
                r"environment.*variable",
                r"setting.*invalid",
                r"permission.*denied"
            ]
        }

        # Recovery action templates
        self.recovery_templates = {
            ErrorCategory.PERFORMANCE: [
                "Optimize data processing algorithms",
                "Implement intelligent caching",
                "Add pagination for large datasets",
                "Review memory usage patterns"
            ],
            ErrorCategory.DATA_INTEGRITY: [
                "Add data validation checks",
                "Implement data cleaning pipelines",
                "Add null value handling",
                "Create data schema validation"
            ],
            ErrorCategory.INTEGRATION: [
                "Implement retry mechanisms",
                "Add circuit breaker patterns",
                "Create fallback data sources",
                "Improve error handling"
            ],
            ErrorCategory.USER_INPUT: [
                "Add input validation",
                "Improve user interface feedback",
                "Create input sanitization",
                "Add helpful error messages"
            ],
            ErrorCategory.SYSTEM_RESOURCE: [
                "Implement resource monitoring",
                "Add resource cleanup routines",
                "Optimize memory usage",
                "Add disk space monitoring"
            ],
            ErrorCategory.NETWORK: [
                "Implement connection pooling",
                "Add retry with exponential backoff",
                "Create offline mode capabilities",
                "Improve timeout handling"
            ],
            ErrorCategory.CONFIGURATION: [
                "Add configuration validation",
                "Create configuration templates",
                "Implement environment detection",
                "Add permission checks"
            ]
        }

        # Start background analysis
        self._start_background_analysis()

    def analyze_test_results(self, test_results: List[TestResult]) -> ErrorAnalysisResult:
        """
        Perform comprehensive error analysis on test results.

        Args:
            test_results: List of test results to analyze

        Returns:
            ErrorAnalysisResult with patterns, alerts, and recommendations
        """
        logger.info(f"Starting enhanced error analysis on {len(test_results)} test results")

        # Extract errors from test results
        errors = self._extract_errors_from_results(test_results)

        # Add to error history
        for error in errors:
            self.error_history.append(error)

        # Detect patterns
        patterns = self._detect_error_patterns(errors)

        # Generate predictive alerts
        alerts = self._generate_predictive_alerts(patterns)

        # Calculate component health scores
        health_scores = self._calculate_component_health_scores(test_results)

        # Generate recommendations
        recommendations = self._generate_recommendations(patterns, alerts, health_scores)

        result = ErrorAnalysisResult(
            total_errors_analyzed=len(errors),
            patterns_identified=patterns,
            predictive_alerts=alerts,
            component_health_scores=health_scores,
            recommendations=recommendations,
            analysis_timestamp=datetime.now()
        )

        logger.info(f"Error analysis completed: {len(patterns)} patterns, {len(alerts)} alerts")

        return result

    def _extract_errors_from_results(self, test_results: List[TestResult]) -> List[Dict[str, Any]]:
        """Extract error information from test results."""
        errors = []

        for result in test_results:
            if not result.success or result.error_details:
                error_data = {
                    'timestamp': result.executed_at,
                    'component': result.scenario.component_name,
                    'test_type': result.scenario.test_type,
                    'error_message': result.error_details or 'Test failure',
                    'deviations': result.deviations,
                    'execution_time': result.execution_time,
                    'performance_metrics': result.performance_metrics,
                    'scenario_id': result.scenario.scenario_id
                }
                errors.append(error_data)

        return errors

    def _detect_error_patterns(self, errors: List[Dict[str, Any]]) -> List[ErrorPattern]:
        """Detect patterns in error data using advanced analysis."""
        patterns = []

        # Group errors by signature
        error_groups = defaultdict(list)

        for error in errors:
            signature = self._generate_error_signature(error)
            error_groups[signature].append(error)

        # Analyze each group for patterns
        for signature, group_errors in error_groups.items():
            if len(group_errors) >= 2:  # Pattern requires at least 2 occurrences
                pattern = self._create_pattern_from_group(signature, group_errors)
                patterns.append(pattern)

        # Sort by severity and frequency
        patterns.sort(key=lambda p: (p.severity.value, -p.frequency))

        return patterns

    def _generate_error_signature(self, error: Dict[str, Any]) -> str:
        """Generate a unique signature for error pattern matching."""
        # Normalize error message for pattern matching
        message = str(error.get('error_message', '')).lower()
        component = error.get('component', 'unknown')
        test_type = error.get('test_type', 'unknown')

        # Remove variable parts (numbers, timestamps, etc.)
        normalized_message = re.sub(r'\d+', 'N', message)
        normalized_message = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', 'DATE', normalized_message)
        normalized_message = re.sub(r'\b\d{2}:\d{2}:\d{2}\b', 'TIME', normalized_message)

        # Create signature
        signature_data = f"{component}:{test_type}:{normalized_message[:100]}"
        return hashlib.md5(signature_data.encode()).hexdigest()[:12]

    def _create_pattern_from_group(self, signature: str, errors: List[Dict[str, Any]]) -> ErrorPattern:
        """Create an error pattern from a group of similar errors."""
        first_error = errors[0]
        last_error = errors[-1]

        # Determine category and severity
        category = self._classify_error_category(first_error['error_message'])
        severity = self._determine_error_severity(errors)

        # Extract affected components
        affected_components = list(set(e.get('component', 'unknown') for e in errors))

        # Generate recovery actions
        recovery_actions = self._generate_recovery_actions(category, errors)

        # Calculate prediction confidence based on pattern consistency
        prediction_confidence = self._calculate_prediction_confidence(errors)

        pattern = ErrorPattern(
            pattern_id=signature,
            pattern_type=f"{category.value}_pattern",
            description=self._generate_pattern_description(errors, category),
            error_signature=signature,
            severity=severity,
            category=category,
            frequency=len(errors),
            first_seen=min(e['timestamp'] for e in errors),
            last_seen=max(e['timestamp'] for e in errors),
            affected_components=affected_components,
            recovery_actions=recovery_actions,
            prediction_confidence=prediction_confidence
        )

        # Cache the pattern
        self.pattern_cache[signature] = pattern

        return pattern

    def _classify_error_category(self, error_message: str) -> ErrorCategory:
        """Classify error into category using pattern matching."""
        message_lower = error_message.lower()

        for category, patterns in self.error_signatures.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return category

        return ErrorCategory.UNKNOWN

    def _determine_error_severity(self, errors: List[Dict[str, Any]]) -> ErrorSeverity:
        """Determine severity based on error characteristics."""
        frequency = len(errors)
        avg_exec_time = np.mean([e.get('execution_time', 0) for e in errors])

        # Check for critical indicators
        has_crash = any('crash' in str(e.get('error_message', '')).lower() for e in errors)
        has_timeout = any('timeout' in str(e.get('error_message', '')).lower() for e in errors)

        if has_crash or frequency > 10:
            return ErrorSeverity.CRITICAL
        elif has_timeout or frequency > 5 or avg_exec_time > 5.0:
            return ErrorSeverity.HIGH
        elif frequency > 2 or avg_exec_time > 2.0:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW

    def _generate_recovery_actions(self, category: ErrorCategory, errors: List[Dict[str, Any]]) -> List[str]:
        """Generate specific recovery actions for the error pattern."""
        base_actions = self.recovery_templates.get(category, [])

        # Add specific actions based on error details
        specific_actions = []

        if category == ErrorCategory.PERFORMANCE:
            avg_time = np.mean([e.get('execution_time', 0) for e in errors])
            if avg_time > 3.0:
                specific_actions.append(f"Optimize component performance (current avg: {avg_time:.2f}s)")

        elif category == ErrorCategory.DATA_INTEGRITY:
            if any('null' in str(e.get('error_message', '')).lower() for e in errors):
                specific_actions.append("Implement null value checks and default handling")

        return base_actions + specific_actions

    def _calculate_prediction_confidence(self, errors: List[Dict[str, Any]]) -> float:
        """Calculate confidence that this pattern will recur."""
        frequency = len(errors)
        time_span = (max(e['timestamp'] for e in errors) - min(e['timestamp'] for e in errors)).total_seconds()

        # Higher frequency and consistency = higher confidence
        base_confidence = min(0.9, frequency / 10.0)

        # Adjust for time consistency
        if time_span > 0:
            error_rate = frequency / (time_span / 3600)  # errors per hour
            if error_rate > 1:  # More than 1 error per hour
                base_confidence += 0.1

        return min(1.0, base_confidence)

    def _generate_pattern_description(self, errors: List[Dict[str, Any]], category: ErrorCategory) -> str:
        """Generate human-readable description of the error pattern."""
        frequency = len(errors)
        components = set(e.get('component', 'unknown') for e in errors)

        description = f"{category.value.title()} issues occurring {frequency} times"

        if len(components) == 1:
            description += f" in {list(components)[0]} component"
        else:
            description += f" across {len(components)} components"

        return description

    def _generate_predictive_alerts(self, patterns: List[ErrorPattern]) -> List[PredictiveAlert]:
        """Generate predictive alerts based on identified patterns."""
        alerts = []

        for pattern in patterns:
            # Only generate alerts for patterns with high confidence and severity
            if pattern.prediction_confidence > 0.7 and pattern.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:

                # Estimate time to failure based on pattern frequency
                if pattern.frequency > 5:
                    time_to_failure = timedelta(hours=2)  # High frequency = imminent
                elif pattern.frequency > 2:
                    time_to_failure = timedelta(hours=6)  # Medium frequency
                else:
                    time_to_failure = timedelta(hours=24)  # Low frequency

                alert = PredictiveAlert(
                    alert_id=f"alert_{pattern.pattern_id}",
                    predicted_failure_type=f"{pattern.category.value}_failure",
                    confidence_score=pattern.prediction_confidence,
                    time_to_failure_estimate=time_to_failure,
                    affected_components=pattern.affected_components,
                    preventive_actions=pattern.recovery_actions,
                    risk_factors=[f"Pattern observed {pattern.frequency} times",
                                f"Severity: {pattern.severity.value}"],
                    generated_at=datetime.now()
                )

                alerts.append(alert)

        return alerts

    def _calculate_component_health_scores(self, test_results: List[TestResult]) -> Dict[str, float]:
        """Calculate health scores for each component based on test results."""
        component_stats = defaultdict(lambda: {'total': 0, 'success': 0, 'avg_time': []})

        # Collect statistics
        for result in test_results:
            component = result.scenario.component_name
            component_stats[component]['total'] += 1
            if result.success:
                component_stats[component]['success'] += 1
            component_stats[component]['avg_time'].append(result.execution_time)

        # Calculate health scores
        health_scores = {}
        for component, stats in component_stats.items():
            success_rate = stats['success'] / stats['total'] if stats['total'] > 0 else 0
            avg_time = np.mean(stats['avg_time']) if stats['avg_time'] else 0

            # Health score based on success rate and performance
            health_score = success_rate * 100

            # Penalty for slow performance
            if avg_time > 3.0:
                health_score *= 0.8
            elif avg_time > 1.0:
                health_score *= 0.9

            health_scores[component] = max(0, min(100, health_score))

            # Cache for future use
            self.component_health_cache[component] = health_scores[component]

        return health_scores

    def _generate_recommendations(self, patterns: List[ErrorPattern],
                                alerts: List[PredictiveAlert],
                                health_scores: Dict[str, float]) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []

        # Recommendations based on patterns
        if patterns:
            critical_patterns = [p for p in patterns if p.severity == ErrorSeverity.CRITICAL]
            if critical_patterns:
                recommendations.append(f"URGENT: Address {len(critical_patterns)} critical error patterns immediately")

            performance_patterns = [p for p in patterns if p.category == ErrorCategory.PERFORMANCE]
            if performance_patterns:
                recommendations.append(f"Optimize performance: {len(performance_patterns)} performance issues identified")

        # Recommendations based on alerts
        if alerts:
            high_confidence_alerts = [a for a in alerts if a.confidence_score > 0.8]
            if high_confidence_alerts:
                recommendations.append(f"Take preventive action: {len(high_confidence_alerts)} high-confidence failure predictions")

        # Recommendations based on component health
        unhealthy_components = [comp for comp, score in health_scores.items() if score < 70]
        if unhealthy_components:
            recommendations.append(f"Review component health: {', '.join(unhealthy_components)} showing poor performance")

        # General recommendations
        if len(patterns) > 10:
            recommendations.append("Consider implementing automated error recovery mechanisms")

        if not recommendations:
            recommendations.append("System performing well - continue monitoring for emerging patterns")

        return recommendations

    def _start_background_analysis(self):
        """Start background analysis thread."""
        def analysis_loop():
            while True:
                try:
                    self._periodic_analysis()
                    time.sleep(300)  # Run every 5 minutes
                except Exception as e:
                    logger.error(f"Background analysis error: {e}")
                    time.sleep(600)  # Wait longer on error

        analysis_thread = threading.Thread(target=analysis_loop, daemon=True)
        analysis_thread.start()

    def _periodic_analysis(self):
        """Perform periodic analysis of accumulated error data."""
        # Clean old error history
        cutoff_time = datetime.now() - timedelta(hours=self.history_window_hours)

        # Filter error history
        recent_errors = [
            error for error in self.error_history
            if error.get('timestamp', datetime.min) > cutoff_time
        ]

        # Update deque with filtered data
        self.error_history.clear()
        self.error_history.extend(recent_errors)

        # Log periodic status
        if recent_errors:
            logger.info(f"Periodic analysis: {len(recent_errors)} recent errors, "
                       f"{len(self.pattern_cache)} patterns tracked")

    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive system health summary."""
        return {
            'total_patterns_tracked': len(self.pattern_cache),
            'recent_errors_count': len(self.error_history),
            'component_health_scores': self.component_health_cache.copy(),
            'analysis_timestamp': datetime.now().isoformat(),
            'critical_patterns': [
                p.pattern_id for p in self.pattern_cache.values()
                if p.severity == ErrorSeverity.CRITICAL
            ]
        }

    def get_detected_patterns(self) -> List[ErrorPattern]:
        """Get all detected error patterns for launcher integration."""
        return list(self.pattern_cache.values())

    def get_active_alerts(self) -> List[PredictiveAlert]:
        """Get active predictive alerts for launcher integration."""
        return list(self.alert_cache.values())


# Global instance
_enhanced_detector: Optional[EnhancedErrorDetector] = None


def get_enhanced_error_detector() -> EnhancedErrorDetector:
    """Get the global enhanced error detector instance."""
    global _enhanced_detector
    if _enhanced_detector is None:
        _enhanced_detector = EnhancedErrorDetector()
    return _enhanced_detector


def analyze_test_results_with_enhanced_detection(test_results: List[TestResult]) -> ErrorAnalysisResult:
    """Convenience function to analyze test results with enhanced error detection."""
    detector = get_enhanced_error_detector()
    return detector.analyze_test_results(test_results)


def get_predictive_alerts() -> List[PredictiveAlert]:
    """Get current predictive alerts from the enhanced detector."""
    detector = get_enhanced_error_detector()
    # Analyze recent patterns to generate alerts
    recent_patterns = list(detector.pattern_cache.values())
    return detector._generate_predictive_alerts(recent_patterns)


def get_system_health_summary() -> Dict[str, Any]:
    """Get comprehensive system health summary."""
    detector = get_enhanced_error_detector()
    return detector.get_system_health_summary()