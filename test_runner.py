#!/usr/bin/env python3
"""
AI-Testable Test Runner for Alabama Auction Watcher

This script provides an AI-friendly interface for running tests with
comprehensive reporting and performance metrics.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

import psutil


class AITestRunner:
    """Enhanced test runner with AI-friendly features and reporting."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the test runner with configuration."""
        self.start_time = time.time()
        self.config = self._load_config(config_path)
        self.results = {
            "summary": {},
            "performance_metrics": {},
            "test_results": [],
            "ai_analysis": {}
        }

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load test configuration."""
        default_config = {
            "parallel_execution": True,
            "max_workers": 4,
            "coverage_threshold": 95,
            "performance_monitoring": True,
            "ai_reporting": True,
            "timeout_seconds": 3600,
            "retry_failed_tests": True,
            "max_retries": 3
        }

        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)

        return default_config

    def run_tests(self, test_pattern: str = "tests/", markers: List[str] = None,
                 verbose: bool = True) -> Dict[str, Any]:
        """
        Run tests with AI-friendly reporting.

        Args:
            test_pattern: Test file pattern to run
            markers: Pytest markers to filter tests
            verbose: Enable verbose output

        Returns:
            Comprehensive test results for AI analysis
        """
        print(f"AI Test Runner Starting - Pattern: {test_pattern}")

        # Build pytest command
        cmd = self._build_pytest_command(test_pattern, markers, verbose)

        # Monitor system resources
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        start_cpu = psutil.cpu_percent()

        # Execute tests
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=self.config["timeout_seconds"])
        end_time = time.time()

        # Calculate performance metrics
        end_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_usage = end_memory - start_memory

        # Parse results
        self._parse_test_results(result, end_time - start_time, memory_usage)

        # Generate AI analysis
        self._generate_ai_analysis()

        return self.results

    def _build_pytest_command(self, test_pattern: str, markers: List[str],
                            verbose: bool) -> List[str]:
        """Build the pytest command with appropriate flags."""
        cmd = ["python", "-m", "pytest", test_pattern]

        # Add markers
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])

        # Add parallel execution if configured
        if self.config["parallel_execution"]:
            cmd.extend(["-n", str(self.config["max_workers"])])

        # Add verbosity
        if verbose:
            cmd.append("-v")

        return cmd

    def _parse_test_results(self, result: subprocess.CompletedProcess,
                          duration: float, memory_usage: float) -> None:
        """Parse pytest output and extract results."""
        self.results["summary"] = {
            "exit_code": result.returncode,
            "duration_seconds": duration,
            "success": result.returncode == 0
        }

        self.results["performance_metrics"] = {
            "execution_time": duration,
            "memory_usage_mb": memory_usage,
            "tests_per_second": 0  # Will be calculated from pytest output
        }

        # Parse pytest JSON report if available
        json_report_path = Path("test-results.json")
        if json_report_path.exists():
            with open(json_report_path, 'r') as f:
                pytest_data = json.load(f)
                self._extract_pytest_metrics(pytest_data)

        # Store output for AI analysis
        self.results["stdout"] = result.stdout
        self.results["stderr"] = result.stderr

    def _extract_pytest_metrics(self, pytest_data: Dict[str, Any]) -> None:
        """Extract metrics from pytest JSON report."""
        summary = pytest_data.get("summary", {})

        self.results["summary"].update({
            "total_tests": summary.get("total", 0),
            "passed": summary.get("passed", 0),
            "failed": summary.get("failed", 0),
            "skipped": summary.get("skipped", 0),
            "errors": summary.get("error", 0)
        })

        # Calculate test execution rate
        if self.results["summary"]["total_tests"] > 0:
            self.results["performance_metrics"]["tests_per_second"] = (
                self.results["summary"]["total_tests"] /
                self.results["performance_metrics"]["execution_time"]
            )

        # Extract individual test results
        self.results["test_results"] = pytest_data.get("tests", [])

    def _generate_ai_analysis(self) -> None:
        """Generate AI-friendly analysis of test results."""
        summary = self.results["summary"]
        metrics = self.results["performance_metrics"]

        analysis = {
            "overall_health": "healthy" if summary.get("success", False) else "unhealthy",
            "performance_rating": self._rate_performance(metrics),
            "recommendations": [],
            "actionable_items": [],
            "risk_factors": []
        }

        # Performance analysis
        if metrics.get("execution_time", 0) > 300:  # 5 minutes
            analysis["recommendations"].append("Consider optimizing slow tests")
            analysis["actionable_items"].append("identify_slow_tests")

        if metrics.get("memory_usage_mb", 0) > 1000:  # 1GB
            analysis["recommendations"].append("Memory usage is high - check for memory leaks")
            analysis["risk_factors"].append("high_memory_usage")

        # Failure analysis
        if summary.get("failed", 0) > 0:
            analysis["actionable_items"].append("analyze_failed_tests")
            analysis["risk_factors"].append("test_failures")

        # Coverage analysis
        coverage_path = Path("coverage.xml")
        if coverage_path.exists():
            # Could parse coverage here for AI analysis
            pass

        self.results["ai_analysis"] = analysis

    def _rate_performance(self, metrics: Dict[str, Any]) -> str:
        """Rate overall performance for AI understanding."""
        execution_time = metrics.get("execution_time", 0)
        tests_per_second = metrics.get("tests_per_second", 0)

        if execution_time < 60 and tests_per_second > 5:
            return "excellent"
        elif execution_time < 180 and tests_per_second > 2:
            return "good"
        elif execution_time < 300 and tests_per_second > 1:
            return "acceptable"
        else:
            return "needs_improvement"

    def generate_ai_report(self, output_path: str = "ai-test-report.json") -> None:
        """Generate a comprehensive AI-readable report."""
        report = {
            "metadata": {
                "timestamp": time.time(),
                "runner_version": "1.0.0",
                "python_version": sys.version,
                "platform": sys.platform
            },
            "test_execution": self.results,
            "ai_recommendations": self._generate_detailed_recommendations()
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"📊 AI Test Report generated: {output_path}")

    def _generate_detailed_recommendations(self) -> Dict[str, Any]:
        """Generate detailed recommendations for AI consumption."""
        return {
            "immediate_actions": [],
            "optimization_opportunities": [],
            "maintenance_tasks": [],
            "monitoring_suggestions": []
        }


def main():
    """CLI interface for the AI test runner."""
    parser = argparse.ArgumentParser(description="AI-Testable Test Runner")
    parser.add_argument("--pattern", default="tests/", help="Test pattern to run")
    parser.add_argument("--markers", nargs="*", help="Pytest markers to filter")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--ai-report", action="store_true", help="Generate AI report")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    runner = AITestRunner(config_path=args.config)
    results = runner.run_tests(
        test_pattern=args.pattern,
        markers=args.markers,
        verbose=args.verbose
    )

    # Print summary
    summary = results["summary"]
    print(f"\nTest Execution Complete:")
    print(f"   Success: {summary.get('success', False)}")
    print(f"   Duration: {summary.get('duration_seconds', 0):.2f}s")
    print(f"   Tests: {summary.get('total_tests', 0)}")
    print(f"   Passed: {summary.get('passed', 0)}")
    print(f"   Failed: {summary.get('failed', 0)}")

    # Generate AI report if requested
    if args.ai_report:
        runner.generate_ai_report()

    # Exit with appropriate code
    sys.exit(0 if summary.get("success", False) else 1)


if __name__ == "__main__":
    main()