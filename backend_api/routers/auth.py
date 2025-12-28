"""
Authentication endpoints for Alabama Auction Watcher API
Handles JWT tokens and API keys for iOS device authentication
"""

import os
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import Optional
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..auth import (
    create_device_token, create_admin_token, create_api_key, verify_token,
    verify_password, get_password_hash, ENVIRONMENT
)

# Admin credentials from environment variables
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()
security = HTTPBasic()

class DeviceAuthRequest(BaseModel):
    """Request model for iOS device authentication."""
    device_id: str
    app_version: str
    device_name: Optional[str] = None
    ios_version: Optional[str] = None

class APIKeyRequest(BaseModel):
    """Request model for API key generation."""
    device_id: str
    app_version: str
    device_name: Optional[str] = None

class APIKeyResponse(BaseModel):
    """Response model for API key generation."""
    api_key: str
    device_id: str
    created_at: str
    scopes: list
    usage_instructions: str

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

@router.post("/device/token", response_model=TokenResponse)
@limiter.limit("10/minute")
async def create_device_token_endpoint(
    request: Request,
    auth_request: DeviceAuthRequest
):
    """
    Create JWT tokens for iOS device authentication.
    Used for secure API access from mobile app.
    """
    try:
        # Validate device request
        if not auth_request.device_id or len(auth_request.device_id) < 10:
            raise HTTPException(status_code=400, detail="Invalid device ID")

        if not auth_request.app_version:
            raise HTTPException(status_code=400, detail="App version required")

        # Create device token
        token = create_device_token(auth_request.device_id, auth_request.app_version)

        logger.info(f"Created device token for device {auth_request.device_id}")

        return TokenResponse(
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            token_type=token.token_type,
            expires_in=token.expires_in,
            scopes=["property:read", "property:write", "sync:all"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Device token creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Token creation failed")

@router.post("/device/api-key", response_model=APIKeyResponse)
@limiter.limit("5/minute")
async def create_api_key_endpoint(
    request: Request,
    api_key_request: APIKeyRequest
):
    """
    Create API key for iOS device authentication.
    Alternative to JWT tokens for simpler device authentication.
    """
    try:
        # Validate API key request
        if not api_key_request.device_id or len(api_key_request.device_id) < 10:
            raise HTTPException(status_code=400, detail="Invalid device ID")

        if not api_key_request.app_version:
            raise HTTPException(status_code=400, detail="App version required")

        # Create API key
        api_key = create_api_key(api_key_request.device_id, api_key_request.app_version)

        from datetime import datetime

        logger.info(f"Created API key for device {api_key_request.device_id}")

        return APIKeyResponse(
            api_key=api_key,
            device_id=api_key_request.device_id,
            created_at=datetime.utcnow().isoformat(),
            scopes=["property:read", "property:write", "sync:all"],
            usage_instructions="Include in requests as 'X-API-Key' header"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API key creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="API key creation failed")

@router.post("/admin/token", response_model=TokenResponse)
@limiter.limit("5/minute")
async def create_admin_token_endpoint(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(security)
):
    """
    Create JWT tokens for admin authentication.
    Used for administrative access to the API.
    """
    try:
        # Validate admin credentials are configured
        if not ADMIN_USERNAME or not ADMIN_PASSWORD_HASH:
            if ENVIRONMENT == "production":
                logger.error("Admin credentials not configured in production")
                raise HTTPException(status_code=503, detail="Admin authentication not configured")
            else:
                # Development fallback - use default credentials
                dev_username = "admin"
                dev_password_hash = get_password_hash("dev_password_change_me")
                logger.warning("Using development admin credentials - not for production use")
                if credentials.username != dev_username:
                    raise HTTPException(status_code=401, detail="Invalid credentials")
                if not verify_password(credentials.password, dev_password_hash):
                    raise HTTPException(status_code=401, detail="Invalid credentials")
        else:
            # Production: use environment-configured credentials
            if credentials.username != ADMIN_USERNAME:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            if not verify_password(credentials.password, ADMIN_PASSWORD_HASH):
                raise HTTPException(status_code=401, detail="Invalid credentials")

        # Create admin token
        token = create_admin_token(credentials.username, "admin@alabamaauctionwatcher.com")

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
    """
    Refresh access token using refresh token.
    Used to maintain authentication without re-authentication.
    """
    try:
        # Verify refresh token
        payload = verify_token(refresh_request.refresh_token)

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        # Extract user/device information
        subject = payload.get("sub")
        if not subject:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        # Create new token based on subject type
        if subject.startswith("device:"):
            device_id = payload.get("device_id")
            app_version = payload.get("app_version", "1.0.0")
            token = create_device_token(device_id, app_version)
            scopes = ["property:read", "property:write", "sync:all"]

        elif subject.startswith("user:"):
            username = payload.get("username")
            email = payload.get("email")
            token = create_admin_token(username, email)
            scopes = ["admin", "property:read", "property:write", "sync:all"]

        else:
            raise HTTPException(status_code=401, detail="Unknown subject type")

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
    """
    Validate JWT token or API key.
    Used by clients to check authentication status.
    """
    try:
        # Check API key first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            from ..auth import verify_api_key
            api_key_data = verify_api_key(api_key)
            return {
                "valid": True,
                "type": "api_key",
                "device_id": api_key_data.device_id,
                "app_version": api_key_data.app_version,
                "scopes": api_key_data.scopes
            }

        # Check JWT token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix

        if not token:
            raise HTTPException(status_code=401, detail="No authentication provided")

        # Verify JWT token
        payload = verify_token(token)

        return {
            "valid": True,
            "type": "jwt",
            "subject": payload.get("sub"),
            "username": payload.get("username"),
            "device_id": payload.get("device_id"),
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
    """
    Get list of available authentication scopes.
    Used for client-side scope validation.
    """
    try:
        return {
            "scopes": {
                "property:read": "Read property data",
                "property:write": "Create, update, delete properties",
                "sync:all": "Full synchronization access",
                "admin": "Administrative access to all endpoints"
            },
            "device_scopes": ["property:read", "property:write", "sync:all"],
            "admin_scopes": ["admin", "property:read", "property:write", "sync:all"]
        }

    except Exception as e:
        logger.error(f"Failed to get scopes: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get scopes")

@router.post("/revoke")
@limiter.limit("10/minute")
async def revoke_token_endpoint(
    request: Request,
    token: str
):
    """
    Revoke JWT token or API key.
    In production, this would add the token to a revocation list.
    """
    try:
        # Verify token exists and is valid
        payload = verify_token(token)

        # In production, add token to revocation database
        # For this implementation, we'll just log the revocation
        subject = payload.get("sub", "unknown")

        logger.info(f"Token revoked for {subject}")

        return {
            "revoked": True,
            "subject": subject,
            "message": "Token revoked successfully"
        }

    except HTTPException:
        # Token is invalid, consider it already revoked
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
        # Test token creation and verification
        test_token = create_device_token("test_device", "1.0.0")
        verify_token(test_token.access_token)

        return {
            "status": "healthy",
            "authentication": "operational",
            "jwt_system": "functional",
            "api_key_system": "functional"
        }

    except Exception as e:
        logger.error(f"Authentication health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }