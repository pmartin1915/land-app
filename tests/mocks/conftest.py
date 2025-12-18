"""
Pytest fixtures for the mocking infrastructure.

This module defines shared fixtures that provide instances of mock objects
to be used across the test suite. This promotes consistency and reduces
boilerplate code in test files.
"""
from typing import AsyncGenerator

import pytest
import pytest_asyncio

from .database_mocks import MockAsyncSession, mock_database_transaction
from .file_mocks import MockFileSystem
from .http_mocks import ADORWebsiteMock, MockHTTPClient


@pytest.fixture
def mock_db_session() -> MockAsyncSession:
    """
    Provides a basic instance of MockAsyncSession.

    Returns:
        A new instance of MockAsyncSession for each test.
    """
    return MockAsyncSession()


@pytest_asyncio.fixture
async def isolated_database_test() -> AsyncGenerator[MockAsyncSession, None]:
    """
    Provides a mock database session within a transaction that is always
    rolled back. This ensures test isolation.

    Yields:
        A MockAsyncSession instance managed by a rollback context.
    """
    async with mock_database_transaction() as session:
        yield session


@pytest.fixture
def mock_ador_website() -> ADORWebsiteMock:
    """
    Provides an instance of ADORWebsiteMock.

    Returns:
        A new instance of ADORWebsiteMock for each test.
    """
    return ADORWebsiteMock()


@pytest.fixture
def mock_http_client() -> MockHTTPClient:
    """
    Provides a generic mock HTTP client.

    Returns:
        A new instance of MockHTTPClient for each test.
    """
    return MockHTTPClient()


@pytest.fixture
def mock_file_system() -> MockFileSystem:
    """
    Provides an in-memory mock file system.

    Returns:
        A new instance of MockFileSystem for each test.
    """
    return MockFileSystem()
