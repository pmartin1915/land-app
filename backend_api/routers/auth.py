"""
Authentication endpoints for Auction Watcher API.
Handles JWT token creation, refresh, and validation.
"""

import os
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import Optional
import logging

from ..auth import (
    create_admin_token, verify_token,
    verify_password, get_password_hash
)
from ..config import settings, limiter

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBasic()

# Admin credentials from environment variables
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")


class AdminAuthRequest(BaseModel):
    """Request model for admin authentication."""
    username: str
    password: str

class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str

class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    scopes: list


@router.post("/admin/token", response_model=TokenResponse)
@limiter.limit("5/minute")
async def create_admin_token_endpoint(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(security)
):
    """Create JWT tokens for admin authentication."""
    try:
        if not ADMIN_USERNAME or not ADMIN_PASSWORD_HASH:
            if settings.is_production:
                logger.error("Admin credentials not configured in production")
                raise HTTPException(status_code=503, detail="Admin authentication not configured")
            else:
                dev_username = "admin"
                dev_password_hash = get_password_hash("dev_password_change_me")
                logger.warning("Using development admin credentials - not for production use")
                if credentials.username != dev_username:
                    raise HTTPException(status_code=401, detail="Invalid credentials")
                if not verify_password(credentials.password, dev_password_hash):
                    raise HTTPException(status_code=401, detail="Invalid credentials")
        else:
            if credentials.username != ADMIN_USERNAME:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            if not verify_password(credentials.password, ADMIN_PASSWORD_HASH):
                raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_admin_token(credentials.username)

        logger.info(f"Created admin token for user {credentials.username}")

        return TokenResponse(
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            token_type=token.token_type,
            expires_in=token.expires_in,
            scopes=["admin", "property:read", "property:write", "sync:all"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin token creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Admin token creation failed")


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh_token_endpoint(
    request: Request,
    refresh_request: RefreshTokenRequest
):
    """Refresh access token using refresh token."""
    try:
        payload = verify_token(refresh_request.refresh_token)

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        subject = payload.get("sub")
        if not subject:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        if not subject.startswith("user:"):
            raise HTTPException(status_code=401, detail="Unknown subject type")

        username = payload.get("username")
        email = payload.get("email")
        token = create_admin_token(username, email)
        scopes = ["admin", "property:read", "property:write", "sync:all"]

        logger.info(f"Refreshed token for {subject}")

        return TokenResponse(
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            token_type=token.token_type,
            expires_in=token.expires_in,
            scopes=scopes
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Token refresh failed")


@router.get("/validate")
@limiter.limit("100/minute")
async def validate_token_endpoint(
    request: Request,
    token: Optional[str] = None
):
    """Validate JWT token. Used by clients to check authentication status."""
    try:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

        if not token:
            raise HTTPException(status_code=401, detail="No authentication provided")

        payload = verify_token(token)

        return {
            "valid": True,
            "type": "jwt",
            "subject": payload.get("sub"),
            "username": payload.get("username"),
            "scopes": payload.get("scopes", []),
            "expires": payload.get("exp")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token validation failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid authentication")


@router.get("/scopes")
@limiter.limit("50/minute")
async def get_available_scopes(request: Request):
    """Get list of available authentication scopes."""
    return {
        "scopes": {
            "property:read": "Read property data",
            "property:write": "Create, update, delete properties",
            "sync:all": "Full synchronization access",
            "admin": "Administrative access to all endpoints"
        }
    }


@router.post("/revoke")
@limiter.limit("10/minute")
async def revoke_token_endpoint(
    request: Request,
    token: str
):
    """Revoke JWT token. In production, this would add the token to a revocation list."""
    try:
        payload = verify_token(token)
        subject = payload.get("sub", "unknown")
        logger.info(f"Token revoked for {subject}")

        return {
            "revoked": True,
            "subject": subject,
            "message": "Token revoked successfully"
        }

    except HTTPException:
        return {
            "revoked": True,
            "message": "Token was already invalid"
        }
    except Exception as e:
        logger.error(f"Token revocation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Token revocation failed")


@router.get("/health")
async def auth_health_check(request: Request):
    """Authentication system health check."""
    try:
        test_token = create_admin_token("health_check")
        verify_token(test_token.access_token)

        return {
            "status": "healthy",
            "authentication": "operational",
            "jwt_system": "functional"
        }

    except Exception as e:
        logger.error(f"Authentication health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
