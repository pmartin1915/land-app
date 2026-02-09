"""
Caching Middleware for Auction Watcher API

This middleware integrates the enhanced caching system with FastAPI,
providing automatic caching for API responses and cache invalidation.
"""

import time
import json
import hashlib
import logging
import base64
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response

import sys
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.caching import get_cache_manager, get_cache_invalidator

logger = logging.getLogger(__name__)


class CachingMiddleware:
    """FastAPI middleware for response caching."""

    def __init__(self, app):
        self.app = app
        self.cache_manager = get_cache_manager()
        self.cache_invalidator = get_cache_invalidator()

        # Cacheable endpoints and their configurations
        self.cacheable_endpoints = {
            # Property endpoints
            "/api/v1/properties/": {
                "ttl": self.cache_manager.config.property_list_ttl,
                "cache_query_params": True,
                "invalidate_on": ["POST", "PUT", "DELETE"]
            },
            "/api/v1/properties/search": {
                "ttl": self.cache_manager.config.search_results_ttl,
                "cache_query_params": True,
                "invalidate_on": ["POST", "PUT", "DELETE"]
            },
            "/api/v1/properties/county/": {
                "ttl": self.cache_manager.config.county_stats_ttl,
                "cache_query_params": True,
                "invalidate_on": ["POST", "PUT", "DELETE"]
            },
            "/api/v1/analytics/": {
                "ttl": self.cache_manager.config.analytics_ttl,
                "cache_query_params": True,
                "invalidate_on": ["POST", "PUT", "DELETE"]
            },
            "/api/v1/analytics/investment-insights": {
                "ttl": self.cache_manager.config.investment_scores_ttl,
                "cache_query_params": True,
                "invalidate_on": ["POST", "PUT", "DELETE"]
            }
        }

        # Endpoints that should trigger cache invalidation
        self.invalidation_endpoints = {
            "/api/v1/properties/": ["property_list", "search_results", "analytics", "county_stats"],
            "/api/v1/sync/": ["property_list", "search_results", "analytics", "county_stats"],
            "/api/v1/admin/": ["property_list", "search_results", "analytics", "county_stats"]
        }

        # Methods that don't affect caching
        self.safe_methods = {"GET", "HEAD", "OPTIONS"}

    async def __call__(self, scope: dict, receive: Callable, send: Callable):
        """Process request through caching middleware."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Check if this endpoint is cacheable
        cache_config = self._get_cache_config(request.url.path)

        if cache_config and request.method in self.safe_methods:
            # Try to serve from cache
            cached_response = await self._get_cached_response(request, cache_config)
            if cached_response:
                await self._send_cached_response(send, cached_response)
                return

        # Process request normally and potentially cache response
        response_data = {"body_chunks": []}
        status_code = 200

        async def capture_send(message):
            """Capture response data for caching."""
            nonlocal response_data, status_code

            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))

                # Add X-Cache: MISS header for non-cached responses
                headers.append([b"x-cache", b"MISS"])

                response_data["headers"] = headers
                message = {**message, "headers": headers}

            elif message["type"] == "http.response.body":
                # Accumulate body chunks (ASGI may send body in multiple parts)
                body_chunk = message.get("body", b"")
                if body_chunk:
                    response_data["body_chunks"].append(body_chunk)

                # Check if this is the final body chunk
                more_body = message.get("more_body", False)
                if not more_body:
                    # Combine all chunks into final body
                    response_data["body"] = b"".join(response_data["body_chunks"])

                    # Cache successful responses
                    if (cache_config and
                        request.method in self.safe_methods and
                        200 <= status_code < 300):
                        await self._cache_response(request, cache_config, response_data, status_code)

                    # Handle cache invalidation for non-safe methods
                    if request.method not in self.safe_methods:
                        await self._handle_cache_invalidation(request)

            await send(message)

        await self.app(scope, receive, capture_send)

    def _get_cache_config(self, path: str) -> Optional[Dict[str, Any]]:
        """Get cache configuration for endpoint path."""
        for endpoint_pattern, config in self.cacheable_endpoints.items():
            if self._path_matches(path, endpoint_pattern):
                return config
        return None

    def _path_matches(self, path: str, pattern: str) -> bool:
        """Check if path matches endpoint pattern."""
        if pattern.endswith("/"):
            return path.startswith(pattern) or path == pattern[:-1]
        return path.startswith(pattern)

    async def _get_cached_response(self, request: Request, cache_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached response if available."""
        try:
            cache_key = self._generate_cache_key(request, cache_config)
            cached_data = self.cache_manager.get(cache_key)

            if cached_data:
                logger.debug(f"Cache hit for key: {cache_key}")
                # Return cached data as-is - don't add extra headers
                # Adding headers here would cause Content-Length mismatch
                return cached_data

        except Exception as e:
            logger.warning(f"Failed to get cached response: {e}")

        return None

    async def _cache_response(self, request: Request, cache_config: Dict[str, Any],
                             response_data: Dict[str, Any], status_code: int):
        """Cache the response data."""
        try:
            cache_key = self._generate_cache_key(request, cache_config)

            # Convert headers to JSON-serializable format, stripping Content-Length
            # Headers come as list of [bytes, bytes] tuples from ASGI
            serializable_headers = []
            for header in response_data["headers"]:
                header_name = header[0] if isinstance(header[0], str) else header[0].decode('latin-1')
                # Skip Content-Length - will be recalculated on retrieval
                if header_name.lower() == 'content-length':
                    continue
                # Skip X-Cache header if present (we add our own)
                if header_name.lower() == 'x-cache':
                    continue
                header_value = header[1] if isinstance(header[1], str) else header[1].decode('latin-1')
                serializable_headers.append([header_name, header_value])

            # Encode body to base64 for safe JSON serialization
            body_bytes = response_data["body"]
            if isinstance(body_bytes, bytes):
                body_b64 = base64.b64encode(body_bytes).decode('ascii')
            else:
                body_b64 = base64.b64encode(body_bytes.encode('utf-8')).decode('ascii')

            # Prepare response for caching
            cache_data = {
                "status_code": status_code,
                "headers": serializable_headers,
                "body_b64": body_b64,
                "cached_at": time.time(),
                "cache_ttl": cache_config["ttl"]
            }

            self.cache_manager.set(cache_key, cache_data, cache_config["ttl"])
            logger.debug(f"Cached response for key: {cache_key}")

        except Exception as e:
            logger.warning(f"Failed to cache response: {e}")

    def _generate_cache_key(self, request: Request, cache_config: Dict[str, Any]) -> str:
        """Generate cache key for request."""
        key_components = [
            "api_response",
            request.url.path,
            request.method
        ]

        # Include query parameters if configured
        if cache_config.get("cache_query_params", False):
            query_params = dict(request.query_params)
            if query_params:
                # Sort parameters for consistent keys
                sorted_params = json.dumps(query_params, sort_keys=True)
                key_components.append(hashlib.md5(sorted_params.encode()).hexdigest()[:8])

        # Note: We intentionally exclude accept-encoding from cache key.
        # The response body is stored as-is (compressed or not), so clients
        # may receive compressed responses even if they didn't request it.
        # For JSON APIs this is generally acceptable.

        # Include accept header for content negotiation (json vs other formats)
        accept_header = request.headers.get("accept", "")
        if accept_header and "application/json" not in accept_header:
            headers_hash = hashlib.md5(accept_header.encode()).hexdigest()[:8]
            key_components.append(headers_hash)

        return self.cache_manager._get_cache_key(*key_components)

    async def _send_cached_response(self, send: Callable, cached_data: Dict[str, Any]):
        """Send cached response with correct Content-Length."""
        # Handle both new format (body_b64) and legacy format (body)
        if "body_b64" in cached_data:
            body = base64.b64decode(cached_data["body_b64"])
        elif "body" in cached_data:
            # Legacy format fallback
            body = cached_data["body"]
            if isinstance(body, str):
                body = body.encode('utf-8')
            elif not isinstance(body, bytes):
                body = str(body).encode('utf-8')
        else:
            logger.warning("No body found in cached data")
            body = b""

        # Rebuild headers with correct Content-Length
        headers = []
        for header in cached_data["headers"]:
            # Convert string headers back to bytes (ASGI requires bytes)
            header_name = header[0].encode('latin-1') if isinstance(header[0], str) else header[0]
            header_value = header[1].encode('latin-1') if isinstance(header[1], str) else header[1]

            # Skip any existing content-length (shouldn't be there, but be defensive)
            if header_name.lower() == b'content-length':
                continue
            headers.append([header_name, header_value])

        # Add correct Content-Length based on actual body size
        headers.append([b"content-length", str(len(body)).encode('ascii')])

        # Add X-Cache: HIT header for debugging
        headers.append([b"x-cache", b"HIT"])

        # Add X-Cache-Age header showing how old the cached response is
        cached_at = cached_data.get("cached_at", 0)
        if cached_at:
            cache_age = int(time.time() - cached_at)
            headers.append([b"x-cache-age", str(cache_age).encode('ascii')])

        await send({
            "type": "http.response.start",
            "status": cached_data["status_code"],
            "headers": headers,
        })

        await send({
            "type": "http.response.body",
            "body": body,
        })

    async def _handle_cache_invalidation(self, request: Request):
        """Handle cache invalidation for modifying requests."""
        try:
            # Find matching invalidation patterns
            for endpoint_pattern, cache_types in self.invalidation_endpoints.items():
                if self._path_matches(request.url.path, endpoint_pattern):
                    logger.info(f"Invalidating caches for {request.method} {request.url.path}")

                    # Invalidate specific cache types
                    for cache_type in cache_types:
                        self.cache_manager.clear_pattern(f"aaw:{cache_type}:*")

                    # Also clear API response caches
                    self.cache_manager.clear_pattern("aaw:api_response:*")
                    break

        except Exception as e:
            logger.warning(f"Failed to handle cache invalidation: {e}")


class CacheControlMiddleware:
    """Middleware to add cache control headers."""

    def __init__(self, app):
        self.app = app

        # Default cache control settings by endpoint type
        self.cache_control_settings = {
            "/api/v1/properties/": {
                "max_age": 300,  # 5 minutes
                "public": True,
                "must_revalidate": False
            },
            "/api/v1/analytics/": {
                "max_age": 1800,  # 30 minutes
                "public": True,
                "must_revalidate": False
            },
            "/api/v1/admin/": {
                "max_age": 0,
                "no_cache": True,
                "no_store": True
            }
        }

    async def __call__(self, scope: dict, receive: Callable, send: Callable):
        """Add cache control headers to responses."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        async def add_cache_headers(message):
            """Add cache control headers."""
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))

                # Get cache control settings for this endpoint
                cache_settings = self._get_cache_settings(request.url.path)

                if cache_settings:
                    cache_control_parts = []

                    if cache_settings.get("no_cache"):
                        cache_control_parts.append("no-cache")
                    if cache_settings.get("no_store"):
                        cache_control_parts.append("no-store")
                    if cache_settings.get("public"):
                        cache_control_parts.append("public")
                    if cache_settings.get("private"):
                        cache_control_parts.append("private")
                    if cache_settings.get("must_revalidate"):
                        cache_control_parts.append("must-revalidate")

                    max_age = cache_settings.get("max_age")
                    if max_age is not None:
                        cache_control_parts.append(f"max-age={max_age}")

                    if cache_control_parts:
                        cache_control_value = ", ".join(cache_control_parts)
                        headers.append([b"cache-control", cache_control_value.encode()])

                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, add_cache_headers)

    def _get_cache_settings(self, path: str) -> Optional[Dict[str, Any]]:
        """Get cache control settings for path."""
        for endpoint_pattern, settings in self.cache_control_settings.items():
            if path.startswith(endpoint_pattern):
                return settings
        return None


def add_cache_headers_dependency():
    """FastAPI dependency to add cache information to responses."""
    def _add_headers(request: Request, response: Response):
        """Add cache-related headers to response."""
        cache_manager = get_cache_manager()

        # Add cache statistics headers (for debugging)
        stats = cache_manager.get_stats()
        response.headers["X-Cache-Hit-Rate"] = f"{stats['hit_rate']:.2f}"
        response.headers["X-Cache-Backend"] = "redis" if stats["redis_available"] else "memory"

        # Add cache warming info
        if hasattr(request.state, 'cache_warmed'):
            response.headers["X-Cache-Warmed"] = "true"

        return response

    return _add_headers


# Convenience functions for manual cache operations

def invalidate_property_cache(property_id: str):
    """Manually invalidate cache for a specific property."""
    cache_invalidator = get_cache_invalidator()
    cache_invalidator.invalidate_property_caches(property_id=property_id)

def invalidate_county_cache(county: str):
    """Manually invalidate cache for a specific county."""
    cache_invalidator = get_cache_invalidator()
    cache_invalidator.invalidate_property_caches(county=county)

def invalidate_all_search_caches():
    """Manually invalidate all search caches."""
    cache_invalidator = get_cache_invalidator()
    cache_invalidator.invalidate_search_caches()

def get_cache_stats() -> Dict[str, Any]:
    """Get current cache statistics."""
    cache_manager = get_cache_manager()
    return cache_manager.get_stats()