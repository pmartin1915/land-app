"""
Authentication utility functions for API testing.

This module provides helper functions to generate JWT tokens, API keys,
and authentication headers required for testing secured API endpoints.
It mirrors the logic in `backend_api.auth` to ensure test authenticity.
"""
import base64
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

import jwt

# Import production auth settings to ensure consistency
from backend_api.auth import ALGORITHM, API_KEY_SECRET, SECRET_KEY


def generate_test_jwt_token(
    device_id: str,
    scopes: Optional[List[str]] = None,
    expires_delta: Optional[timedelta] = None,
    **extra_payload: Any,
) -> str:
    """
    Generate a JWT token for testing purposes.

    Args:
        device_id: The device ID to include in the token payload.
        scopes: A list of authorization scopes.
        expires_delta: The lifespan of the token. Defaults to 30 minutes.
        extra_payload: Any additional data to include in the token payload.

    Returns:
        A signed JWT token string.
    """
    if scopes is None:
        scopes = ["property:read", "property:write", "sync:all"]
    if expires_delta is None:
        expires_delta = timedelta(minutes=30)

    expire = datetime.utcnow() + expires_delta
    to_encode = {
        "sub": f"device:{device_id}",
        "device_id": device_id,
        "scopes": scopes,
        "exp": expire,
        "type": "access",
    }
    to_encode.update(extra_payload)
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def generate_admin_jwt_token(
    username: str = "test_admin",
    scopes: Optional[List[str]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Generate a JWT token for an admin user.

    Args:
        username: The admin username.
        scopes: A list of scopes. Defaults to admin scopes.
        expires_delta: The lifespan of the token.

    Returns:
        A signed JWT token string for an admin user.
    """
    if scopes is None:
        scopes = ["admin", "property:read", "property:write", "sync:all"]

    return generate_test_jwt_token(
        device_id="admin-device",
        scopes=scopes,
        expires_delta=expires_delta,
        sub=f"user:{username}",
        username=username,
    )


def generate_test_api_key(device_id: str, app_version: str = "1.0.0-test") -> str:
    """
    Generate a test API key for a device.

    This function replicates the API key generation logic from `backend_api.auth`.

    Args:
        device_id: The device ID for which to generate the key.
        app_version: The application version string.

    Returns:
        A formatted API key string.
    """
    created_at = datetime.utcnow().isoformat()
    payload_str = f"{device_id}:{app_version}:{created_at}"
    signature = hmac.digest(
        API_KEY_SECRET.encode(), payload_str.encode(), hashlib.sha256
    )
    api_key_signature = base64.b64encode(signature).decode()
    return f"AW_{device_id}_{api_key_signature}"


def create_auth_headers(token: str, auth_type: str = "bearer") -> Dict[str, str]:
    """
    Create an authentication headers dictionary.

    Args:
        token: The token or API key.
        auth_type: The type of authentication ('bearer' or 'api_key').

    Returns:
        A dictionary containing the appropriate authentication header.
    """
    if auth_type.lower() == "bearer":
        return {"Authorization": f"Bearer {token}"}
    if auth_type.lower() == "api_key":
        return {"X-API-Key": token}
    raise ValueError(f"Unsupported authentication type: {auth_type}")


def decode_and_validate_token(token: str) -> Dict[str, Any]:
    """
    Decode a JWT token and validate its structure.

    Args:
        token: The JWT token string.

    Returns:
        The decoded token payload.

    Raises:
        jwt.PyJWTError: If the token is invalid or expired.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def assert_token_valid(token: str, expected_scopes: List[str]):
    """
    Assert that a JWT token is valid and contains the expected scopes.

    Args:
        token: The JWT token string.
        expected_scopes: A list of scopes expected to be in the token.
    """
    payload = decode_and_validate_token(token)
    assert "exp" in payload
    assert payload["exp"] > time.time()
    assert "scopes" in payload
    assert all(scope in payload["scopes"] for scope in expected_scopes)


def assert_token_expired(token: str):
    """

    Assert that a JWT token is expired.

    Args:
        token: The expired JWT token string.
    """
    try:
        decode_and_validate_token(token)
        raise AssertionError("Token did not raise ExpiredSignatureError as expected.")
    except jwt.ExpiredSignatureError:
        pass  # Expected behavior
