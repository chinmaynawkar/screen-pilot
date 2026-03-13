"""
Fallback planner wrapper.

Uses primary planner first and falls back to secondary planner on errors.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.domain.models import Action
from backend.app.domain.ports import IGeminiClient

logger = logging.getLogger(__name__)


class GeminiPlannerFallbackClient(IGeminiClient):
    def __init__(self, primary: IGeminiClient, fallback: IGeminiClient) -> None:
        self._primary = primary
        self._fallback = fallback

    def plan_actions(
        self,
        goal: str,
        parameters: dict[str, Any],
        screenshot_bytes: bytes,
    ) -> list[Action]:
        try:
            return self._primary.plan_actions(
                goal=goal,
                parameters=parameters,
                screenshot_bytes=screenshot_bytes,
            )
        except Exception as exc:
            logger.warning(
                "Primary planner failed; falling back to JSON planner. error=%s",
                exc,
            )
            return self._fallback.plan_actions(
                goal=goal,
                parameters=parameters,
                screenshot_bytes=screenshot_bytes,
            )
