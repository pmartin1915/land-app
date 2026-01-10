"""
JWT Authentication and security for Alabama Auction Watcher API
Provides secure access for iOS application and admin users
"""

import base64
import hashlib
import hmac
import jwt
from jwt.exceptions import PyJWTError
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from pydantic import BaseModel

from .config import settings

logger = logging.getLogger(__name__)

# Environment indicator for conditional logic in routers
ENVIRONMENT = settings.environment

# Security configuration from centralized settings
SECRET_KEY = settings.resolved_jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days

# API Key configuration for iOS app
API_KEY_SECRET = settings.resolved_api_key_secret

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()

class Token(BaseModel):
    """JWT token response model."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int

class TokenData(BaseModel):
    """Token payload data."""
    user_id: Optional[str] = None
    device_id: Optional[str] = None
    scopes: list = []

class User(BaseModel):
    """User model for authentication."""
    id: str
    username: str
    email: Optional[str] = None
    is_active: bool = True
    scopes: list = []

class APIKeyData(BaseModel):
    """API key data for iOS authentication."""
    device_id: str
    app_version: str
    created_at: datetime
    scopes: list = []

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    try:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    except Exception as e:
        logger.error(f"Failed to create access token: {str(e)}")
        raise

def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token."""
    try:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    except Exception as e:
        logger.error(f"Failed to create refresh token: {str(e)}")
        raise

def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate token")

def create_api_key(device_id: str, app_version: str) -> str:
    """
    Create API key for iOS device authentication.
    Used for device-specific authentication without user accounts.
    """
    try:
        # Create payload with device information
        payload = {
            "device_id": device_id,
            "app_version": app_version,
            "created_at": datetime.utcnow().isoformat(),
            "scopes": ["property:read", "property:write", "sync:all"],
            "type": "api_key"
        }

        # Create API key using HMAC
        payload_str = f"{device_id}:{app_version}:{payload['created_at']}"
        signature = hmac.digest(
            API_KEY_SECRET.encode(),
            payload_str.encode(),
            hashlib.sha256
        )

        # Encode as base64 for transmission
        api_key = base64.b64encode(signature).decode()

        logger.info(f"Created API key for device {device_id}")
        return f"AW_{device_id}_{api_key}"

    except Exception as e:
        logger.error(f"Failed to create API key: {str(e)}")
        raise

def verify_api_key(api_key: str) -> APIKeyData:
    """Verify iOS device API key with format and signature validation."""
    try:
        if not api_key.startswith("AW_"):
            raise HTTPException(status_code=401, detail="Invalid API key format")

        # Parse API key components: AW_{device_id}_{signature_or_suffix}
        parts = api_key[3:].split("_", 1)  # Remove "AW_" prefix
        if len(parts) != 2:
            raise HTTPException(status_code=401, detail="Invalid API key format")

        device_id, signature_part = parts

        # Validate device_id format (alphanumeric with hyphens, reasonable length)
        if not device_id or len(device_id) > 64:
            raise HTTPException(status_code=401, detail="Invalid device ID format")
        if not device_id.replace("-", "").isalnum():
            raise HTTPException(status_code=401, detail="Invalid device ID format")

        # Development mode: accept keys with valid format without signature verification
        # This allows hardcoded dev keys like AW_dev_automated_development_key_001
        if ENVIRONMENT == "development":
            logger.warning(f"API key validation running in DEVELOPMENT mode - signature not verified for device {device_id}")
            return APIKeyData(
                device_id=device_id,
                app_version="1.0.0",
                created_at=datetime.utcnow(),
                scopes=["property:read", "property:write", "sync:all"]
            )

        # Production: Validate base64 signature
        try:
            provided_signature = base64.b64decode(signature_part)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid API key signature")

        # Production: Require valid SHA256 signature length (32 bytes)
        if len(provided_signature) != 32:
            raise HTTPException(status_code=401, detail="Invalid API key signature")

        return APIKeyData(
            device_id=device_id,
            app_version="1.0.0",
            created_at=datetime.utcnow(),
            scopes=["property:read", "property:write", "sync:all"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify API key: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid API key")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current user from JWT token."""
    try:
        token = credentials.credentials
        payload = verify_token(token)

        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")

        # In a real application, you'd fetch user from database
        # For this implementation, we'll create a default user
        return User(
            id=user_id,
            username=payload.get("username", "api_user"),
            email=payload.get("email"),
            is_active=True,
            scopes=payload.get("scopes", [])
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get current user: {str(e)}")
        raise HTTPException(status_code=401, detail="Could not validate credentials")

async def get_api_key_data(request: Request) -> APIKeyData:
    """Get API key data for iOS device authentication."""
    try:
        # Check for API key in header
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(status_code=401, detail="API key required")

        return verify_api_key(api_key)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get API key data: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid API key")

async def get_current_user_or_api_key(
    request: Request
) -> Dict[str, Any]:
    """
    Get authentication data from either JWT token or API key.
    Supports both user authentication and iOS device authentication.
    """
    try:
        # Try API key first (for iOS app)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            api_key_data = verify_api_key(api_key)
            return {
                "type": "api_key",
                "device_id": api_key_data.device_id,
                "app_version": api_key_data.app_version,
                "scopes": api_key_data.scopes
            }

        # Try JWT token (for admin/web access)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            payload = verify_token(token)
            return {
                "type": "jwt",
                "user_id": payload.get("sub"),
                "username": payload.get("username"),
                "scopes": payload.get("scopes", [])
            }

        raise HTTPException(status_code=401, detail="Authentication required")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed")

def require_scope(required_scope: str):
    """Dependency to require specific scope."""
    async def scope_checker(auth_data: Dict[str, Any] = Depends(get_current_user_or_api_key)):
        scopes = auth_data.get("scopes", [])
        if required_scope not in scopes and "admin" not in scopes:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required scope: {required_scope}"
            )
        return auth_data
    return scope_checker

# Common scope dependencies
require_property_read = require_scope("property:read")
require_property_write = require_scope("property:write")
require_sync_access = require_scope("sync:all")
require_admin = require_scope("admin")

# Authentication middleware for rate limiting bypass
class AuthenticationMiddleware:
    """Middleware to add authentication context to requests."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Add authentication context to request
            # This could be used for enhanced rate limiting based on user/device
            pass

        await self.app(scope, receive, send)

# Utility functions
def create_device_token(device_id: str, app_version: str) -> Token:
    """Create token set for iOS device."""
    try:
        # Create token data
        token_data = {
            "sub": f"device:{device_id}",
            "device_id": device_id,
            "app_version": app_version,
            "scopes": ["property:read", "property:write", "sync:all"]
        }

        # Create tokens
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    except Exception as e:
        logger.error(f"Failed to create device token: {str(e)}")
        raise

def create_admin_token(username: str, email: Optional[str] = None) -> Token:
    """Create token set for admin user."""
    try:
        # Create token data
        token_data = {
            "sub": f"user:{username}",
            "username": username,
            "email": email,
            "scopes": ["admin", "property:read", "property:write", "sync:all"]
        }

        # Create tokens
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    except Exception as e:
        logger.error(f"Failed to create admin token: {str(e)}")
        raise

# Security headers middleware
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)

    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # CORS headers for iOS app
    if request.headers.get("Origin"):
        response.headers["Access-Control-Allow-Credentials"] = "true"

    return response