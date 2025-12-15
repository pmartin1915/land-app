"""
Enhanced Caching System for Alabama Auction Watcher

This module implements a comprehensive caching strategy to improve
application performance by caching frequently accessed data and queries.
"""

import json
import time
import hashlib
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from functools import wraps
from datetime import datetime

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """Configuration for the caching system."""

    # Redis configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_ssl: bool = False

    # Cache TTL settings (in seconds)
    property_list_ttl: int = 300  # 5 minutes
    property_detail_ttl: int = 900  # 15 minutes
    search_results_ttl: int = 180  # 3 minutes
    county_stats_ttl: int = 1800  # 30 minutes
    investment_scores_ttl: int = 3600  # 1 hour
    analytics_ttl: int = 7200  # 2 hours

    # Cache size limits (for memory fallback)
    max_memory_cache_size: int = 1000
    max_key_length: int = 250

    # Performance settings
    enable_compression: bool = True
    compression_threshold: int = 1024  # Compress if data > 1KB
    enable_cache_warming: bool = True

    # Cache invalidation
    auto_invalidate_on_update: bool = True
    batch_invalidation_size: int = 100


class MemoryCache:
    """Fallback in-memory cache when Redis is unavailable."""

    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.access_times: Dict[str, float] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        if key in self.cache:
            # Check expiration
            entry = self.cache[key]
            if entry["expires_at"] > time.time():
                self.access_times[key] = time.time()
                return entry["value"]
            else:
                # Expired, remove it
                self._remove(key)
        return None

    def set(self, key: str, value: Any, ttl: int = 300):
        """Set value in memory cache."""
        # Remove oldest entries if at capacity
        while len(self.cache) >= self.max_size:
            oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
            self._remove(oldest_key)

        self.cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl,
            "created_at": time.time()
        }
        self.access_times[key] = time.time()

    def delete(self, key: str):
        """Delete key from memory cache."""
        self._remove(key)

    def clear(self):
        """Clear all cached data."""
        self.cache.clear()
        self.access_times.clear()

    def _remove(self, key: str):
        """Remove key from both cache and access times."""
        self.cache.pop(key, None)
        self.access_times.pop(key, None)

    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern (simplified for memory cache)."""
        if pattern == "*":
            return list(self.cache.keys())
        # Simple wildcard support
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k for k in self.cache.keys() if k.startswith(prefix)]
        return [k for k in self.cache.keys() if pattern in k]


class EnhancedCacheManager:
    """Comprehensive cache management system."""

    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self.redis_client = None
        self.memory_cache = MemoryCache(self.config.max_memory_cache_size)
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }

        # Initialize Redis connection
        self._initialize_redis()

    def _initialize_redis(self):
        """Initialize Redis connection if available."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using memory cache fallback")
            return

        try:
            self.redis_client = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                password=self.config.redis_password,
                ssl=self.config.redis_ssl,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                health_check_interval=30
            )

            # Test connection
            self.redis_client.ping()
            logger.info("Redis cache initialized successfully")

        except Exception as e:
            logger.warning(f"Failed to initialize Redis: {e}. Using memory cache fallback.")
            self.redis_client = None

    def _get_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and parameters."""
        # Create deterministic key from arguments
        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items()) if kwargs else {}
        }

        key_string = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()[:12]

        cache_key = f"aaw:{prefix}:{key_hash}"

        # Ensure key length doesn't exceed limit
        if len(cache_key) > self.config.max_key_length:
            cache_key = f"aaw:{prefix}:" + hashlib.md5(cache_key.encode()).hexdigest()

        return cache_key

    def _serialize_data(self, data: Any) -> str:
        """Serialize data for caching."""
        try:
            serialized = json.dumps(data, default=str, ensure_ascii=False)

            # Compress if enabled and data is large enough
            if (self.config.enable_compression and
                len(serialized) > self.config.compression_threshold):
                try:
                    import gzip
                    import base64
                    compressed = gzip.compress(serialized.encode())
                    return f"gzip:{base64.b64encode(compressed).decode()}"
                except ImportError:
                    pass

            return f"json:{serialized}"
        except Exception as e:
            logger.error(f"Failed to serialize data: {e}")
            raise

    def _deserialize_data(self, serialized: str) -> Any:
        """Deserialize cached data."""
        try:
            if serialized.startswith("gzip:"):
                import gzip
                import base64
                compressed = base64.b64decode(serialized[5:])
                decompressed = gzip.decompress(compressed).decode()
                return json.loads(decompressed)
            elif serialized.startswith("json:"):
                return json.loads(serialized[5:])
            else:
                # Legacy format
                return json.loads(serialized)
        except Exception as e:
            logger.error(f"Failed to deserialize data: {e}")
            raise

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            # Try Redis first
            if self.redis_client:
                try:
                    cached_data = self.redis_client.get(key)
                    if cached_data:
                        self.cache_stats["hits"] += 1
                        return self._deserialize_data(cached_data)
                except Exception as e:
                    logger.warning(f"Redis get failed: {e}")
                    self.cache_stats["errors"] += 1

            # Fall back to memory cache
            result = self.memory_cache.get(key)
            if result is not None:
                self.cache_stats["hits"] += 1
                return result

            self.cache_stats["misses"] += 1
            return None

        except Exception as e:
            logger.error(f"Cache get failed for key {key}: {e}")
            self.cache_stats["errors"] += 1
            return None

    def set(self, key: str, value: Any, ttl: int = 300):
        """Set value in cache."""
        try:
            serialized_data = self._serialize_data(value)

            # Try Redis first
            if self.redis_client:
                try:
                    self.redis_client.setex(key, ttl, serialized_data)
                    self.cache_stats["sets"] += 1
                    return
                except Exception as e:
                    logger.warning(f"Redis set failed: {e}")
                    self.cache_stats["errors"] += 1

            # Fall back to memory cache
            self.memory_cache.set(key, value, ttl)
            self.cache_stats["sets"] += 1

        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            self.cache_stats["errors"] += 1

    def delete(self, key: str):
        """Delete key from cache."""
        try:
            # Try Redis first
            if self.redis_client:
                try:
                    self.redis_client.delete(key)
                except Exception as e:
                    logger.warning(f"Redis delete failed: {e}")
                    self.cache_stats["errors"] += 1

            # Also remove from memory cache
            self.memory_cache.delete(key)
            self.cache_stats["deletes"] += 1

        except Exception as e:
            logger.error(f"Cache delete failed for key {key}: {e}")
            self.cache_stats["errors"] += 1

    def clear_pattern(self, pattern: str):
        """Clear all keys matching pattern."""
        try:
            # Redis pattern deletion
            if self.redis_client:
                try:
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        # Delete in batches
                        batch_size = self.config.batch_invalidation_size
                        for i in range(0, len(keys), batch_size):
                            batch = keys[i:i + batch_size]
                            self.redis_client.delete(*batch)
                except Exception as e:
                    logger.warning(f"Redis pattern clear failed: {e}")
                    self.cache_stats["errors"] += 1

            # Memory cache pattern deletion
            memory_keys = self.memory_cache.keys(pattern)
            for key in memory_keys:
                self.memory_cache.delete(key)

            self.cache_stats["deletes"] += len(memory_keys)

        except Exception as e:
            logger.error(f"Cache pattern clear failed for pattern {pattern}: {e}")
            self.cache_stats["errors"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self.cache_stats.copy()
        stats["hit_rate"] = (
            stats["hits"] / (stats["hits"] + stats["misses"])
            if (stats["hits"] + stats["misses"]) > 0 else 0
        )
        stats["redis_available"] = self.redis_client is not None
        stats["memory_cache_size"] = len(self.memory_cache.cache)

        if self.redis_client:
            try:
                redis_info = self.redis_client.info("memory")
                stats["redis_memory_used"] = redis_info.get("used_memory_human", "N/A")
                stats["redis_keys"] = self.redis_client.dbsize()
            except Exception:
                pass

        return stats


# Global cache manager instance
_cache_manager: Optional[EnhancedCacheManager] = None


def get_cache_manager() -> EnhancedCacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = EnhancedCacheManager()
    return _cache_manager


def cache_result(prefix: str, ttl: Optional[int] = None):
    """Decorator to cache function results."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()

            # Determine TTL based on prefix
            if ttl is None:
                ttl_mapping = {
                    "property_list": cache_manager.config.property_list_ttl,
                    "property_detail": cache_manager.config.property_detail_ttl,
                    "search_results": cache_manager.config.search_results_ttl,
                    "county_stats": cache_manager.config.county_stats_ttl,
                    "investment_scores": cache_manager.config.investment_scores_ttl,
                    "analytics": cache_manager.config.analytics_ttl,
                }
                actual_ttl = ttl_mapping.get(prefix, 300)  # Default 5 minutes
            else:
                actual_ttl = ttl

            # Generate cache key
            cache_key = cache_manager._get_cache_key(prefix, *args, **kwargs)

            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, actual_ttl)

            return result

        # Add cache invalidation method
        def invalidate_cache(*args, **kwargs):
            cache_manager = get_cache_manager()
            cache_key = cache_manager._get_cache_key(prefix, *args, **kwargs)
            cache_manager.delete(cache_key)

        wrapper.invalidate_cache = invalidate_cache
        wrapper.cache_prefix = prefix

        return wrapper
    return decorator


async def warm_cache():
    """Warm up cache with frequently accessed data."""
    cache_manager = get_cache_manager()

    if not cache_manager.config.enable_cache_warming:
        return

    logger.info("Starting cache warming...")

    try:
        # Import here to avoid circular dependencies
        from backend_api.database.connection import get_db
        from sqlalchemy import text

        db = next(get_db())

        # Warm county statistics
        counties_result = db.execute(text("""
            SELECT county, COUNT(*) as count
            FROM properties
            WHERE is_deleted = FALSE
            GROUP BY county
            ORDER BY count DESC
            LIMIT 10
        """)).fetchall()

        for county_row in counties_result:
            county = county_row[0]
            # This would trigger caching for county stats
            cache_key = cache_manager._get_cache_key("county_stats", county=county)
            if cache_manager.get(cache_key) is None:
                logger.debug(f"Warming cache for county: {county}")
                # Cache basic county stats
                cache_manager.set(cache_key, {
                    "county": county,
                    "property_count": county_row[1],
                    "cached_at": datetime.now().isoformat()
                }, cache_manager.config.county_stats_ttl)

        # Warm popular search terms
        popular_searches = [
            {"min_amount": 10000, "max_amount": 50000},
            {"min_amount": 50000, "max_amount": 100000},
            {"county": "Baldwin"},
            {"county": "Mobile"},
            {"min_acreage": 1.0, "max_acreage": 5.0}
        ]

        for search_params in popular_searches:
            cache_key = cache_manager._get_cache_key("search_results", **search_params)
            if cache_manager.get(cache_key) is None:
                logger.debug(f"Warming cache for search: {search_params}")
                # Cache search parameters for quick access
                cache_manager.set(cache_key, {
                    "search_params": search_params,
                    "warmed_at": datetime.now().isoformat()
                }, cache_manager.config.search_results_ttl)

        logger.info("Cache warming completed successfully")

    except Exception as e:
        logger.error(f"Cache warming failed: {e}")


class CacheInvalidator:
    """Handles cache invalidation strategies."""

    def __init__(self, cache_manager: EnhancedCacheManager):
        self.cache_manager = cache_manager

    def invalidate_property_caches(self, property_id: Optional[str] = None, county: Optional[str] = None):
        """Invalidate property-related caches."""
        patterns_to_clear = []

        if property_id:
            patterns_to_clear.extend([
                f"aaw:property_detail:*{property_id}*",
                f"aaw:investment_scores:*{property_id}*"
            ])

        if county:
            patterns_to_clear.extend([
                f"aaw:county_stats:*{county}*",
                f"aaw:search_results:*{county}*"
            ])

        # Always clear general listing caches when properties change
        patterns_to_clear.extend([
            "aaw:property_list:*",
            "aaw:analytics:*"
        ])

        for pattern in patterns_to_clear:
            self.cache_manager.clear_pattern(pattern)

    def invalidate_search_caches(self, search_type: Optional[str] = None):
        """Invalidate search-related caches."""
        if search_type:
            self.cache_manager.clear_pattern(f"aaw:{search_type}:*")
        else:
            self.cache_manager.clear_pattern("aaw:search_results:*")

    def invalidate_analytics_caches(self):
        """Invalidate analytics and statistics caches."""
        patterns = [
            "aaw:analytics:*",
            "aaw:county_stats:*",
            "aaw:investment_scores:*"
        ]

        for pattern in patterns:
            self.cache_manager.clear_pattern(pattern)


def get_cache_invalidator() -> CacheInvalidator:
    """Get cache invalidator instance."""
    return CacheInvalidator(get_cache_manager())