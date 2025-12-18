"""
Mocking infrastructure for Alabama Auction Watcher tests.

This package provides a centralized set of mock objects and utilities for simulating
external dependencies like databases, HTTP services, and the file system. This allows for
fast, isolated, and deterministic testing of application components.

The mock registry provides a single point of access for mock classes, which can be
useful for dynamic mock management in advanced testing scenarios.
"""

from .database_mocks import MockAsyncSession, mock_database_transaction
from .http_mocks import ADORWebsiteMock, MockHTTPClient, MockHTTPResponse
from .file_mocks import MockFileSystem, mock_file_operations

# A simple registry for centralized access to mock classes.
# This can be expanded to manage mock instances or configurations.
mock_registry = {
    "db_session": MockAsyncSession,
    "ador_website": ADORWebsiteMock,
    "http_client": MockHTTPClient,
    "file_system": MockFileSystem,
}

__all__ = [
    "MockAsyncSession",
    "mock_database_transaction",
    "ADORWebsiteMock",
    "MockHTTPClient",
    "MockHTTPResponse",
    "MockFileSystem",
    "mock_file_operations",
    "mock_registry",
]
