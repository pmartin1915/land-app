"""
Enhanced Rate Limiting Middleware for Alabama Auction Watcher API

This middleware integrates the sophisticated rate limiting system with FastAPI,
providing comprehensive protection against various types of abuse and attacks.
"""

import time
import logging
from fastapi import Request, Response, HTTPException
from typing import Callable, Dict, Any
import json

import sys
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.rate_limiting import get_rate_limiter

logger = logging.getLogger(__name__)


class RateLimitingMiddleware:
    """FastAPI middleware for enhanced rate limiting."""

    def __init__(self, app):
        self.app = app
        self.rate_limiter = get_rate_limiter()

        # Endpoint classifications for resource-specific limiting
        self.endpoint_resources = {
            "/api/v1/properties/": "search",
            "/api/v1/properties/search": "search",
            "/api/v1/properties/bulk": "bulk_operations",
            "/api/v1/properties/export": "data_export",
            "/api/v1/sync/full": "bulk_operations",
            "/api/v1/sync/bulk": "bulk_operations"
        }

        # Exempt endpoints (health checks, etc.)
        self.exempt_endpoints = {
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc"
        }

    async def __call__(self, scope: dict, receive: Callable, send: Callable):
        """Process request through rate limiting middleware."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Skip rate limiting for exempt endpoints
        if any(request.url.path.startswith(exempt) for exempt in self.exempt_endpoints):
            await self.app(scope, receive, send)
            return

        # Get client identifier and authentication data
        client_id = self.rate_limiter.get_client_identifier(request)
        auth_data = self._extract_auth_data(request)

        # Update client tier based on auth data
        if auth_data:
            tier = self.rate_limiter.get_client_tier(client_id, auth_data)
            self.rate_limiter.client_tiers[client_id] = tier

        # Determine resource type for this endpoint
        resource = self._get_resource_type(request.url.path)

        # Check rate limits
        start_time = time.time()
        allowed, limit_info = self.rate_limiter.check_rate_limit(
            client_id=client_id,
            resource=resource,
            request_size=self._get_request_size(request)
        )

        if not allowed:
            # Rate limit exceeded - return 429 response
            await self._send_rate_limit_response(send, limit_info)

            # Still record the blocked request for metrics
            self.rate_limiter.record_request(
                client_id=client_id,
                endpoint=request.url.path,
                user_agent=request.headers.get('user-agent', ''),
                request_size=self._get_request_size(request),
                response_time=time.time() - start_time,
                error_occurred=True
            )
            return

        # Store rate limit info for potential use by endpoints
        request.state.rate_limit_info = limit_info
        request.state.client_id = client_id

        # Process request normally
        error_occurred = False
        try:
            await self.app(scope, receive, send)
        except Exception:
            error_occurred = True
            raise
        finally:
            # Record request metrics
            response_time = time.time() - start_time
            self.rate_limiter.record_request(
                client_id=client_id,
                endpoint=request.url.path,
                user_agent=request.headers.get('user-agent', ''),
                request_size=self._get_request_size(request),
                response_time=response_time,
                error_occurred=error_occurred
            )

    def _extract_auth_data(self, request: Request) -> Dict[str, Any]:
        """Extract authentication data from request."""
        auth_data = {}

        # Check for API key in headers
        api_key = request.headers.get("X-API-Key")
        if api_key:
            # Basic tier detection based on API key pattern
            if api_key.startswith("AW_admin_"):
                auth_data["is_admin"] = True
            elif api_key.startswith("AW_premium_"):
                auth_data["is_premium"] = True
            elif api_key.startswith("AW_"):
                auth_data["is_authenticated"] = True

        # Check for user data in request state (set by auth middleware)
        if hasattr(request.state, 'user_data'):
            auth_data.update(request.state.user_data)

        return auth_data

    def _get_resource_type(self, path: str) -> str:
        """Determine resource type for rate limiting."""
        for endpoint_pattern, resource in self.endpoint_resources.items():
            if path.startswith(endpoint_pattern):
                return resource

        # Default resource type
        return "default"

    def _get_request_size(self, request: Request) -> int:
        """Estimate request size for rate limiting purposes."""
        # This is a simplified estimation
        # In production, you might want to read the actual body size
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                return int(content_length)
            except ValueError:
                pass

        # Estimate based on headers and query params
        header_size = sum(len(k) + len(v) for k, v in request.headers.items())
        query_size = len(str(request.query_params))

        return header_size + query_size

    async def _send_rate_limit_response(self, send: Callable, limit_info: Dict[str, Any]):
        """Send rate limit exceeded response."""
        response_data = {
            "error": "Rate limit exceeded",
            "message": limit_info.get("error", "Too many requests"),
            "retry_after": limit_info.get("retry_after", 60),
            "limit_info": {
                "current": limit_info.get("current"),
                "limit": limit_info.get("limit"),
                "tier": limit_info.get("tier"),
                "penalty_applied": limit_info.get("penalty_applied", False)
            }
        }

        # Add helpful information for legitimate users
        if not limit_info.get("penalty_applied"):
            response_data["help"] = {
                "message": "Consider authenticating for higher rate limits",
                "documentation": "/docs#rate-limiting"
            }

        response_body = json.dumps(response_data).encode()
        retry_after = str(limit_info.get("retry_after", 60))

        await send({
            "type": "http.response.start",
            "status": 429,
            "headers": [
                [b"content-type", b"application/json"],
                [b"content-length", str(len(response_body)).encode()],
                [b"retry-after", retry_after.encode()],
                [b"x-ratelimit-limit", str(limit_info.get("limit", 0)).encode()],
                [b"x-ratelimit-remaining", str(max(0, limit_info.get("limit", 0) - limit_info.get("current", 0))).encode()],
                [b"x-ratelimit-reset", str(int(time.time() + limit_info.get("retry_after", 60))).encode()],
            ],
        })

        await send({
            "type": "http.response.body",
            "body": response_body,
        })


def add_rate_limit_headers(response: Response, request: Request) -> Response:
    """Add rate limiting information to response headers."""
    if hasattr(request.state, 'rate_limit_info') and hasattr(request.state, 'client_id'):
        rate_limiter = get_rate_limiter()
        client_stats = rate_limiter.get_client_stats(request.state.client_id)

        # Add informational headers
        response.headers["X-RateLimit-Tier"] = client_stats["tier"]
        response.headers["X-RateLimit-Requests-Remaining"] = str(client_stats.get("remaining_minute", 0))
        response.headers["X-RateLimit-Daily-Remaining"] = str(client_stats.get("remaining_daily", 0))
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))

        # Add warning headers if approaching limits
        if client_stats.get("remaining_minute", 0) < 10:
            response.headers["X-RateLimit-Warning"] = "Approaching rate limit"

        if client_stats.get("penalty_multiplier", 1.0) < 1.0:
            response.headers["X-RateLimit-Penalty"] = f"Reduced limit due to violations (multiplier: {client_stats['penalty_multiplier']:.2f})"

    return response


class RateLimitingDependency:
    """FastAPI dependency for endpoint-specific rate limiting."""

    def __init__(self, resource: str = "default", strict: bool = False):
        self.resource = resource
        self.strict = strict

    async def __call__(self, request: Request) -> Dict[str, Any]:
        """Check rate limits for specific endpoint."""
        rate_limiter = get_rate_limiter()
        client_id = rate_limiter.get_client_identifier(request)

        # Check if already checked by middleware
        if hasattr(request.state, 'rate_limit_info'):
            return request.state.rate_limit_info

        # Perform rate limit check
        allowed, limit_info = rate_limiter.check_rate_limit(
            client_id=client_id,
            resource=self.resource
        )

        if not allowed and self.strict:
            raise HTTPException(
                status_code=429,
                detail=limit_info.get("error", "Rate limit exceeded"),
                headers={"Retry-After": str(limit_info.get("retry_after", 60))}
            )

        return limit_info


# Convenience dependencies for common resources
search_rate_limit = RateLimitingDependency("search", strict=True)
bulk_rate_limit = RateLimitingDependency("bulk_operations", strict=True)
export_rate_limit = RateLimitingDependency("data_export", strict=True)


def get_client_stats_endpoint():
    """Dependency to get client statistics for monitoring endpoints."""
    async def _get_stats(request: Request) -> Dict[str, Any]:
        rate_limiter = get_rate_limiter()
        client_id = rate_limiter.get_client_identifier(request)
        return rate_limiter.get_client_stats(client_id)

    return _get_stats