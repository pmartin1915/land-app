"""
Enhanced AI Testing Controller
Alabama Auction Watcher - Advanced AI Testing with Error Detection

This module provides an enhanced testing controller that combines:
- Existing AI testability framework
- Advanced error detection patterns
- Predictive failure analysis
- Automated recovery suggestions
- Real-time health monitoring

Author: Claude Code AI Assistant
Date: 2025-09-21
Version: 1.1.0
"""

import streamlit as st
import pandas as pd
import time
import json
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import logging
import threading
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.ai_logging import get_ai_logger, LogCategory
from streamlit_app.core.performance_monitor import get_performance_monitor, monitor_performance
from streamlit_app.testing.ai_testability import (
    get_test_generator, get_test_executor, TestResult, TestScenario, ComponentHealthReport
)
from streamlit_app.testing.enhanced_error_detection import (
    get_enhanced_error_detector, ErrorAnalysisResult, PredictiveAlert, ErrorPattern
)

logger = get_ai_logger(__name__)


@dataclass
class EnhancedTestReport:
    """Comprehensive test report with error analysis."""
    component_name: str
    test_execution_time: float

    # Basic test results
    total_scenarios: int
    successful_scenarios: int
    failed_scenarios: int
    success_rate: float

    # Performance metrics
    avg_execution_time: float
    max_execution_time: float
    memory_usage_mb: float

    # Error analysis
    error_analysis: ErrorAnalysisResult
    component_health: ComponentHealthReport
    predictive_alerts: List[PredictiveAlert]

    # Recommendations
    immediate_actions: List[str]
    preventive_measures: List[str]
    performance_optimizations: List[str]

    # Metadata
    generated_at: datetime
    test_coverage_score: float


class EnhancedAITestingController:
    """
    Enhanced AI testing controller that provides comprehensive testing
    with advanced error detection and predictive analysis.
    """

    def __init__(self):
        self.test_generator = get_test_generator()
        self.test_executor = get_test_executor()
        self.error_detector = get_enhanced_error_detector()
        self.performance_monitor = get_performance_monitor()

        # Testing history
        self.testing_history: List[EnhancedTestReport] = []

        # Configuration
        self.max_scenarios_per_component = 20
        self.performance_threshold_seconds = 3.0
        self.health_score_threshold = 70.0

    @monitor_performance("enhanced_ai_testing", include_memory=True)
    def run_comprehensive_test(self, component_name: str,
                             component_function: Callable,
                             component_type: str = 'data_loading',
                             include_stress_tests: bool = True) -> EnhancedTestReport:
        """
        Run comprehensive AI testing with advanced error detection.

        Args:
            component_name: Name of the component to test
            component_function: Function to test
            component_type: Type of component (data_loading, visualization, user_interaction)
            include_stress_tests: Whether to include stress testing scenarios

        Returns:
            EnhancedTestReport with comprehensive analysis
        """
        start_time = time.time()

        logger.info(f"Starting comprehensive AI testing for {component_name}")

        # Generate test scenarios
        scenarios = self._generate_enhanced_scenarios(
            component_name, component_type, include_stress_tests
        )

        # Execute tests
        test_results = self._execute_test_scenarios(scenarios, component_function)

        # Perform error analysis
        error_analysis = self.error_detector.analyze_test_results(test_results)

        # Generate component health report
        component_health = self.test_executor.generate_component_health_report(
            component_name, test_results
        )

        # Get predictive alerts
        predictive_alerts = self._filter_relevant_alerts(
            error_analysis.predictive_alerts, component_name
        )

        # Generate recommendations
        recommendations = self._generate_enhanced_recommendations(
            test_results, error_analysis, component_health, predictive_alerts
        )

        # Calculate metrics
        total_scenarios = len(test_results)
        successful_scenarios = sum(1 for r in test_results if r.success)
        failed_scenarios = total_scenarios - successful_scenarios
        success_rate = successful_scenarios / total_scenarios if total_scenarios > 0 else 0

        execution_times = [r.execution_time for r in test_results]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        max_execution_time = max(execution_times) if execution_times else 0

        # Get memory usage from performance monitor
        memory_usage_mb = self._get_current_memory_usage()

        # Calculate test coverage score
        test_coverage_score = self._calculate_test_coverage_score(scenarios, test_results)

        # Create comprehensive report
        report = EnhancedTestReport(
            component_name=component_name,
            test_execution_time=time.time() - start_time,
            total_scenarios=total_scenarios,
            successful_scenarios=successful_scenarios,
            failed_scenarios=failed_scenarios,
            success_rate=success_rate,
            avg_execution_time=avg_execution_time,
            max_execution_time=max_execution_time,
            memory_usage_mb=memory_usage_mb,
            error_analysis=error_analysis,
            component_health=component_health,
            predictive_alerts=predictive_alerts,
            immediate_actions=recommendations['immediate'],
            preventive_measures=recommendations['preventive'],
            performance_optimizations=recommendations['performance'],
            generated_at=datetime.now(),
            test_coverage_score=test_coverage_score
        )

        # Store in history
        self.testing_history.append(report)

        # Log comprehensive results
        logger.info(
            f"Enhanced testing completed for {component_name}",
            extra={
                "category": LogCategory.TESTING,
                "ai_actionable": True,
                "component_name": component_name,
                "success_rate": success_rate,
                "health_score": component_health.health_score,
                "error_patterns": len(error_analysis.patterns_identified),
                "predictive_alerts": len(predictive_alerts),
                "test_coverage": test_coverage_score
            }
        )

        return report

    def _generate_enhanced_scenarios(self, component_name: str,
                                   component_type: str,
                                   include_stress_tests: bool) -> List[TestScenario]:
        """Generate enhanced test scenarios including stress tests."""

        # Get standard scenarios
        scenarios = self.test_generator.generate_scenarios_for_component(
            component_name, component_type
        )

        # Add stress test scenarios if requested
        if include_stress_tests:
            stress_scenarios = self._generate_stress_test_scenarios(
                component_name, component_type
            )
            scenarios.extend(stress_scenarios)

        # Limit total scenarios
        if len(scenarios) > self.max_scenarios_per_component:
            # Prioritize scenarios by confidence and coverage
            scenarios.sort(key=lambda s: s.ai_confidence, reverse=True)
            scenarios = scenarios[:self.max_scenarios_per_component]

        return scenarios

    def _generate_stress_test_scenarios(self, component_name: str,
                                      component_type: str) -> List[TestScenario]:
        """Generate stress testing scenarios for edge cases."""
        stress_scenarios = []

        if component_type == 'data_loading':
            # Large dataset stress test
            stress_scenarios.append(TestScenario(
                scenario_id=f"stress_{component_name}_large_data",
                component_name=component_name,
                test_type='performance',
                description=f"Stress test {component_name} with large dataset",
                input_data={
                    'data_size': 10000,
                    'complexity': 'very_high',
                    'concurrent_requests': 5
                },
                expected_behavior={'max_execution_time': 5.0},
                success_criteria=['Execution time < 5.0s', 'No memory overflow'],
                generated_at=datetime.now(),
                ai_confidence=0.9
            ))

            # Concurrent access stress test
            stress_scenarios.append(TestScenario(
                scenario_id=f"stress_{component_name}_concurrent",
                component_name=component_name,
                test_type='performance',
                description=f"Stress test {component_name} with concurrent access",
                input_data={
                    'concurrent_users': 10,
                    'request_rate': 5
                },
                expected_behavior={'maintain_performance': True},
                success_criteria=['No degradation > 50%', 'No errors under load'],
                generated_at=datetime.now(),
                ai_confidence=0.85
            ))

        elif component_type == 'visualization':
            # Large visualization stress test
            stress_scenarios.append(TestScenario(
                scenario_id=f"stress_{component_name}_large_viz",
                component_name=component_name,
                test_type='performance',
                description=f"Stress test {component_name} with large visualization",
                input_data={
                    'data_points': 50000,
                    'chart_complexity': 'maximum'
                },
                expected_behavior={'render_time': 3.0},
                success_criteria=['Render time < 3.0s', 'No UI freezing'],
                generated_at=datetime.now(),
                ai_confidence=0.8
            ))

        return stress_scenarios

    def _execute_test_scenarios(self, scenarios: List[TestScenario],
                              component_function: Callable) -> List[TestResult]:
        """Execute test scenarios with enhanced monitoring."""
        test_results = []

        for scenario in scenarios:
            try:
                # Execute with performance monitoring
                result = self.test_executor.execute_scenario(scenario, component_function)
                test_results.append(result)

                # Check for immediate issues
                if not result.success and result.error_details:
                    logger.warning(f"Test failure in {scenario.component_name}: {result.error_details}")

            except Exception as e:
                logger.error(f"Test execution failed for scenario {scenario.scenario_id}: {e}")

        return test_results

    def _filter_relevant_alerts(self, alerts: List[PredictiveAlert],
                              component_name: str) -> List[PredictiveAlert]:
        """Filter alerts relevant to the current component."""
        return [
            alert for alert in alerts
            if component_name in alert.affected_components
        ]

    def _generate_enhanced_recommendations(self, test_results: List[TestResult],
                                         error_analysis: ErrorAnalysisResult,
                                         component_health: ComponentHealthReport,
                                         alerts: List[PredictiveAlert]) -> Dict[str, List[str]]:
        """Generate enhanced recommendations based on comprehensive analysis."""

        immediate_actions = []
        preventive_measures = []
        performance_optimizations = []

        # Immediate actions based on failures
        failed_tests = [r for r in test_results if not r.success]
        if failed_tests:
            failure_rate = len(failed_tests) / len(test_results)
            if failure_rate > 0.3:
                immediate_actions.append(f"URGENT: {failure_rate:.1%} test failure rate - investigate immediately")

        # Actions based on error patterns
        for pattern in error_analysis.patterns_identified:
            if pattern.severity.value in ['critical', 'high']:
                immediate_actions.extend(pattern.recovery_actions[:2])  # Top 2 actions
            else:
                preventive_measures.extend(pattern.recovery_actions)

        # Actions based on predictive alerts
        for alert in alerts:
            if alert.confidence_score > 0.8:
                immediate_actions.extend(alert.preventive_actions[:2])
            else:
                preventive_measures.extend(alert.preventive_actions)

        # Performance optimizations
        if component_health.performance_score < 70:
            performance_optimizations.append("Optimize component performance - current score below threshold")

        avg_execution_time = sum(r.execution_time for r in test_results) / len(test_results) if test_results else 0
        if avg_execution_time > self.performance_threshold_seconds:
            performance_optimizations.append(f"Reduce execution time - current average: {avg_execution_time:.2f}s")

        # Memory optimizations
        high_memory_tests = [r for r in test_results if r.performance_metrics.get('memory_usage', 0) > 100]
        if high_memory_tests:
            performance_optimizations.append("Optimize memory usage - high consumption detected")

        # Remove duplicates and limit recommendations
        immediate_actions = list(set(immediate_actions))[:5]
        preventive_measures = list(set(preventive_measures))[:5]
        performance_optimizations = list(set(performance_optimizations))[:5]

        return {
            'immediate': immediate_actions,
            'preventive': preventive_measures,
            'performance': performance_optimizations
        }

    def _get_current_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0

    def _calculate_test_coverage_score(self, scenarios: List[TestScenario],
                                     results: List[TestResult]) -> float:
        """Calculate test coverage score based on scenario diversity and success."""

        if not scenarios:
            return 0.0

        # Coverage dimensions
        test_types = set(s.test_type for s in scenarios)
        component_aspects = set(s.description.split()[0] for s in scenarios)  # First word as aspect

        # Coverage score based on diversity
        type_coverage = len(test_types) / 4.0  # Assume 4 main test types
        aspect_coverage = len(component_aspects) / max(len(scenarios), 10)  # Normalize by scenario count

        # Success rate factor
        success_rate = sum(1 for r in results if r.success) / len(results) if results else 0

        # Combine scores
        coverage_score = (type_coverage * 0.4 + aspect_coverage * 0.3 + success_rate * 0.3) * 100

        return min(100.0, coverage_score)

    def get_testing_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get testing summary for the specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        recent_reports = [
            report for report in self.testing_history
            if report.generated_at > cutoff_time
        ]

        if not recent_reports:
            return {
                'status': 'no_data',
                'message': f'No testing data available for the last {hours} hours'
            }

        # Calculate aggregate metrics
        total_tests = sum(r.total_scenarios for r in recent_reports)
        total_successful = sum(r.successful_scenarios for r in recent_reports)
        avg_success_rate = sum(r.success_rate for r in recent_reports) / len(recent_reports)
        avg_health_score = sum(r.component_health.health_score for r in recent_reports) / len(recent_reports)

        # Count alerts and patterns
        total_alerts = sum(len(r.predictive_alerts) for r in recent_reports)
        total_patterns = sum(len(r.error_analysis.patterns_identified) for r in recent_reports)

        return {
            'status': 'healthy' if avg_success_rate > 0.8 else 'warning',
            'time_period_hours': hours,
            'reports_generated': len(recent_reports),
            'total_tests_executed': total_tests,
            'total_successful_tests': total_successful,
            'average_success_rate': avg_success_rate,
            'average_health_score': avg_health_score,
            'total_predictive_alerts': total_alerts,
            'total_error_patterns': total_patterns,
            'components_tested': list(set(r.component_name for r in recent_reports)),
            'last_updated': datetime.now().isoformat()
        }

    def run_system_wide_health_check(self) -> Dict[str, Any]:
        """Run a comprehensive system-wide health check."""
        health_summary = self.error_detector.get_system_health_summary()
        testing_summary = self.get_testing_summary(hours=24)

        # Get performance metrics
        performance_summary = self.performance_monitor.get_performance_summary()

        return {
            'system_health': health_summary,
            'testing_metrics': testing_summary,
            'performance_metrics': performance_summary,
            'overall_status': self._determine_overall_status(health_summary, testing_summary),
            'generated_at': datetime.now().isoformat()
        }

    def _determine_overall_status(self, health_summary: Dict[str, Any],
                                testing_summary: Dict[str, Any]) -> str:
        """Determine overall system status based on health and testing metrics."""

        # Check for critical issues
        if health_summary.get('critical_patterns'):
            return 'critical'

        # Check testing success rate
        success_rate = testing_summary.get('average_success_rate', 0)
        if success_rate < 0.7:
            return 'warning'

        # Check component health
        health_scores = health_summary.get('component_health_scores', {})
        if health_scores:
            avg_health = sum(health_scores.values()) / len(health_scores)
            if avg_health < 70:
                return 'warning'

        return 'healthy'

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics for launcher integration."""
        if not self.testing_history:
            return {
                'total_tests_run': 0,
                'success_rate': 0.0,
                'avg_execution_time': 0.0,
                'last_test_time': None,
                'component_health_scores': {},
                'active_alerts': 0,
                'status': 'inactive'
            }

        latest_report = self.testing_history[-1]

        # Calculate overall statistics
        total_tests = sum(report.total_scenarios for report in self.testing_history)
        total_successful = sum(report.successful_scenarios for report in self.testing_history)

        # Component health scores from recent reports
        component_health_scores = {}
        for report in self.testing_history[-5:]:  # Last 5 reports
            component_health_scores[report.component_name] = report.component_health.overall_health_score

        return {
            'total_tests_run': total_tests,
            'success_rate': (total_successful / total_tests * 100) if total_tests > 0 else 0.0,
            'avg_execution_time': sum(r.test_execution_time for r in self.testing_history) / len(self.testing_history),
            'last_test_time': latest_report.generated_at.isoformat(),
            'component_health_scores': component_health_scores,
            'active_alerts': len(latest_report.predictive_alerts),
            'status': 'active' if len(self.testing_history) > 0 else 'inactive'
        }


# Global instance
_enhanced_controller: Optional[EnhancedAITestingController] = None


def get_enhanced_ai_testing_controller() -> EnhancedAITestingController:
    """Get the global enhanced AI testing controller instance."""
    global _enhanced_controller
    if _enhanced_controller is None:
        _enhanced_controller = EnhancedAITestingController()
    return _enhanced_controller


def run_enhanced_component_test(component_name: str,
                               component_function: Callable,
                               component_type: str = 'data_loading',
                               include_stress_tests: bool = True) -> EnhancedTestReport:
    """Convenience function to run enhanced testing on a component."""
    controller = get_enhanced_ai_testing_controller()
    return controller.run_comprehensive_test(
        component_name, component_function, component_type, include_stress_tests
    )


def get_system_health_dashboard() -> Dict[str, Any]:
    """Get comprehensive system health dashboard data."""
    controller = get_enhanced_ai_testing_controller()
    return controller.run_system_wide_health_check()


# Decorator for easy integration
def enhanced_ai_test(component_name: str = None,
                    component_type: str = 'data_loading',
                    include_stress_tests: bool = False):
    """Decorator to add enhanced AI testing to functions."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # Run enhanced testing in background
            if st.session_state.get('enhanced_ai_testing_enabled', False):
                threading.Thread(
                    target=lambda: run_enhanced_component_test(
                        component_name or func.__name__,
                        func,
                        component_type,
                        include_stress_tests
                    ),
                    daemon=True
                ).start()

            return result
        return wrapper
    return decorator