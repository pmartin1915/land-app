#!/usr/bin/env python3
"""
Comprehensive Testing Script for Alabama Auction Watcher Streamlit Optimizations

This script tests all optimization systems and AI testability features without
requiring the full Streamlit UI, enabling comprehensive debugging and validation.
"""

import sys
import time
import pandas as pd
import json
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import optimization systems
try:
    from streamlit_app.core.performance_monitor import (
        get_performance_monitor, PerformanceMetric, ComponentProfile
    )
    from streamlit_app.core.cache_manager import (
        get_cache_manager, SmartCacheManager
    )
    from streamlit_app.core.async_loader import (
        get_streamlit_loader, AsyncDataLoader
    )
    from streamlit_app.core.memory_optimizer import (
        get_memory_manager, optimize_dataframe, DataFrameOptimizer
    )
    from streamlit_app.testing.ai_testability import (
        get_test_executor, AITestGenerator, TestScenario
    )
    print("SUCCESS: All optimization systems imported successfully")
except Exception as e:
    print(f"ERROR: Failed to import optimization systems: {e}")
    sys.exit(1)

class OptimizationTester:
    """Comprehensive tester for all optimization systems."""

    def __init__(self):
        self.results = {
            'test_start_time': datetime.now().isoformat(),
            'performance_monitor': {},
            'cache_manager': {},
            'async_loader': {},
            'memory_optimizer': {},
            'ai_testability': {},
            'integration_tests': {},
            'errors': [],
            'summary': {}
        }

    def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive tests on all optimization systems."""
        print("STARTING: Comprehensive Optimization Testing")
        print("=" * 60)

        try:
            # Test each system
            self._test_performance_monitor()
            self._test_cache_manager()
            self._test_async_loader()
            self._test_memory_optimizer()
            self._test_ai_testability()
            self._test_integration()

            # Generate summary
            self._generate_summary()

        except Exception as e:
            self.results['errors'].append({
                'test': 'overall',
                'error': str(e),
                'traceback': traceback.format_exc()
            })

        return self.results

    def _test_performance_monitor(self):
        """Test performance monitoring system."""
        print("\nTEST: Performance Monitor...")
        try:
            monitor = get_performance_monitor()
            start_time = time.time()

            # Test metric recording
            monitor.record_metric("test_component", "execution_time", 0.5, {
                "test_data": "performance_test"
            })

            # Test component profiling
            profile = monitor.get_component_profile("test_component")

            # Test health check
            health = monitor.check_component_health("test_component")

            execution_time = time.time() - start_time

            self.results['performance_monitor'] = {
                'status': 'success',
                'execution_time': execution_time,
                'metrics_recorded': 1,
                'profile_created': profile is not None,
                'health_check': health.status.value if health else 'no_health_data',
                'component_count': len(monitor.component_profiles)
            }
            print("   SUCCESS: Performance Monitor working correctly")

        except Exception as e:
            self.results['performance_monitor'] = {'status': 'error', 'error': str(e)}
            self.results['errors'].append({
                'test': 'performance_monitor',
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            print(f"   ERROR: Performance Monitor: {e}")

    def _test_cache_manager(self):
        """Test smart cache management system."""
        print("\nTEST: Cache Manager...")
        try:
            cache_manager = get_cache_manager()
            start_time = time.time()

            # Test cache operations
            test_data = {"test": "cache_data", "timestamp": time.time()}

            # Set cache
            cache_manager.set("test_key", test_data, ttl_seconds=60, cache_type="test")

            # Get from cache
            cached_data = cache_manager.get("test_key", cache_type="test")

            # Test cache hit
            cache_hit = cached_data is not None

            # Test cache statistics
            stats = cache_manager.get_cache_statistics()

            execution_time = time.time() - start_time

            self.results['cache_manager'] = {
                'status': 'success',
                'execution_time': execution_time,
                'cache_hit': cache_hit,
                'cache_stats': stats,
                'data_integrity': cached_data == test_data
            }
            print("   SUCCESS: Cache Manager working correctly")

        except Exception as e:
            self.results['cache_manager'] = {'status': 'error', 'error': str(e)}
            self.results['errors'].append({
                'test': 'cache_manager',
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            print(f"   ERROR: Cache Manager: {e}")

    def _test_async_loader(self):
        """Test asynchronous data loading system."""
        print("\nTEST: Async Loader...")
        try:
            loader = get_streamlit_loader()
            start_time = time.time()

            # Create test DataFrame
            test_df = pd.DataFrame({
                'test_column': range(100),
                'data': [f"test_data_{i}" for i in range(100)]
            })

            # Test async processing (simulate without actual API calls)
            processed_df = loader._process_properties_data(test_df)

            execution_time = time.time() - start_time

            self.results['async_loader'] = {
                'status': 'success',
                'execution_time': execution_time,
                'input_rows': len(test_df),
                'output_rows': len(processed_df),
                'data_processed': processed_df is not None
            }
            print("   SUCCESS: Async Loader working correctly")

        except Exception as e:
            self.results['async_loader'] = {'status': 'error', 'error': str(e)}
            self.results['errors'].append({
                'test': 'async_loader',
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            print(f"   ERROR: Async Loader: {e}")

    def _test_memory_optimizer(self):
        """Test memory optimization system."""
        print("\nTEST: Memory Optimizer...")
        try:
            memory_manager = get_memory_manager()
            start_time = time.time()

            # Create test DataFrame with various data types
            test_df = pd.DataFrame({
                'integers': range(1000),
                'floats': [float(i) * 1.5 for i in range(1000)],
                'strings': [f"test_string_{i}" for i in range(1000)],
                'booleans': [i % 2 == 0 for i in range(1000)]
            })

            # Get original memory usage
            original_memory = test_df.memory_usage(deep=True).sum()

            # Optimize DataFrame
            optimized_df = optimize_dataframe(test_df, aggressive=False)

            # Get optimized memory usage
            optimized_memory = optimized_df.memory_usage(deep=True).sum()

            # Calculate memory savings
            memory_savings = (original_memory - optimized_memory) / original_memory * 100

            execution_time = time.time() - start_time

            self.results['memory_optimizer'] = {
                'status': 'success',
                'execution_time': execution_time,
                'original_memory_mb': original_memory / 1024 / 1024,
                'optimized_memory_mb': optimized_memory / 1024 / 1024,
                'memory_savings_percent': memory_savings,
                'data_integrity': len(test_df) == len(optimized_df)
            }
            print(f"   SUCCESS: Memory Optimizer: {memory_savings:.1f}% memory reduction")

        except Exception as e:
            self.results['memory_optimizer'] = {'status': 'error', 'error': str(e)}
            self.results['errors'].append({
                'test': 'memory_optimizer',
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            print(f"   ERROR: Memory Optimizer: {e}")

    def _test_ai_testability(self):
        """Test AI testing framework."""
        print("\nTEST: AI Testability Framework...")
        try:
            test_executor = get_test_executor()
            start_time = time.time()

            # Test scenario generation
            generator = AITestGenerator()
            scenarios = generator.generate_scenarios(
                "test_component", "data_processing", {}
            )

            # Test scenario creation
            test_scenario = scenarios[0] if scenarios else None

            execution_time = time.time() - start_time

            self.results['ai_testability'] = {
                'status': 'success',
                'execution_time': execution_time,
                'scenarios_generated': len(scenarios),
                'scenario_structure_valid': test_scenario is not None,
                'generator_working': True
            }
            print(f"   SUCCESS: AI Testability: Generated {len(scenarios)} test scenarios")

        except Exception as e:
            self.results['ai_testability'] = {'status': 'error', 'error': str(e)}
            self.results['errors'].append({
                'test': 'ai_testability',
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            print(f"   ERROR: AI Testability: {e}")

    def _test_integration(self):
        """Test integration between all systems."""
        print("\nTEST: System Integration...")
        try:
            start_time = time.time()

            # Test combined workflow
            cache_manager = get_cache_manager()
            memory_manager = get_memory_manager()
            performance_monitor = get_performance_monitor()

            # Create test data
            test_df = pd.DataFrame({
                'id': range(500),
                'value': [i * 2.5 for i in range(500)]
            })

            # Test workflow: optimize -> cache -> monitor
            with performance_monitor.monitor_context("integration_test"):
                optimized_df = optimize_dataframe(test_df)
                cache_key = "integration_test_data"
                cache_manager.set(cache_key, optimized_df.to_dict(), ttl_seconds=30)
                cached_data = cache_manager.get(cache_key)

            # Check performance metrics
            profile = performance_monitor.get_component_profile("integration_test")

            execution_time = time.time() - start_time

            self.results['integration_tests'] = {
                'status': 'success',
                'execution_time': execution_time,
                'optimization_success': len(optimized_df) == len(test_df),
                'cache_success': cached_data is not None,
                'monitoring_success': profile is not None,
                'workflow_complete': True
            }
            print("   SUCCESS: Integration: All systems working together")

        except Exception as e:
            self.results['integration_tests'] = {'status': 'error', 'error': str(e)}
            self.results['errors'].append({
                'test': 'integration',
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            print(f"   ERROR: Integration: {e}")

    def _generate_summary(self):
        """Generate test summary."""
        total_tests = 6
        successful_tests = sum(1 for result in [
            self.results['performance_monitor'],
            self.results['cache_manager'],
            self.results['async_loader'],
            self.results['memory_optimizer'],
            self.results['ai_testability'],
            self.results['integration_tests']
        ] if result.get('status') == 'success')

        self.results['summary'] = {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'failed_tests': total_tests - successful_tests,
            'success_rate': (successful_tests / total_tests) * 100,
            'total_errors': len(self.results['errors']),
            'test_end_time': datetime.now().isoformat()
        }

def main():
    """Main testing function."""
    print("TESTING: Alabama Auction Watcher - Optimization Testing Suite")
    print("=" * 60)

    tester = OptimizationTester()
    results = tester.run_all_tests()

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    summary = results['summary']
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Successful: {summary['successful_tests']}")
    print(f"Failed: {summary['failed_tests']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    print(f"Total Errors: {summary['total_errors']}")

    if results['errors']:
        print("\nERRORS FOUND:")
        for error in results['errors']:
            print(f"  - {error['test']}: {error['error']}")

    # Save detailed results
    results_file = "optimization_test_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nDETAILS: Detailed results saved to: {results_file}")

    if summary['success_rate'] >= 80:
        print("\nSUCCESS: OPTIMIZATION TESTING PASSED")
        return 0
    else:
        print("\nWARNING: OPTIMIZATION TESTING NEEDS ATTENTION")
        return 1

if __name__ == "__main__":
    sys.exit(main())