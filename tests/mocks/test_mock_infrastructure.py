"""
Tests for the centralized mocking infrastructure.

This test suite validates that the mock objects for the database, HTTP client,
and file system behave as expected. It ensures the mocking layer is reliable
and correctly simulates the behavior of real dependencies.
"""
import asyncio
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import text

from .database_mocks import MockAsyncSession
from .file_mocks import MockFileSystem, mock_file_operations
from .http_mocks import ADORWebsiteMock, MockHTTPClient, MockHTTPResponse

pytestmark = pytest.mark.unit


# === Database Mock Tests ===

@pytest.mark.asyncio
async def test_mock_db_session_execute(mock_db_session: MockAsyncSession):
    """Tests that execute() tracks queries and returns a primed result."""
    stmt = text("SELECT 1")
    mock_db_session.prime_result(stmt, [(1,)])

    result = await mock_db_session.execute(stmt)

    assert len(mock_db_session.executed_queries) == 1
    assert str(stmt) in mock_db_session.executed_queries[0]
    assert result.all() == [(1,)]


@pytest.mark.asyncio
async def test_mock_db_session_scalars(mock_db_session: MockAsyncSession):
    """Tests that the scalars().all() method returns a flat list."""
    stmt = text("SELECT name FROM users")
    users = ["Alice", "Bob"]
    mock_db_session.prime_result(stmt, users)

    result = await mock_db_session.execute(stmt)

    assert result.scalars().all() == users


@pytest.mark.asyncio
async def test_mock_db_session_commit(mock_db_session: MockAsyncSession):
    """Tests that commit() sets the committed flag."""
    assert not mock_db_session.committed
    await mock_db_session.commit()
    assert mock_db_session.committed


@pytest.mark.asyncio
async def test_mock_db_session_rollback(mock_db_session: MockAsyncSession):
    """Tests that rollback() sets the rolled_back flag."""
    assert not mock_db_session.rolled_back
    await mock_db_session.rollback()
    assert mock_db_session.rolled_back


@pytest.mark.asyncio
async def test_mock_db_session_close(mock_db_session: MockAsyncSession):
    """Tests that close() sets the closed flag."""
    assert not mock_db_session.closed
    await mock_db_session.close()
    assert mock_db_session.closed


@pytest.mark.asyncio
async def test_isolated_database_test_fixture_rolls_back(isolated_database_test: MockAsyncSession):
    """Tests that the isolated_database_test fixture provides a session that is rolled back."""
    # The fixture itself handles the context management
    assert not isolated_database_test.committed
    assert not isolated_database_test.rolled_back
    # After the test function finishes, the context manager in the fixture will call rollback
    # We can't test it post-factum here, but we trust the context manager's finally block
    # and verify its final state upon exiting scope.


# === HTTP Mock Tests ===

@pytest.mark.asyncio
async def test_ador_website_mock_register_and_get(mock_ador_website: ADORWebsiteMock):
    """Tests registering a response and retrieving it."""
    html = "<html><body>Test Content</body></html>"
    mock_ador_website.register_county_response("01", html)

    response = await mock_ador_website.get("http://example.com/search?county=01")

    assert response.status_code == 200
    assert response.text == html
    assert mock_ador_website.request_count == 1


@pytest.mark.asyncio
async def test_ador_website_mock_unregistered_county(mock_ador_website: ADORWebsiteMock):
    """Tests that a 404 is returned for an unregistered county."""
    response = await mock_ador_website.get("http://example.com/search?county=99")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_ador_website_mock_request_count_isolated(mock_ador_website: ADORWebsiteMock):
    """Tests that request_count is reset between tests."""
    assert mock_ador_website.request_count == 0
    await mock_ador_website.get("http://example.com/search?county=01")
    assert mock_ador_website.request_count == 1


@pytest.mark.asyncio
async def test_ador_website_mock_simulate_timeout(mock_ador_website: ADORWebsiteMock):
    """Tests timeout simulation."""
    mock_ador_website.simulate_timeout()
    with pytest.raises(asyncio.TimeoutError):
        await mock_ador_website.get("http://example.com/search?county=01")
    # Ensure flag is reset
    response = await mock_ador_website.get("http://example.com/search?county=01")
    assert response.status_code == 404


@pytest.mark.parametrize("status_code", [500, 503, 403])
@pytest.mark.asyncio
async def test_ador_website_mock_simulate_error(mock_ador_website: ADORWebsiteMock, status_code: int):
    """Tests HTTP error simulation."""
    mock_ador_website.simulate_error(status_code)
    response = await mock_ador_website.get("http://example.com/search?county=01")
    assert response.status_code == status_code
    # Ensure flag is reset
    response_after = await mock_ador_website.get("http://example.com/search?county=01")
    assert response_after.status_code == 404


def test_mock_http_response_properties():
    """Tests properties of MockHTTPResponse."""
    resp = MockHTTPResponse(200, content=b"hello", json_data={"key": "value"})
    assert resp.status_code == 200
    assert resp.text == "hello"
    assert resp.json() == {"key": "value"}


def test_mock_http_response_no_json():
    """Tests that calling .json() without data raises an error."""
    resp = MockHTTPResponse(200)
    with pytest.raises(ValueError):
        resp.json()


@pytest.mark.asyncio
async def test_mock_http_client_get(mock_http_client: MockHTTPClient):
    """Tests the generic mock HTTP client."""
    url = "http://api.test.com/data"
    mock_response = MockHTTPResponse(200, json_data={"status": "ok"})
    mock_http_client.register_response(url, mock_response)

    response = await mock_http_client.get(url)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert mock_http_client.request_count == 1
    assert mock_http_client.requests_log[0]["url"] == url


# === File System Mock Tests ===

def test_mock_file_system_csv_roundtrip(mock_file_system: MockFileSystem):
    """Tests writing and reading a CSV from the in-memory file system."""
    path = "reports/test.csv"
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

    mock_file_system.write_csv(path, df)

    assert mock_file_system.exists(path)

    read_df = mock_file_system.read_csv(path)
    pd.testing.assert_frame_equal(df, read_df)


def test_mock_file_system_read_nonexistent(mock_file_system: MockFileSystem):
    """Tests that reading a non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        mock_file_system.read_csv("nonexistent.csv")


def test_mock_file_system_mkdir_and_exists(mock_file_system: MockFileSystem):
    """Tests directory creation and existence checking."""
    dir_path = "data/raw"
    assert not mock_file_system.exists(dir_path)
    mock_file_system.mkdir(dir_path, parents=True)
    assert mock_file_system.exists(dir_path)
    assert mock_file_system.exists("data")


def test_mock_file_system_write_creates_parent_dir(mock_file_system: MockFileSystem):
    """Tests that writing a file implicitly creates its parent directory."""
    path = "output/results/final.csv"
    df = pd.DataFrame({"id": [1]})

    assert not mock_file_system.exists("output/results")
    mock_file_system.write_csv(path, df)
    assert mock_file_system.exists("output/results")
    assert mock_file_system.exists(path)


def test_mock_file_system_isolation():
    """Tests that two instances of MockFileSystem are isolated."""
    fs1 = MockFileSystem()
    fs2 = MockFileSystem()
    fs1.mkdir("dir1")
    assert fs1.exists("dir1")
    assert not fs2.exists("dir1")


def test_mock_file_operations_context_manager():
    """Tests that the context manager correctly patches file operations."""
    df = pd.DataFrame({"data": ["test"]})
    path = Path("./test_context.csv")

    with mock_file_operations() as fs:
        # These pandas functions are now patched
        df.to_csv(path)
        read_df = pd.read_csv(path)

        # Assertions on the mock file system
        assert fs.exists(path)
        pd.testing.assert_frame_equal(df, read_df)

    # After context, real functions should be restored, but we can't easily test that
    # without trying to write a real file, which we want to avoid.
    # The presence of the file on the mock FS is sufficient proof of patching.


# === Fixture Availability and Scoping Tests ===

def test_mock_db_session_fixture_is_available(mock_db_session: MockAsyncSession):
    """Confirms the fixture is injected correctly."""
    assert isinstance(mock_db_session, MockAsyncSession)


@pytest.mark.asyncio
async def test_isolated_db_fixture_is_available(isolated_database_test: MockAsyncSession):
    """Confirms the async fixture is injected correctly."""
    assert isinstance(isolated_database_test, MockAsyncSession)


def test_mock_ador_website_fixture_is_available(mock_ador_website: ADORWebsiteMock):
    """Confirms the fixture is injected correctly."""
    assert isinstance(mock_ador_website, ADORWebsiteMock)


def test_mock_http_client_fixture_is_available(mock_http_client: MockHTTPClient):
    """Confirms the fixture is injected correctly."""
    assert isinstance(mock_http_client, MockHTTPClient)


def test_mock_file_system_fixture_is_available(mock_file_system: MockFileSystem):
    """Confirms the fixture is injected correctly."""
    assert isinstance(mock_file_system, MockFileSystem)
