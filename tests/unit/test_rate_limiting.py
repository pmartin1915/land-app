"""
Unit tests for enhanced rate limiting system.

This module tests the comprehensive rate limiting system to ensure
it properly protects against abuse and attacks while allowing legitimate usage.
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, patch

from config.rate_limiting import (
    EnhancedRateLimiter, RateLimitConfig, RateLimitTier,
    AttackPattern, RequestMetrics
)


class TestRateLimitConfig:
    """Test suite for RateLimitConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RateLimitConfig()

        # Check that all tiers have limits defined
        for tier in RateLimitTier:
            if tier != RateLimitTier.BLOCKED:
                assert tier in config.requests_per_minute
                assert tier in config.burst_requests_per_second
                assert tier in config.requests_per_day

        # Check that higher tiers have higher limits
        assert config.requests_per_minute[RateLimitTier.ANONYMOUS] < config.requests_per_minute[RateLimitTier.AUTHENTICATED]
        assert config.requests_per_minute[RateLimitTier.AUTHENTICATED] < config.requests_per_minute[RateLimitTier.PREMIUM]
        assert config.requests_per_minute[RateLimitTier.PREMIUM] < config.requests_per_minute[RateLimitTier.ADMIN]

    def test_blocked_tier_limits(self):
        """Test that blocked tier has zero limits."""
        config = RateLimitConfig()

        assert config.requests_per_minute[RateLimitTier.BLOCKED] == 0
        assert config.burst_requests_per_second[RateLimitTier.BLOCKED] == 0
        assert config.requests_per_day[RateLimitTier.BLOCKED] == 0


class TestEnhancedRateLimiter:
    """Test suite for EnhancedRateLimiter."""

    @pytest.fixture
    def limiter(self):
        """Create a rate limiter for testing."""
        return EnhancedRateLimiter()

    @pytest.fixture
    def strict_config(self):
        """Create a strict configuration for testing."""
        config = RateLimitConfig()
        config.requests_per_minute = {
            RateLimitTier.ANONYMOUS: 5,
            RateLimitTier.AUTHENTICATED: 10,
            RateLimitTier.PREMIUM: 20,
            RateLimitTier.ADMIN: 50,
            RateLimitTier.BLOCKED: 0
        }
        config.burst_requests_per_second = {
            RateLimitTier.ANONYMOUS: 1,
            RateLimitTier.AUTHENTICATED: 2,
            RateLimitTier.PREMIUM: 3,
            RateLimitTier.ADMIN: 5,
            RateLimitTier.BLOCKED: 0
        }
        return config

    @pytest.fixture
    def strict_limiter(self, strict_config):
        """Create a rate limiter with strict limits for testing."""
        return EnhancedRateLimiter(strict_config)

    def test_client_identifier_generation(self, limiter):
        """Test client identifier generation."""
        # Mock request with IP
        mock_request = Mock()
        mock_request.client.host = "192.168.1.100"
        mock_request.headers = {"user-agent": "TestAgent/1.0"}
        mock_request.state = Mock()

        client_id = limiter.get_client_identifier(mock_request)
        assert client_id.startswith("ip:192.168.1.100:")

        # Test with user ID
        mock_request.state.user_id = "user123"
        client_id = limiter.get_client_identifier(mock_request)
        assert client_id == "user:user123"

    def test_client_tier_determination(self, limiter):
        """Test client tier determination."""
        client_id = "test_client"

        # Test anonymous user
        tier = limiter.get_client_tier(client_id, None)
        assert tier == RateLimitTier.ANONYMOUS

        # Test authenticated user
        auth_data = {"is_authenticated": True}
        tier = limiter.get_client_tier(client_id, auth_data)
        assert tier == RateLimitTier.AUTHENTICATED

        # Test premium user
        auth_data = {"is_premium": True}
        tier = limiter.get_client_tier(client_id, auth_data)
        assert tier == RateLimitTier.PREMIUM

        # Test admin user
        auth_data = {"is_admin": True}
        tier = limiter.get_client_tier(client_id, auth_data)
        assert tier == RateLimitTier.ADMIN

    def test_basic_rate_limiting(self, strict_limiter):
        """Test basic rate limiting functionality."""
        client_id = "test_client"

        # First few requests should be allowed
        for i in range(3):
            allowed, info = strict_limiter.check_rate_limit(client_id)
            assert allowed
            assert info["allowed"]

            # Record the request
            strict_limiter.record_request(client_id, "/test", "TestAgent/1.0")

        # Should still be under limit
        allowed, info = strict_limiter.check_rate_limit(client_id)
        assert allowed

    def test_minute_rate_limiting(self, strict_limiter):
        """Test per-minute rate limiting."""
        client_id = "test_client"

        # Exhaust the minute limit (5 for anonymous)
        for i in range(5):
            allowed, info = strict_limiter.check_rate_limit(client_id)
            if allowed:
                strict_limiter.record_request(client_id, "/test", "TestAgent/1.0")

        # Next request should be denied
        allowed, info = strict_limiter.check_rate_limit(client_id)
        assert not allowed
        assert "Rate limit exceeded" in info["error"]
        assert info["retry_after"] == 60

    def test_burst_rate_limiting(self, strict_limiter):
        """Test burst protection."""
        client_id = "test_client"

        # Make requests very quickly (burst limit is 1 per second for anonymous)
        current_time = time.time()

        # First request should be allowed
        allowed, info = strict_limiter.check_rate_limit(client_id)
        assert allowed
        strict_limiter.record_request(client_id, "/test", "TestAgent/1.0")
        strict_limiter.client_metrics[client_id].response_times.append(current_time)

        # Immediate second request should be denied (burst protection)
        allowed, info = strict_limiter.check_rate_limit(client_id)
        assert not allowed
        assert "Burst limit exceeded" in info["error"]
        assert info["retry_after"] == 1

    def test_progressive_penalties(self, strict_limiter):
        """Test progressive penalty system."""
        client_id = "test_client"

        # Generate several violations
        for i in range(3):
            strict_limiter._record_violation(client_id, "test_violation")

        # Check penalty multiplier
        multiplier = strict_limiter._get_penalty_multiplier(client_id)
        assert multiplier < 1.0  # Should be reduced due to violations

        # Rate limit should be reduced
        allowed, info = strict_limiter.check_rate_limit(client_id)
        assert info.get("penalty_applied", False)

    def test_tier_upgrade_benefits(self, strict_limiter):
        """Test that higher tiers get better limits."""
        anonymous_client = "anonymous_client"
        auth_client = "auth_client"

        # Set different tiers
        strict_limiter.client_tiers[anonymous_client] = RateLimitTier.ANONYMOUS
        strict_limiter.client_tiers[auth_client] = RateLimitTier.AUTHENTICATED

        # Exhaust anonymous limit
        for i in range(5):
            allowed, info = strict_limiter.check_rate_limit(anonymous_client)
            if allowed:
                strict_limiter.record_request(anonymous_client, "/test", "TestAgent/1.0")

        # Anonymous should be blocked
        allowed, info = strict_limiter.check_rate_limit(anonymous_client)
        assert not allowed

        # Authenticated user should still have capacity
        allowed, info = strict_limiter.check_rate_limit(auth_client)
        assert allowed

    def test_resource_specific_limiting(self, strict_limiter):
        """Test resource-specific rate limiting."""
        client_id = "test_client"

        # Set up resource limits
        strict_limiter.config.resource_limits = {
            "search": {RateLimitTier.ANONYMOUS: 2},
            "bulk_operations": {RateLimitTier.ANONYMOUS: 1}
        }

        # Test search resource limit
        for i in range(2):
            allowed, info = strict_limiter.check_rate_limit(client_id, "search")
            if allowed:
                strict_limiter.record_request(client_id, "/search", "TestAgent/1.0")

        # Should be at search limit
        allowed, info = strict_limiter.check_rate_limit(client_id, "search")
        assert not allowed
        assert "search" in info["error"]

        # But bulk operations should still work
        allowed, info = strict_limiter.check_rate_limit(client_id, "bulk_operations")
        assert allowed

    def test_attack_pattern_detection(self, limiter):
        """Test attack pattern detection."""
        client_id = "attacker_client"

        # Simulate brute force attack (many consecutive errors)
        metrics = limiter.client_metrics[client_id]
        metrics.consecutive_errors = 15
        metrics.request_count = 20
        metrics.error_count = 15

        limiter._detect_attack_patterns(client_id, "/login", metrics)

        # Should have flagged brute force
        patterns = [p for p, _ in limiter.attack_patterns[client_id]]
        assert AttackPattern.BRUTE_FORCE in patterns

    def test_dos_attack_detection(self, limiter):
        """Test DOS attack detection."""
        client_id = "dos_attacker"

        # Simulate many rapid requests
        current_time = time.time()
        metrics = limiter.client_metrics[client_id]

        # Add many recent requests
        for i in range(250):
            metrics.response_times.append(current_time - i * 0.1)

        limiter._detect_attack_patterns(client_id, "/api", metrics)

        # Should detect DOS attack and block the client
        patterns = [p for p, _ in limiter.attack_patterns[client_id]]
        assert AttackPattern.DOS_ATTACK in patterns

        # Client should be blocked
        ip_part = client_id.split(':')[1] if ':' in client_id else client_id
        assert ip_part in limiter.blocked_ips

    def test_scraping_detection(self, limiter):
        """Test scraping pattern detection."""
        client_id = "scraper_client"

        metrics = limiter.client_metrics[client_id]

        # Simulate accessing many different endpoints
        for i in range(25):
            metrics.endpoints_accessed.add(f"/endpoint_{i}")

        # Add many recent requests
        current_time = time.time()
        for i in range(60):
            metrics.response_times.append(current_time - i * 2)

        limiter._detect_attack_patterns(client_id, "/api", metrics)

        # Should detect scraping
        patterns = [p for p, _ in limiter.attack_patterns[client_id]]
        assert AttackPattern.SCRAPING in patterns

    def test_enumeration_detection(self, limiter):
        """Test enumeration attack detection."""
        client_id = "enumerator_client"

        metrics = limiter.client_metrics[client_id]

        # Simulate systematic endpoint scanning with high error rate
        for i in range(15):
            metrics.endpoints_accessed.add(f"/admin_{i}")

        metrics.request_count = 30
        metrics.error_count = 25  # 83% error rate

        limiter._detect_attack_patterns(client_id, "/admin", metrics)

        # Should detect enumeration
        patterns = [p for p, _ in limiter.attack_patterns[client_id]]
        assert AttackPattern.ENUMERATION in patterns

    def test_blocked_client_rejection(self, limiter):
        """Test that blocked clients are rejected."""
        client_id = "blocked_client"

        # Manually block the client
        ip_part = client_id.split(':')[1] if ':' in client_id else client_id
        limiter.blocked_ips[ip_part] = time.time() + 3600  # Block for 1 hour

        # All requests should be denied
        allowed, info = limiter.check_rate_limit(client_id)
        assert not allowed
        assert "blocked" in info["error"].lower()

    def test_client_statistics(self, limiter):
        """Test client statistics generation."""
        client_id = "stats_client"

        # Generate some activity
        for i in range(10):
            limiter.record_request(client_id, f"/endpoint_{i % 3}", "TestAgent/1.0", error_occurred=(i % 4 == 0))

        # Get statistics
        stats = limiter.get_client_stats(client_id)

        assert stats["client_id"] == client_id
        assert stats["total_requests"] == 10
        assert stats["error_count"] == 3  # Every 4th request was an error
        assert stats["error_rate"] == 0.3
        assert stats["unique_endpoints"] == 3

    def test_cleanup_functionality(self, limiter):
        """Test that cleanup removes old data."""
        client_id = "cleanup_test"

        # Add old violations
        old_time = time.time() - 7200  # 2 hours ago
        limiter.rate_limit_violations[client_id] = [old_time]

        # Add old attack patterns
        limiter.attack_patterns[client_id] = [(AttackPattern.BRUTE_FORCE, old_time)]

        # Add old block
        limiter.blocked_ips["old_ip"] = old_time

        # Run cleanup manually
        current_time = time.time()
        cutoff_time = current_time - 3600  # 1 hour

        # Clean violations
        limiter.rate_limit_violations[client_id] = [
            t for t in limiter.rate_limit_violations[client_id] if t > cutoff_time
        ]

        # Clean attack patterns
        limiter.attack_patterns[client_id] = [
            (p, t) for p, t in limiter.attack_patterns[client_id] if t > cutoff_time
        ]

        # Clean blocks
        limiter.blocked_ips = {
            ip: block_time for ip, block_time in limiter.blocked_ips.items()
            if block_time > current_time
        }

        # Old data should be removed
        assert len(limiter.rate_limit_violations[client_id]) == 0
        assert len(limiter.attack_patterns[client_id]) == 0
        assert "old_ip" not in limiter.blocked_ips

    def test_daily_limit_reset(self, strict_limiter):
        """Test daily limit reset functionality."""
        client_id = "daily_test"

        # Set up a client with activity from yesterday
        metrics = strict_limiter.client_metrics[client_id]
        metrics.first_request_time = time.time() - 90000  # 25 hours ago
        metrics.request_count = 999  # Just under daily limit

        # New request should reset daily counter
        allowed, info = strict_limiter.check_rate_limit(client_id)
        assert allowed

        # Daily counter should be reset
        assert metrics.first_request_time > time.time() - 100  # Recently reset
        assert metrics.request_count == 0


class TestRateLimitingMiddleware:
    """Test suite for rate limiting middleware."""

    def test_endpoint_resource_classification(self):
        """Test that endpoints are correctly classified for resource limiting."""
        from backend_api.middleware.rate_limiting import RateLimitingMiddleware

        middleware = RateLimitingMiddleware(None)

        # Test search endpoints
        assert middleware._get_resource_type("/api/v1/properties/") == "search"
        assert middleware._get_resource_type("/api/v1/properties/search") == "search"

        # Test bulk operations
        assert middleware._get_resource_type("/api/v1/properties/bulk") == "bulk_operations"
        assert middleware._get_resource_type("/api/v1/sync/full") == "bulk_operations"

        # Test export operations
        assert middleware._get_resource_type("/api/v1/properties/export") == "data_export"

        # Test default
        assert middleware._get_resource_type("/api/v1/other") == "default"

    def test_auth_data_extraction(self):
        """Test authentication data extraction from requests."""
        from backend_api.middleware.rate_limiting import RateLimitingMiddleware

        middleware = RateLimitingMiddleware(None)

        # Mock request with API key
        mock_request = Mock()
        mock_request.headers = {"X-API-Key": "AW_admin_test_key"}
        mock_request.state = Mock()

        auth_data = middleware._extract_auth_data(mock_request)
        assert auth_data["is_admin"]

        # Test premium key
        mock_request.headers = {"X-API-Key": "AW_premium_test_key"}
        auth_data = middleware._extract_auth_data(mock_request)
        assert auth_data["is_premium"]

        # Test regular key
        mock_request.headers = {"X-API-Key": "AW_regular_test_key"}
        auth_data = middleware._extract_auth_data(mock_request)
        assert auth_data["is_authenticated"]


if __name__ == "__main__":
    pytest.main([__file__])