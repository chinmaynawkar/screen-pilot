"""
Core agent loop (domain layer).

This module orchestrates the loop:
1) open browser
2) screenshot
3) plan actions with Gemini
4) execute actions
5) persist steps
6) stop/finalize

It depends only on domain models and ports (no FastAPI / SDK imports).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Optional
from uuid import uuid4

from backend.app.domain.models import Action, ActionTarget, ActionType, Run, RunStatus, RunStep
from backend.app.domain.ports import AgentAdapters

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentLoopConfig:
    """
    Configuration for the agent loop execution.
    """

    max_iterations: int = 10
    max_failures: int = 5
    allow_submit: bool = False


def run_timesheet_task(
    goal: str,
    parameters: dict[str, Any],
    adapters: AgentAdapters,
    *,
    task_type: str = "fill_timesheet",
    config: AgentLoopConfig = AgentLoopConfig(),
) -> Run:
    """
    Run the ScreenPilot agent loop for the timesheet demo task.

    Guardrails:
    - The loop never executes a likely-final \"Submit\" click unless `config.allow_submit` is True.
      Instead, it records a step with result starting with \"pending_confirmation:\" and returns
      with status PARTIAL.
    """

    now = _now_utc()
    run = Run(
        id=str(uuid4()),
        task_type=task_type,
        parameters=parameters,
        status=RunStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    run = adapters.run_repository.create_run(run)
    return execute_timesheet_run(
        run=run,
        goal=goal,
        parameters=parameters,
        adapters=adapters,
        config=config,
    )


def execute_timesheet_run(
    *,
    run: Run,
    goal: str,
    parameters: dict[str, Any],
    adapters: AgentAdapters,
    config: AgentLoopConfig = AgentLoopConfig(),
) -> Run:
    """
    Execute the agent loop for an existing Run.

    This enables API endpoints to create a run immediately (return run_id),
    then continue execution in a background task.
    """

    failures = 0
    step_index = 0

    try:
        adapters.browser.open_timesheet_page()

        run.status = RunStatus.RUNNING
        run.updated_at = _now_utc()
        run = adapters.run_repository.update_run(run)

        for iteration in range(config.max_iterations):
            screenshot_bytes = adapters.browser.take_screenshot()
            screenshot_url = adapters.screenshot_store.save_screenshot(
                run_id=run.id,
                step_index=step_index,
                data=screenshot_bytes,
            )

            try:
                actions = adapters.gemini.plan_actions(
                    goal=goal,
                    parameters=parameters,
                    screenshot_bytes=screenshot_bytes,
                )
            except Exception:
                logger.exception("Gemini planning failed (run_id=%s)", run.id)
                run.status = RunStatus.FAILED
                run.updated_at = _now_utc()
                return adapters.run_repository.update_run(run)

            if not actions:
                if run.steps and failures == 0:
                    run.status = RunStatus.SUCCEEDED
                else:
                    run.status = RunStatus.FAILED
                run.updated_at = _now_utc()
                return adapters.run_repository.update_run(run)

            submit_action = _find_submit_like_action(actions)
            if submit_action is not None and not config.allow_submit:
                prefix = _actions_before(actions, submit_action)
                step_index, failures = _execute_and_record_steps(
                    run=run,
                    adapters=adapters,
                    actions=prefix,
                    screenshot_url=screenshot_url,
                    start_index=step_index,
                    failures=failures,
                )

                pending_step = RunStep(
                    index=step_index,
                    action=submit_action,
                    reason=None,
                    result="pending_confirmation: submit requested",
                    screenshot_url=screenshot_url,
                )
                _append_step(run, adapters, pending_step)
                step_index += 1

                run.status = RunStatus.PARTIAL
                run.updated_at = _now_utc()
                return adapters.run_repository.update_run(run)

            step_index, failures = _execute_and_record_steps(
                run=run,
                adapters=adapters,
                actions=actions,
                screenshot_url=screenshot_url,
                start_index=step_index,
                failures=failures,
            )

            if failures >= config.max_failures:
                run.status = RunStatus.FAILED
                run.updated_at = _now_utc()
                return adapters.run_repository.update_run(run)

            logger.info(
                "Iteration complete (run_id=%s, iteration=%s, steps=%s, failures=%s)",
                run.id,
                iteration,
                len(run.steps),
                failures,
            )

        run.status = RunStatus.PARTIAL
        run.updated_at = _now_utc()
        return adapters.run_repository.update_run(run)
    finally:
        try:
            adapters.browser.close()
        except Exception:
            logger.exception("Failed to close browser (run_id=%s)", run.id)


def _execute_and_record_steps(
    *,
    run: Run,
    adapters: AgentAdapters,
    actions: list[Action],
    screenshot_url: Optional[str],
    start_index: int,
    failures: int,
) -> tuple[int, int]:
    """
    Execute actions and append steps to the run and repository.

    Returns: (next_step_index, failures_count).
    """
    if not actions:
        return start_index, failures

    results = adapters.browser.execute_actions(actions)
    next_index = start_index
    for action, result in zip(actions, results):
        if result.startswith("failed"):
            failures += 1
        step = RunStep(
            index=next_index,
            action=action,
            reason=None,
            result=result,
            screenshot_url=screenshot_url,
        )
        _append_step(run, adapters, step)
        next_index += 1

    run.updated_at = _now_utc()
    adapters.run_repository.update_run(run)
    return next_index, failures


def _append_step(run: Run, adapters: AgentAdapters, step: RunStep) -> None:
    run.steps.append(step)
    adapters.run_repository.append_step(run.id, step)


def _find_submit_like_action(actions: Iterable[Action]) -> Optional[Action]:
    """
    Identify a likely-final submit action.

    We treat any click whose target contains 'submit' (text or label) as submit-like.
    """
    for action in actions:
        if action.action != ActionType.CLICK:
            continue
        text = (action.target.text or "").strip().lower()
        label = (action.target.label or "").strip().lower()
        if "submit" in text or "submit" in label:
            return action
    return None


def _actions_before(actions: list[Action], stop_action: Action) -> list[Action]:
    prefix: list[Action] = []
    for a in actions:
        if a is stop_action:
            break
        prefix.append(a)
    return prefix


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)

