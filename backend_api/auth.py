"""
JWT Authentication and security for Auction Watcher API.
Provides secure access for web application and admin users.
"""

import jwt
from jwt.exceptions import PyJWTError
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from pydantic import BaseModel

from .config import settings

logger = logging.getLogger(__name__)

# Security configuration from centralized settings
SECRET_KEY = settings.resolved_jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days

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
    scopes: list = []

class User(BaseModel):
    """User model for authentication."""
    id: str
    username: str
    email: Optional[str] = None
    is_active: bool = True
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
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

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
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
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

async def get_current_user_or_api_key(
    request: Request
) -> Dict[str, Any]:
    """
    Get authentication data from JWT token in the Authorization header.
    Returns a dict with user_id, username, and scopes for use in route handlers.
    """
    try:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
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

    if request.headers.get("Origin"):
        response.headers["Access-Control-Allow-Credentials"] = "true"

    return response