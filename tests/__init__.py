"""
Alabama Auction Watcher Test Suite

Comprehensive test package for validating all aspects of the auction watcher system.
Designed for AI-testability with machine-readable specifications and automated validation.
"""

__version__ = "1.0.0"

# Test categories
UNIT_TESTS = "unit"
INTEGRATION_TESTS = "integration"
E2E_TESTS = "e2e"
BENCHMARK_TESTS = "benchmarks"

# Test markers for AI categorization
AI_TEST_MARKERS = [
    "unit",
    "integration",
    "e2e",
    "slow",
    "network",
    "scraping",
    "benchmark",
    "ai_test",
    "error_handling",
    "cross_platform"
]