"""
Computer Use planner adapter using the official GenAI tool-calling pattern.

This adapter mirrors the Google web-agent flow:
- send task prompt + current screenshot
- enable Computer Use tool
- read function calls from model response
- map function calls into domain `Action` values for the existing agent loop
"""

from __future__ import annotations

import logging
from typing import Any

from google import genai
from google.genai import types

from backend.app.config import get_settings
from backend.app.domain.models import Action, ActionTarget, ActionType
from backend.app.domain.ports import IGeminiClient

logger = logging.getLogger(__name__)


def _build_computer_use_prompt(goal: str, parameters: dict[str, Any]) -> str:
    return (
        "You are ScreenPilot, a visual UI navigator.\n"
        "Use Computer Use tool calls to complete the task from the screenshot.\n"
        "Prefer precise and grounded targeting.\n\n"
        f"Goal: {goal}\n"
        f"Parameters: {parameters}\n\n"
        "Grounding rules:\n"
        "- Target elements using visible clues from the screenshot.\n"
        "- Use descriptions like 'field under heading', 'button near label', "
        "'checkbox to the left of text' when needed.\n"
        "- If uncertain, avoid guessing; return no action.\n"
        "- Use minimal safe actions that make progress.\n"
    )


class GeminiComputerUseClient(IGeminiClient):
    def __init__(self) -> None:
        settings = get_settings()
        self._model_id = settings.gemini_computer_use_model_id
        self._client = genai.Client(api_key=settings.gemini_api_key or None)

    def plan_actions(
        self,
        goal: str,
        parameters: dict[str, Any],
        screenshot_bytes: bytes,
    ) -> list[Action]:
        prompt = _build_computer_use_prompt(goal=goal, parameters=parameters)
        screenshot = types.Part.from_bytes(data=screenshot_bytes, mime_type="image/png")

        config = types.GenerateContentConfig(
            tools=[
                types.Tool(
                    computer_use=types.ComputerUse(
                        environment=types.Environment.ENVIRONMENT_BROWSER,
                        excluded_predefined_functions=["drag_and_drop"],
                    )
                )
            ]
        )

        response = self._client.models.generate_content(
            model=self._model_id,
            contents=[prompt, screenshot],
            config=config,
        )
        return _response_to_actions(response)


def _response_to_actions(response: Any) -> list[Action]:
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return []
    content = getattr(candidates[0], "content", None)
    parts = getattr(content, "parts", None) or []

    actions: list[Action] = []
    reasoning_snippets: list[str] = []
    for part in parts:
        part_text = getattr(part, "text", None)
        if isinstance(part_text, str) and part_text.strip():
            reasoning_snippets.append(part_text.strip())
        function_call = getattr(part, "function_call", None)
        if function_call is None:
            continue
        actions.extend(_map_function_call(function_call.name, function_call.args or {}))

    if reasoning_snippets:
        logger.info("Computer Use reasoning: %s", " ".join(reasoning_snippets))
    if not actions:
        logger.info("Computer Use returned no executable function calls.")
    return actions


def _map_function_call(name: str, args: dict[str, Any]) -> list[Action]:
    # Some predefined functions (navigate/open browser) are already handled
    # by our own browser controller; we ignore those here.
    if name in {"open_web_browser", "navigate", "go_back", "wait"}:
        return []

    if name == "click_at":
        return [
            Action(
                action=ActionType.CLICK,
                target=ActionTarget(
                    type="computer_use_coordinates",
                    x=_to_int(args.get("x")),
                    y=_to_int(args.get("y")),
                ),
            )
        ]

    if name == "type_text_at":
        text = str(args.get("text", ""))
        press_enter = bool(args.get("press_enter", False))
        return [
            Action(
                action=ActionType.TYPE,
                target=ActionTarget(
                    type="computer_use_coordinates",
                    x=_to_int(args.get("x")),
                    y=_to_int(args.get("y")),
                ),
                value=text,
                press_enter=press_enter,
            )
        ]

    if name in {"scroll", "scroll_down", "scroll_up"}:
        return [
            Action(
                action=ActionType.SCROLL,
                target=ActionTarget(
                    type="computer_use_coordinates",
                    x=_to_int(args.get("x", 0)),
                    y=_to_int(args.get("y", 300 if name != "scroll_up" else -300)),
                ),
            )
        ]

    logger.info("Ignoring unsupported Computer Use function call: %s", name)
    return []


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
