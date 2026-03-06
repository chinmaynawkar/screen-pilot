"""
Concrete IBrowserController implementation using Playwright.

Launches Chromium, navigates to the timesheet demo URL, captures screenshots,
and executes actions (click, type, scroll) via Playwright locators.
"""

from __future__ import annotations

import logging
from typing import Optional

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from backend.app.config import get_settings
from backend.app.domain.models import Action, ActionType
from backend.app.domain.ports import IBrowserController

logger = logging.getLogger(__name__)

# Default timeout for Playwright actions (ms).
DEFAULT_TIMEOUT_MS = 10_000


class BrowserControllerImpl(IBrowserController):
    """
    IBrowserController implementation backed by Playwright sync API.

    Uses Chromium with flags suitable for local dev; Cloud Run flags can be
    added later (e.g. --no-sandbox, --disable-dev-shm-usage).
    """

    def __init__(self, headless: bool = True) -> None:
        """
        Initialize the BrowserControllerImpl.

        Args:
            headless (bool): Whether to run the browser in headless mode. Defaults to True.

        Loads settings and prepares uninitialized Playwright/browser handles.
        """
        settings = get_settings()
        self._timesheet_url = settings.timesheet_url
        self._headless = headless
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    def open_timesheet_page(self) -> None:
        """
        Launch Chromium, create a browser context and page, and navigate to the timesheet URL.

        Raises:
            Any exceptions from Playwright or navigation logic.
        """
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self._headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
            ],
        )
        self._context = self._browser.new_context()
        self._page = self._context.new_page()
        self._page.set_default_timeout(DEFAULT_TIMEOUT_MS)
        self._page.goto(self._timesheet_url, wait_until="domcontentloaded")
        logger.info("Opened timesheet page: %s", self._timesheet_url)

    def take_screenshot(self) -> bytes:
        """
        Capture a screenshot of the current browser viewport.

        Returns:
            bytes: PNG bytes of the screenshot.

        Raises:
            RuntimeError: If the browser/page is not open.
        """
        if self._page is None:
            raise RuntimeError("Browser not opened; call open_timesheet_page() first.")
        return self._page.screenshot(type="png")

    def execute_actions(self, actions: list[Action]) -> list[str]:
        """
        Execute a list of UI Actions using Playwright and return result strings.

        Args:
            actions (list[Action]): List of user interface actions to perform.

        Returns:
            list[str]: Results for each action, e.g., "ok", "failed: <reason>".

        Raises:
            RuntimeError: If the browser/page is not open.
        """
        if self._page is None:
            raise RuntimeError("Browser not opened; call open_timesheet_page() first.")

        results: list[str] = []
        for action in actions:
            result = self._execute_one(action)
            results.append(result)
        return results

    def _execute_one(self, action: Action) -> str:
        """
        Execute a single Action and return the result as a string.

        Args:
            action (Action): The action to execute.

        Returns:
            str: "ok" on success, or an error message on failure.
        """
        try:
            if action.action == ActionType.CLICK:
                return self._do_click(action)
            if action.action == ActionType.TYPE:
                return self._do_type(action)
            if action.action == ActionType.SCROLL:
                return self._do_scroll(action)
            return f"failed: unknown action type {action.action}"
        except Exception as exc:
            return f"failed: {exc}"

    def _do_click(self, action: Action) -> str:
        """
        Perform a click action on the target element.

        Args:
            action (Action): The Action containing click info.

        Returns:
            str: "ok" if click successful, or error string otherwise.
        """
        target = action.target
        if target.text:
            locator = self._page.get_by_text(target.text, exact=False)
        elif target.label:
            locator = self._page.get_by_label(target.label)
        else:
            return "failed: click target needs text or label"
        locator.first.click()
        return "ok"

    def _do_type(self, action: Action) -> str:
        """
        Perform a type (fill) action on the target input element.

        Args:
            action (Action): The Action containing type info.

        Returns:
            str: "ok" if typing successful, or error string otherwise.
        """
        if action.value is None:
            return "failed: type action requires value"
        target = action.target
        if target.label:
            locator = self._page.get_by_label(target.label)
        elif target.placeholder:
            locator = self._page.get_by_placeholder(target.placeholder)
        elif target.text:
            locator = self._page.get_by_text(target.text, exact=False)
        else:
            return "failed: type target needs label, placeholder, or text"
        locator.first.fill(action.value)
        return "ok"

    def _do_scroll(self, action: Action) -> str:
        """
        Perform a scroll action on the page.

        Args:
            action (Action): The Action containing scroll info.

        Returns:
            str: "ok" if scrolling is successful.
        """
        target = action.target
        if target.x is not None and target.y is not None:
            self._page.mouse.wheel(target.x, target.y)
        else:
            self._page.evaluate("window.scrollBy(0, 300)")
        return "ok"

    def close(self) -> None:
        """
        Release all browser, context, and Playwright resources.

        Closes the page, context, browser, and stops Playwright. Safe to call multiple times.
        """
        if self._context:
            self._context.close()
            self._context = None
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
        self._page = None
        logger.info("Browser controller closed")
