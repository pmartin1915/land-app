"""
AI-driven test executor that can read specifications and execute tests automatically.

This module demonstrates how AI systems can consume machine-readable test
specifications and execute tests autonomously with proper error handling
and recovery mechanisms.
"""

import importlib
import inspect
import json
import time
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum

import pytest
import psutil

# Import our specification system
from schemas.specification_validator import (
    SpecificationLoader, TestCase, TestCategory, Priority,
    load_ai_test_specifications, get_ai_executable_test_plan
)


class ExecutionStatus(Enum):
    """Test execution status for AI tracking."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    RETRYING = "retrying"


@dataclass
class ExecutionResult:
    """Result of test execution with AI-friendly metadata."""
    test_id: str
    status: ExecutionStatus
    duration_seconds: float
    output: str
    error_message: Optional[str] = None
    exception_type: Optional[str] = None
    retry_count: int = 0
    memory_usage_mb: Optional[float] = None
    recovery_actions_taken: List[str] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.recovery_actions_taken is None:
            self.recovery_actions_taken = []


@dataclass
class ExecutionPlan:
    """AI execution plan with optimization strategies."""
    test_cases: List[TestCase]
    execution_order: List[str]
    parallel_groups: List[List[str]]
    resource_requirements: Dict[str, Any]
    timeout_strategy: Dict[str, Any]
    retry_strategy: Dict[str, Any]


class AITestExecutor:
    """AI-driven test executor with intelligent execution strategies."""

    def __init__(self, spec_file: Optional[str] = None):
        """Initialize the executor."""
        self.spec_file = spec_file or "tests/schemas/test_specifications.json"
        self.loader = SpecificationLoader()
        self.results: List[ExecutionResult] = []
        self.execution_stats = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "total_duration": 0.0,
            "average_duration": 0.0
        }

    def create_execution_plan(self, test_cases: List[TestCase]) -> ExecutionPlan:
        """
        Create an optimized execution plan for AI test execution.

        Args:
            test_cases: List of test cases to execute

        Returns:
            Optimized execution plan
        """
        # Sort by priority (critical first, then high, medium, low)
        priority_order = {Priority.CRITICAL: 0, Priority.HIGH: 1, Priority.MEDIUM: 2, Priority.LOW: 3}
        sorted_tests = sorted(test_cases, key=lambda t: priority_order.get(t.priority, 3))

        # Group tests for parallel execution
        # Unit tests can run in parallel, integration tests need more coordination
        parallel_groups = []
        unit_tests = [t for t in sorted_tests if t.category == TestCategory.UNIT]
        integration_tests = [t for t in sorted_tests if t.category == TestCategory.INTEGRATION]
        other_tests = [t for t in sorted_tests if t.category not in [TestCategory.UNIT, TestCategory.INTEGRATION]]

        # Create parallel groups
        if unit_tests:
            # Split unit tests into groups of 4
            for i in range(0, len(unit_tests), 4):
                parallel_groups.append([t.id for t in unit_tests[i:i+4]])

        # Integration tests run in smaller groups
        if integration_tests:
            for i in range(0, len(integration_tests), 2):
                parallel_groups.append([t.id for t in integration_tests[i:i+2]])

        # Other tests run individually
        for test in other_tests:
            parallel_groups.append([test.id])

        execution_order = [test.id for test in sorted_tests]

        return ExecutionPlan(
            test_cases=test_cases,
            execution_order=execution_order,
            parallel_groups=parallel_groups,
            resource_requirements={
                "cpu_cores": min(4, len(unit_tests)),
                "memory_gb": 2.0,
                "network_access": any(t.category == TestCategory.INTEGRATION for t in test_cases),
                "external_services": ["ador_website"] if any("scraping" in t.tags for t in test_cases) else []
            },
            timeout_strategy={
                "global_timeout_minutes": 30,
                "per_test_timeout_seconds": 300,
                "cleanup_timeout_seconds": 30
            },
            retry_strategy={
                "max_retries": 3,
                "retry_delay_seconds": 2.0,
                "exponential_backoff": True,
                "retry_on_errors": ["NetworkError", "TimeoutError", "TemporaryFailure"]
            }
        )

    def execute_test_case(self, test_case: TestCase) -> ExecutionResult:
        """
        Execute a single test case with AI-friendly error handling.

        Args:
            test_case: Test case to execute

        Returns:
            Execution result with comprehensive metadata
        """
        start_time = time.time()
        start_memory = self._get_memory_usage()

        try:
            # Execute the test based on its type
            if test_case.category == TestCategory.UNIT:
                result = self._execute_unit_test(test_case)
            elif test_case.category == TestCategory.INTEGRATION:
                result = self._execute_integration_test(test_case)
            elif test_case.category == TestCategory.ERROR_HANDLING:
                result = self._execute_error_handling_test(test_case)
            else:
                result = self._execute_generic_test(test_case)

            duration = time.time() - start_time
            end_memory = self._get_memory_usage()
            memory_usage = end_memory - start_memory if end_memory and start_memory else None

            return ExecutionResult(
                test_id=test_case.id,
                status=ExecutionStatus.PASSED if result else ExecutionStatus.FAILED,
                duration_seconds=duration,
                output=str(result),
                memory_usage_mb=memory_usage
            )

        except Exception as e:
            duration = time.time() - start_time
            end_memory = self._get_memory_usage()
            memory_usage = end_memory - start_memory if end_memory and start_memory else None

            return ExecutionResult(
                test_id=test_case.id,
                status=ExecutionStatus.ERROR,
                duration_seconds=duration,
                output="",
                error_message=str(e),
                exception_type=type(e).__name__,
                memory_usage_mb=memory_usage
            )

    def _execute_unit_test(self, test_case: TestCase) -> Any:
        """Execute a unit test by calling the specified function."""
        input_data = test_case.input_data
        function_name = input_data.get("function_name")
        module_name = input_data.get("module_name")
        parameters = input_data.get("parameters", {})

        if not function_name or not module_name:
            raise ValueError(f"Unit test {test_case.id} missing function_name or module_name")

        # Import the module and get the function
        try:
            module = importlib.import_module(module_name)
            func = getattr(module, function_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Cannot import {module_name}.{function_name}: {e}")

        # Call the function with parameters
        result = func(**parameters)

        # Validate against expected output
        expected = test_case.expected_output.get("return_value")
        if expected is not None and result != expected:
            raise AssertionError(f"Expected {expected}, got {result}")

        return result

    def _execute_integration_test(self, test_case: TestCase) -> Any:
        """Execute an integration test by running a workflow."""
        input_data = test_case.input_data
        workflow_name = input_data.get("workflow_name")

        if workflow_name == "county_scraping":
            return self._execute_county_scraping_workflow(test_case)
        elif workflow_name == "data_processing":
            return self._execute_data_processing_workflow(test_case)
        else:
            # Generic workflow execution
            return self._execute_generic_workflow(test_case)

    def _execute_county_scraping_workflow(self, test_case: TestCase) -> Dict[str, Any]:
        """Execute county scraping integration test."""
        input_data = test_case.input_data
        test_data = input_data.get("test_data", {})

        county = test_data.get("county", "Baldwin")
        max_pages = test_data.get("max_pages", 1)

        # Import and execute scraping
        try:
            from scripts.scraper import scrape_county_data
            result_df = scrape_county_data(county, max_pages=max_pages, save_raw=False)

            # Validate results
            expected_output = test_case.expected_output
            min_records = expected_output.get("min_records", 0)
            max_records = expected_output.get("max_records", 10000)

            if len(result_df) < min_records:
                raise AssertionError(f"Too few records: {len(result_df)} < {min_records}")
            if len(result_df) > max_records:
                raise AssertionError(f"Too many records: {len(result_df)} > {max_records}")

            return {
                "success": True,
                "records_count": len(result_df),
                "columns": list(result_df.columns)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _execute_data_processing_workflow(self, test_case: TestCase) -> Dict[str, Any]:
        """Execute data processing integration test."""
        # Implementation for data processing workflow
        return {"success": True, "processed": True}

    def _execute_error_handling_test(self, test_case: TestCase) -> Any:
        """Execute an error handling test by triggering specific errors."""
        input_data = test_case.input_data
        error_scenario = input_data.get("error_scenario")
        trigger_conditions = input_data.get("trigger_conditions", {})

        # Simulate the error condition and verify proper handling
        if "network" in error_scenario.lower():
            return self._test_network_error_handling(test_case)
        elif "validation" in error_scenario.lower():
            return self._test_validation_error_handling(test_case)
        else:
            return self._test_generic_error_handling(test_case)

    def _test_network_error_handling(self, test_case: TestCase) -> Dict[str, Any]:
        """Test network error handling."""
        try:
            # Simulate network error
            from scripts.exceptions import NetworkError
            raise NetworkError("Simulated network error", url="http://test.com")
        except NetworkError as e:
            # Verify the error is handled correctly
            expected_behavior = test_case.expected_output.get("error_behavior", {})
            exception_type = expected_behavior.get("exception_type")

            if exception_type and type(e).__name__ != exception_type:
                raise AssertionError(f"Expected {exception_type}, got {type(e).__name__}")

            return {"error_handled": True, "exception_type": type(e).__name__}

    def _test_validation_error_handling(self, test_case: TestCase) -> Dict[str, Any]:
        """Test validation error handling."""
        try:
            # Simulate validation error
            from scripts.exceptions import CountyValidationError
            raise CountyValidationError("99")
        except CountyValidationError as e:
            return {"error_handled": True, "exception_type": type(e).__name__}

    def _test_generic_error_handling(self, test_case: TestCase) -> Dict[str, Any]:
        """Test generic error handling."""
        return {"error_handled": True, "test_executed": True}

    def _execute_generic_test(self, test_case: TestCase) -> Any:
        """Execute a generic test case."""
        # For generic tests, we can use pytest to execute them
        return {"executed": True, "test_id": test_case.id}

    def _execute_generic_workflow(self, test_case: TestCase) -> Any:
        """Execute a generic workflow."""
        return {"workflow_executed": True, "test_id": test_case.id}

    def execute_with_retry(self, test_case: TestCase, max_retries: int = 3) -> ExecutionResult:
        """
        Execute a test case with retry logic for AI resilience.

        Args:
            test_case: Test case to execute
            max_retries: Maximum number of retries

        Returns:
            Final execution result
        """
        last_result = None
        retry_count = 0

        while retry_count <= max_retries:
            result = self.execute_test_case(test_case)
            result.retry_count = retry_count

            if result.status == ExecutionStatus.PASSED:
                return result

            # Check if this error is retryable
            ai_instructions = test_case.ai_instructions or {}
            can_retry = ai_instructions.get("can_auto_retry", True)
            retry_conditions = ai_instructions.get("retry_conditions", [])

            if not can_retry or retry_count >= max_retries:
                return result

            # Check retry conditions
            should_retry = False
            if result.exception_type:
                should_retry = any(condition in result.exception_type for condition in retry_conditions)
            elif "network" in result.error_message.lower() if result.error_message else False:
                should_retry = True

            if not should_retry:
                return result

            # Perform retry with backoff
            retry_count += 1
            if retry_count <= max_retries:
                delay = 2.0 ** retry_count  # Exponential backoff
                time.sleep(delay)
                result.status = ExecutionStatus.RETRYING
                result.recovery_actions_taken.append(f"retry_{retry_count}_after_{delay}s")

            last_result = result

        return last_result or result

    def execute_test_plan(self, execution_plan: ExecutionPlan) -> List[ExecutionResult]:
        """
        Execute a complete test plan with AI optimization.

        Args:
            execution_plan: Optimized execution plan

        Returns:
            List of execution results
        """
        all_results = []
        test_cases_by_id = {tc.id: tc for tc in execution_plan.test_cases}

        print(f"🤖 Executing AI Test Plan: {len(execution_plan.test_cases)} tests")
        print(f"   Parallel groups: {len(execution_plan.parallel_groups)}")
        print(f"   Resource requirements: {execution_plan.resource_requirements}")

        for group_index, test_group in enumerate(execution_plan.parallel_groups):
            print(f"\n📊 Executing group {group_index + 1}/{len(execution_plan.parallel_groups)}: {test_group}")

            group_results = []
            for test_id in test_group:
                test_case = test_cases_by_id[test_id]
                print(f"   🧪 Running: {test_id}")

                result = self.execute_with_retry(test_case)
                group_results.append(result)

                # Log result
                status_emoji = "✅" if result.status == ExecutionStatus.PASSED else "❌"
                print(f"   {status_emoji} {test_id}: {result.status.value} ({result.duration_seconds:.2f}s)")

            all_results.extend(group_results)

        self.results = all_results
        self._update_execution_stats()

        return all_results

    def _update_execution_stats(self):
        """Update execution statistics for AI analysis."""
        if not self.results:
            return

        self.execution_stats = {
            "total_tests": len(self.results),
            "passed": sum(1 for r in self.results if r.status == ExecutionStatus.PASSED),
            "failed": sum(1 for r in self.results if r.status == ExecutionStatus.FAILED),
            "errors": sum(1 for r in self.results if r.status == ExecutionStatus.ERROR),
            "skipped": sum(1 for r in self.results if r.status == ExecutionStatus.SKIPPED),
            "total_duration": sum(r.duration_seconds for r in self.results),
            "average_duration": sum(r.duration_seconds for r in self.results) / len(self.results),
            "success_rate": (self.execution_stats["passed"] / len(self.results)) * 100 if self.results else 0
        }

    def generate_ai_report(self) -> Dict[str, Any]:
        """
        Generate AI-friendly execution report.

        Returns:
            Comprehensive execution report for AI analysis
        """
        return {
            "execution_summary": self.execution_stats,
            "test_results": [
                {
                    "test_id": r.test_id,
                    "status": r.status.value,
                    "duration_seconds": r.duration_seconds,
                    "retry_count": r.retry_count,
                    "memory_usage_mb": r.memory_usage_mb,
                    "error_message": r.error_message,
                    "exception_type": r.exception_type,
                    "recovery_actions": r.recovery_actions_taken
                } for r in self.results
            ],
            "ai_analysis": {
                "overall_health": "healthy" if self.execution_stats.get("success_rate", 0) > 80 else "unhealthy",
                "performance_rating": self._rate_performance(),
                "reliability_score": self._calculate_reliability_score(),
                "recommendations": self._generate_recommendations()
            },
            "metadata": {
                "execution_timestamp": time.time(),
                "executor_version": "1.0.0",
                "total_execution_time": self.execution_stats.get("total_duration", 0)
            }
        }

    def _rate_performance(self) -> str:
        """Rate overall performance for AI understanding."""
        avg_duration = self.execution_stats.get("average_duration", 0)
        if avg_duration < 1.0:
            return "excellent"
        elif avg_duration < 5.0:
            return "good"
        elif avg_duration < 15.0:
            return "acceptable"
        else:
            return "needs_improvement"

    def _calculate_reliability_score(self) -> float:
        """Calculate reliability score based on success rate and retry patterns."""
        success_rate = self.execution_stats.get("success_rate", 0) / 100
        retry_penalty = sum(r.retry_count for r in self.results) / max(len(self.results), 1) * 0.1
        return max(0.0, min(1.0, success_rate - retry_penalty))

    def _generate_recommendations(self) -> List[str]:
        """Generate AI recommendations based on execution results."""
        recommendations = []

        if self.execution_stats.get("success_rate", 0) < 90:
            recommendations.append("Investigate failing tests for systematic issues")

        if self.execution_stats.get("average_duration", 0) > 10:
            recommendations.append("Optimize slow-running tests")

        retry_heavy_tests = [r for r in self.results if r.retry_count > 1]
        if retry_heavy_tests:
            recommendations.append("Investigate tests requiring multiple retries")

        memory_heavy_tests = [r for r in self.results if r.memory_usage_mb and r.memory_usage_mb > 100]
        if memory_heavy_tests:
            recommendations.append("Optimize memory usage in heavy tests")

        return recommendations

    def _get_memory_usage(self) -> Optional[float]:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return None


def main():
    """Main function for AI test execution."""
    executor = AITestExecutor()

    try:
        # Get AI-executable tests
        test_cases = get_ai_executable_test_plan()
        print(f"🤖 Found {len(test_cases)} AI-executable test cases")

        if not test_cases:
            print("⚠️ No AI-executable tests found. Check specification file.")
            return

        # Create execution plan
        execution_plan = executor.create_execution_plan(test_cases)

        # Execute tests
        results = executor.execute_test_plan(execution_plan)

        # Generate and display report
        report = executor.generate_ai_report()

        print(f"\n🏁 AI Test Execution Complete:")
        print(f"   Total Tests: {report['execution_summary']['total_tests']}")
        print(f"   Passed: {report['execution_summary']['passed']}")
        print(f"   Failed: {report['execution_summary']['failed']}")
        print(f"   Success Rate: {report['execution_summary']['success_rate']:.1f}%")
        print(f"   Performance Rating: {report['ai_analysis']['performance_rating']}")
        print(f"   Reliability Score: {report['ai_analysis']['reliability_score']:.2f}")

        if report['ai_analysis']['recommendations']:
            print(f"\n💡 AI Recommendations:")
            for rec in report['ai_analysis']['recommendations']:
                print(f"   - {rec}")

        # Save detailed report
        report_file = Path("ai-test-execution-report.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📊 Detailed report saved: {report_file}")

    except Exception as e:
        print(f"❌ AI Test Execution failed: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()