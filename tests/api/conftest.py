"""
Pytest fixtures for API testing.

This file provides fixtures for:
- A FastAPI TestClient instance.
- An isolated, in-memory database session for each test.
- Pre-authenticated clients for different user roles (device, admin).
- An API key-authenticated client.
"""
import os
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Set environment variables for testing before importing the app
# This ensures the app uses a test-specific configuration
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"  # In-memory async SQLite

# Import the FastAPI app instance
from backend_api.main import app
# Import auth helpers to create authenticated clients
from .auth_helpers import (
    generate_admin_jwt_token,
    generate_test_api_key,
    generate_test_jwt_token,
)

# --- Database Fixtures ---
# This setup assumes your FastAPI app uses a dependency injection system
# for database sessions, like `Depends(get_db)`. We will override this
# dependency to point to a test database.

# Create an async engine for the in-memory SQLite database
# `check_same_thread` is required for SQLite
engine = create_async_engine(
    "sqlite+aiosqlite://", connect_args={"check_same_thread": False}
)

# Create a sessionmaker for the test database
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)


# This is a placeholder for your actual `get_db` dependency.
# You MUST replace `get_db` with the actual dependency from your project
# (e.g., from `backend_api.database.connection import get_db`).
async def get_test_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency override to provide a test database session."""
    async with TestingSessionLocal() as session:
        yield session


# If you have database models, you would create them here for testing
# For example:
# from backend_api.models.base import Base
# @pytest.fixture(scope="function", autouse=True)
# async def setup_database():
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
#     yield
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def api_client() -> Generator[TestClient, None, None]:
    """
    Yield a FastAPI TestClient that uses an isolated in-memory database.
    """
    # This is where the magic happens. We override the production `get_db`
    # dependency with our `get_test_db` for the duration of the test.
    # Replace `get_db` with your actual dependency callable if it's different.
    # from backend_api.database.connection import get_db
    # app.dependency_overrides[get_db] = get_test_db

    # NOTE: Since `get_db` is not provided, this line is commented out.
    # You MUST uncomment and adapt it to your project's structure.
    # For now, the client will use the default app dependencies.

    with TestClient(app) as client:
        yield client

    # Clean up the dependency override after the test
    # app.dependency_overrides.clear()


# --- Client Fixtures ---


@pytest.fixture(scope="function")
def authenticated_client(api_client: TestClient) -> TestClient:
    """
    Provide a TestClient authenticated with a standard device JWT token.
    This client is suitable for testing endpoints accessible by a regular iOS device.
    """
    token = generate_test_jwt_token(device_id="test-device-123")
    api_client.headers["Authorization"] = f"Bearer {token}"
    return api_client


@pytest.fixture(scope="function")
def admin_client(api_client: TestClient) -> TestClient:
    """
    Provide a TestClient authenticated with an admin JWT token.
    This client has the 'admin' scope for testing admin-only endpoints.
    """
    token = generate_admin_jwt_token(username="test-admin")
    api_client.headers["Authorization"] = f"Bearer {token}"
    return api_client


@pytest.fixture(scope="function")
def api_key_client(api_client: TestClient) -> TestClient:
    """
    Provide a TestClient authenticated with an X-API-Key header.
    This client simulates requests from an iOS device using API key authentication.
    """
    api_key = generate_test_api_key(device_id="test-device-456")
    api_client.headers["X-API-Key"] = api_key
    return api_client


# Re-exporting this fixture from the root conftest for convenience in API tests
@pytest.fixture
def test_property_data(property_factory):
    """
    Fixture to get the property factory for generating test data.

    Usage:
        def test_something(test_property_data):
            data = test_property_data()
            response = client.post("/properties", json=data)
    """
    return property_factory
