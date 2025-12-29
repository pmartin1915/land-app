"""
Enhanced Rate Limiting System for Alabama Auction Watcher

This module provides sophisticated rate limiting with multiple protection layers:
- Adaptive limits based on user behavior
- Burst protection and progressive penalties
- Geographic and IP reputation-based limiting
- Resource-specific protection
- Attack pattern detection and mitigation
"""

import time
import logging
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


class RateLimitTier(Enum):
    """Rate limiting tiers based on authentication and behavior."""
    ANONYMOUS = "anonymous"
    AUTHENTICATED = "authenticated"
    PREMIUM = "premium"
    ADMIN = "admin"
    BLOCKED = "blocked"


class AttackPattern(Enum):
    """Types of attack patterns to detect."""
    BRUTE_FORCE = "brute_force"
    SCRAPING = "scraping"
    ENUMERATION = "enumeration"
    DOS_ATTACK = "dos_attack"
    INJECTION_ATTEMPT = "injection_attempt"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting rules."""
    # Basic limits per tier
    requests_per_minute: Dict[RateLimitTier, int] = field(default_factory=lambda: {
        RateLimitTier.ANONYMOUS: 30,
        RateLimitTier.AUTHENTICATED: 100,
        RateLimitTier.PREMIUM: 500,
        RateLimitTier.ADMIN: 1000,
        RateLimitTier.BLOCKED: 0
    })

    # Burst limits (short-term)
    burst_requests_per_second: Dict[RateLimitTier, int] = field(default_factory=lambda: {
        RateLimitTier.ANONYMOUS: 2,
        RateLimitTier.AUTHENTICATED: 5,
        RateLimitTier.PREMIUM: 10,
        RateLimitTier.ADMIN: 20,
        RateLimitTier.BLOCKED: 0
    })

    # Daily limits
    requests_per_day: Dict[RateLimitTier, int] = field(default_factory=lambda: {
        RateLimitTier.ANONYMOUS: 1000,
        RateLimitTier.AUTHENTICATED: 10000,
        RateLimitTier.PREMIUM: 100000,
        RateLimitTier.ADMIN: 1000000,
        RateLimitTier.BLOCKED: 0
    })

    # Progressive penalty multipliers
    penalty_escalation: List[float] = field(default_factory=lambda: [1.0, 0.5, 0.25, 0.1, 0.0])

    # Resource-specific limits
    resource_limits: Dict[str, Dict[RateLimitTier, int]] = field(default_factory=lambda: {
        "search": {
            RateLimitTier.ANONYMOUS: 10,
            RateLimitTier.AUTHENTICATED: 50,
            RateLimitTier.PREMIUM: 200,
            RateLimitTier.ADMIN: 500
        },
        "bulk_operations": {
            RateLimitTier.ANONYMOUS: 0,
            RateLimitTier.AUTHENTICATED: 5,
            RateLimitTier.PREMIUM: 20,
            RateLimitTier.ADMIN: 100
        },
        "data_export": {
            RateLimitTier.ANONYMOUS: 0,
            RateLimitTier.AUTHENTICATED: 3,
            RateLimitTier.PREMIUM: 10,
            RateLimitTier.ADMIN: 50
        }
    })


@dataclass
class RequestMetrics:
    """Metrics for tracking request patterns."""
    request_count: int = 0
    error_count: int = 0
    last_request_time: float = 0
    first_request_time: float = 0
    consecutive_errors: int = 0
    endpoints_accessed: set = field(default_factory=set)
    user_agents: set = field(default_factory=set)
    request_sizes: List[int] = field(default_factory=list)
    # maxlen=300 allows DOS detection (threshold 200) to work correctly
    response_times: deque = field(default_factory=lambda: deque(maxlen=300))


class EnhancedRateLimiter:
    """Sophisticated rate limiting with multiple protection layers."""

    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()

        # Tracking storage
        self.client_metrics: Dict[str, RequestMetrics] = defaultdict(RequestMetrics)
        self.rate_limit_violations: Dict[str, List[float]] = defaultdict(list)
        self.blocked_ips: Dict[str, float] = {}  # IP -> block_until_timestamp
        self.client_tiers: Dict[str, RateLimitTier] = defaultdict(lambda: RateLimitTier.ANONYMOUS)

        # Attack pattern detection
        self.attack_patterns: Dict[str, List[Tuple[AttackPattern, float]]] = defaultdict(list)

        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()

    def _start_cleanup_task(self):
        """Start background task for cleaning up old data."""
        if self._cleanup_task is None or self._cleanup_task.done():
            try:
                # Only create task if there's a running event loop
                loop = asyncio.get_running_loop()
                self._cleanup_task = loop.create_task(self._cleanup_old_data())
            except RuntimeError:
                # No running event loop (e.g., during testing or sync context)
                # Cleanup will be handled manually or when a loop is available
                pass

    async def _cleanup_old_data(self):
        """Periodically clean up old tracking data."""
        while True:
            try:
                current_time = time.time()
                cutoff_time = current_time - 86400  # 24 hours

                # Clean up old violations
                for client_id in list(self.rate_limit_violations.keys()):
                    self.rate_limit_violations[client_id] = [
                        t for t in self.rate_limit_violations[client_id]
                        if t > cutoff_time
                    ]
                    if not self.rate_limit_violations[client_id]:
                        del self.rate_limit_violations[client_id]

                # Clean up expired blocks
                self.blocked_ips = {
                    ip: block_time for ip, block_time in self.blocked_ips.items()
                    if block_time > current_time
                }

                # Clean up old attack patterns
                for client_id in list(self.attack_patterns.keys()):
                    self.attack_patterns[client_id] = [
                        (pattern, timestamp) for pattern, timestamp in self.attack_patterns[client_id]
                        if timestamp > cutoff_time
                    ]
                    if not self.attack_patterns[client_id]:
                        del self.attack_patterns[client_id]

                await asyncio.sleep(3600)  # Clean up every hour

            except Exception as e:
                logger.error(f"Error in rate limiter cleanup: {e}")
                await asyncio.sleep(300)  # Retry in 5 minutes on error

    def get_client_identifier(self, request: Any) -> str:
        """Generate unique client identifier from request."""
        # Try to get user ID from auth data
        # Use getattr with None default to handle Mock objects properly
        user_id = getattr(request.state, 'user_id', None)
        if user_id is not None and not str(user_id).startswith('<Mock'):
            return f"user:{user_id}"

        # Fall back to IP address
        client_ip = getattr(request.client, 'host', 'unknown')

        # Add additional fingerprinting for anonymous users
        user_agent = request.headers.get('user-agent', '')
        fingerprint = hashlib.md5(f"{client_ip}:{user_agent}".encode()).hexdigest()[:8]

        return f"ip:{client_ip}:{fingerprint}"

    def get_client_tier(self, client_id: str, auth_data: Optional[Dict] = None) -> RateLimitTier:
        """Determine client rate limiting tier."""
        # Check if IP is blocked
        ip_part = client_id.split(':')[1] if ':' in client_id else client_id
        if ip_part in self.blocked_ips and self.blocked_ips[ip_part] > time.time():
            return RateLimitTier.BLOCKED

        # When auth_data is provided, always recalculate tier (auth state may have changed)
        # Only use cached tier when no auth_data is provided
        if auth_data is None and client_id in self.client_tiers:
            return self.client_tiers[client_id]

        # Determine tier from auth data
        if auth_data:
            if auth_data.get('is_admin'):
                tier = RateLimitTier.ADMIN
            elif auth_data.get('is_premium'):
                tier = RateLimitTier.PREMIUM
            elif auth_data.get('is_authenticated'):
                tier = RateLimitTier.AUTHENTICATED
            else:
                # auth_data provided but no recognized flags - treat as authenticated
                tier = RateLimitTier.AUTHENTICATED
        else:
            tier = RateLimitTier.ANONYMOUS

        # Cache the tier
        self.client_tiers[client_id] = tier
        return tier

    def check_rate_limit(self, client_id: str, resource: str = "default",
                        request_size: int = 0) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request should be allowed based on rate limits.

        Returns:
            Tuple of (allowed, info_dict)
        """
        current_time = time.time()

        # Get client metrics
        metrics = self.client_metrics[client_id]
        tier = self.get_client_tier(client_id)

        # Check if client is blocked
        if tier == RateLimitTier.BLOCKED:
            return False, {
                "error": "Client is blocked",
                "retry_after": 3600,
                "tier": tier.value
            }

        # Initialize tracking if first request
        if metrics.first_request_time == 0:
            metrics.first_request_time = current_time

        # Check burst protection (requests per second)
        time_window = 1  # 1 second
        recent_requests = sum(1 for t in metrics.response_times
                            if current_time - t <= time_window)

        burst_limit = self.config.burst_requests_per_second[tier]
        if recent_requests >= burst_limit:
            self._record_violation(client_id, "burst_limit")
            return False, {
                "error": "Burst limit exceeded",
                "retry_after": 1,
                "limit": burst_limit,
                "current": recent_requests
            }

        # Check per-minute limits
        minute_window = 60
        minute_requests = sum(1 for t in metrics.response_times
                            if current_time - t <= minute_window)

        minute_limit = self.config.requests_per_minute[tier]

        # Apply progressive penalties for repeated violations
        penalty_multiplier = self._get_penalty_multiplier(client_id)
        effective_limit = int(minute_limit * penalty_multiplier)

        if minute_requests >= effective_limit:
            self._record_violation(client_id, "minute_limit")
            return False, {
                "error": "Rate limit exceeded",
                "retry_after": 60,
                "limit": effective_limit,
                "current": minute_requests,
                "penalty_applied": penalty_multiplier < 1.0
            }

        # Check resource-specific limits
        if resource in self.config.resource_limits:
            resource_limit = self.config.resource_limits[resource].get(tier, 0)
            resource_requests = len([t for t in metrics.response_times
                                   if current_time - t <= minute_window])

            if resource_requests >= resource_limit:
                self._record_violation(client_id, f"resource_limit_{resource}")
                return False, {
                    "error": f"Resource limit exceeded for {resource}",
                    "retry_after": 60,
                    "limit": resource_limit,
                    "current": resource_requests
                }

        # Check daily limits
        day_window = 86400  # 24 hours
        if metrics.first_request_time < current_time - day_window:
            # Reset daily counter
            metrics.first_request_time = current_time
            metrics.request_count = 0

        daily_limit = self.config.requests_per_day[tier]
        if metrics.request_count >= daily_limit:
            return False, {
                "error": "Daily limit exceeded",
                "retry_after": int((metrics.first_request_time + day_window) - current_time),
                "limit": daily_limit,
                "current": metrics.request_count
            }

        # Request is allowed
        return True, {
            "allowed": True,
            "tier": tier.value,
            "remaining_minute": effective_limit - minute_requests,
            "remaining_daily": daily_limit - metrics.request_count
        }

    def record_request(self, client_id: str, endpoint: str, user_agent: str = "",
                      request_size: int = 0, response_time: float = 0,
                      error_occurred: bool = False):
        """Record request metrics for monitoring and analysis."""
        current_time = time.time()
        metrics = self.client_metrics[client_id]

        # Update basic metrics
        metrics.request_count += 1
        metrics.last_request_time = current_time
        metrics.response_times.append(current_time)

        # Track endpoints and user agents
        metrics.endpoints_accessed.add(endpoint)
        if user_agent:
            metrics.user_agents.add(user_agent)

        # Track request sizes
        if request_size > 0:
            metrics.request_sizes.append(request_size)

        # Track errors
        if error_occurred:
            metrics.error_count += 1
            metrics.consecutive_errors += 1
        else:
            metrics.consecutive_errors = 0

        # Detect attack patterns
        self._detect_attack_patterns(client_id, endpoint, metrics)

    def _record_violation(self, client_id: str, violation_type: str):
        """Record rate limit violation for progressive penalties."""
        current_time = time.time()
        self.rate_limit_violations[client_id].append(current_time)

        # Clean up old violations (older than 1 hour)
        cutoff_time = current_time - 3600
        self.rate_limit_violations[client_id] = [
            t for t in self.rate_limit_violations[client_id] if t > cutoff_time
        ]

        logger.warning(f"Rate limit violation: {client_id} - {violation_type}")

    def _get_penalty_multiplier(self, client_id: str) -> float:
        """Calculate penalty multiplier based on recent violations."""
        violations_count = len(self.rate_limit_violations[client_id])

        if violations_count >= len(self.config.penalty_escalation):
            return self.config.penalty_escalation[-1]
        elif violations_count > 0:
            return self.config.penalty_escalation[violations_count - 1]
        else:
            return 1.0

    def _detect_attack_patterns(self, client_id: str, endpoint: str, metrics: RequestMetrics):
        """Detect potential attack patterns and escalate accordingly."""
        current_time = time.time()

        # Brute force detection (many errors in sequence)
        if metrics.consecutive_errors >= 10:
            self._flag_attack_pattern(client_id, AttackPattern.BRUTE_FORCE)

        # Scraping detection (many different endpoints accessed quickly)
        if len(metrics.endpoints_accessed) > 20:
            recent_requests = sum(1 for t in metrics.response_times
                                if current_time - t <= 300)  # 5 minutes
            if recent_requests > 50:
                self._flag_attack_pattern(client_id, AttackPattern.SCRAPING)

        # DOS attack detection (very high request rate)
        recent_requests = sum(1 for t in metrics.response_times
                            if current_time - t <= 60)  # 1 minute
        if recent_requests > 200:
            self._flag_attack_pattern(client_id, AttackPattern.DOS_ATTACK)

        # Enumeration detection (systematic endpoint scanning)
        if len(metrics.endpoints_accessed) > 10 and metrics.error_count > 20:
            error_rate = metrics.error_count / metrics.request_count
            if error_rate > 0.7:  # 70% error rate
                self._flag_attack_pattern(client_id, AttackPattern.ENUMERATION)

    def _flag_attack_pattern(self, client_id: str, pattern: AttackPattern):
        """Flag a detected attack pattern and take appropriate action."""
        current_time = time.time()
        self.attack_patterns[client_id].append((pattern, current_time))

        # Count recent attack patterns
        recent_patterns = [p for p, t in self.attack_patterns[client_id]
                          if current_time - t <= 3600]  # Last hour

        # Escalate based on pattern severity and frequency
        if len(recent_patterns) >= 3 or pattern == AttackPattern.DOS_ATTACK:
            # Block the client
            ip_part = client_id.split(':')[1] if ':' in client_id else client_id
            self.blocked_ips[ip_part] = current_time + 3600  # Block for 1 hour

            logger.error(f"Client blocked due to attack pattern: {client_id} - {pattern.value}")

        logger.warning(f"Attack pattern detected: {client_id} - {pattern.value}")

    def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a client."""
        metrics = self.client_metrics[client_id]
        tier = self.get_client_tier(client_id)

        current_time = time.time()

        # Calculate request rates
        minute_requests = sum(1 for t in metrics.response_times
                            if current_time - t <= 60)
        hour_requests = sum(1 for t in metrics.response_times
                          if current_time - t <= 3600)

        # Calculate average response time
        if metrics.response_times:
            avg_response_time = sum(metrics.response_times) / len(metrics.response_times)
        else:
            avg_response_time = 0

        return {
            "client_id": client_id,
            "tier": tier.value,
            "total_requests": metrics.request_count,
            "error_count": metrics.error_count,
            "error_rate": metrics.error_count / max(metrics.request_count, 1),
            "requests_last_minute": minute_requests,
            "requests_last_hour": hour_requests,
            "unique_endpoints": len(metrics.endpoints_accessed),
            "unique_user_agents": len(metrics.user_agents),
            "consecutive_errors": metrics.consecutive_errors,
            "average_response_time": avg_response_time,
            "violations_last_hour": len(self.rate_limit_violations[client_id]),
            "attack_patterns": [p.value for p, _ in self.attack_patterns[client_id]],
            "penalty_multiplier": self._get_penalty_multiplier(client_id)
        }


# Global rate limiter instance
_rate_limiter: Optional[EnhancedRateLimiter] = None


def get_rate_limiter() -> EnhancedRateLimiter:
    """Get global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = EnhancedRateLimiter()
    return _rate_limiter


def create_rate_limit_decorator(resource: str = "default"):
    """Create a decorator for endpoint-specific rate limiting."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract request from args
            request = None
            for arg in args:
                if hasattr(arg, 'client'):  # FastAPI Request object
                    request = arg
                    break

            if request:
                limiter = get_rate_limiter()
                client_id = limiter.get_client_identifier(request)

                # Check rate limit
                allowed, info = limiter.check_rate_limit(client_id, resource)

                if not allowed:
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=429,
                        detail=info.get("error", "Rate limit exceeded"),
                        headers={"Retry-After": str(info.get("retry_after", 60))}
                    )

                # Record the request
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)

                    # Record successful request
                    response_time = time.time() - start_time
                    limiter.record_request(
                        client_id=client_id,
                        endpoint=request.url.path,
                        user_agent=request.headers.get('user-agent', ''),
                        response_time=response_time,
                        error_occurred=False
                    )

                    return result

                except Exception:
                    # Record error
                    response_time = time.time() - start_time
                    limiter.record_request(
                        client_id=client_id,
                        endpoint=request.url.path,
                        user_agent=request.headers.get('user-agent', ''),
                        response_time=response_time,
                        error_occurred=True
                    )
                    raise
            else:
                return await func(*args, **kwargs)

        return wrapper
    return decorator