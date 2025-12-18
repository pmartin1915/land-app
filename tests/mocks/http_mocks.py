"""
HTTP mocking utilities for simulating web requests and responses.

This module provides classes to mock HTTP clients and responses, particularly
for interactions with the Alabama Department of Revenue (ADOR) website.
It allows for registering predefined responses for specific URLs and simulating
various network conditions like timeouts and server errors.
"""
from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse


class MockHTTPResponse:
    """A mock of an HTTP response object (e.g., from `httpx` or `requests`)."""

    def __init__(
        self,
        status_code: int,
        content: bytes = b"",
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ):
        """
        Initializes the mock HTTP response.

        Args:
            status_code: The HTTP status code.
            content: The response body as bytes.
            headers: A dictionary of response headers.
            json_data: A dictionary to be returned by the `json()` method.
        """
        self.status_code = status_code
        self.content = content
        self.headers = headers or {"Content-Type": "text/html"}
        self._json_data = json_data

    @property
    def text(self) -> str:
        """Returns the response content as a string."""
        return self.content.decode("utf-8")

    def json(self) -> Dict[str, Any]:
        """
        Returns the response body as a JSON object.
        Raises a ValueError if no JSON data is available.
        """
        if self._json_data is None:
            raise ValueError("No JSON object could be decoded")
        return self._json_data


class ADORWebsiteMock:
    """Mocks interactions with the ADOR (Alabama Dept. of Revenue) website."""

    def __init__(self):
        """Initializes the ADOR website mock."""
        self.request_count = 0
        self._county_responses: Dict[str, str] = {}
        self._simulate_timeout = False
        self._error_status_code: Optional[int] = None

    def register_county_response(self, county_code: str, html_content: str) -> None:
        """
        Registers a predefined HTML response for a specific county code.

        Args:
            county_code: The 2-digit county code (e.g., '01' for Autauga).
            html_content: The HTML string to be returned for this county.
        """
        self._county_responses[county_code] = html_content

    def simulate_timeout(self) -> None:
        """Configures the mock to raise a timeout error on the next request."""
        self._simulate_timeout = True
        self._error_status_code = None

    def simulate_error(self, status_code: int) -> None:
        """
        Configures the mock to return a specific HTTP error status.

        Args:
            status_code: The HTTP error code to return (e.g., 500, 404).
        """
        self._error_status_code = status_code
        self._simulate_timeout = False

    async def get(self, url: str, **kwargs: Any) -> MockHTTPResponse:
        """
        Simulates an asynchronous GET request to the ADOR website.

        It parses the URL to find a county code and returns the registered
        response or simulates a configured error.

        Args:
            url: The URL being requested.
            **kwargs: Additional request arguments (ignored).

        Returns:
            A MockHTTPResponse object.

        Raises:
            asyncio.TimeoutError: If `simulate_timeout` was called.
        """
        self.request_count += 1
        await asyncio.sleep(0)  # Simulate async network call

        if self._simulate_timeout:
            self._simulate_timeout = False  # Reset after firing
            raise asyncio.TimeoutError("The request timed out.")

        if self._error_status_code:
            status = self._error_status_code
            self._error_status_code = None  # Reset after firing
            return MockHTTPResponse(status, content=f"Error {status}".encode())

        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)

        # Heuristic to find county code in URL path or query params
        county_code = query_params.get("county", [None])[0] or \
                      query_params.get("countyCode", [None])[0]

        if not county_code:
             match = re.search(r'county=(\d+)', url) or re.search(r'/(\d+)/', url)
             if match:
                 county_code = match.group(1).zfill(2)

        if county_code and county_code in self._county_responses:
            html = self._county_responses[county_code]
            return MockHTTPResponse(200, content=html.encode("utf-8"))

        return MockHTTPResponse(404, content=b"County not found or no response registered.")


class MockHTTPClient:
    """A generic mock HTTP client for various testing purposes."""

    def __init__(self):
        """Initializes the generic mock client."""
        self.request_count = 0
        self.requests_log: List[Dict[str, Any]] = []
        self._responses: Dict[str, MockHTTPResponse] = {}
        self._error_to_raise: Optional[Exception] = None

    def register_response(self, url: str, response: MockHTTPResponse) -> None:
        """
        Registers a predefined response for a specific URL.

        Args:
            url: The exact URL to match.
            response: The MockHTTPResponse to return.
        """
        self._responses[url] = response

    def simulate_error(self, error: Exception) -> None:
        """
        Configures the mock to raise a specific exception on the next request.

        Args:
            error: The exception instance to raise.
        """
        self._error_to_raise = error

    async def get(self, url: str, **kwargs: Any) -> MockHTTPResponse:
        """
        Simulates a generic asynchronous GET request.

        Args:
            url: The URL for the request.
            **kwargs: Additional request parameters.

        Returns:
            A MockHTTPResponse object.

        Raises:
            Exception: The exception configured via `simulate_error`.
        """
        self.request_count += 1
        self.requests_log.append({"method": "GET", "url": url, "kwargs": kwargs})
        await asyncio.sleep(0)

        if self._error_to_raise:
            error = self._error_to_raise
            self._error_to_raise = None
            raise error

        if url in self._responses:
            return self._responses[url]

        return MockHTTPResponse(404, content=b"Not Found")
