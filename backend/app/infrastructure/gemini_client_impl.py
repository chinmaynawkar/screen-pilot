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
import time

from google.genai.errors import ClientError, ServerError
from pydantic import ValidationError

from backend.app.config import get_settings
from backend.app.domain.models import Action
from backend.app.domain.ports import IGeminiClient


# Default model for planning actions (override via GEMINI_ACTION_MODEL_ID).
DEFAULT_ACTION_MODEL_ID = "gemini-3-flash-preview"


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
        self._model_id = model_id or settings.gemini_action_model_id
        self._fallback_model_id = settings.gemini_action_fallback_model_id

    def plan_actions(
        self,
        goal: str,
        parameters: dict[str, Any],
        screenshot_bytes: bytes,
    ) -> list[Action]:
        prompt = _build_actions_prompt(goal=goal, parameters=parameters)
        screenshot_part = types.Part.from_bytes(data=screenshot_bytes, mime_type="image/png")

        strict_prompt = (
            prompt
            + "\n\nIMPORTANT: Output MUST be valid JSON array only. If unsure, output []."
        )

        # Small retry loop for transient model errors (503) and rate limiting (429).
        # Keep this conservative to avoid long request hangs.
        attempts = 3
        last_exc: Exception | None = None

        for attempt in range(attempts):
            try:
                return self._plan_actions_once(
                    model_id=self._model_id, prompt=prompt, screenshot_part=screenshot_part
                )
            except GeminiParseError:
                # Retry once with stricter prompt (still counts within attempts loop).
                prompt = strict_prompt
                last_exc = None
            except ClientError as exc:
                last_exc = exc
                if getattr(exc, "status_code", None) == 429:
                    # Free-tier rate limits / quota exhaustion. If a fallback model is configured,
                    # try it once before sleeping.
                    if self._fallback_model_id and self._fallback_model_id != self._model_id:
                        try:
                            return self._plan_actions_once(
                                model_id=self._fallback_model_id,
                                prompt=prompt,
                                screenshot_part=screenshot_part,
                            )
                        except Exception as fallback_exc:
                            last_exc = fallback_exc
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise
            except ServerError as exc:
                last_exc = exc
                # 503 spikes are common; wait a bit and retry.
                if getattr(exc, "status_code", None) == 503:
                    # Also attempt fallback model if configured.
                    if self._fallback_model_id and self._fallback_model_id != self._model_id:
                        try:
                            return self._plan_actions_once(
                                model_id=self._fallback_model_id,
                                prompt=prompt,
                                screenshot_part=screenshot_part,
                            )
                        except Exception as fallback_exc:
                            last_exc = fallback_exc
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise

        if last_exc is not None:
            raise last_exc
        raise GeminiParseError("Failed to obtain valid JSON actions from Gemini after retries.")

    def _plan_actions_once(
        self, *, model_id: str, prompt: str, screenshot_part: types.Part
    ) -> list[Action]:
        # The SDK supports a `config` object; we request JSON output explicitly.
        response = self._client.models.generate_content(
            model=model_id,
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

