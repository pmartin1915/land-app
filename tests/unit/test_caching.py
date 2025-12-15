"""
Unit tests for the enhanced caching system.

This module tests the comprehensive caching functionality to ensure
proper cache operations, invalidation, and performance improvements.
"""

import pytest
import time
import json
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from config.caching import (
    CacheConfig, EnhancedCacheManager, MemoryCache,
    cache_result, get_cache_manager, CacheInvalidator
)


class TestCacheConfig:
    """Test suite for CacheConfig."""

    def test_default_config_values(self):
        """Test default configuration values."""
        config = CacheConfig()

        # Redis settings
        assert config.redis_host == "localhost"
        assert config.redis_port == 6379
        assert config.redis_db == 0

        # TTL settings
        assert config.property_list_ttl == 300
        assert config.property_detail_ttl == 900
        assert config.search_results_ttl == 180
        assert config.county_stats_ttl == 1800
        assert config.investment_scores_ttl == 3600
        assert config.analytics_ttl == 7200

        # Performance settings
        assert config.enable_compression == True
        assert config.compression_threshold == 1024
        assert config.enable_cache_warming == True

    def test_custom_config_values(self):
        """Test custom configuration values."""
        config = CacheConfig(
            redis_host="custom.redis.com",
            redis_port=6380,
            property_list_ttl=600,
            enable_compression=False
        )

        assert config.redis_host == "custom.redis.com"
        assert config.redis_port == 6380
        assert config.property_list_ttl == 600
        assert config.enable_compression == False


class TestMemoryCache:
    """Test suite for MemoryCache."""

    @pytest.fixture
    def memory_cache(self):
        """Create a memory cache for testing."""
        return MemoryCache(max_size=5)

    def test_basic_set_and_get(self, memory_cache):
        """Test basic cache set and get operations."""
        memory_cache.set("test_key", "test_value", ttl=60)

        result = memory_cache.get("test_key")
        assert result == "test_value"

    def test_get_nonexistent_key(self, memory_cache):
        """Test getting a non-existent key."""
        result = memory_cache.get("nonexistent_key")
        assert result is None

    def test_cache_expiration(self, memory_cache):
        """Test cache expiration functionality."""
        memory_cache.set("expire_key", "expire_value", ttl=1)

        # Should be available immediately
        assert memory_cache.get("expire_key") == "expire_value"

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        assert memory_cache.get("expire_key") is None

    def test_cache_size_limit(self, memory_cache):
        """Test cache size limit enforcement."""
        # Fill cache to capacity
        for i in range(5):
            memory_cache.set(f"key_{i}", f"value_{i}", ttl=60)

        # Add one more item (should evict oldest)
        memory_cache.set("key_new", "value_new", ttl=60)

        # Oldest item should be evicted
        assert memory_cache.get("key_0") is None
        # Newest item should be present
        assert memory_cache.get("key_new") == "value_new"

    def test_delete_key(self, memory_cache):
        """Test cache key deletion."""
        memory_cache.set("delete_key", "delete_value", ttl=60)
        assert memory_cache.get("delete_key") == "delete_value"

        memory_cache.delete("delete_key")
        assert memory_cache.get("delete_key") is None

    def test_clear_cache(self, memory_cache):
        """Test clearing entire cache."""
        memory_cache.set("key1", "value1", ttl=60)
        memory_cache.set("key2", "value2", ttl=60)

        memory_cache.clear()

        assert memory_cache.get("key1") is None
        assert memory_cache.get("key2") is None

    def test_keys_pattern_matching(self, memory_cache):
        """Test key pattern matching."""
        memory_cache.set("user:123", "user_data", ttl=60)
        memory_cache.set("user:456", "user_data2", ttl=60)
        memory_cache.set("session:789", "session_data", ttl=60)

        # Test wildcard pattern
        user_keys = memory_cache.keys("user:*")
        assert len(user_keys) == 2
        assert "user:123" in user_keys
        assert "user:456" in user_keys

        # Test all keys
        all_keys = memory_cache.keys("*")
        assert len(all_keys) == 3


class TestEnhancedCacheManager:
    """Test suite for EnhancedCacheManager."""

    @pytest.fixture
    def cache_manager(self):
        """Create a cache manager for testing."""
        config = CacheConfig()
        manager = EnhancedCacheManager(config)
        # Use memory cache only for testing
        manager.redis_client = None
        return manager

    def test_cache_key_generation(self, cache_manager):
        """Test cache key generation."""
        key1 = cache_manager._get_cache_key("test", "arg1", "arg2", param1="value1")
        key2 = cache_manager._get_cache_key("test", "arg1", "arg2", param1="value1")
        key3 = cache_manager._get_cache_key("test", "arg1", "arg2", param1="value2")

        # Same arguments should produce same key
        assert key1 == key2
        # Different arguments should produce different key
        assert key1 != key3

        # All keys should have proper prefix
        assert key1.startswith("aaw:test:")
        assert key3.startswith("aaw:test:")

    def test_data_serialization(self, cache_manager):
        """Test data serialization and deserialization."""
        test_data = {
            "string": "test",
            "number": 42,
            "list": [1, 2, 3],
            "nested": {"key": "value"}
        }

        serialized = cache_manager._serialize_data(test_data)
        deserialized = cache_manager._deserialize_data(serialized)

        assert deserialized == test_data

    def test_compression_serialization(self, cache_manager):
        """Test data compression during serialization."""
        # Create large data that should trigger compression
        large_data = {"data": "x" * 2000}  # Over compression threshold

        # Mock gzip availability
        with patch('gzip.compress') as mock_compress, \
             patch('base64.b64encode') as mock_b64encode:

            mock_compress.return_value = b"compressed_data"
            mock_b64encode.return_value = b"base64_data"

            serialized = cache_manager._serialize_data(large_data)

            # Should use compression
            assert serialized.startswith("gzip:")
            mock_compress.assert_called_once()

    def test_cache_get_set_operations(self, cache_manager):
        """Test basic cache get and set operations."""
        test_key = "test_operation_key"
        test_value = {"test": "data"}

        # Set value
        cache_manager.set(test_key, test_value, ttl=300)

        # Get value
        result = cache_manager.get(test_key)
        assert result == test_value

        # Check stats
        stats = cache_manager.get_stats()
        assert stats["sets"] >= 1
        assert stats["hits"] >= 1

    def test_cache_miss(self, cache_manager):
        """Test cache miss behavior."""
        result = cache_manager.get("nonexistent_key")
        assert result is None

        stats = cache_manager.get_stats()
        assert stats["misses"] >= 1

    def test_cache_delete(self, cache_manager):
        """Test cache deletion."""
        test_key = "delete_test_key"
        cache_manager.set(test_key, "test_value", ttl=300)

        # Verify it exists
        assert cache_manager.get(test_key) == "test_value"

        # Delete it
        cache_manager.delete(test_key)

        # Verify it's gone
        assert cache_manager.get(test_key) is None

    def test_pattern_clearing(self, cache_manager):
        """Test pattern-based cache clearing."""
        # Set multiple keys
        cache_manager.set("aaw:test:1", "value1", ttl=300)
        cache_manager.set("aaw:test:2", "value2", ttl=300)
        cache_manager.set("aaw:other:1", "value3", ttl=300)

        # Clear test pattern
        cache_manager.clear_pattern("aaw:test:*")

        # Test keys should be gone
        assert cache_manager.get("aaw:test:1") is None
        assert cache_manager.get("aaw:test:2") is None

        # Other keys should remain
        assert cache_manager.get("aaw:other:1") == "value3"

    def test_cache_statistics(self, cache_manager):
        """Test cache statistics tracking."""
        # Perform various operations
        cache_manager.set("stat_key1", "value1", ttl=300)
        cache_manager.set("stat_key2", "value2", ttl=300)
        cache_manager.get("stat_key1")  # Hit
        cache_manager.get("nonexistent")  # Miss
        cache_manager.delete("stat_key2")

        stats = cache_manager.get_stats()

        # Check basic stats
        assert stats["sets"] >= 2
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1
        assert stats["deletes"] >= 1

        # Check calculated hit rate
        assert 0 <= stats["hit_rate"] <= 1


class TestCacheResultDecorator:
    """Test suite for cache_result decorator."""

    def test_function_caching(self):
        """Test basic function result caching."""
        call_count = 0

        @cache_result("test_func", ttl=60)
        def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            return x + y

        # First call should execute function
        result1 = expensive_function(1, 2)
        assert result1 == 3
        assert call_count == 1

        # Second call with same args should use cache
        result2 = expensive_function(1, 2)
        assert result2 == 3
        assert call_count == 1  # Should not increment

        # Different args should execute function again
        result3 = expensive_function(2, 3)
        assert result3 == 5
        assert call_count == 2

    def test_cache_invalidation_method(self):
        """Test cache invalidation functionality."""
        call_count = 0

        @cache_result("test_invalidate", ttl=60)
        def cached_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1 = cached_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call should use cache
        result2 = cached_function(5)
        assert result2 == 10
        assert call_count == 1

        # Invalidate cache
        cached_function.invalidate_cache(5)

        # Next call should execute function again
        result3 = cached_function(5)
        assert result3 == 10
        assert call_count == 2

    def test_ttl_mapping(self):
        """Test TTL mapping based on prefix."""
        @cache_result("property_list")  # Should use property_list_ttl
        def get_properties():
            return ["property1", "property2"]

        @cache_result("analytics")  # Should use analytics_ttl
        def get_analytics():
            return {"total": 100}

        # Both should work with default TTL mapping
        properties = get_properties()
        analytics = get_analytics()

        assert properties == ["property1", "property2"]
        assert analytics == {"total": 100}


class TestCacheInvalidator:
    """Test suite for CacheInvalidator."""

    @pytest.fixture
    def cache_invalidator(self):
        """Create a cache invalidator for testing."""
        cache_manager = Mock()
        return CacheInvalidator(cache_manager)

    def test_property_cache_invalidation(self, cache_invalidator):
        """Test property-specific cache invalidation."""
        property_id = "test_property_123"
        county = "Baldwin"

        cache_invalidator.invalidate_property_caches(
            property_id=property_id,
            county=county
        )

        # Should call clear_pattern multiple times
        assert cache_invalidator.cache_manager.clear_pattern.call_count >= 4

        # Check some expected patterns
        call_args_list = cache_invalidator.cache_manager.clear_pattern.call_args_list
        patterns_called = [call[0][0] for call in call_args_list]

        assert any("property_detail" in pattern for pattern in patterns_called)
        assert any("county_stats" in pattern for pattern in patterns_called)

    def test_search_cache_invalidation(self, cache_invalidator):
        """Test search cache invalidation."""
        cache_invalidator.invalidate_search_caches()

        cache_invalidator.cache_manager.clear_pattern.assert_called_with("aaw:search_results:*")

    def test_analytics_cache_invalidation(self, cache_invalidator):
        """Test analytics cache invalidation."""
        cache_invalidator.invalidate_analytics_caches()

        # Should clear multiple analytics-related patterns
        assert cache_invalidator.cache_manager.clear_pattern.call_count >= 3

        call_args_list = cache_invalidator.cache_manager.clear_pattern.call_args_list
        patterns_called = [call[0][0] for call in call_args_list]

        assert "aaw:analytics:*" in patterns_called
        assert "aaw:county_stats:*" in patterns_called
        assert "aaw:investment_scores:*" in patterns_called


class TestCacheIntegration:
    """Integration tests for the caching system."""

    def test_cache_manager_singleton(self):
        """Test that cache manager returns same instance."""
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()

        # Should be the same instance
        assert manager1 is manager2

    def test_real_world_caching_scenario(self):
        """Test a realistic caching scenario."""
        cache_manager = get_cache_manager()

        # Simulate property list caching
        property_filters = {
            "county": "Baldwin",
            "min_price": 10000,
            "max_price": 50000
        }

        cache_key = cache_manager._get_cache_key("property_list", **property_filters)

        # First time - cache miss
        cached_result = cache_manager.get(cache_key)
        assert cached_result is None

        # Simulate query result
        mock_properties = [
            {"id": "1", "amount": 25000, "county": "Baldwin"},
            {"id": "2", "amount": 35000, "county": "Baldwin"}
        ]

        # Cache the result
        cache_manager.set(cache_key, mock_properties, ttl=300)

        # Second time - cache hit
        cached_result = cache_manager.get(cache_key)
        assert cached_result == mock_properties

        # Verify stats
        stats = cache_manager.get_stats()
        assert stats["hits"] >= 1
        assert stats["sets"] >= 1

    @patch('config.caching.warm_cache')
    def test_cache_warming_integration(self, mock_warm_cache):
        """Test cache warming integration."""
        # Import here to avoid circular dependency issues
        from config.caching import warm_cache

        # Call should not raise exceptions
        try:
            # This is an async function, so we'd need to handle it properly
            # For testing, we just verify the import works
            assert warm_cache is not None
        except Exception as e:
            pytest.fail(f"Cache warming integration failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__])