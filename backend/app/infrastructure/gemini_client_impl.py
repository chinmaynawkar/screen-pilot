"""
Concrete IGeminiClient implementation using the official Google GenAI SDK.

Responsibilities:
- Build a structured prompt using the user goal, parameters, and latest screenshot.
- Call Gemini with JSON response requested for actions.
- Parse the JSON into domain `Action` models, with a single retry on parse failure.
"""

from __future__ import annotations

import json
from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError

from backend.app.config import get_settings
from backend.app.domain.models import Action
from backend.app.domain.ports import IGeminiClient


# Model chosen per docs/agent-loop.md reference.
DEFAULT_ACTION_MODEL_ID = "gemini-2.5-computer-use-preview-10-2025"


class GeminiParseError(Exception):
    """Raised when Gemini does not return valid JSON actions."""


def _build_actions_prompt(goal: str, parameters: dict[str, Any]) -> str:
    params_json = json.dumps(parameters, indent=2, sort_keys=True)
    return (
        "You are a UI navigation assistant called ScreenPilot.\n"
        "You control a browser to complete a specific task on a timesheet web app.\n\n"
        f"User goal:\n{goal}\n\n"
        f"Task parameters (JSON):\n{params_json}\n\n"
        "You are given a screenshot of the current page.\n"
        "You must respond ONLY with a JSON array of actions, no extra text.\n\n"
        "Each action must have this schema:\n"
        "[\n"
        "  {\n"
        "    \"action\": \"click\" | \"type\" | \"scroll\",\n"
        "    \"target\": {\n"
        "      \"type\": \"text_button\" | \"field_label\" | \"other\",\n"
        "      \"text\": \"visible text of button or link\" (optional),\n"
        "      \"label\": \"label text of form field\" (optional),\n"
        "      \"placeholder\": \"input placeholder\" (optional),\n"
        "      \"x\": 0 (optional pixel x coordinate),\n"
        "      \"y\": 0 (optional pixel y coordinate)\n"
        "    },\n"
        "    \"value\": \"text to type (for action = type)\" (optional)\n"
        "  }\n"
        "]\n\n"
        "Rules:\n"
        "- Only emit valid JSON, no comments or trailing commas.\n"
        "- Do not include natural language outside the JSON.\n"
        "- Prefer using labels and visible text over coordinates.\n"
        "- Use as few actions as needed to make progress toward the goal.\n"
    )


class GeminiClientImpl(IGeminiClient):
    def __init__(self, model_id: str = DEFAULT_ACTION_MODEL_ID) -> None:
        settings = get_settings()
        self._client = genai.Client(api_key=settings.gemini_api_key or None)
        self._model_id = model_id

    def plan_actions(
        self,
        goal: str,
        parameters: dict[str, Any],
        screenshot_bytes: bytes,
    ) -> list[Action]:
        prompt = _build_actions_prompt(goal=goal, parameters=parameters)
        screenshot_part = types.Part.from_bytes(data=screenshot_bytes, mime_type="image/png")

        try:
            return self._plan_actions_once(prompt=prompt, screenshot_part=screenshot_part)
        except GeminiParseError:
            strict_prompt = (
                prompt
                + "\n\nIMPORTANT: Output MUST be valid JSON array only. If unsure, output []."
            )
            return self._plan_actions_once(prompt=strict_prompt, screenshot_part=screenshot_part)

    def _plan_actions_once(self, prompt: str, screenshot_part: types.Part) -> list[Action]:
        # The SDK supports a `config` object; we request JSON output explicitly.
        response = self._client.models.generate_content(
            model=self._model_id,
            contents=[prompt, screenshot_part],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )

        raw_text = getattr(response, "text", None)
        if raw_text is None:
            raise GeminiParseError("Gemini response missing text; cannot parse JSON actions.")

        return _parse_actions_json(raw_text)


def _parse_actions_json(raw_text: str) -> list[Action]:
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise GeminiParseError(f"Failed to decode JSON from Gemini: {exc}") from exc

    if not isinstance(data, list):
        raise GeminiParseError("Gemini JSON must be a list of actions.")

    actions: list[Action] = []
    errors: list[str] = []
    for idx, item in enumerate(data):
        try:
            actions.append(Action.model_validate(item))
        except ValidationError as exc:
            errors.append(f"index {idx}: {exc}")

    if errors:
        raise GeminiParseError("One or more actions failed validation: " + "; ".join(errors))

    return actions

