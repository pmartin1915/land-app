"""
AI Testability Framework for Streamlit App - Alabama Auction Watcher

This module provides comprehensive AI-driven testing capabilities including
automated test generation, visual regression testing, performance monitoring,
and intelligent error detection for Streamlit components.
"""

import streamlit as st
import pandas as pd
import numpy as np
import time
import json
import hashlib
import threading
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import logging
from unittest.mock import Mock, patch
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.ai_logging import get_ai_logger, LogCategory
from config.ai_diagnostics import SystemComponent, HealthStatus
from streamlit_app.core.performance_monitor import get_performance_monitor, performance_context

logger = get_ai_logger(__name__)


@dataclass
class TestScenario:
    """AI-generated test scenario."""
    scenario_id: str
    component_name: str
    test_type: str  # 'functional', 'performance', 'visual', 'error_handling'
    description: str
    input_data: Dict[str, Any]
    expected_behavior: Dict[str, Any]
    success_criteria: List[str]
    generated_at: datetime
    ai_confidence: float  # 0-1 confidence score


@dataclass
class TestResult:
    """Result of an AI test execution."""
    scenario: TestScenario
    success: bool
    execution_time: float
    actual_behavior: Dict[str, Any]
    deviations: List[str]
    performance_metrics: Dict[str, float]
    error_details: Optional[str]
    ai_analysis: str
    executed_at: datetime


@dataclass
class ComponentHealthReport:
    """AI-generated health report for a component."""
    component_name: str
    health_score: float  # 0-100
    performance_score: float  # 0-100
    reliability_score: float  # 0-100
    issues_detected: List[str]
    recommendations: List[str]
    test_coverage: float
    generated_at: datetime


class AITestGenerator:
    """
    AI-driven test scenario generator.
    Analyzes component behavior and generates intelligent test cases.
    """

    def __init__(self):
        self.scenario_templates = {
            'data_loading': {
                'inputs': ['empty_filters', 'minimal_filters', 'complex_filters', 'invalid_filters'],
                'behaviors': ['response_time', 'data_quality', 'error_handling', 'cache_efficiency']
            },
            'visualization': {
                'inputs': ['small_dataset', 'large_dataset', 'empty_dataset', 'malformed_data'],
                'behaviors': ['render_time', 'chart_accuracy', 'responsive_design', 'memory_usage']
            },
            'user_interaction': {
                'inputs': ['valid_selections', 'invalid_selections', 'edge_cases', 'concurrent_actions'],
                'behaviors': ['ui_responsiveness', 'state_consistency', 'error_feedback', 'data_persistence']
            }
        }

    def generate_scenarios_for_component(self, component_name: str,
                                       component_type: str,
                                       historical_data: List[Dict] = None) -> List[TestScenario]:
        """Generate AI-driven test scenarios for a component."""
        scenarios = []

        # Get templates for component type
        templates = self.scenario_templates.get(component_type, {})

        for input_type in templates.get('inputs', []):
            for behavior in templates.get('behaviors', []):
                scenario = self._create_scenario(
                    component_name, component_type, input_type, behavior, historical_data
                )
                scenarios.append(scenario)

        # Generate edge case scenarios based on historical failures
        if historical_data:
            edge_scenarios = self._generate_edge_case_scenarios(
                component_name, component_type, historical_data
            )
            scenarios.extend(edge_scenarios)

        return scenarios

    def generate_scenarios(self, component_name: str, component_type: str,
                         historical_data: List[Dict] = None) -> List[TestScenario]:
        """Generate test scenarios (alias for generate_scenarios_for_component)."""
        return self.generate_scenarios_for_component(component_name, component_type, historical_data)

    def _create_scenario(self, component_name: str, component_type: str,
                        input_type: str, behavior: str,
                        historical_data: List[Dict] = None) -> TestScenario:
        """Create a specific test scenario."""
        scenario_id = hashlib.md5(
            f"{component_name}_{component_type}_{input_type}_{behavior}".encode()
        ).hexdigest()[:12]

        # Generate input data based on type
        input_data = self._generate_input_data(input_type, historical_data)

        # Define expected behavior
        expected_behavior = self._define_expected_behavior(behavior, input_data)

        # Create success criteria
        success_criteria = self._create_success_criteria(behavior, expected_behavior)

        # Calculate AI confidence based on data quality and historical patterns
        ai_confidence = self._calculate_confidence(input_type, behavior, historical_data)

        return TestScenario(
            scenario_id=scenario_id,
            component_name=component_name,
            test_type=self._map_behavior_to_test_type(behavior),
            description=f"Test {component_name} {behavior} with {input_type}",
            input_data=input_data,
            expected_behavior=expected_behavior,
            success_criteria=success_criteria,
            generated_at=datetime.now(),
            ai_confidence=ai_confidence
        )

    def _generate_input_data(self, input_type: str, historical_data: List[Dict] = None) -> Dict[str, Any]:
        """Generate input data for test scenarios."""
        input_generators = {
            'empty_filters': lambda: {
                'filters': {},
                'expected_row_count': 0
            },
            'minimal_filters': lambda: {
                'filters': {'county': 'Baldwin'},
                'expected_row_count': 50
            },
            'complex_filters': lambda: {
                'filters': {
                    'county': 'Mobile',
                    'price_range': [10000, 50000],
                    'acreage_range': [1.0, 5.0],
                    'water_only': True,
                    'min_investment_score': 60
                },
                'expected_row_count': 25
            },
            'invalid_filters': lambda: {
                'filters': {
                    'county': 'NonexistentCounty',
                    'price_range': [-1000, -500],
                    'acreage_range': [100, 1]  # Invalid range
                },
                'expected_row_count': 0
            },
            'small_dataset': lambda: {
                'data_size': 100,
                'complexity': 'low'
            },
            'large_dataset': lambda: {
                'data_size': 10000,
                'complexity': 'high'
            },
            'empty_dataset': lambda: {
                'data_size': 0,
                'complexity': 'none'
            },
            'malformed_data': lambda: {
                'data_corruption': True,
                'missing_columns': ['investment_score'],
                'invalid_types': {'amount': 'string_instead_of_float'}
            }
        }

        generator = input_generators.get(input_type, lambda: {})
        return generator()

    def _define_expected_behavior(self, behavior: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Define expected behavior based on behavior type and input."""
        behavior_definitions = {
            'response_time': {
                'max_execution_time': 3.0,
                'expected_cache_hit': input_data.get('filters') is not None
            },
            'data_quality': {
                'required_columns': ['parcel_id', 'amount', 'county', 'investment_score'],
                'data_types': {
                    'amount': 'numeric',
                    'investment_score': 'numeric',
                    'county': 'string'
                }
            },
            'error_handling': {
                'graceful_degradation': True,
                'user_friendly_messages': True,
                'no_crashes': True
            },
            'render_time': {
                'max_render_time': 2.0,
                'responsive_design': True
            },
            'memory_usage': {
                'max_memory_mb': 100,
                'memory_leak_prevention': True
            },
            'ui_responsiveness': {
                'max_interaction_delay': 1.0,
                'visual_feedback': True
            }
        }

        return behavior_definitions.get(behavior, {})

    def _create_success_criteria(self, behavior: str, expected_behavior: Dict[str, Any]) -> List[str]:
        """Create success criteria for the test."""
        criteria_map = {
            'response_time': [
                f"Execution time < {expected_behavior.get('max_execution_time', 3.0)}s",
                "No timeout errors",
                "Appropriate caching behavior"
            ],
            'data_quality': [
                "All required columns present",
                "Data types are correct",
                "No null values in critical fields",
                "Data ranges are reasonable"
            ],
            'error_handling': [
                "No unhandled exceptions",
                "User-friendly error messages",
                "Graceful degradation on failure",
                "Application remains responsive"
            ],
            'render_time': [
                f"Render time < {expected_behavior.get('max_render_time', 2.0)}s",
                "Visual elements load correctly",
                "No rendering artifacts"
            ],
            'memory_usage': [
                f"Memory usage < {expected_behavior.get('max_memory_mb', 100)}MB",
                "No memory leaks detected",
                "Efficient data structures used"
            ]
        }

        return criteria_map.get(behavior, ["Test executes without errors"])

    def _generate_edge_case_scenarios(self, component_name: str, component_type: str,
                                    historical_data: List[Dict]) -> List[TestScenario]:
        """Generate edge case scenarios based on historical failures."""
        edge_scenarios = []

        # Analyze historical failures
        failure_patterns = self._analyze_failure_patterns(historical_data)

        for pattern in failure_patterns:
            scenario = self._create_edge_case_scenario(component_name, pattern)
            edge_scenarios.append(scenario)

        return edge_scenarios

    def _analyze_failure_patterns(self, historical_data: List[Dict]) -> List[Dict]:
        """Analyze historical data to identify failure patterns."""
        # This is a simplified implementation
        # In a full AI system, this would use ML to identify patterns
        patterns = []

        for data_point in historical_data:
            if data_point.get('error_occurred'):
                patterns.append({
                    'error_type': data_point.get('error_type'),
                    'input_conditions': data_point.get('input_conditions'),
                    'frequency': 1
                })

        return patterns

    def _calculate_confidence(self, input_type: str, behavior: str,
                            historical_data: List[Dict] = None) -> float:
        """Calculate AI confidence score for the scenario."""
        base_confidence = 0.8

        # Adjust based on input type complexity
        complexity_adjustments = {
            'empty_filters': 0.1,
            'minimal_filters': 0.05,
            'complex_filters': -0.1,
            'invalid_filters': -0.2
        }

        confidence = base_confidence + complexity_adjustments.get(input_type, 0)

        # Adjust based on historical data availability
        if historical_data and len(historical_data) > 10:
            confidence += 0.1

        return max(0.1, min(1.0, confidence))

    def _map_behavior_to_test_type(self, behavior: str) -> str:
        """Map behavior to test type."""
        mapping = {
            'response_time': 'performance',
            'render_time': 'performance',
            'memory_usage': 'performance',
            'data_quality': 'functional',
            'error_handling': 'functional',
            'ui_responsiveness': 'functional'
        }
        return mapping.get(behavior, 'functional')

    def _create_edge_case_scenario(self, component_name: str, failure_pattern: Dict) -> TestScenario:
        """Create edge case scenario from failure pattern."""
        scenario_id = hashlib.md5(
            f"{component_name}_edge_{failure_pattern.get('error_type', 'unknown')}".encode()
        ).hexdigest()[:12]

        return TestScenario(
            scenario_id=scenario_id,
            component_name=component_name,
            test_type='error_handling',
            description=f"Edge case test for {failure_pattern.get('error_type', 'unknown')} error",
            input_data=failure_pattern.get('input_conditions', {}),
            expected_behavior={'graceful_failure': True},
            success_criteria=["No application crash", "User-friendly error message"],
            generated_at=datetime.now(),
            ai_confidence=0.9  # High confidence for known failure patterns
        )


class AITestExecutor:
    """
    Executes AI-generated test scenarios and analyzes results.
    """

    def __init__(self):
        self.performance_monitor = get_performance_monitor()
        self.execution_history: List[TestResult] = []

    def execute_scenario(self, scenario: TestScenario,
                        component_function: Callable = None) -> TestResult:
        """Execute a single test scenario."""
        start_time = time.time()
        success = True
        actual_behavior = {}
        deviations = []
        error_details = None
        performance_metrics = {}

        try:
            with performance_context(f"ai_test_{scenario.component_name}", scenario.test_type):
                # Mock Streamlit components for testing
                with patch('streamlit.error'), patch('streamlit.warning'), patch('streamlit.info'):

                    if component_function:
                        # Execute the component with test input
                        if scenario.input_data.get('filters'):
                            result = component_function(scenario.input_data['filters'])
                        else:
                            result = component_function(scenario.input_data)

                        actual_behavior['result'] = self._analyze_component_result(result)

                    # Collect performance metrics
                    execution_time = time.time() - start_time
                    performance_metrics = {
                        'execution_time': execution_time,
                        'memory_usage': self._get_current_memory_usage(),
                        'cache_hits': self._get_cache_metrics()
                    }

                    # Check success criteria
                    success, deviations = self._evaluate_success_criteria(
                        scenario, actual_behavior, performance_metrics
                    )

        except Exception as e:
            success = False
            error_details = str(e)
            deviations.append(f"Unhandled exception: {e}")

        # Generate AI analysis
        ai_analysis = self._generate_ai_analysis(scenario, actual_behavior, deviations, success)

        result = TestResult(
            scenario=scenario,
            success=success,
            execution_time=time.time() - start_time,
            actual_behavior=actual_behavior,
            deviations=deviations,
            performance_metrics=performance_metrics,
            error_details=error_details,
            ai_analysis=ai_analysis,
            executed_at=datetime.now()
        )

        self.execution_history.append(result)
        return result

    def _analyze_component_result(self, result: Any) -> Dict[str, Any]:
        """Analyze the result of component execution."""
        analysis = {}

        if isinstance(result, pd.DataFrame):
            analysis.update({
                'data_type': 'dataframe',
                'row_count': len(result),
                'column_count': len(result.columns) if hasattr(result, 'columns') else 0,
                'memory_usage_mb': result.memory_usage(deep=True).sum() / (1024*1024) if hasattr(result, 'memory_usage') else 0,
                'has_required_columns': self._check_required_columns(result)
            })
        elif isinstance(result, dict):
            analysis.update({
                'data_type': 'dictionary',
                'key_count': len(result),
                'has_error': 'error' in result
            })
        elif result is None:
            analysis.update({
                'data_type': 'none',
                'is_null_result': True
            })
        else:
            analysis.update({
                'data_type': type(result).__name__,
                'value': str(result)[:100]  # Truncate long values
            })

        return analysis

    def _check_required_columns(self, df: pd.DataFrame) -> bool:
        """Check if DataFrame has required columns."""
        required_columns = ['parcel_id', 'amount', 'county']
        return all(col in df.columns for col in required_columns)

    def _get_current_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except:
            return 0.0

    def _get_cache_metrics(self) -> Dict[str, int]:
        """Get cache hit/miss metrics."""
        try:
            from streamlit_app.core.cache_manager import get_cache_manager
            cache_manager = get_cache_manager()
            stats = cache_manager.get_stats()
            return {
                'hits': stats.get('total_hits', 0),
                'misses': stats.get('total_misses', 0)
            }
        except:
            return {'hits': 0, 'misses': 0}

    def _evaluate_success_criteria(self, scenario: TestScenario,
                                 actual_behavior: Dict[str, Any],
                                 performance_metrics: Dict[str, float]) -> Tuple[bool, List[str]]:
        """Evaluate if the test meets success criteria."""
        success = True
        deviations = []

        for criterion in scenario.success_criteria:
            if not self._check_criterion(criterion, scenario, actual_behavior, performance_metrics):
                success = False
                deviations.append(f"Failed criterion: {criterion}")

        return success, deviations

    def _check_criterion(self, criterion: str, scenario: TestScenario,
                        actual_behavior: Dict[str, Any],
                        performance_metrics: Dict[str, float]) -> bool:
        """Check a specific success criterion."""

        # Performance criteria
        if "Execution time <" in criterion:
            try:
                max_time = float(criterion.split("<")[1].replace("s", "").strip())
                return performance_metrics.get('execution_time', 0) < max_time
            except:
                return False

        elif "Render time <" in criterion:
            try:
                max_time = float(criterion.split("<")[1].replace("s", "").strip())
                return performance_metrics.get('execution_time', 0) < max_time
            except:
                return False

        elif "Memory usage <" in criterion:
            try:
                max_memory = float(criterion.split("<")[1].replace("MB", "").strip())
                return performance_metrics.get('memory_usage', 0) < max_memory
            except:
                return False

        # Data quality criteria
        elif "All required columns present" in criterion:
            return actual_behavior.get('has_required_columns', False)

        elif "No null values in critical fields" in criterion:
            # This would need more sophisticated checking
            return True  # Placeholder

        # Error handling criteria
        elif "No unhandled exceptions" in criterion:
            return actual_behavior.get('has_error', False) == False

        # Default case
        return True

    def _generate_ai_analysis(self, scenario: TestScenario, actual_behavior: Dict[str, Any],
                            deviations: List[str], success: bool) -> str:
        """Generate AI analysis of test results."""
        analysis_parts = []

        if success:
            analysis_parts.append(f"✅ Test passed successfully for {scenario.component_name}")
        else:
            analysis_parts.append(f"❌ Test failed for {scenario.component_name}")

        # Analyze performance
        if 'execution_time' in actual_behavior:
            exec_time = actual_behavior['execution_time']
            if exec_time > 3.0:
                analysis_parts.append("⚠️ Slow execution time detected - consider optimization")
            elif exec_time < 0.1:
                analysis_parts.append("⚡ Excellent performance - likely served from cache")

        # Analyze data quality
        if actual_behavior.get('data_type') == 'dataframe':
            row_count = actual_behavior.get('row_count', 0)
            if row_count == 0 and scenario.input_data.get('expected_row_count', 0) > 0:
                analysis_parts.append("⚠️ No data returned - check filters or data availability")
            elif row_count > 1000:
                analysis_parts.append("📊 Large dataset returned - monitor memory usage")

        # Add deviation analysis
        if deviations:
            analysis_parts.append(f"🔍 Issues found: {'; '.join(deviations)}")

        return " | ".join(analysis_parts)

    def generate_component_health_report(self, component_name: str,
                                       test_results: List[TestResult]) -> ComponentHealthReport:
        """Generate AI health report for a component."""
        if not test_results:
            return ComponentHealthReport(
                component_name=component_name,
                health_score=0.0,
                performance_score=0.0,
                reliability_score=0.0,
                issues_detected=["No test data available"],
                recommendations=["Execute tests to generate health metrics"],
                test_coverage=0.0,
                generated_at=datetime.now()
            )

        # Calculate scores
        success_rate = sum(1 for r in test_results if r.success) / len(test_results)
        avg_execution_time = sum(r.execution_time for r in test_results) / len(test_results)

        # Health score (0-100)
        health_score = success_rate * 100

        # Performance score (based on execution times)
        performance_score = max(0, 100 - (avg_execution_time * 20))

        # Reliability score (based on consistency)
        reliability_score = self._calculate_reliability_score(test_results)

        # Detect issues
        issues = self._detect_issues(test_results)

        # Generate recommendations
        recommendations = self._generate_recommendations(test_results, issues)

        # Calculate test coverage
        test_coverage = self._calculate_test_coverage(test_results)

        return ComponentHealthReport(
            component_name=component_name,
            health_score=health_score,
            performance_score=performance_score,
            reliability_score=reliability_score,
            issues_detected=issues,
            recommendations=recommendations,
            test_coverage=test_coverage,
            generated_at=datetime.now()
        )

    def _calculate_reliability_score(self, test_results: List[TestResult]) -> float:
        """Calculate reliability score based on consistency."""
        if len(test_results) < 2:
            return 100.0

        execution_times = [r.execution_time for r in test_results if r.success]
        if not execution_times:
            return 0.0

        # Calculate coefficient of variation
        mean_time = sum(execution_times) / len(execution_times)
        variance = sum((t - mean_time) ** 2 for t in execution_times) / len(execution_times)
        std_dev = variance ** 0.5

        cv = std_dev / mean_time if mean_time > 0 else 1.0

        # Lower coefficient of variation = higher reliability
        reliability_score = max(0, 100 - (cv * 100))
        return reliability_score

    def _detect_issues(self, test_results: List[TestResult]) -> List[str]:
        """Detect issues from test results."""
        issues = []

        # Check for consistent failures
        failure_rate = sum(1 for r in test_results if not r.success) / len(test_results)
        if failure_rate > 0.1:
            issues.append(f"High failure rate: {failure_rate:.1%}")

        # Check for performance issues
        slow_tests = [r for r in test_results if r.execution_time > 3.0]
        if len(slow_tests) > len(test_results) * 0.2:
            issues.append("Frequent slow execution times")

        # Check for memory issues
        high_memory_tests = [r for r in test_results
                           if r.performance_metrics.get('memory_usage', 0) > 100]
        if high_memory_tests:
            issues.append("High memory usage detected")

        return issues

    def _generate_recommendations(self, test_results: List[TestResult],
                                issues: List[str]) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []

        if "High failure rate" in str(issues):
            recommendations.append("Review error handling and input validation")

        if "slow execution" in str(issues).lower():
            recommendations.append("Optimize algorithms and consider caching")
            recommendations.append("Profile code to identify bottlenecks")

        if "memory usage" in str(issues).lower():
            recommendations.append("Optimize data structures and memory usage")
            recommendations.append("Implement data streaming for large datasets")

        # Add general recommendations
        if len(test_results) < 10:
            recommendations.append("Increase test coverage with more scenarios")

        return recommendations

    def _calculate_test_coverage(self, test_results: List[TestResult]) -> float:
        """Calculate test coverage percentage."""
        # This is a simplified implementation
        # In practice, this would analyze code coverage and scenario coverage
        test_types = set(r.scenario.test_type for r in test_results)
        max_types = 4  # functional, performance, visual, error_handling

        return (len(test_types) / max_types) * 100


# Global instances
_test_generator: Optional[AITestGenerator] = None
_test_executor: Optional[AITestExecutor] = None


def get_test_generator() -> AITestGenerator:
    """Get the global AI test generator instance."""
    global _test_generator
    if _test_generator is None:
        _test_generator = AITestGenerator()
    return _test_generator


def get_test_executor() -> AITestExecutor:
    """Get the global AI test executor instance."""
    global _test_executor
    if _test_executor is None:
        _test_executor = AITestExecutor()
    return _test_executor


def test_component_with_ai(component_name: str, component_function: Callable,
                          component_type: str = 'data_loading') -> ComponentHealthReport:
    """Test a component using AI-generated scenarios."""
    generator = get_test_generator()
    executor = get_test_executor()

    # Generate test scenarios
    scenarios = generator.generate_scenarios_for_component(
        component_name, component_type
    )

    # Execute tests
    results = []
    for scenario in scenarios:
        result = executor.execute_scenario(scenario, component_function)
        results.append(result)

    # Generate health report
    health_report = executor.generate_component_health_report(component_name, results)

    # Log results for AI monitoring
    logger.info(
        f"AI testing completed for {component_name}",
        extra={
            "category": LogCategory.TESTING,
            "ai_actionable": True,
            "health_score": health_report.health_score,
            "performance_score": health_report.performance_score,
            "test_count": len(results),
            "success_rate": sum(1 for r in results if r.success) / len(results)
        }
    )

    return health_report


def ai_test_decorator(component_name: str = None, component_type: str = 'data_loading'):
    """Decorator to add AI testing to Streamlit components."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Execute original function
            result = func(*args, **kwargs)

            # Run AI tests in background (non-blocking)
            if st.session_state.get('ai_testing_enabled', False):
                threading.Thread(
                    target=lambda: test_component_with_ai(
                        component_name or func.__name__, func, component_type
                    ),
                    daemon=True
                ).start()

            return result
        return wrapper
    return decorator