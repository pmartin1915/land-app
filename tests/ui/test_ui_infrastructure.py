"""
Validation tests for the UI testing infrastructure.

These tests act as smoke tests to ensure that the core components of the
UI testing setup are functioning correctly, including:
- Streamlit server fixture
- Playwright page fixture
- Page Object Model instantiation and methods
- Helper utilities
- Visual comparison capabilities
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.ui.pages.main_dashboard import MainDashboardPage

# Mark all tests in this file with the 'ui' marker
pytestmark = pytest.mark.ui


@pytest.mark.smoke
class TestUIInfrastructure:
    """Validates the core UI test infrastructure."""

    def test_streamlit_server_is_running(self, page: Page):
        """Checks if the page fixture successfully loads the app."""
        expect(page).to_have_title(
            "Alabama Auction Watcher", timeout=10000
        )
        assert "http://localhost:" in page.url

    def test_main_dashboard_page_fixture(self, main_dashboard_page: MainDashboardPage):
        """Ensures the MainDashboardPage fixture provides a valid object."""
        assert main_dashboard_page is not None
        assert isinstance(main_dashboard_page, MainDashboardPage)
        main_dashboard_page.verify_dashboard_loaded()

    def test_base_page_methods_work(self, main_dashboard_page: MainDashboardPage):
        """Validates a few methods from the BasePage."""
        assert "Alabama Auction Watcher" in main_dashboard_page.get_title()
        assert main_dashboard_page.is_visible(main_dashboard_page.SIDEBAR)

    def test_dashboard_locators_are_valid(self, main_dashboard_page: MainDashboardPage):
        """Confirms that key locators on the dashboard page are present."""
        expect(main_dashboard_page.page.locator(main_dashboard_page.SIDEBAR)).to_be_visible()
        expect(main_dashboard_page.page.locator(main_dashboard_page.DASHBOARD_TAB)).to_be_visible()

    def test_page_title_is_correct(self, page: Page):
        """Verifies the page title matches expectations."""
        title = page.title()
        assert "Alabama Auction Watcher" in title


@pytest.mark.interactions
class TestUIInteractions:
    """Validates basic user interactions using Page Objects."""

    def test_tab_navigation_works(self, main_dashboard_page: MainDashboardPage):
        """Tests navigating between dashboard tabs."""
        # Start on Dashboard tab
        expect(main_dashboard_page.page.locator(main_dashboard_page.DASHBOARD_TAB)).to_be_visible()

        # Navigate to another tab if it exists
        all_tabs = main_dashboard_page.page.locator("button[role='tab']").all()
        if len(all_tabs) > 1:
            second_tab_text = all_tabs[1].inner_text()
            main_dashboard_page.navigate_to_tab(second_tab_text)
            # Verify navigation occurred (page didn't crash)
            assert main_dashboard_page.page.locator("div[data-testid='stAppViewContainer']").is_visible()

    def test_sidebar_is_interactive(self, main_dashboard_page: MainDashboardPage):
        """Tests that the sidebar contains interactive elements."""
        sidebar = main_dashboard_page.page.locator(main_dashboard_page.SIDEBAR)
        expect(sidebar).to_be_visible()

        # Check if sidebar has some content
        sidebar_content = sidebar.inner_text()
        assert len(sidebar_content) > 0


@pytest.mark.visual
class TestVisualRegressions:
    """Performs visual snapshot testing."""

    @pytest.mark.skip(reason="Visual regression requires baseline screenshots to be established first")
    def test_main_dashboard_layout(self, page: Page):
        """
        Takes a screenshot of the main dashboard and compares it to a baseline.
        To update the baseline, run:
        pytest tests/ui --update-snapshots
        """
        # Hide dynamic elements like charts that may cause flaky tests
        chart_locators = page.locator(".stPlotlyChart")
        for i in range(chart_locators.count()):
            chart_locators.nth(i).evaluate("element => element.style.visibility = 'hidden'")

        # Take a screenshot and compare
        expect(page).to_have_screenshot("main_dashboard_layout.png", threshold=0.1)

    @pytest.mark.skip(reason="Visual regression requires baseline screenshots to be established first")
    def test_sidebar_layout(self, page: Page):
        """Takes a screenshot of just the sidebar component."""
        sidebar = page.locator("section[data-testid='stSidebar']")
        expect(sidebar).to_have_screenshot("sidebar_layout.png", threshold=0.1)


@pytest.mark.helpers
class TestHelperUtilities:
    """Validates helper utility functions."""

    def test_base_page_wait_for_app_load(self, page: Page):
        """Tests that wait_for_app_load helper works."""
        from tests.ui.pages.base_page import BasePage

        base_page = BasePage(page)
        # Should not raise an exception
        base_page.wait_for_app_load(timeout=10000)
        assert page.locator("div[data-testid='stAppViewContainer']").is_visible()

    def test_screenshot_capture_works(self, main_dashboard_page: MainDashboardPage, tmp_path):
        """Tests that screenshot capture functionality works."""
        screenshot_path = tmp_path / "test_screenshot.png"
        main_dashboard_page.take_screenshot(str(screenshot_path))
        assert screenshot_path.exists()
        assert screenshot_path.stat().st_size > 0
