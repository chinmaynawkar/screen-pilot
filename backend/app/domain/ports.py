"""
Ports (interfaces) for external systems.

Pure Python Protocol classes — no concrete SDK or framework imports.
Decouples the agent core from Gemini, Playwright, storage implementations.
"""

from dataclasses import dataclass
from typing import Any, Optional, Protocol

from backend.app.domain.models import Action, Run, RunStep


# ---------------------------------------------------------------------------
#  IGeminiClient protocol
# ---------------------------------------------------------------------------
class IGeminiClient(Protocol):
    """
    Port for calling Gemini to plan UI actions from a screenshot.
    """

    def plan_actions(
        self,
        goal: str,
        parameters: dict[str, Any],
        screenshot_bytes: bytes,
    ) -> list[Action]:
        """
        Given a goal, parameters, and screenshot, return a list of actions.

        Raises on parse/model errors. Implementations may retry internally.
        """
        ...


# ---------------------------------------------------------------------------
# IBrowserController protocol
# ---------------------------------------------------------------------------
class IBrowserController(Protocol):
    """
    Port for browser automation: open page, screenshot, execute actions.
    """

    def open_timesheet_page(self) -> None:
        """Launch browser, navigate to the timesheet demo URL."""
        ...

    def take_screenshot(self) -> bytes:
        """Return PNG bytes of the current viewport."""
        ...

    def execute_actions(self, actions: list[Action]) -> list[str]:
        """
        Execute each action via Playwright; return per-action result strings.

        Results: e.g. "ok", "failed: element not found".
        """
        ...

    def close(self) -> None:
        """Release browser resources. Call when the run is finished."""
        ...


# ---------------------------------------------------------------------------
#  IRunRepository protocol
# ---------------------------------------------------------------------------
class IRunRepository(Protocol):
    """
    Port for persisting and retrieving run metadata and steps.
    """

    def create_run(self, run: Run) -> Run:
        """Persist a new run; return the created run (possibly with server-set fields)."""
        ...

    def update_run(self, run: Run) -> Run:
        """Update an existing run (e.g. status, updated_at)."""
        ...

    def append_step(self, run_id: str, step: RunStep) -> None:
        """Append a step to the run's steps list."""
        ...

    def get_run(self, run_id: str) -> Optional[Run]:
        """Return the run by id, or None if not found."""
        ...


# ---------------------------------------------------------------------------
#  IScreenshotStore protocol
# ---------------------------------------------------------------------------
class IScreenshotStore(Protocol):
    """
    Port for saving screenshot bytes and obtaining a URL.
    """

    def save_screenshot(self, run_id: str, step_index: int, data: bytes) -> str:
        """
        Save screenshot bytes and return a URL (public or semi-public).
        """
        ...

    def get_screenshot(self, run_id: str, step_index: int) -> Optional[bytes]:
        """
        Return screenshot bytes for the given run and step index, or None if not found.

        Used by the API layer to serve screenshots via the backend (avoids browser CORS
        issues when clients cannot load signed URLs directly).
        """
        ...


# ---------------------------------------------------------------------------
# AgentAdapters dataclass
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AgentAdapters:
    """
    Bundles all four ports for injection into the agent loop.
    """

    gemini: IGeminiClient
    browser: IBrowserController
    run_repository: IRunRepository
    screenshot_store: IScreenshotStore
