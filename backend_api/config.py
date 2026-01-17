"""
Centralized configuration for Alabama Auction Watcher API.
All environment-based settings consolidated in one place.
Uses pydantic-settings for type-safe configuration with validation.
"""

import os
import secrets
from pathlib import Path
from typing import List, Optional
from functools import lru_cache

from fastapi import Request
from pydantic import field_validator
from pydantic_settings import BaseSettings
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_project_root() -> Path:
    """Get project root directory (parent of backend_api)."""
    return Path(__file__).parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    environment: str = "development"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    # Server
    host: str = "0.0.0.0"
    port: int = 8001

    @property
    def server_url(self) -> str:
        """Full server URL for internal use."""
        return f"http://{self.host}:{self.port}"

    # Database
    database_url: Optional[str] = None

    @property
    def resolved_database_url(self) -> str:
        """Database URL with resolved paths."""
        if self.database_url:
            return self.database_url
        # Default: SQLite in project_root/data/
        db_path = get_project_root() / "data" / "alabama_auction_watcher.db"
        return f"sqlite:///{db_path}"

    # CORS
    cors_origins: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if self.cors_origins:
            return [origin.strip() for origin in self.cors_origins.split(",")]
        # Development defaults
        return [
            "http://localhost:3000",      # React dev
            "http://localhost:5173",      # Vite dev
            "http://localhost:5174",      # Vite dev (alternate port)
            "http://localhost:8501",      # Streamlit
            "tauri://localhost",          # Tauri desktop
            "https://tauri.localhost",    # Tauri HTTPS
            "capacitor://localhost",      # iOS Capacitor
            "ionic://localhost",          # Ionic
        ]

    # JWT Authentication
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    @property
    def resolved_jwt_secret_key(self) -> str:
        """Get JWT secret, generating one if not set (dev only)."""
        if self.jwt_secret_key:
            return self.jwt_secret_key
        if self.is_development:
            return secrets.token_urlsafe(32)
        raise ValueError("JWT_SECRET_KEY must be set in production")

    # API Key (for iOS device auth)
    api_key_secret: str = ""

    @property
    def resolved_api_key_secret(self) -> str:
        """Get API key secret, generating one if not set (dev only)."""
        if self.api_key_secret:
            return self.api_key_secret
        if self.is_development:
            return secrets.token_urlsafe(32)
        raise ValueError("API_KEY_SECRET must be set in production")

    # Admin credentials (for initial setup)
    admin_password_hash: Optional[str] = None

    # Logging
    log_level: str = "INFO"
    sql_echo: bool = True  # SQL query logging

    @property
    def resolved_sql_echo(self) -> bool:
        """Disable SQL echo in production."""
        if self.is_production:
            return False
        return self.sql_echo

    # Algorithm validation (for iOS compatibility)
    expected_investment_score: float = 52.8
    expected_water_score: float = 3.0
    score_tolerance: float = 0.1
    compatible_algorithm_versions: str = "1.0.0,1.0.1,1.1.0"

    @property
    def algorithm_versions_list(self) -> List[str]:
        """Parse algorithm versions from comma-separated string."""
        return [v.strip() for v in self.compatible_algorithm_versions.split(",")]

    # Rate limiting
    rate_limit_enabled: bool = True

    @property
    def resolved_rate_limit_enabled(self) -> bool:
        """Disable rate limiting in development."""
        if self.is_development:
            return False
        return self.rate_limit_enabled

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience exports
settings = get_settings()


def _get_rate_limit_key(request: Request) -> str:
    """Return key for rate limiting, or empty string to bypass in development."""
    if settings.is_development:
        return ""  # Empty key bypasses rate limiting
    return get_remote_address(request)


# Shared rate limiter for all routers
# Uses development-aware key function that bypasses limits in dev mode
limiter = Limiter(
    key_func=_get_rate_limit_key,
    enabled=settings.resolved_rate_limit_enabled
)
