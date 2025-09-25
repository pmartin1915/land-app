"""
Secure configuration management for Alabama Auction Watcher

This module provides secure handling of API keys, secrets, and other sensitive configuration
using environment variables with secure fallbacks for development.
"""

import os
import secrets
from typing import Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SecurityConfig:
    """Security configuration with environment variable support."""

    # API Configuration
    api_key: str
    api_base_url: str
    api_timeout: int = 30

    # Security Settings
    rate_limit_per_minute: int = 60
    max_request_size_mb: int = 10
    enable_cors: bool = True

    # Session Security
    session_timeout_minutes: int = 60
    secure_cookies: bool = True


def get_api_key() -> str:
    """
    Get API key from environment variables with secure fallback.

    Returns:
        str: API key for backend authentication

    Raises:
        ValueError: If no API key is configured
    """
    # Try environment variable first
    api_key = os.getenv("AUCTION_WATCHER_API_KEY")

    if api_key:
        return api_key

    # For development, try local config file
    local_config_path = Path(__file__).parent / ".env.local"
    if local_config_path.exists():
        try:
            with open(local_config_path, 'r') as f:
                for line in f:
                    if line.startswith("AUCTION_WATCHER_API_KEY="):
                        return line.split("=", 1)[1].strip()
        except Exception:
            pass

    # Generate a temporary development key if nothing is configured
    dev_key = os.getenv("DEV_API_KEY")
    if not dev_key:
        # Generate a secure temporary key for development
        dev_key = f"AW_dev_{secrets.token_urlsafe(32)}"
        print(f"⚠️  WARNING: Using temporary development API key: {dev_key}")
        print("   Set AUCTION_WATCHER_API_KEY environment variable for production")

    return dev_key


def get_api_base_url() -> str:
    """
    Get API base URL from environment with secure default.

    Returns:
        str: Base URL for API endpoints
    """
    return os.getenv("AUCTION_WATCHER_API_URL", "http://localhost:8001/api/v1")


def get_security_config() -> SecurityConfig:
    """
    Get complete security configuration.

    Returns:
        SecurityConfig: Secure configuration object
    """
    return SecurityConfig(
        api_key=get_api_key(),
        api_base_url=get_api_base_url(),
        api_timeout=int(os.getenv("API_TIMEOUT", "30")),
        rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
        max_request_size_mb=int(os.getenv("MAX_REQUEST_SIZE_MB", "10")),
        enable_cors=os.getenv("ENABLE_CORS", "true").lower() == "true",
        session_timeout_minutes=int(os.getenv("SESSION_TIMEOUT_MINUTES", "60")),
        secure_cookies=os.getenv("SECURE_COOKIES", "true").lower() == "true"
    )


def validate_api_key(api_key: str) -> bool:
    """
    Validate API key format.

    Args:
        api_key: API key to validate

    Returns:
        bool: True if key format is valid
    """
    if not api_key or not isinstance(api_key, str):
        return False

    # Must start with AW_ prefix
    if not api_key.startswith("AW_"):
        return False

    # Must have minimum length
    if len(api_key) < 20:
        return False

    return True


def create_secure_headers(api_key: Optional[str] = None) -> dict:
    """
    Create secure HTTP headers for API requests.

    Args:
        api_key: Optional API key override

    Returns:
        dict: HTTP headers for secure API communication
    """
    if not api_key:
        api_key = get_api_key()

    return {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
        "User-Agent": "Alabama-Auction-Watcher/1.0",
        "Accept": "application/json"
    }


# Global security configuration instance
_security_config: Optional[SecurityConfig] = None


def get_global_security_config() -> SecurityConfig:
    """
    Get global security configuration instance (singleton pattern).

    Returns:
        SecurityConfig: Global security configuration
    """
    global _security_config
    if _security_config is None:
        _security_config = get_security_config()
    return _security_config


def reload_security_config() -> None:
    """Force reload of security configuration from environment."""
    global _security_config
    _security_config = None