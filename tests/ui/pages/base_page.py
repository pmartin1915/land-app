"""
Base Page Object for the Streamlit application.

This class provides a foundation for all other page objects. It contains
common methods for interacting with web elements, especially those specific
to Streamlit's component library, ensuring reusable and maintainable test code.
"""
from __future__ import annotations

from typing import List, Dict

from playwright.sync_api import Page, Locator, expect

from tests.ui.helpers.streamlit_helpers import wait_for_streamlit_rerun


class BasePage:
    """Base class for all Page Objects, providing common functionalities."""

    def __init__(self, page: Page):
        """
        Initializes the BasePage with a Playwright Page instance.

        Args:
            page: The Playwright Page object to interact with.
        """
        self.page = page

    def goto(self, url: str, wait_until: str = "networkidle"):
        """Navigates to a specific URL."""
        self.page.goto(url, wait_until=wait_until)
        self.wait_for_app_load()

    def wait_for_app_load(self, timeout: int = 20000):
        """Waits for the main Streamlit app container to be visible."""
        expect(self.page.locator("div[data-testid='stAppViewContainer']")).to_be_visible(timeout=timeout)

    def wait_for_rerun(self, timeout: int = 15000):
        """Waits for a Streamlit rerun cycle to complete."""
        wait_for_streamlit_rerun(self.page, timeout)

    def get_title(self) -> str:
        """Returns the title of the current page."""
        return self.page.title()

    def click_button(self, text: str, exact: bool = True):
        """Finds and clicks a button by its visible text."""
        self.page.get_by_role("button", name=text, exact=exact).click()
        self.wait_for_rerun()

    def fill_input_by_label(self, label: str, text: str):
        """Fills a text input field identified by its label."""
        self.page.get_by_label(label).fill(text)

    def get_text(self, locator: str) -> str:
        """Gets the inner text of an element found by a selector."""
        return self.page.locator(locator).inner_text()

    def is_visible(self, locator: str) -> bool:
        """Checks if an element is visible on the page."""
        return self.page.locator(locator).is_visible()

    def select_from_selectbox(self, label_text: str, option_text: str):
        """Selects an option from a Streamlit selectbox by its text."""
        self.page.get_by_label(label_text).click()  # Open the dropdown
        self.page.get_by_role("option", name=option_text).click()
        self.wait_for_rerun()

    def check_checkbox(self, label: str):
        """Checks a checkbox identified by its label."""
        self.page.get_by_label(label).check()
        self.wait_for_rerun()

    def uncheck_checkbox(self, label: str):
        """Unchecks a checkbox identified by its label."""
        self.page.get_by_label(label).uncheck()
        self.wait_for_rerun()

    def take_screenshot(self, path: str, full_page: bool = True):
        """Takes a screenshot of the page."""
        self.page.screenshot(path=path, full_page=full_page)

    def expect_toast_message(self, text: str, timeout: int = 5000):
        """Waits for and asserts a Streamlit toast message."""
        toast = self.page.locator('[data-testid="stToast"]')
        expect(toast).to_be_visible(timeout=timeout)
        expect(toast).to_have_text(text)

    def wait_for_element(self, locator: str, timeout: int = 10000) -> Locator:
        """Waits for an element to be attached to the DOM and returns it."""
        element = self.page.locator(locator)
        element.wait_for(state="attached", timeout=timeout)
        return element

    def expect_element_to_have_text(self, locator: str, text: str, timeout: int = 5000):
        """Asserts that an element contains the specified text."""
        element = self.wait_for_element(locator, timeout)
        expect(element).to_have_text(text)

    def get_attribute(self, locator: str, attribute: str) -> str | None:
        """Gets a specific attribute from an element."""
        return self.page.locator(locator).get_attribute(attribute)

    def scroll_to_element(self, locator: str):
        """Scrolls the page to bring the specified element into view."""
        self.page.locator(locator).scroll_into_view_if_needed()

    def hover_element(self, locator: str):
        """Hovers the mouse cursor over an element."""
        self.page.locator(locator).hover()
