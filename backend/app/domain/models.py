"""
Domain models for the ScreenPilot agent loop.

Defines action types, run states, and step metadata. Uses Pydantic for
validation and JSON serialization. No external SDK or framework imports.
"""

from enum import Enum
from datetime import datetime, timezone
from typing import Any, Optional


from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
#  ActionType enum
# ---------------------------------------------------------------------------
class ActionType(str, Enum):
    """
    Supported UI action types for the agent.

    - click: Locate and click a button or link.
    - type: Fill an input field with a value.
    - scroll: Scroll the page or a container.
    """

    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"


# ---------------------------------------------------------------------------
#  ActionTarget + Action models
# ---------------------------------------------------------------------------
class ActionTarget(BaseModel):
    """
    Describes the target of an action for Playwright locator resolution.

    type: Kind of element (e.g. text_button, field_label).
    text: Visible text for buttons/links (used with get_by_text).
    label: Label text for form fields (used with get_by_label).
    placeholder: Optional placeholder for input lookup.
    x: Optional x coordinate for scroll or click fallback.
    y: Optional y coordinate for scroll or click fallback.
    """

    type: str = Field(..., description="Element type, e.g. text_button, field_label")
    text: Optional[str] = Field(default=None, description="Visible text for buttons/links")
    label: Optional[str] = Field(default=None, description="Label for form fields")
    placeholder: Optional[str] = Field(default=None, description="Placeholder for inputs")
    x: Optional[int] = Field(default=None, description="Optional x coordinate")
    y: Optional[int] = Field(default=None, description="Optional y coordinate")


class Action(BaseModel):
    """
    A single UI action to be executed by the browser controller.

    action: The kind of action (click, type, scroll).
    target: Where to apply the action (element description).
    value: Required for type actions; the text to fill.
    """

    action: ActionType
    target: ActionTarget
    value: Optional[str] = Field(default=None, description="Required for type action")


# ---------------------------------------------------------------------------
#  RunStatus enum + RunStep model
# ---------------------------------------------------------------------------
class RunStatus(str, Enum):
    """
    Lifecycle status of a run.
    """

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL = "partial"


class StepSeverity(str, Enum):
    """
    Severity of a run step outcome for UI rendering.
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class RunStep(BaseModel):
    """
    A single step in an agent run: one planned action and its outcome.
    """

    index: int = Field(..., ge=0)
    action: Action
    reason: Optional[str] = Field(default=None, description="Short Gemini reasoning snippet")
    evidence: Optional[str] = Field(
        default=None, description="Short visual grounding evidence for the action"
    )
    result: str = Field(..., description="e.g. success, failed: element not found")
    severity: StepSeverity = Field(default=StepSeverity.INFO)
    attempt: Optional[int] = Field(default=None, ge=1)
    screenshot_url: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


# ---------------------------------------------------------------------------
# Substep 1.5: Run model with full metadata fields
# ---------------------------------------------------------------------------
class Run(BaseModel):
    """
    A complete agent run: task parameters, status, and logged steps.
    """

    id: str
    task_type: str = Field(..., description="e.g. fill_timesheet")
    parameters: dict[str, Any] = Field(default_factory=dict)
    status: RunStatus = RunStatus.PENDING
    steps: list[RunStep] = Field(default_factory=list)
    final_screenshot_url: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
