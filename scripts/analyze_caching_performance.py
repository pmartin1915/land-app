"""
Caching Performance Analysis Script for Alabama Auction Watcher

This script demonstrates and analyzes the performance improvements
achieved through the comprehensive caching implementation.
"""

import time
import asyncio
import statistics
from typing import List, Dict, Any
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import caching system
from config.caching import get_cache_manager, cache_result


class CachingPerformanceAnalyzer:
    """Analyze caching performance improvements."""

    def __init__(self):
        self.cache_manager = get_cache_manager()
        self.results = {}

    def simulate_expensive_operation(self, operation_id: str, delay: float = 0.5) -> Dict[str, Any]:
        """Simulate an expensive database operation."""
        time.sleep(delay)  # Simulate processing time
        return {
            "operation_id": operation_id,
            "data": f"Result for {operation_id}",
            "timestamp": time.time(),
            "processing_time": delay
        }

    @cache_result("performance_test", ttl=300)
    def cached_expensive_operation(self, operation_id: str, delay: float = 0.5) -> Dict[str, Any]:
        """Cached version of expensive operation."""
        return self.simulate_expensive_operation(operation_id, delay)

    def benchmark_without_cache(self, operation_ids: List[str], iterations: int = 3) -> Dict[str, Any]:
        """Benchmark operations without caching."""
        logger.info("Running benchmark WITHOUT caching...")
        execution_times = []

        for i in range(iterations):
            start_time = time.time()
            for op_id in operation_ids:
                self.simulate_expensive_operation(op_id)
            end_time = time.time()
            execution_times.append(end_time - start_time)

        return {
            "total_operations": len(operation_ids) * iterations,
            "execution_times": execution_times,
            "average_time": statistics.mean(execution_times),
            "min_time": min(execution_times),
            "max_time": max(execution_times),
            "total_time": sum(execution_times)
        }

    def benchmark_with_cache(self, operation_ids: List[str], iterations: int = 3) -> Dict[str, Any]:
        """Benchmark operations with caching."""
        logger.info("Running benchmark WITH caching...")
        execution_times = []

        # Clear cache before starting
        self.cache_manager.clear_pattern("aaw:performance_test:*")

        for i in range(iterations):
            start_time = time.time()
            for op_id in operation_ids:
                self.cached_expensive_operation(op_id)
            end_time = time.time()
            execution_times.append(end_time - start_time)

        return {
            "total_operations": len(operation_ids) * iterations,
            "execution_times": execution_times,
            "average_time": statistics.mean(execution_times),
            "min_time": min(execution_times),
            "max_time": max(execution_times),
            "total_time": sum(execution_times)
        }

    def analyze_cache_hit_performance(self, operation_ids: List[str]) -> Dict[str, Any]:
        """Analyze performance with cache hits vs misses."""
        logger.info("Analyzing cache hit performance...")

        # Clear cache
        self.cache_manager.clear_pattern("aaw:performance_test:*")

        # First run (cache misses)
        miss_times = []
        for op_id in operation_ids:
            start_time = time.time()
            self.cached_expensive_operation(op_id)
            end_time = time.time()
            miss_times.append(end_time - start_time)

        # Second run (cache hits)
        hit_times = []
        for op_id in operation_ids:
            start_time = time.time()
            self.cached_expensive_operation(op_id)
            end_time = time.time()
            hit_times.append(end_time - start_time)

        return {
            "cache_miss_times": miss_times,
            "cache_hit_times": hit_times,
            "average_miss_time": statistics.mean(miss_times),
            "average_hit_time": statistics.mean(hit_times),
            "speedup_factor": statistics.mean(miss_times) / statistics.mean(hit_times),
            "time_saved_per_hit": statistics.mean(miss_times) - statistics.mean(hit_times)
        }

    def analyze_memory_vs_redis_performance(self) -> Dict[str, Any]:
        """Compare memory cache vs Redis performance."""
        logger.info("Analyzing memory vs Redis cache performance...")

        test_data = {"test": "data", "number": 42, "list": [1, 2, 3]}
        test_key = "performance_comparison_key"

        # Test memory cache (when Redis is unavailable)
        redis_client = self.cache_manager.redis_client
        self.cache_manager.redis_client = None  # Force memory cache

        memory_times = []
        for i in range(100):
            start_time = time.time()
            self.cache_manager.set(f"{test_key}_{i}", test_data, 300)
            self.cache_manager.get(f"{test_key}_{i}")
            end_time = time.time()
            memory_times.append(end_time - start_time)

        # Restore Redis client
        self.cache_manager.redis_client = redis_client

        # Test Redis cache (if available)
        redis_times = []
        if self.cache_manager.redis_client:
            for i in range(100):
                start_time = time.time()
                self.cache_manager.set(f"{test_key}_redis_{i}", test_data, 300)
                self.cache_manager.get(f"{test_key}_redis_{i}")
                end_time = time.time()
                redis_times.append(end_time - start_time)

        return {
            "memory_cache": {
                "average_time": statistics.mean(memory_times),
                "min_time": min(memory_times),
                "max_time": max(memory_times)
            },
            "redis_cache": {
                "average_time": statistics.mean(redis_times) if redis_times else None,
                "min_time": min(redis_times) if redis_times else None,
                "max_time": max(redis_times) if redis_times else None,
                "available": bool(redis_times)
            }
        }

    def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """Run comprehensive caching performance analysis."""
        logger.info("Starting comprehensive caching performance analysis...")

        # Test data
        operation_ids = [f"operation_{i}" for i in range(10)]

        # Get initial cache stats
        initial_stats = self.cache_manager.get_stats()

        # Benchmark without cache
        no_cache_results = self.benchmark_without_cache(operation_ids, iterations=3)

        # Benchmark with cache
        cache_results = self.benchmark_with_cache(operation_ids, iterations=3)

        # Analyze cache hit performance
        hit_miss_analysis = self.analyze_cache_hit_performance(operation_ids[:5])

        # Analyze memory vs Redis
        backend_comparison = self.analyze_memory_vs_redis_performance()

        # Get final cache stats
        final_stats = self.cache_manager.get_stats()

        # Calculate improvements
        time_improvement = ((no_cache_results["average_time"] - cache_results["average_time"])
                          / no_cache_results["average_time"] * 100)

        results = {
            "summary": {
                "time_improvement_percentage": round(time_improvement, 2),
                "absolute_time_saved": round(no_cache_results["total_time"] - cache_results["total_time"], 3),
                "cache_hit_speedup": round(hit_miss_analysis["speedup_factor"], 2),
                "operations_tested": len(operation_ids) * 3
            },
            "detailed_results": {
                "no_cache_benchmark": no_cache_results,
                "with_cache_benchmark": cache_results,
                "cache_hit_analysis": hit_miss_analysis,
                "backend_comparison": backend_comparison
            },
            "cache_statistics": {
                "initial_stats": initial_stats,
                "final_stats": final_stats,
                "operations_performed": final_stats["sets"] - initial_stats["sets"]
            }
        }

        self.results = results
        return results

    def print_analysis_report(self):
        """Print a formatted analysis report."""
        if not self.results:
            logger.error("No analysis results available. Run run_comprehensive_analysis() first.")
            return

        print("\n" + "="*80)
        print("CACHING PERFORMANCE ANALYSIS REPORT")
        print("="*80)

        summary = self.results["summary"]
        print(f"\n🚀 PERFORMANCE IMPROVEMENTS:")
        print(f"   Time Improvement: {summary['time_improvement_percentage']}%")
        print(f"   Absolute Time Saved: {summary['absolute_time_saved']}s")
        print(f"   Cache Hit Speedup: {summary['cache_hit_speedup']}x faster")
        print(f"   Operations Tested: {summary['operations_tested']}")

        detailed = self.results["detailed_results"]
        print(f"\n📊 DETAILED BENCHMARKS:")
        print(f"   Without Cache - Average: {detailed['no_cache_benchmark']['average_time']:.3f}s")
        print(f"   With Cache - Average: {detailed['with_cache_benchmark']['average_time']:.3f}s")

        hit_analysis = detailed["cache_hit_analysis"]
        print(f"\n⚡ CACHE HIT ANALYSIS:")
        print(f"   Cache Miss Average: {hit_analysis['average_miss_time']:.3f}s")
        print(f"   Cache Hit Average: {hit_analysis['average_hit_time']:.3f}s")
        print(f"   Time Saved per Hit: {hit_analysis['time_saved_per_hit']:.3f}s")

        backend = detailed["backend_comparison"]
        print(f"\n💾 CACHE BACKEND COMPARISON:")
        print(f"   Memory Cache Average: {backend['memory_cache']['average_time']:.6f}s")
        if backend['redis_cache']['available']:
            print(f"   Redis Cache Average: {backend['redis_cache']['average_time']:.6f}s")
        else:
            print("   Redis Cache: Not Available")

        cache_stats = self.results["cache_statistics"]["final_stats"]
        print(f"\n📈 CACHE STATISTICS:")
        print(f"   Hit Rate: {cache_stats['hit_rate']:.2%}")
        print(f"   Total Hits: {cache_stats['hits']}")
        print(f"   Total Misses: {cache_stats['misses']}")
        print(f"   Backend: {'Redis' if cache_stats['redis_available'] else 'Memory'}")

        print("\n" + "="*80)


async def main():
    """Main analysis function."""
    print("Starting Alabama Auction Watcher Caching Performance Analysis...")

    analyzer = CachingPerformanceAnalyzer()

    try:
        # Run comprehensive analysis
        results = analyzer.run_comprehensive_analysis()

        # Print formatted report
        analyzer.print_analysis_report()

        # Save results to file
        import json
        with open("caching_performance_results.json", "w") as f:
            json.dump(results, f, indent=2)

        logger.info("Analysis complete! Results saved to caching_performance_results.json")

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())