"""
Automated Parallel Test Execution Pipeline for Alabama Auction Watcher.

This module provides advanced parallel test execution capabilities with intelligent
test scheduling, performance monitoring, and comprehensive AI-friendly reporting.
Designed for CI/CD integration and autonomous testing workflows.

Features:
- Intelligent test categorization and parallel scheduling
- Resource-aware test execution optimization
- Real-time performance monitoring and reporting
- Comprehensive test result aggregation
- AI-friendly structured output and analysis
- Automated test discovery and execution strategies
"""

import asyncio
import json
import sys
import time
import threading
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Any, Optional
import multiprocessing
import psutil

# Import AI logging for structured reporting
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.ai_logging import get_ai_logger


@dataclass
class TestSuite:
    """Test suite configuration and metadata."""
    name: str
    pattern: str
    markers: List[str]
    parallel_capable: bool
    estimated_duration: float
    dependencies: List[str]
    priority: int
    resource_requirements: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TestResult:
    """Individual test execution result."""
    test_id: str
    suite_name: str
    status: str
    duration: float
    memory_usage: float
    error_message: Optional[str]
    performance_metrics: Dict[str, Any]
    ai_analysis: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionPlan:
    """Test execution plan with scheduling and resource allocation."""
    total_suites: int
    parallel_groups: List[List[TestSuite]]
    estimated_total_duration: float
    resource_allocation: Dict[str, Any]
    execution_strategy: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'parallel_groups': [[suite.to_dict() for suite in group] for group in self.parallel_groups]
        }


class TestScheduler:
    """Intelligent test scheduler for optimal parallel execution."""

    def __init__(self, max_workers: int = None):
        """Initialize the test scheduler."""
        self.max_workers = max_workers or min(multiprocessing.cpu_count(), 8)
        self.logger = get_ai_logger(__name__)
        self.resource_monitor = ResourceMonitor()

    def create_execution_plan(self, test_suites: List[TestSuite]) -> ExecutionPlan:
        """Create an optimized execution plan for test suites."""
        self.logger.info(f"Creating execution plan for {len(test_suites)} test suites")

        # Sort suites by priority and estimated duration
        sorted_suites = sorted(test_suites, key=lambda s: (s.priority, -s.estimated_duration))

        # Group suites for parallel execution
        parallel_groups = self._create_parallel_groups(sorted_suites)

        # Calculate estimated total duration
        estimated_duration = max(
            sum(suite.estimated_duration for suite in group)
            for group in parallel_groups
        ) if parallel_groups else 0

        # Determine execution strategy
        strategy = self._determine_execution_strategy(test_suites)

        # Calculate resource allocation
        resource_allocation = self._calculate_resource_allocation(parallel_groups)

        plan = ExecutionPlan(
            total_suites=len(test_suites),
            parallel_groups=parallel_groups,
            estimated_total_duration=estimated_duration,
            resource_allocation=resource_allocation,
            execution_strategy=strategy
        )

        self.logger.log_performance(
            "execution_plan_creation",
            duration_ms=0,  # Quick operation
            total_suites=len(test_suites),
            parallel_groups=len(parallel_groups)
        )

        return plan

    def _create_parallel_groups(self, test_suites: List[TestSuite]) -> List[List[TestSuite]]:
        """Create groups of test suites that can run in parallel."""
        groups = []
        remaining_suites = test_suites.copy()

        while remaining_suites:
            current_group = []
            current_resources = {
                'cpu_cores': 0,
                'memory_mb': 0,
                'network_slots': 0
            }

            for suite in remaining_suites[:]:
                # Check if suite can fit in current group
                if self._can_add_to_group(suite, current_group, current_resources):
                    current_group.append(suite)
                    remaining_suites.remove(suite)

                    # Update resource usage
                    req = suite.resource_requirements
                    current_resources['cpu_cores'] += req.get('cpu_cores', 1)
                    current_resources['memory_mb'] += req.get('memory_mb', 256)
                    current_resources['network_slots'] += req.get('network_slots', 0)

                    # Limit group size to prevent resource exhaustion
                    if len(current_group) >= self.max_workers:
                        break

            if current_group:
                groups.append(current_group)
            else:
                # If no suite could be added, take the first one to avoid infinite loop
                if remaining_suites:
                    groups.append([remaining_suites.pop(0)])

        return groups

    def _can_add_to_group(self, suite: TestSuite, group: List[TestSuite], resources: Dict[str, int]) -> bool:
        """Check if a suite can be added to the current parallel group."""
        # Check dependencies
        for dep in suite.dependencies:
            if any(dep in existing.name for existing in group):
                return False

        # Check resource constraints
        req = suite.resource_requirements
        available_cores = self.max_workers - resources['cpu_cores']
        available_memory = (psutil.virtual_memory().available / 1024 / 1024) - resources['memory_mb']

        if req.get('cpu_cores', 1) > available_cores:
            return False
        if req.get('memory_mb', 256) > available_memory * 0.8:  # Leave 20% buffer
            return False

        # Check if suite is parallel capable
        if not suite.parallel_capable and group:
            return False

        return True

    def _determine_execution_strategy(self, test_suites: List[TestSuite]) -> str:
        """Determine the best execution strategy based on test characteristics."""
        total_suites = len(test_suites)
        parallel_capable = sum(1 for s in test_suites if s.parallel_capable)
        avg_duration = sum(s.estimated_duration for s in test_suites) / total_suites if total_suites > 0 else 0

        if total_suites <= 5:
            return "sequential"
        elif parallel_capable / total_suites > 0.8 and avg_duration < 60:
            return "aggressive_parallel"
        elif parallel_capable / total_suites > 0.5:
            return "balanced_parallel"
        else:
            return "conservative_parallel"

    def _calculate_resource_allocation(self, parallel_groups: List[List[TestSuite]]) -> Dict[str, Any]:
        """Calculate optimal resource allocation for execution plan."""
        max_concurrent = max(len(group) for group in parallel_groups) if parallel_groups else 1
        total_memory_needed = 0
        total_cpu_cores = 0

        for group in parallel_groups:
            group_memory = sum(suite.resource_requirements.get('memory_mb', 256) for suite in group)
            group_cpu = sum(suite.resource_requirements.get('cpu_cores', 1) for suite in group)
            total_memory_needed = max(total_memory_needed, group_memory)
            total_cpu_cores = max(total_cpu_cores, group_cpu)

        return {
            'max_concurrent_suites': max_concurrent,
            'estimated_memory_mb': total_memory_needed,
            'estimated_cpu_cores': total_cpu_cores,
            'worker_allocation': min(self.max_workers, max_concurrent)
        }


class ResourceMonitor:
    """Real-time resource monitoring during test execution."""

    def __init__(self):
        """Initialize the resource monitor."""
        self.monitoring = False
        self.metrics = defaultdict(list)
        self.start_time = None

    def start_monitoring(self) -> None:
        """Start resource monitoring."""
        self.monitoring = True
        self.start_time = time.time()
        self.metrics.clear()

        # Start monitoring thread
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return collected metrics."""
        self.monitoring = False

        if not self.metrics:
            return {}

        # Calculate summary statistics
        return {
            'duration_seconds': time.time() - self.start_time if self.start_time else 0,
            'cpu_usage': {
                'max': max(self.metrics['cpu']) if self.metrics['cpu'] else 0,
                'avg': sum(self.metrics['cpu']) / len(self.metrics['cpu']) if self.metrics['cpu'] else 0,
                'min': min(self.metrics['cpu']) if self.metrics['cpu'] else 0
            },
            'memory_usage_mb': {
                'max': max(self.metrics['memory']) if self.metrics['memory'] else 0,
                'avg': sum(self.metrics['memory']) / len(self.metrics['memory']) if self.metrics['memory'] else 0,
                'min': min(self.metrics['memory']) if self.metrics['memory'] else 0
            },
            'sample_count': len(self.metrics['cpu'])
        }

    def _monitor_loop(self) -> None:
        """Monitoring loop running in background thread."""
        while self.monitoring:
            try:
                # Collect CPU and memory metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_mb = psutil.virtual_memory().used / 1024 / 1024

                self.metrics['cpu'].append(cpu_percent)
                self.metrics['memory'].append(memory_mb)

                time.sleep(2)  # Monitor every 2 seconds

            except Exception:
                # Continue monitoring despite errors
                pass


class ParallelTestExecutor:
    """Advanced parallel test executor with AI-friendly reporting."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the parallel test executor."""
        self.config = config or self._default_config()
        self.logger = get_ai_logger(__name__)
        self.scheduler = TestScheduler(max_workers=self.config['max_workers'])
        self.resource_monitor = ResourceMonitor()
        self.test_suites = self._discover_test_suites()
        self.results = []
        self.execution_plan = None

    def _default_config(self) -> Dict[str, Any]:
        """Get default configuration for the executor."""
        return {
            'max_workers': min(multiprocessing.cpu_count(), 8),
            'timeout_seconds': 1800,  # 30 minutes
            'retry_failed_tests': True,
            'max_retries': 2,
            'coverage_threshold': 95,
            'performance_monitoring': True,
            'ai_reporting': True,
            'output_formats': ['json', 'html', 'xml'],
            'parallel_strategy': 'auto'
        }

    def _discover_test_suites(self) -> List[TestSuite]:
        """Discover and categorize test suites."""
        suites = []

        # Unit tests - fast, highly parallel
        suites.append(TestSuite(
            name="unit_tests",
            pattern="tests/unit/",
            markers=["unit"],
            parallel_capable=True,
            estimated_duration=120.0,
            dependencies=[],
            priority=1,
            resource_requirements={'cpu_cores': 2, 'memory_mb': 512, 'network_slots': 0}
        ))

        # Integration tests - moderate speed, parallel with constraints
        suites.append(TestSuite(
            name="integration_tests",
            pattern="tests/integration/",
            markers=["integration"],
            parallel_capable=True,
            estimated_duration=300.0,
            dependencies=[],
            priority=2,
            resource_requirements={'cpu_cores': 2, 'memory_mb': 768, 'network_slots': 1}
        ))

        # End-to-end tests - slower, limited parallelism
        suites.append(TestSuite(
            name="e2e_tests",
            pattern="tests/e2e/",
            markers=["e2e"],
            parallel_capable=True,
            estimated_duration=600.0,
            dependencies=[],
            priority=3,
            resource_requirements={'cpu_cores': 3, 'memory_mb': 1024, 'network_slots': 2}
        ))

        # Benchmark tests - resource intensive, run separately
        suites.append(TestSuite(
            name="benchmark_tests",
            pattern="tests/benchmarks/",
            markers=["benchmark"],
            parallel_capable=False,
            estimated_duration=480.0,
            dependencies=[],
            priority=4,
            resource_requirements={'cpu_cores': 4, 'memory_mb': 2048, 'network_slots': 0}
        ))

        # AI tests - specialized tests for AI functionality
        suites.append(TestSuite(
            name="ai_tests",
            pattern="tests/",
            markers=["ai_test"],
            parallel_capable=True,
            estimated_duration=180.0,
            dependencies=[],
            priority=2,
            resource_requirements={'cpu_cores': 2, 'memory_mb': 768, 'network_slots': 0}
        ))

        return suites

    async def execute_all_tests(self) -> Dict[str, Any]:
        """Execute all test suites with optimal parallel scheduling."""
        self.logger.info("Starting parallel test execution pipeline")

        # Create execution plan
        self.execution_plan = self.scheduler.create_execution_plan(self.test_suites)
        self.logger.info(f"Execution plan created: {self.execution_plan.execution_strategy}")

        # Start resource monitoring
        self.resource_monitor.start_monitoring()

        start_time = time.time()
        all_results = []

        try:
            # Execute parallel groups sequentially
            for group_idx, suite_group in enumerate(self.execution_plan.parallel_groups):
                self.logger.info(f"Executing parallel group {group_idx + 1}/{len(self.execution_plan.parallel_groups)}")

                # Execute suites in this group in parallel
                group_results = await self._execute_parallel_group(suite_group)
                all_results.extend(group_results)

                # Brief pause between groups for resource cleanup
                if group_idx < len(self.execution_plan.parallel_groups) - 1:
                    await asyncio.sleep(2)

        except Exception as e:
            self.logger.log_error_with_ai_context(e, "parallel_test_execution")
            raise

        finally:
            # Stop resource monitoring
            resource_metrics = self.resource_monitor.stop_monitoring()

        # Compile final results
        execution_summary = self._compile_execution_summary(
            all_results, time.time() - start_time, resource_metrics
        )

        self.logger.log_performance(
            "complete_test_execution",
            duration_ms=(time.time() - start_time) * 1000,
            total_suites=len(self.test_suites),
            total_tests=execution_summary.get('total_tests', 0)
        )

        return execution_summary

    async def _execute_parallel_group(self, suite_group: List[TestSuite]) -> List[TestResult]:
        """Execute a group of test suites in parallel."""
        if not suite_group:
            return []

        self.logger.info(f"Executing {len(suite_group)} suites in parallel")

        # Create tasks for parallel execution
        tasks = []
        for suite in suite_group:
            task = asyncio.create_task(self._execute_test_suite(suite))
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Create error result
                error_result = TestResult(
                    test_id=f"suite_error_{i}",
                    suite_name=suite_group[i].name,
                    status="error",
                    duration=0.0,
                    memory_usage=0.0,
                    error_message=str(result),
                    performance_metrics={},
                    ai_analysis={'error_type': type(result).__name__}
                )
                processed_results.append(error_result)
            else:
                processed_results.extend(result)

        return processed_results

    async def _execute_test_suite(self, suite: TestSuite) -> List[TestResult]:
        """Execute a single test suite."""
        self.logger.info(f"Executing test suite: {suite.name}")

        start_time = time.time()
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Build pytest command
        cmd = self._build_pytest_command(suite)

        try:
            # Execute pytest
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate()

            end_time = time.time()
            end_memory = process.memory_info().rss / 1024 / 1024  # MB
            duration = end_time - start_time
            memory_usage = end_memory - start_memory

            # Parse results
            test_results = self._parse_suite_results(
                suite, result.returncode, stdout.decode(), stderr.decode(),
                duration, memory_usage
            )

            self.logger.log_performance(
                f"test_suite_{suite.name}",
                duration_ms=duration * 1000,
                memory_usage_mb=memory_usage,
                exit_code=result.returncode
            )

            return test_results

        except Exception as e:
            self.logger.log_error_with_ai_context(e, f"test_suite_execution_{suite.name}")

            # Return error result
            return [TestResult(
                test_id=f"{suite.name}_execution_error",
                suite_name=suite.name,
                status="error",
                duration=time.time() - start_time,
                memory_usage=0.0,
                error_message=str(e),
                performance_metrics={},
                ai_analysis={'error_category': 'execution_error'}
            )]

    def _build_pytest_command(self, suite: TestSuite) -> List[str]:
        """Build pytest command for a test suite."""
        cmd = [sys.executable, "-m", "pytest", suite.pattern]

        # Add markers
        if suite.markers:
            for marker in suite.markers:
                cmd.extend(["-m", marker])

        # Add parallel execution for parallel-capable suites
        if suite.parallel_capable:
            worker_count = min(self.config['max_workers'] // 2, 4)  # Conservative allocation
            cmd.extend(["-n", str(worker_count)])

        # Add output options
        cmd.extend([
            "--tb=short",
            "--json-report",
            f"--json-report-file=results_{suite.name}.json",
            "--quiet"
        ])

        # Add timeout
        if self.config.get('timeout_seconds'):
            cmd.extend(["--timeout", str(self.config['timeout_seconds'] // len(self.test_suites))])

        return cmd

    def _parse_suite_results(self, suite: TestSuite, exit_code: int, stdout: str, stderr: str,
                           duration: float, memory_usage: float) -> List[TestResult]:
        """Parse test suite results from pytest output."""
        results = []

        # Try to load JSON report
        json_file = Path(f"results_{suite.name}.json")
        if json_file.exists():
            try:
                with open(json_file, 'r') as f:
                    pytest_data = json.load(f)

                # Extract individual test results
                tests = pytest_data.get('tests', [])
                for test in tests:
                    result = TestResult(
                        test_id=test.get('nodeid', 'unknown'),
                        suite_name=suite.name,
                        status=test.get('outcome', 'unknown'),
                        duration=test.get('duration', 0.0),
                        memory_usage=memory_usage / len(tests) if tests else memory_usage,
                        error_message=test.get('call', {}).get('longrepr') if test.get('outcome') == 'failed' else None,
                        performance_metrics={
                            'setup_duration': test.get('setup', {}).get('duration', 0.0),
                            'call_duration': test.get('call', {}).get('duration', 0.0),
                            'teardown_duration': test.get('teardown', {}).get('duration', 0.0)
                        },
                        ai_analysis=self._analyze_test_result(test)
                    )
                    results.append(result)

                # Clean up JSON file
                json_file.unlink()

            except Exception as e:
                self.logger.log_error_with_ai_context(e, f"parse_results_{suite.name}")

        # If no individual results, create suite-level result
        if not results:
            results.append(TestResult(
                test_id=f"{suite.name}_suite",
                suite_name=suite.name,
                status="passed" if exit_code == 0 else "failed",
                duration=duration,
                memory_usage=memory_usage,
                error_message=stderr if exit_code != 0 else None,
                performance_metrics={'total_duration': duration},
                ai_analysis={'suite_level': True, 'exit_code': exit_code}
            ))

        return results

    def _analyze_test_result(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze individual test result for AI insights."""
        analysis = {
            'complexity_score': 0.0,
            'reliability_score': 1.0,
            'performance_category': 'normal',
            'risk_factors': []
        }

        # Analyze duration
        duration = test_data.get('call', {}).get('duration', 0.0)
        if duration > 30:
            analysis['performance_category'] = 'slow'
            analysis['risk_factors'].append('long_execution_time')
        elif duration > 10:
            analysis['performance_category'] = 'moderate'

        # Analyze failure patterns
        if test_data.get('outcome') == 'failed':
            analysis['reliability_score'] = 0.0
            error_info = test_data.get('call', {}).get('longrepr', '')
            if 'timeout' in error_info.lower():
                analysis['risk_factors'].append('timeout_failure')
            if 'memory' in error_info.lower():
                analysis['risk_factors'].append('memory_issue')

        return analysis

    def _compile_execution_summary(self, all_results: List[TestResult],
                                 total_duration: float, resource_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Compile comprehensive execution summary."""
        # Aggregate results by status
        status_counts = defaultdict(int)
        suite_summaries = defaultdict(lambda: {'passed': 0, 'failed': 0, 'error': 0, 'skipped': 0})

        for result in all_results:
            status_counts[result.status] += 1
            suite_summaries[result.suite_name][result.status] += 1

        # Calculate performance metrics
        total_tests = len(all_results)
        success_rate = (status_counts['passed'] / total_tests * 100) if total_tests > 0 else 0
        tests_per_second = total_tests / total_duration if total_duration > 0 else 0

        # Generate AI analysis
        ai_analysis = self._generate_execution_analysis(all_results, resource_metrics)

        summary = {
            'execution_metadata': {
                'timestamp': time.time(),
                'total_duration_seconds': total_duration,
                'execution_plan': self.execution_plan.to_dict() if self.execution_plan else {},
                'config': self.config
            },
            'test_summary': {
                'total_tests': total_tests,
                'passed': status_counts['passed'],
                'failed': status_counts['failed'],
                'error': status_counts['error'],
                'skipped': status_counts['skipped'],
                'success_rate_percent': success_rate
            },
            'performance_metrics': {
                'total_duration_seconds': total_duration,
                'tests_per_second': tests_per_second,
                'resource_usage': resource_metrics,
                'parallel_efficiency': self._calculate_parallel_efficiency(total_duration)
            },
            'suite_summaries': dict(suite_summaries),
            'detailed_results': [result.to_dict() for result in all_results],
            'ai_analysis': ai_analysis
        }

        return summary

    def _generate_execution_analysis(self, results: List[TestResult],
                                   resource_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI analysis of the execution."""
        analysis = {
            'overall_health': 'healthy',
            'performance_rating': 'good',
            'reliability_score': 1.0,
            'recommendations': [],
            'optimization_opportunities': [],
            'risk_factors': []
        }

        # Analyze failure patterns
        failed_tests = [r for r in results if r.status == 'failed']
        if failed_tests:
            failure_rate = len(failed_tests) / len(results)
            if failure_rate > 0.1:
                analysis['overall_health'] = 'unhealthy'
                analysis['risk_factors'].append('high_failure_rate')
            elif failure_rate > 0.05:
                analysis['overall_health'] = 'degraded'

        # Analyze performance
        total_duration = sum(r.duration for r in results)
        avg_duration = total_duration / len(results) if results else 0

        if avg_duration > 30:
            analysis['performance_rating'] = 'needs_improvement'
            analysis['optimization_opportunities'].append('test_performance_optimization')
        elif avg_duration > 10:
            analysis['performance_rating'] = 'acceptable'

        # Analyze resource usage
        if resource_metrics:
            max_memory = resource_metrics.get('memory_usage_mb', {}).get('max', 0)
            if max_memory > 4096:  # 4GB
                analysis['risk_factors'].append('high_memory_usage')
                analysis['recommendations'].append('optimize_memory_usage')

        # Calculate reliability score
        if results:
            passed_count = sum(1 for r in results if r.status == 'passed')
            analysis['reliability_score'] = passed_count / len(results)

        return analysis

    def _calculate_parallel_efficiency(self, actual_duration: float) -> float:
        """Calculate parallel execution efficiency."""
        if not self.execution_plan:
            return 0.0

        estimated_sequential = sum(suite.estimated_duration for suite in self.test_suites)
        if estimated_sequential == 0:
            return 1.0

        efficiency = estimated_sequential / actual_duration if actual_duration > 0 else 0.0
        return min(efficiency, self.config['max_workers'])  # Cap at theoretical maximum

    def generate_reports(self, summary: Dict[str, Any], output_dir: str = "test_reports") -> None:
        """Generate comprehensive test reports in multiple formats."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # Generate JSON report (AI-friendly)
        json_report_path = output_path / "parallel_test_report.json"
        with open(json_report_path, 'w') as f:
            json.dump(summary, f, indent=2)

        # Generate summary report
        summary_path = output_path / "execution_summary.txt"
        with open(summary_path, 'w') as f:
            self._write_text_summary(f, summary)

        # Generate performance report
        perf_path = output_path / "performance_analysis.json"
        with open(perf_path, 'w') as f:
            json.dump({
                'performance_metrics': summary['performance_metrics'],
                'ai_analysis': summary['ai_analysis'],
                'execution_plan': summary['execution_metadata']['execution_plan']
            }, f, indent=2)

        self.logger.info(f"Test reports generated in {output_dir}")

    def _write_text_summary(self, file, summary: Dict[str, Any]) -> None:
        """Write human-readable text summary."""
        test_summary = summary['test_summary']
        perf_metrics = summary['performance_metrics']

        file.write("=== PARALLEL TEST EXECUTION SUMMARY ===\n\n")

        file.write(f"Total Tests: {test_summary['total_tests']}\n")
        file.write(f"Passed: {test_summary['passed']}\n")
        file.write(f"Failed: {test_summary['failed']}\n")
        file.write(f"Errors: {test_summary['error']}\n")
        file.write(f"Success Rate: {test_summary['success_rate_percent']:.1f}%\n\n")

        file.write(f"Execution Time: {perf_metrics['total_duration_seconds']:.2f} seconds\n")
        file.write(f"Tests per Second: {perf_metrics['tests_per_second']:.2f}\n")
        file.write(f"Parallel Efficiency: {perf_metrics['parallel_efficiency']:.2f}x\n\n")

        # Suite summaries
        file.write("Suite Summaries:\n")
        for suite_name, suite_data in summary['suite_summaries'].items():
            total = sum(suite_data.values())
            file.write(f"  {suite_name}: {total} tests ({suite_data['passed']} passed, {suite_data['failed']} failed)\n")


async def main():
    """Main entry point for parallel test execution."""
    executor = ParallelTestExecutor()

    try:
        # Execute all tests
        results = await executor.execute_all_tests()

        # Generate reports
        executor.generate_reports(results)

        # Print summary
        test_summary = results['test_summary']
        print(f"\n🏁 Parallel Test Execution Complete:")
        print(f"   Total Tests: {test_summary['total_tests']}")
        print(f"   Passed: {test_summary['passed']}")
        print(f"   Failed: {test_summary['failed']}")
        print(f"   Success Rate: {test_summary['success_rate_percent']:.1f}%")
        print(f"   Duration: {results['performance_metrics']['total_duration_seconds']:.2f}s")
        print(f"   Tests/sec: {results['performance_metrics']['tests_per_second']:.2f}")

        # Return appropriate exit code
        return 0 if test_summary['failed'] == 0 else 1

    except Exception as e:
        print(f"❌ Execution failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)