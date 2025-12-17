"""
Page Object for the Main Dashboard of the Alabama Auction Watcher.

This class encapsulates the locators and interaction methods for the primary
dashboard view, including filters, summary metrics, the properties table, and tabs.
"""
from __future__ import annotations

from playwright.sync_api import Page, Locator, expect

from tests.ui.pages.base_page import BasePage


class MainDashboardPage(BasePage):
    """Represents the main dashboard page and its components."""

    # --- Locators ---
    HEADER_TITLE = "h1:has-text('Alabama Auction Watcher')"
    SIDEBAR = "section[data-testid='stSidebar']"
    FILTERS_HEADER = "text='FILTERS'"

    # Filters
    PRICE_RANGE_SLIDER = "[data-testid='stSlider'][key='price_range_slider']"
    ACREAGE_RANGE_SLIDER = "[data-testid='stSlider'][key='acreage_range_slider']"
    COUNTY_SELECTOR = "label:has-text('County') + div"
    WATER_ONLY_CHECKBOX = "input[type='checkbox'][aria-label='Show only properties with water features']"

    # Tabs
    DASHBOARD_TAB = "button[role='tab']:has-text('Dashboard')"
    STATEWIDE_COMMAND_TAB = "button[role='tab']:has-text('Statewide Command')"

    # Main Content
    SUMMARY_METRICS_HEADER = "h3:has-text('SUMMARY METRICS')"
    METRIC_CONTAINERS = "[data-testid='metric-container']"
    PROPERTIES_TABLE = "[data-testid='stDataEditor']"
    PROPERTIES_TABLE_ROWS = "[data-testid='stDataEditor'] .data-grid-row"
    EXPORT_CSV_BUTTON = "button:has-text('Export Current View as CSV')"

    def __init__(self, page: Page):
        """Initializes the MainDashboardPage object."""
        super().__init__(page)

    def filter_by_county(self, county: str):
        """
        Selects a county from the county filter dropdown.

        Args:
            county: The name of the county to select.
        """
        self.page.locator(self.COUNTY_SELECTOR).click()
        self.page.get_by_role("option", name=county, exact=True).click()
        self.wait_for_rerun()

    def get_total_properties_metric(self) -> int:
        """
        Retrieves the 'Total Properties' value from the summary metrics.

        Returns:
            The total number of properties as an integer.
        """
        total_props_metric = self.page.locator(self.METRIC_CONTAINERS, has_text="Total Properties")
        value_element = total_props_metric.locator("div").nth(1)
        value_text = value_element.inner_text().replace(",", "")
        return int(value_text)

    def get_table_row_count(self) -> int:
        """
        Gets the number of data rows currently visible in the properties table.

        Returns:
            The count of rows in the table.
        """
        self.wait_for_element(self.PROPERTIES_TABLE)
        # Add a small delay for rows to render after a rerun
        self.page.wait_for_timeout(500)
        return self.page.locator(self.PROPERTIES_TABLE_ROWS).count()

    def navigate_to_tab(self, tab_name: str):
        """
        Clicks on a tab to switch to a different view.

        Args:
            tab_name: The text of the tab to click (e.g., 'Dashboard').
        """
        tab_locator = self.page.locator(f"button[role='tab']:has-text('{tab_name}')")
        tab_locator.click()
        # Navigating tabs may or may not trigger a full rerun, but a small wait is safe
        self.page.wait_for_timeout(500)

    def sort_properties_by(self, sort_option: str):
        """
        Selects a sorting option from the 'Sort By' dropdown.

        Args:
            sort_option: The exact text of the sort option to select.
        """
        self.select_from_selectbox("Sort By", sort_option)

    def verify_dashboard_loaded(self):
        """Asserts that all key components of the main dashboard are visible."""
        expect(self.page.locator(self.HEADER_TITLE)).to_be_visible()
        expect(self.page.locator(self.SIDEBAR)).to_be_visible()
        expect(self.page.locator(self.FILTERS_HEADER)).to_be_visible()
        expect(self.page.locator(self.PROPERTIES_TABLE)).to_be_visible()
        expect(self.page.locator(self.SUMMARY_METRICS_HEADER)).to_be_visible()
