"""
Pytest fixtures for UI testing with Playwright.

This file provides shared fixtures for:
- Managing the Streamlit server lifecycle.
- Providing configured Playwright page instances to tests.
- Instantiating Page Object Models (POMs) for test functions.
- Capturing screenshots on test failure for easier debugging.
"""
from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Generator

import pytest
from playwright.sync_api import BrowserContext, Page

# Add project root to path to allow imports from the app
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.ui.pages.main_dashboard import MainDashboardPage


def find_free_port() -> int:
    """Find and return a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        return s.getsockname()[1]


class StreamlitServer:
    """Context manager for running the Streamlit server during tests."""

    def __init__(self, app_path: str, port: int | None = None, timeout: int = 60):
        self.app_path = app_path
        self.port = port or find_free_port()
        self.timeout = timeout
        self.process: subprocess.Popen | None = None
        self.url = f"http://localhost:{self.port}"

    def start(self) -> str:
        """Start the Streamlit server and wait for it to be ready."""
        cmd = [
            sys.executable, "-m", "streamlit", "run",
            self.app_path,
            "--server.port", str(self.port),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
            "--server.fileWatcherType", "none",
        ]

        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creation_flags,
            cwd=str(project_root)
        )

        start_time = time.time()
        while time.time() - start_time < self.timeout:
            try:
                with socket.create_connection(("localhost", self.port), timeout=1):
                    return self.url
            except (socket.timeout, ConnectionRefusedError):
                time.sleep(0.5)

        raise TimeoutError(f"Streamlit server did not start at {self.url} within {self.timeout}s")

    def stop(self):
        """Stop the Streamlit server process."""
        if self.process:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                    capture_output=True,
                    check=False
                )
            else:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            self.process = None

@pytest.fixture(scope="session")
def streamlit_server() -> Generator[str, None, None]:
    """Session-scoped fixture to start and stop the Streamlit server."""
    app_path = str(project_root / "streamlit_app" / "app.py")
    server = StreamlitServer(app_path)
    try:
        url = server.start()
        yield url
    finally:
        server.stop()


@pytest.fixture(scope="function")
def page(browser_context: BrowserContext, streamlit_server: str) -> Generator[Page, None, None]:
    """
    Provides a new, isolated page for each test function, automatically navigated
    to the Streamlit app's URL.
    """
    page = browser_context.new_page()
    page.goto(streamlit_server)
    # Wait for the main app container to be visible, indicating the app has loaded.
    page.wait_for_selector("div[data-testid='stAppViewContainer']", timeout=30000)
    yield page
    page.close()


@pytest.fixture(scope="function")
def main_dashboard_page(page: Page) -> MainDashboardPage:
    """Fixture to provide an instance of the MainDashboardPage object."""
    return MainDashboardPage(page)


@pytest.fixture(scope="function")
def authenticated_page(page: Page) -> Page:
    """
    Fixture for a page with an authenticated user.

    Placeholder: Currently, the app has no authentication. This fixture can be
    extended to perform login steps once authentication is implemented. For now,
    it returns the standard page.
    """
    # Example future implementation:
    # login_page = LoginPage(page)
    # login_page.login("test_user", "password")
    return page


# Hook to capture screenshots on test failure
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """Capture a screenshot on test failure and save it."""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        try:
            page_fixture = item.funcargs.get("page")
            if page_fixture:
                screenshot_dir = project_root / "test-results" / "screenshots"
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                test_name = item.nodeid.replace("::", "_").replace("/", "_")
                screenshot_path = screenshot_dir / f"failure_{test_name}.png"
                page_fixture.screenshot(path=screenshot_path, full_page=True)
                print(f"\nScreenshot saved to: {screenshot_path}")
        except Exception as e:
            print(f"Failed to capture screenshot: {e}")
