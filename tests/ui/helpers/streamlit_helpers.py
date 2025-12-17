"""
Utility functions for testing Streamlit applications with Playwright.

These helpers provide common, reusable actions and waits that are specific
to how Streamlit renders its components and manages its lifecycle.
"""
from __future__ import annotations

from playwright.sync_api import Page, expect


def wait_for_streamlit_rerun(page: Page, timeout: int = 15000):
    """
    Waits for the Streamlit app to finish its execution/rerun cycle.

    Streamlit displays a "Running..." or status widget in the top-right corner
    while processing. This function waits for that indicator to disappear.

    Args:
        page: The Playwright Page object.
        timeout: Maximum time to wait in milliseconds.
    """
    status_widget = page.locator('[data-testid="stStatusWidget"]')

    # Expect the status widget to appear first, indicating a rerun has started.
    try:
        expect(status_widget).to_be_visible(timeout=timeout / 2)
    except AssertionError:
        # If it never appears, the app might be static or finished before we checked.
        # This is not necessarily an error, so we can proceed.
        pass

    # Now, expect the status widget to disappear, indicating the rerun is complete.
    expect(status_widget).to_be_hidden(timeout=timeout)


def get_metric_value(page: Page, label: str) -> str:
    """
    Extracts the value from a Streamlit metric container given its label.

    Args:
        page: The Playwright Page object.
        label: The text label of the metric to find.

    Returns:
        The string value of the metric.
    """
    metric_container = page.locator('[data-testid="metric-container"]', has_text=label)
    metric_value = metric_container.locator('div').nth(1)
    return metric_value.inner_text()
