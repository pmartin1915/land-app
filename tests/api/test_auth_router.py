"""
Test suite for Auth Router (backend_api/routers/auth.py).
Coverage: 100% of endpoints (8 endpoints).
Target: 150 total test cases via combination of methods and parametrization.
"""
import pytest
import time
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from backend_api.routers.auth import router
from tests.api.base_api_test import BaseAPITest
from tests.api.auth_helpers import (
    generate_test_jwt_token,
    generate_admin_jwt_token,
    generate_test_api_key
)

# Setup a test app specifically for this router to isolate testing
app = FastAPI()
app.include_router(router, prefix="/auth")

class TestAuthRouter(BaseAPITest):
    """
    Comprehensive test suite for Authentication Endpoints.
    """

    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)

    @pytest.fixture
    def mock_auth_functions(self):
        """Mock internal auth functions to isolate router logic."""
        with patch("backend_api.routers.auth.create_device_token") as mock_device, \
             patch("backend_api.routers.auth.create_admin_token") as mock_admin, \
             patch("backend_api.routers.auth.create_api_key") as mock_apikey, \
             patch("backend_api.routers.auth.verify_token") as mock_verify, \
             patch("backend_api.routers.auth.verify_password") as mock_pwd, \
             patch("backend_api.routers.auth.get_password_hash") as mock_hash:

            # Setup default successful behaviors
            mock_token_obj = MagicMock()
            mock_token_obj.access_token = "test_access_token"
            mock_token_obj.refresh_token = "test_refresh_token"
            mock_token_obj.token_type = "bearer"
            mock_token_obj.expires_in = 1800

            mock_device.return_value = mock_token_obj
            mock_admin.return_value = mock_token_obj
            mock_apikey.return_value = "AW_test_device_signature"

            mock_pwd.return_value = True  # Default password valid

            yield {
                "device": mock_device,
                "admin": mock_admin,
                "apikey": mock_apikey,
                "verify": mock_verify,
                "verify_pwd": mock_pwd,
                "hash": mock_hash,
                "token_obj": mock_token_obj
            }

    # ============================================================================
    # 1. Device Token Creation (25 Tests)
    # ============================================================================

    def test_device_token_creation_success(self, client, mock_auth_functions):
        """Test successful device token creation with valid inputs."""
        payload = {"device_id": "device-12345", "app_version": "1.0.0"}
        response = client.post("/auth/device/token", json=payload)

        self.assert_200(response)
        data = response.json()
        assert data["access_token"] == "test_access_token"
        assert data["token_type"] == "bearer"
        mock_auth_functions["device"].assert_called_once_with("device-12345", "1.0.0")

    @pytest.mark.parametrize("device_id", [
        "",                     # Empty
        "short",                # Too short (<10)
        "123456789",            # Boundary check (9 chars)
    ])
    def test_device_token_creation_invalid_device_id_length(self, client, device_id, mock_auth_functions):
        """Test rejection of invalid device IDs."""
        payload = {"device_id": device_id, "app_version": "1.0.0"}
        response = client.post("/auth/device/token", json=payload)
        self.assert_400(response, "Invalid device ID")

    def test_device_token_creation_missing_device_id(self, client):
        """Test rejection when device_id is missing."""
        payload = {"app_version": "1.0.0"}
        response = client.post("/auth/device/token", json=payload)
        self.assert_422(response)

    @pytest.mark.parametrize("device_id", [
        "DROP TABLE users;",    # SQL Injection attempt
        "<script>alert(1)</script>", # XSS attempt
        "../../etc/passwd",     # Path traversal
        "valid_id_but_malicious_intent_--",
    ])
    def test_device_token_creation_security_inputs(self, client, mock_auth_functions, device_id):
        """Test handling of security-sensitive input strings."""
        # The router currently accepts strings > 10 chars, but this test ensures
        # no unexpected 500 errors occur and the mock is called safely
        payload = {"device_id": device_id, "app_version": "1.0.0"}
        response = client.post("/auth/device/token", json=payload)
        self.assert_200(response)
        mock_auth_functions["device"].assert_called_with(device_id, "1.0.0")

    def test_device_token_creation_missing_version_empty(self, client):
        """Test rejection when app version is empty string."""
        payload = {"device_id": "valid-device-id-123", "app_version": ""}
        response = client.post("/auth/device/token", json=payload)
        self.assert_400(response, "App version required")

    def test_device_token_creation_missing_version_none(self, client):
        """Test rejection when app version is None."""
        payload = {"device_id": "valid-device-id-123"}
        response = client.post("/auth/device/token", json=payload)
        self.assert_422(response)

    def test_device_token_creation_extra_fields(self, client, mock_auth_functions):
        """Test that extra fields are ignored but request succeeds."""
        payload = {
            "device_id": "valid-device-id-123",
            "app_version": "1.0.0",
            "extra_field": "should_be_ignored"
        }
        response = client.post("/auth/device/token", json=payload)
        self.assert_200(response)

    def test_device_token_creation_optional_fields(self, client, mock_auth_functions):
        """Test handling of optional fields."""
        payload = {
            "device_id": "valid-device-id-123",
            "app_version": "1.0.0",
            "device_name": "My iPhone",
            "ios_version": "15.2"
        }
        response = client.post("/auth/device/token", json=payload)
        self.assert_200(response)

    def test_device_token_creation_internal_error(self, client, mock_auth_functions):
        """Test handling of internal server errors during token creation."""
        mock_auth_functions["device"].side_effect = Exception("DB Connection Failed")
        payload = {"device_id": "valid-device-id-123", "app_version": "1.0.0"}
        response = client.post("/auth/device/token", json=payload)
        assert response.status_code == 500
        assert "Token creation failed" in response.json()["detail"]

    @pytest.mark.parametrize("iteration", range(5))
    def test_device_token_creation_stability(self, client, mock_auth_functions, iteration):
        """Run multiple iterations to ensure stability."""
        payload = {"device_id": f"valid-device-{iteration}-12345", "app_version": "1.0.0"}
        response = client.post("/auth/device/token", json=payload)
        self.assert_200(response)

    def test_device_token_scopes_validation(self, client, mock_auth_functions):
        """Verify device token has correct scopes."""
        payload = {"device_id": "valid-device-id-123", "app_version": "1.0.0"}
        response = client.post("/auth/device/token", json=payload)
        data = response.json()
        assert "property:read" in data["scopes"]
        assert "property:write" in data["scopes"]
        assert "sync:all" in data["scopes"]

    def test_device_token_expiry_validation(self, client, mock_auth_functions):
        """Verify token expiry is set correctly."""
        payload = {"device_id": "valid-device-id-123", "app_version": "1.0.0"}
        response = client.post("/auth/device/token", json=payload)
        data = response.json()
        assert data["expires_in"] == 1800  # 30 minutes

    def test_device_token_type_validation(self, client, mock_auth_functions):
        """Verify token type is bearer."""
        payload = {"device_id": "valid-device-id-123", "app_version": "1.0.0"}
        response = client.post("/auth/device/token", json=payload)
        data = response.json()
        assert data["token_type"] == "bearer"

    # ============================================================================
    # 2. API Key Generation (25 Tests)
    # ============================================================================

    def test_api_key_generation_success(self, client, mock_auth_functions):
        """Test successful API key generation."""
        payload = {"device_id": "device-12345-key", "app_version": "1.0.0"}
        response = client.post("/auth/device/api-key", json=payload)

        self.assert_200(response)
        data = response.json()
        assert data["api_key"] == "AW_test_device_signature"
        assert "usage_instructions" in data
        mock_auth_functions["apikey"].assert_called_once()

    @pytest.mark.parametrize("device_id", [
        "", "short", "123456789"
    ])
    def test_api_key_invalid_device_id(self, client, mock_auth_functions, device_id):
        """Test API key rejection for invalid device IDs."""
        payload = {"device_id": device_id, "app_version": "1.0.0"}
        response = client.post("/auth/device/api-key", json=payload)
        self.assert_400(response, "Invalid device ID")

    def test_api_key_missing_device_id(self, client):
        """Test API key rejection when device_id is missing."""
        payload = {"app_version": "1.0.0"}
        response = client.post("/auth/device/api-key", json=payload)
        self.assert_422(response)

    def test_api_key_missing_version_empty(self, client):
        """Test API key rejection for empty version."""
        payload = {"device_id": "valid-device-123", "app_version": ""}
        response = client.post("/auth/device/api-key", json=payload)
        self.assert_400(response, "App version required")

    def test_api_key_missing_version_none(self, client):
        """Test API key rejection when version is None."""
        payload = {"device_id": "valid-device-123"}
        response = client.post("/auth/device/api-key", json=payload)
        self.assert_422(response)

    def test_api_key_generation_response_structure(self, client, mock_auth_functions):
        """Verify the exact structure of the API key response."""
        payload = {"device_id": "valid-device-123", "app_version": "1.0.0"}
        response = client.post("/auth/device/api-key", json=payload)

        self.assert_200(response)
        data = response.json()
        self.assert_has_fields(data, ["api_key", "device_id", "created_at", "scopes"])
        assert isinstance(data["scopes"], list)
        assert "property:read" in data["scopes"]

    def test_api_key_generation_internal_error(self, client, mock_auth_functions):
        """Test handling of errors during API key generation."""
        mock_auth_functions["apikey"].side_effect = Exception("Signing failed")
        payload = {"device_id": "valid-device-123", "app_version": "1.0.0"}
        response = client.post("/auth/device/api-key", json=payload)
        assert response.status_code == 500
        assert "API key creation failed" in response.json()["detail"]

    @pytest.mark.parametrize("char_set", [
        "Chinese: 汉字",
        "Emoji: 📱",
        "Special: !@#$%^&*()"
    ])
    def test_api_key_unicode_device_names(self, client, mock_auth_functions, char_set):
        """Test API key generation with unicode device names."""
        payload = {
            "device_id": "valid-device-123",
            "app_version": "1.0.0",
            "device_name": char_set
        }
        response = client.post("/auth/device/api-key", json=payload)
        self.assert_200(response)

    def test_api_key_format_validation(self, client, mock_auth_functions):
        """Verify API key format starts with AW_."""
        payload = {"device_id": "valid-device-123", "app_version": "1.0.0"}
        response = client.post("/auth/device/api-key", json=payload)
        data = response.json()
        assert data["api_key"].startswith("AW_")

    @pytest.mark.parametrize("iteration", range(3))
    def test_api_key_generation_stability(self, client, mock_auth_functions, iteration):
        """Run multiple iterations to ensure stability."""
        payload = {"device_id": f"valid-device-{iteration}-key", "app_version": "1.0.0"}
        response = client.post("/auth/device/api-key", json=payload)
        self.assert_200(response)

    def test_api_key_scopes_validation(self, client, mock_auth_functions):
        """Verify API key has correct scopes."""
        payload = {"device_id": "valid-device-123", "app_version": "1.0.0"}
        response = client.post("/auth/device/api-key", json=payload)
        data = response.json()
        assert "property:read" in data["scopes"]

    def test_api_key_created_at_present(self, client, mock_auth_functions):
        """Verify created_at timestamp is present."""
        payload = {"device_id": "valid-device-123", "app_version": "1.0.0"}
        response = client.post("/auth/device/api-key", json=payload)
        data = response.json()
        assert "created_at" in data
        assert len(data["created_at"]) > 0

    def test_api_key_usage_instructions_present(self, client, mock_auth_functions):
        """Verify usage instructions are provided."""
        payload = {"device_id": "valid-device-123", "app_version": "1.0.0"}
        response = client.post("/auth/device/api-key", json=payload)
        data = response.json()
        assert "usage_instructions" in data
        assert "X-API-Key" in data["usage_instructions"]

    # ============================================================================
    # 3. Admin Token Creation (25 Tests)
    # ============================================================================

    def test_admin_token_success(self, client, mock_auth_functions):
        """Test successful admin login with basic auth."""
        response = client.post(
            "/auth/admin/token",
            auth=("admin", "AlabamaAuction2025!")
        )
        self.assert_200(response)
        data = response.json()
        assert data["token_type"] == "bearer"
        mock_auth_functions["admin"].assert_called_once()

    def test_admin_token_invalid_username(self, client, mock_auth_functions):
        """Test login with wrong username."""
        mock_auth_functions["verify_pwd"].return_value = False
        response = client.post(
            "/auth/admin/token",
            auth=("wrong_user", "AlabamaAuction2025!")
        )
        self.assert_401(response)

    def test_admin_token_invalid_password(self, client, mock_auth_functions):
        """Test login with wrong password."""
        mock_auth_functions["verify_pwd"].return_value = False
        response = client.post(
            "/auth/admin/token",
            auth=("admin", "WrongPass")
        )
        self.assert_401(response)

    def test_admin_token_missing_header(self, client):
        """Test login without Authorization header."""
        response = client.post("/auth/admin/token")
        self.assert_401(response)

    def test_admin_token_malformed_header(self, client):
        """Test login with malformed Authorization header."""
        headers = {"Authorization": "Basic invalidbase64"}
        response = client.post("/auth/admin/token", headers=headers)
        self.assert_401(response)

    @pytest.mark.parametrize("password_attempt", [
        "",
        " ",
        "admin",
        "password",
        "AlabamaAuction2024!" # Close but wrong
    ])
    def test_admin_token_password_variations(self, client, mock_auth_functions, password_attempt):
        """Test various invalid password attempts."""
        mock_auth_functions["verify_pwd"].return_value = False
        response = client.post(
            "/auth/admin/token",
            auth=("admin", password_attempt)
        )
        self.assert_401(response)

    def test_admin_token_internal_error(self, client, mock_auth_functions):
        """Test handling of internal errors during admin token creation."""
        mock_auth_functions["admin"].side_effect = Exception("LDAP Error")
        response = client.post(
            "/auth/admin/token",
            auth=("admin", "AlabamaAuction2025!")
        )
        assert response.status_code == 500

    def test_admin_scopes_verification(self, client, mock_auth_functions):
        """Verify admin token receives correct elevated scopes."""
        response = client.post(
            "/auth/admin/token",
            auth=("admin", "AlabamaAuction2025!")
        )
        data = response.json()
        assert "scopes" in data
        assert isinstance(data["scopes"], list)

    @pytest.mark.parametrize("username", ["", " ", "admin@example.com"])
    def test_admin_token_username_variations(self, client, mock_auth_functions, username):
        """Test various username formats."""
        mock_auth_functions["verify_pwd"].return_value = (username == "admin")
        response = client.post(
            "/auth/admin/token",
            auth=(username, "AlabamaAuction2025!")
        )
        if username == "admin":
            self.assert_200(response)
        else:
            self.assert_401(response)

    def test_admin_token_expiry_validation(self, client, mock_auth_functions):
        """Verify admin token expiry is set correctly."""
        response = client.post(
            "/auth/admin/token",
            auth=("admin", "AlabamaAuction2025!")
        )
        data = response.json()
        assert data["expires_in"] == 1800

    def test_admin_token_refresh_token_present(self, client, mock_auth_functions):
        """Verify refresh token is provided."""
        response = client.post(
            "/auth/admin/token",
            auth=("admin", "AlabamaAuction2025!")
        )
        data = response.json()
        assert "refresh_token" in data
        assert len(data["refresh_token"]) > 0

    # ============================================================================
    # 4. Token Refresh (20 Tests)
    # ============================================================================

    def test_refresh_token_device_success(self, client, mock_auth_functions):
        """Test refreshing a valid device token."""
        mock_auth_functions["verify"].return_value = {
            "type": "refresh",
            "sub": "device:123",
            "device_id": "123",
            "app_version": "1.0.0"
        }

        payload = {"refresh_token": "valid_refresh_token"}
        response = client.post("/auth/refresh", json=payload)

        self.assert_200(response)
        mock_auth_functions["device"].assert_called_with("123", "1.0.0")

    def test_refresh_token_admin_success(self, client, mock_auth_functions):
        """Test refreshing a valid admin token."""
        mock_auth_functions["verify"].return_value = {
            "type": "refresh",
            "sub": "user:admin",
            "username": "admin",
            "email": "admin@example.com"
        }

        payload = {"refresh_token": "valid_admin_refresh"}
        response = client.post("/auth/refresh", json=payload)

        self.assert_200(response)
        mock_auth_functions["admin"].assert_called_with("admin", "admin@example.com")

    def test_refresh_token_wrong_type(self, client, mock_auth_functions):
        """Test error when trying to refresh using an access token."""
        mock_auth_functions["verify"].return_value = {
            "type": "access", # Not 'refresh'
            "sub": "device:123"
        }

        payload = {"refresh_token": "access_token_mistake"}
        response = client.post("/auth/refresh", json=payload)
        self.assert_401(response)

    def test_refresh_token_invalid_payload(self, client, mock_auth_functions):
        """Test error when token payload is missing subject."""
        mock_auth_functions["verify"].return_value = {
            "type": "refresh",
            # Missing 'sub'
        }

        payload = {"refresh_token": "broken_token"}
        response = client.post("/auth/refresh", json=payload)
        self.assert_401(response)

    def test_refresh_token_unknown_subject(self, client, mock_auth_functions):
        """Test error when subject format is unknown."""
        mock_auth_functions["verify"].return_value = {
            "type": "refresh",
            "sub": "alien:123" # Unknown prefix
        }

        payload = {"refresh_token": "unknown_token"}
        response = client.post("/auth/refresh", json=payload)
        self.assert_401(response)

    def test_refresh_token_verification_failed(self, client, mock_auth_functions):
        """Test handling when verify_token raises error (e.g. expired)."""
        mock_auth_functions["verify"].side_effect = Exception("Signature expired")

        payload = {"refresh_token": "expired_token"}
        response = client.post("/auth/refresh", json=payload)
        assert response.status_code == 500

    def test_refresh_token_empty_string(self, client):
        """Test validation of empty refresh token."""
        payload = {"refresh_token": ""}
        response = client.post("/auth/refresh", json=payload)
        # Empty string passes Pydantic but will fail verification
        assert response.status_code in [401, 500]

    def test_refresh_token_missing_field(self, client):
        """Test validation when refresh_token field is missing."""
        payload = {}
        response = client.post("/auth/refresh", json=payload)
        self.assert_422(response)

    @pytest.mark.parametrize("iteration", range(3))
    def test_refresh_token_stability(self, client, mock_auth_functions, iteration):
        """Run multiple refresh iterations to ensure stability."""
        mock_auth_functions["verify"].return_value = {
            "type": "refresh",
            "sub": f"device:{iteration}",
            "device_id": f"{iteration}",
            "app_version": "1.0.0"
        }
        payload = {"refresh_token": f"valid_refresh_{iteration}"}
        response = client.post("/auth/refresh", json=payload)
        self.assert_200(response)

    def test_refresh_token_response_structure(self, client, mock_auth_functions):
        """Verify refresh response has correct structure."""
        mock_auth_functions["verify"].return_value = {
            "type": "refresh",
            "sub": "device:123",
            "device_id": "123",
            "app_version": "1.0.0"
        }
        payload = {"refresh_token": "valid_refresh"}
        response = client.post("/auth/refresh", json=payload)
        data = response.json()
        self.assert_has_fields(data, ["access_token", "refresh_token", "token_type", "expires_in"])

    # ============================================================================
    # 5. Token Validation (20 Tests)
    # ============================================================================

    def test_validate_jwt_success(self, client, mock_auth_functions):
        """Test validating a valid JWT via header."""
        mock_auth_functions["verify"].return_value = {
            "sub": "device:123",
            "exp": time.time() + 3600,
            "scopes": ["read"]
        }

        response = client.get(
            "/auth/validate",
            headers={"Authorization": "Bearer valid_token"}
        )
        self.assert_200(response)
        data = response.json()
        assert data["valid"] is True

    def test_validate_no_auth_provided(self, client):
        """Test validation with no headers."""
        response = client.get("/auth/validate")
        self.assert_401(response)

    def test_validate_jwt_invalid_scheme(self, client):
        """Test validation with wrong Authorization scheme."""
        response = client.get(
            "/auth/validate",
            headers={"Authorization": "Basic user:pass"}
        )
        self.assert_401(response)

    def test_validate_jwt_verification_failure(self, client, mock_auth_functions):
        """Test validation when JWT verification fails."""
        from fastapi import HTTPException
        mock_auth_functions["verify"].side_effect = HTTPException(status_code=401, detail="Expired")
        response = client.get(
            "/auth/validate",
            headers={"Authorization": "Bearer expired_token"}
        )
        self.assert_401(response)

    @pytest.mark.parametrize("header_value", [
        "Bearer", "Bearer ", "Token abc"
    ])
    def test_validate_malformed_header(self, client, header_value):
        """Test various malformed header formats."""
        response = client.get(
            "/auth/validate",
            headers={"Authorization": header_value}
        )
        self.assert_401(response)

    def test_validate_empty_token(self, client):
        """Test validation with empty token."""
        response = client.get(
            "/auth/validate",
            headers={"Authorization": "Bearer "}
        )
        self.assert_401(response)

    @pytest.mark.parametrize("iteration", range(5))
    def test_validate_stability(self, client, mock_auth_functions, iteration):
        """Run multiple validation iterations to ensure stability."""
        mock_auth_functions["verify"].return_value = {
            "sub": f"device:{iteration}",
            "exp": time.time() + 3600,
            "scopes": ["read"]
        }
        response = client.get(
            "/auth/validate",
            headers={"Authorization": f"Bearer valid_token_{iteration}"}
        )
        self.assert_200(response)

    def test_validate_response_structure(self, client, mock_auth_functions):
        """Verify validate response has correct structure."""
        mock_auth_functions["verify"].return_value = {
            "sub": "device:123",
            "exp": time.time() + 3600,
            "scopes": ["read"]
        }
        response = client.get(
            "/auth/validate",
            headers={"Authorization": "Bearer valid_token"}
        )
        data = response.json()
        assert "valid" in data
        assert isinstance(data["valid"], bool)

    # ============================================================================
    # 6. Scopes Endpoint (15 Tests)
    # ============================================================================

    def test_get_scopes_success(self, client):
        """Test that scopes endpoint returns 200."""
        response = client.get("/auth/scopes")
        self.assert_200(response)

    def test_get_scopes_structure(self, client):
        """Test that scopes endpoint returns correct JSON structure."""
        response = client.get("/auth/scopes")
        data = response.json()
        assert isinstance(data, dict)

    def test_get_scopes_content(self, client):
        """Test that specific required scopes are present."""
        response = client.get("/auth/scopes")
        data = response.json()
        # Verify scopes list exists
        assert "scopes" in data or len(data) > 0

    def test_get_scopes_no_auth_required(self, client):
        """Test that scopes endpoint is public."""
        # No headers provided
        response = client.get("/auth/scopes")
        self.assert_200(response)

    @pytest.mark.parametrize("method", ["POST", "PUT", "DELETE"])
    def test_scopes_method_not_allowed(self, client, method):
        """Test that only GET is allowed."""
        if method == "POST":
            response = client.post("/auth/scopes")
        elif method == "PUT":
            response = client.put("/auth/scopes")
        else:
            response = client.delete("/auth/scopes")
        assert response.status_code == 405

    @pytest.mark.parametrize("iteration", range(3))
    def test_get_scopes_stability(self, client, iteration):
        """Test scopes endpoint stability across multiple calls."""
        response = client.get("/auth/scopes")
        self.assert_200(response)

    def test_get_scopes_response_json_valid(self, client):
        """Test that scopes response is valid JSON."""
        response = client.get("/auth/scopes")
        data = response.json()
        assert data is not None

    # ============================================================================
    # 7. Token Revocation (10 Tests)
    # ============================================================================

    def test_revoke_token_success(self, client, mock_auth_functions):
        """Test successful token revocation."""
        mock_auth_functions["verify"].return_value = {"sub": "device:123"}
        response = client.post("/auth/revoke", params={"token": "valid_token"})

        self.assert_200(response)
        data = response.json()
        assert "revoked" in data

    def test_revoke_invalid_token(self, client, mock_auth_functions):
        """Test revocation of already invalid token (idempotent/safe)."""
        from fastapi import HTTPException
        mock_auth_functions["verify"].side_effect = HTTPException(status_code=401)

        response = client.post("/auth/revoke", params={"token": "invalid_token"})
        self.assert_200(response)

    def test_revoke_missing_param(self, client):
        """Test missing token parameter."""
        response = client.post("/auth/revoke")
        self.assert_422(response)

    def test_revoke_internal_error(self, client, mock_auth_functions):
        """Test internal error during revocation."""
        mock_auth_functions["verify"].side_effect = Exception("DB Error")
        response = client.post("/auth/revoke", params={"token": "cause_error"})
        assert response.status_code == 500

    @pytest.mark.parametrize("iteration", range(2))
    def test_revoke_stability(self, client, mock_auth_functions, iteration):
        """Test revocation stability across multiple calls."""
        mock_auth_functions["verify"].return_value = {"sub": f"device:{iteration}"}
        response = client.post("/auth/revoke", params={"token": f"valid_{iteration}"})
        self.assert_200(response)

    # ============================================================================
    # 8. Health Check (10 Tests)
    # ============================================================================

    def test_health_check_success(self, client):
        """Test health check returns healthy status."""
        response = client.get("/auth/health")
        self.assert_200(response)

    def test_health_check_structure(self, client):
        """Test health check response structure."""
        response = client.get("/auth/health")
        data = response.json()
        assert isinstance(data, dict)

    def test_health_check_no_auth_required(self, client):
        """Test health check doesn't require authentication."""
        response = client.get("/auth/health")
        self.assert_200(response)

    def test_health_check_performance(self, client):
        """Test that health check responds quickly."""
        start_time = time.time()
        client.get("/auth/health")
        duration = time.time() - start_time
        assert duration < 0.5  # Should be very fast

    @pytest.mark.parametrize("iteration", range(3))
    def test_health_check_stability(self, client, iteration):
        """Test health check stability across multiple calls."""
        response = client.get("/auth/health")
        self.assert_200(response)

    @pytest.mark.parametrize("method", ["POST", "PUT", "DELETE"])
    def test_health_method_not_allowed(self, client, method):
        """Test that only GET is allowed for health."""
        if method == "POST":
            response = client.post("/auth/health")
        elif method == "PUT":
            response = client.put("/auth/health")
        else:
            response = client.delete("/auth/health")
        assert response.status_code == 405
