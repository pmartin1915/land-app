#!/usr/bin/env python3
"""
Parallel Test Execution Runner Script for Alabama Auction Watcher.

This script provides a convenient interface for running the parallel test execution
pipeline with various configuration options and AI-friendly reporting.

Usage:
    python run_parallel_tests.py [options]

Examples:
    # Run all tests with default configuration
    python run_parallel_tests.py

    # Run only unit tests with verbose output
    python run_parallel_tests.py --suite unit_tests --verbose

    # Run tests with custom configuration
    python run_parallel_tests.py --config custom_test_config.json

    # Run tests with coverage report
    python run_parallel_tests.py --coverage --threshold 95

    # Run in CI mode with parallel execution
    python run_parallel_tests.py --ci-mode --workers 8
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scripts.parallel_test_executor import ParallelTestExecutor, TestSuite
from config.ai_logging import get_ai_logger


class TestExecutionCLI:
    """Command-line interface for parallel test execution."""

    def __init__(self):
        """Initialize the CLI."""
        self.logger = get_ai_logger(__name__)

    def parse_arguments(self) -> argparse.Namespace:
        """Parse command-line arguments."""
        parser = argparse.ArgumentParser(
            description="Alabama Auction Watcher Parallel Test Execution Pipeline",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s                              # Run all tests
  %(prog)s --suite unit_tests           # Run only unit tests
  %(prog)s --ci-mode                    # Run in CI mode
  %(prog)s --coverage --threshold 95    # Run with 95%% coverage requirement
  %(prog)s --workers 4 --timeout 1200   # Custom workers and timeout
            """
        )

        # Test selection options
        test_group = parser.add_argument_group('Test Selection')
        test_group.add_argument(
            '--suite',
            choices=['unit_tests', 'integration_tests', 'e2e_tests', 'benchmark_tests', 'ai_tests', 'all'],
            default='all',
            help='Test suite to run (default: all)'
        )
        test_group.add_argument(
            '--markers',
            nargs='*',
            help='Pytest markers to filter tests'
        )
        test_group.add_argument(
            '--pattern',
            help='Custom test file pattern to run'
        )

        # Execution options
        exec_group = parser.add_argument_group('Execution Options')
        exec_group.add_argument(
            '--workers',
            type=int,
            help='Number of parallel workers (default: auto-detect)'
        )
        exec_group.add_argument(
            '--timeout',
            type=int,
            default=1800,
            help='Timeout in seconds (default: 1800)'
        )
        exec_group.add_argument(
            '--ci-mode',
            action='store_true',
            help='Run in CI mode with optimized settings'
        )
        exec_group.add_argument(
            '--no-parallel',
            action='store_true',
            help='Disable parallel execution'
        )

        # Coverage options
        coverage_group = parser.add_argument_group('Coverage Options')
        coverage_group.add_argument(
            '--coverage',
            action='store_true',
            help='Enable coverage reporting'
        )
        coverage_group.add_argument(
            '--threshold',
            type=float,
            default=95.0,
            help='Coverage threshold percentage (default: 95.0)'
        )
        coverage_group.add_argument(
            '--coverage-fail',
            action='store_true',
            help='Fail if coverage threshold is not met'
        )

        # Reporting options
        report_group = parser.add_argument_group('Reporting Options')
        report_group.add_argument(
            '--output-dir',
            default='test_reports',
            help='Output directory for reports (default: test_reports)'
        )
        report_group.add_argument(
            '--format',
            choices=['json', 'html', 'xml', 'all'],
            default='all',
            help='Report format (default: all)'
        )
        report_group.add_argument(
            '--ai-report',
            action='store_true',
            help='Generate AI-friendly analysis report'
        )

        # Configuration options
        config_group = parser.add_argument_group('Configuration')
        config_group.add_argument(
            '--config',
            help='Path to test configuration file'
        )
        config_group.add_argument(
            '--env',
            choices=['development', 'ci', 'production'],
            default='development',
            help='Environment configuration (default: development)'
        )

        # Output options
        output_group = parser.add_argument_group('Output Options')
        output_group.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Verbose output'
        )
        output_group.add_argument(
            '--quiet', '-q',
            action='store_true',
            help='Quiet output (minimal logging)'
        )
        output_group.add_argument(
            '--no-color',
            action='store_true',
            help='Disable colored output'
        )

        # Development and debugging options
        debug_group = parser.add_argument_group('Debug Options')
        debug_group.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be executed without running tests'
        )
        debug_group.add_argument(
            '--list-suites',
            action='store_true',
            help='List available test suites and exit'
        )
        debug_group.add_argument(
            '--validate-config',
            action='store_true',
            help='Validate configuration and exit'
        )

        return parser.parse_args()

    def load_configuration(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Load and merge configuration from various sources."""
        # Start with default configuration
        config = {
            'max_workers': args.workers or 4,
            'timeout_seconds': args.timeout,
            'parallel_execution': not args.no_parallel,
            'coverage_enabled': args.coverage,
            'coverage_threshold': args.threshold,
            'output_directory': args.output_dir,
            'ai_reporting': args.ai_report,
            'verbose': args.verbose,
            'quiet': args.quiet
        }

        # Load configuration file if specified
        if args.config:
            config_path = Path(args.config)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                    # Merge file configuration
                    self._merge_config(config, file_config)
            else:
                print(f"Warning: Configuration file not found: {args.config}")

        # Apply CI mode optimizations
        if args.ci_mode:
            config.update({
                'max_workers': args.workers or 8,
                'timeout_seconds': args.timeout,
                'coverage_enabled': True,
                'coverage_threshold': 95.0,
                'ai_reporting': True,
                'parallel_execution': True
            })

        # Apply environment-specific settings
        env_config = self._get_environment_config(args.env)
        self._merge_config(config, env_config)

        return config

    def _merge_config(self, base_config: Dict[str, Any], override_config: Dict[str, Any]) -> None:
        """Merge configuration dictionaries."""
        for key, value in override_config.items():
            if isinstance(value, dict) and key in base_config and isinstance(base_config[key], dict):
                self._merge_config(base_config[key], value)
            else:
                base_config[key] = value

    def _get_environment_config(self, environment: str) -> Dict[str, Any]:
        """Get environment-specific configuration."""
        env_configs = {
            'development': {
                'max_workers': 4,
                'timeout_seconds': 3600,
                'coverage_threshold': 85.0
            },
            'ci': {
                'max_workers': 8,
                'timeout_seconds': 1800,
                'coverage_threshold': 95.0,
                'parallel_execution': True,
                'ai_reporting': True
            },
            'production': {
                'max_workers': 16,
                'timeout_seconds': 1200,
                'coverage_threshold': 98.0,
                'parallel_execution': True,
                'ai_reporting': True
            }
        }
        return env_configs.get(environment, {})

    def list_available_suites(self, executor: ParallelTestExecutor) -> None:
        """List available test suites."""
        print("Available Test Suites:")
        print("=" * 50)

        for suite in executor.test_suites:
            print(f"📦 {suite.name}")
            print(f"   Pattern: {suite.pattern}")
            print(f"   Markers: {', '.join(suite.markers)}")
            print(f"   Parallel: {'Yes' if suite.parallel_capable else 'No'}")
            print(f"   Duration: {suite.estimated_duration:.0f}s")
            print(f"   Priority: {suite.priority}")
            print()

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate configuration settings."""
        print("Validating Configuration:")
        print("=" * 30)

        # Check required settings
        required_keys = ['max_workers', 'timeout_seconds', 'output_directory']
        for key in required_keys:
            if key not in config:
                print(f"❌ Missing required setting: {key}")
                return False
            print(f"✅ {key}: {config[key]}")

        # Validate worker count
        if config['max_workers'] < 1 or config['max_workers'] > 32:
            print(f"❌ Invalid worker count: {config['max_workers']} (must be 1-32)")
            return False

        # Validate timeout
        if config['timeout_seconds'] < 60:
            print(f"❌ Invalid timeout: {config['timeout_seconds']} (must be >= 60)")
            return False

        # Validate coverage threshold
        if 'coverage_threshold' in config:
            threshold = config['coverage_threshold']
            if threshold < 0 or threshold > 100:
                print(f"❌ Invalid coverage threshold: {threshold}% (must be 0-100)")
                return False

        print("✅ Configuration is valid")
        return True

    def create_filtered_suites(self, executor: ParallelTestExecutor, args: argparse.Namespace) -> None:
        """Filter test suites based on command-line arguments."""
        if args.suite != 'all':
            # Filter to specific suite
            executor.test_suites = [s for s in executor.test_suites if s.name == args.suite]

        if args.markers:
            # Filter by markers
            executor.test_suites = [
                s for s in executor.test_suites
                if any(marker in s.markers for marker in args.markers)
            ]

        if args.pattern:
            # Override patterns
            for suite in executor.test_suites:
                suite.pattern = args.pattern

    def display_execution_plan(self, executor: ParallelTestExecutor) -> None:
        """Display the execution plan."""
        if not hasattr(executor, 'execution_plan') or not executor.execution_plan:
            return

        plan = executor.execution_plan
        print("\nExecution Plan:")
        print("=" * 40)
        print(f"Strategy: {plan.execution_strategy}")
        print(f"Total Suites: {plan.total_suites}")
        print(f"Parallel Groups: {len(plan.parallel_groups)}")
        print(f"Estimated Duration: {plan.estimated_total_duration:.0f}s")
        print(f"Workers Allocated: {plan.resource_allocation.get('worker_allocation', 'auto')}")
        print()

        for i, group in enumerate(plan.parallel_groups):
            print(f"Group {i + 1}: {', '.join(suite.name for suite in group)}")

    async def run_tests(self, args: argparse.Namespace) -> int:
        """Run the test execution pipeline."""
        try:
            # Load configuration
            config = self.load_configuration(args)

            # Validate configuration if requested
            if args.validate_config:
                return 0 if self.validate_configuration(config) else 1

            # Create executor
            executor = ParallelTestExecutor(config)

            # List suites if requested
            if args.list_suites:
                self.list_available_suites(executor)
                return 0

            # Filter suites based on arguments
            self.create_filtered_suites(executor, args)

            if not executor.test_suites:
                print("❌ No test suites found matching criteria")
                return 1

            # Show dry run information
            if args.dry_run:
                print("🔍 Dry Run - Would execute:")
                for suite in executor.test_suites:
                    print(f"   📦 {suite.name} ({suite.pattern})")
                return 0

            # Display initial information
            if not args.quiet:
                print(f"🚀 Starting Parallel Test Execution")
                print(f"   Suites: {len(executor.test_suites)}")
                print(f"   Workers: {config['max_workers']}")
                print(f"   Timeout: {config['timeout_seconds']}s")
                if config.get('coverage_enabled'):
                    print(f"   Coverage: {config['coverage_threshold']:.1f}% threshold")

            # Execute tests
            start_time = time.time()
            results = await executor.execute_all_tests()
            execution_time = time.time() - start_time

            # Display execution plan
            if args.verbose:
                self.display_execution_plan(executor)

            # Generate reports
            executor.generate_reports(results, config['output_directory'])

            # Display summary
            self.display_summary(results, execution_time, args.quiet)

            # Check exit criteria
            return self.determine_exit_code(results, config)

        except KeyboardInterrupt:
            print("\n🛑 Test execution interrupted by user")
            return 130
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1

    def display_summary(self, results: Dict[str, Any], execution_time: float, quiet: bool) -> None:
        """Display execution summary."""
        if quiet:
            return

        test_summary = results.get('test_summary', {})
        performance = results.get('performance_metrics', {})
        ai_analysis = results.get('ai_analysis', {})

        print("\n" + "=" * 60)
        print("🏁 PARALLEL TEST EXECUTION SUMMARY")
        print("=" * 60)

        # Test results
        print(f"📊 Test Results:")
        print(f"   Total Tests: {test_summary.get('total_tests', 0):,}")
        print(f"   ✅ Passed: {test_summary.get('passed', 0):,}")
        print(f"   ❌ Failed: {test_summary.get('failed', 0):,}")
        print(f"   ⚠️  Errors: {test_summary.get('error', 0):,}")
        print(f"   ⏭️  Skipped: {test_summary.get('skipped', 0):,}")
        print(f"   📈 Success Rate: {test_summary.get('success_rate_percent', 0):.1f}%")

        # Performance metrics
        print(f"\n⚡ Performance:")
        print(f"   Total Time: {execution_time:.2f}s")
        print(f"   Tests/sec: {performance.get('tests_per_second', 0):.2f}")
        print(f"   Parallel Efficiency: {performance.get('parallel_efficiency', 0):.1f}x")

        # AI analysis
        if ai_analysis:
            print(f"\n🤖 AI Analysis:")
            print(f"   Health: {ai_analysis.get('overall_health', 'unknown').title()}")
            print(f"   Performance: {ai_analysis.get('performance_rating', 'unknown').title()}")
            print(f"   Reliability: {ai_analysis.get('reliability_score', 0):.2f}")

        print("=" * 60)

    def determine_exit_code(self, results: Dict[str, Any], config: Dict[str, Any]) -> int:
        """Determine appropriate exit code based on results."""
        test_summary = results.get('test_summary', {})

        # Check for test failures
        if test_summary.get('failed', 0) > 0:
            return 1

        # Check for errors
        if test_summary.get('error', 0) > 0:
            return 2

        # Check coverage threshold if enabled
        if config.get('coverage_enabled') and config.get('coverage_fail_under'):
            success_rate = test_summary.get('success_rate_percent', 0)
            if success_rate < config['coverage_threshold']:
                return 3

        return 0


async def main():
    """Main entry point."""
    cli = TestExecutionCLI()
    args = cli.parse_arguments()

    exit_code = await cli.run_tests(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())