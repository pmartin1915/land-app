"""
Base test class with common HTTP assertion methods for API testing.

This class provides a set of reusable assertion helpers to standardize
response validation in API tests, making them more readable and maintainable.
"""
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union

import pytest
from fastapi.responses import JSONResponse
from httpx import Response
from jsonschema import validate
from jsonschema.exceptions import ValidationError

logger = logging.getLogger(__name__)


class BaseAPITest:
    """Base class for API tests with common assertion helpers."""

    def get_response_json(
        self, response: Response, expected_status: int = 200
    ) -> Any:
        """
        Safely decode JSON from a response after checking the status code.

        Args:
            response: The HTTPX response object.
            expected_status: The expected HTTP status code.

        Returns:
            The decoded JSON content.
        """
        assert response.status_code == expected_status, (
            f"Expected status {expected_status}, got {response.status_code}. "
            f"Response: {response.text}"
        )
        try:
            return response.json()
        except json.JSONDecodeError:
            pytest.fail(f"Failed to decode JSON from response: {response.text}")

    def assert_200(self, response: Response, message: str = "Expected 200 OK"):
        """Assert that the response has a 200 OK status code."""
        assert response.status_code == 200, f"{message}: Got {response.status_code}"

    def assert_201(self, response: Response, message: str = "Expected 201 Created"):
        """Assert that the response has a 201 Created status code."""
        assert response.status_code == 201, f"{message}: Got {response.status_code}"

    def assert_400(
        self, response: Response, expected_error: Optional[str] = None
    ):
        """
        Assert that the response has a 400 Bad Request status code.

        Args:
            response: The HTTPX response object.
            expected_error: An optional error string to look for in the response detail.
        """
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        if expected_error:
            data = self.get_response_json(response, 400)
            assert "detail" in data
            assert expected_error in data["detail"]

    def assert_401(self, response: Response):
        """Assert that the response has a 401 Unauthorized status code."""
        assert (
            response.status_code == 401
        ), f"Expected 401 Unauthorized, got {response.status_code}"

    def assert_404(self, response: Response):
        """Assert that the response has a 404 Not Found status code."""
        assert (
            response.status_code == 404
        ), f"Expected 404 Not Found, got {response.status_code}"

    def assert_422(self, response: Response, expected_fields: Optional[List[str]] = None):
        """
        Assert that the response has a 422 Unprocessable Entity status code.

        Args:
            response: The HTTPX response object.
            expected_fields: A list of field names expected in the validation error.
        """
        assert (
            response.status_code == 422
        ), f"Expected 422, got {response.status_code}"
        if expected_fields:
            data = self.get_response_json(response, 422)
            assert "detail" in data and isinstance(data["detail"], list)
            error_fields = {error["loc"][-1] for error in data["detail"]}
            for field in expected_fields:
                assert (
                    field in error_fields
                ), f"Expected validation error for field '{field}' not found."

    def assert_response_time(self, response: Response, max_seconds: float):
        """
        Assert that the response was received within a given time threshold.

        Args:
            response: The HTTPX response object.
            max_seconds: The maximum allowed response time in seconds.
        """
        elapsed = response.elapsed.total_seconds()
        assert elapsed < max_seconds, (
            f"Response time ({elapsed:.3f}s) exceeded threshold of {max_seconds}s"
        )

    def assert_has_fields(
        self, response_json: Union[Dict, List], required_fields: List[str]
    ):
        """
        Assert that a JSON object or list of objects contains required fields.

        Args:
            response_json: The decoded JSON response (a dict or list of dicts).
            required_fields: A list of keys that must be present.
        """
        if isinstance(response_json, list):
            assert len(response_json) > 0, "Response JSON is an empty list."
            json_to_check = response_json[0]
        else:
            json_to_check = response_json

        missing_fields = [
            field for field in required_fields if field not in json_to_check
        ]
        assert not missing_fields, f"Missing fields in response: {missing_fields}"

    def assert_json_matches_schema(
        self, response_json: Any, schema_dict: Dict[str, Any]
    ):
        """
        Validate a JSON object against a given JSON schema.

        Args:
            response_json: The decoded JSON response.
            schema_dict: The JSON schema to validate against.
        """
        try:
            validate(instance=response_json, schema=schema_dict)
        except ValidationError as e:
            pytest.fail(f"JSON schema validation failed: {e.message}")
