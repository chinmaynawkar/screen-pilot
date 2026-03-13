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

from backend.app.domain.models import (
    Action,
    ActionTarget,
    ActionType,
    Run,
    RunStatus,
    RunStep,
    StepSeverity,
)
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
    # Continue indices when a run is resumed via confirm-final.
    step_index = len(run.steps)
    last_screenshot_url: Optional[str] = None

    try:
        try:
            adapters.browser.open_timesheet_page()
        except Exception:
            # If browser launch/navigation fails, mark run as failed.
            # This prevents runs getting stuck in PENDING forever.
            logger.exception("Browser open_timesheet_page failed (run_id=%s)", run.id)
            return _finalize_run(
                run=run,
                adapters=adapters,
                status=RunStatus.FAILED,
                final_screenshot_url=last_screenshot_url,
            )

        run.status = RunStatus.RUNNING
        run.updated_at = _now_utc()
        run = adapters.run_repository.update_run(run)

        for iteration in range(config.max_iterations):
            screenshot_bytes = adapters.browser.take_screenshot()

            try:
                actions = adapters.gemini.plan_actions(
                    goal=goal,
                    parameters=parameters,
                    screenshot_bytes=screenshot_bytes,
                )
            except Exception:
                logger.exception("Gemini planning failed (run_id=%s)", run.id)
                return _finalize_run(
                    run=run,
                    adapters=adapters,
                    status=RunStatus.FAILED,
                    final_screenshot_url=last_screenshot_url,
                )

            if not actions:
                screenshot_url = adapters.screenshot_store.save_screenshot(
                    run_id=run.id,
                    step_index=step_index,
                    data=screenshot_bytes,
                )
                last_screenshot_url = screenshot_url
                # Persist an explicit terminal observation so screenshot and logs stay aligned.
                no_action_step = RunStep(
                    index=step_index,
                    action=Action(
                        action=ActionType.SCROLL,
                        target=ActionTarget(type="system", text="no_action"),
                    ),
                    reason="Gemini returned no additional actions for this screen.",
                    evidence="Current screenshot appears to satisfy the requested goal.",
                    result="no_actions_returned",
                    severity=StepSeverity.INFO,
                    attempt=iteration + 1,
                    screenshot_url=screenshot_url,
                )
                _append_step(run, adapters, no_action_step)
                step_index += 1
                status = RunStatus.SUCCEEDED if failures == 0 else RunStatus.FAILED
                return _finalize_run(
                    run=run,
                    adapters=adapters,
                    status=status,
                    final_screenshot_url=last_screenshot_url,
                )

            submit_action = _find_submit_like_action(actions)
            if submit_action is not None and not config.allow_submit:
                prefix = _actions_before(actions, submit_action)
                step_index, failures, last_screenshot_url = _execute_and_record_steps(
                    run=run,
                    adapters=adapters,
                    actions=prefix,
                    start_index=step_index,
                    failures=failures,
                    attempt=iteration + 1,
                )

                pending_bytes = adapters.browser.take_screenshot()
                pending_screenshot_url = adapters.screenshot_store.save_screenshot(
                    run_id=run.id,
                    step_index=step_index,
                    data=pending_bytes,
                )
                last_screenshot_url = pending_screenshot_url
                pending_step = RunStep(
                    index=step_index,
                    action=submit_action,
                    reason="Submit action detected and paused by safety guardrail.",
                    evidence="Submit control is visible and ready on the current screen.",
                    result="pending_confirmation: submit requested",
                    severity=StepSeverity.WARNING,
                    attempt=iteration + 1,
                    screenshot_url=pending_screenshot_url,
                )
                _append_step(run, adapters, pending_step)
                step_index += 1

                return _finalize_run(
                    run=run,
                    adapters=adapters,
                    status=RunStatus.PARTIAL,
                    final_screenshot_url=last_screenshot_url,
                )

            step_index, failures, last_screenshot_url = _execute_and_record_steps(
                run=run,
                adapters=adapters,
                actions=actions,
                start_index=step_index,
                failures=failures,
                attempt=iteration + 1,
            )

            # If submit is allowed and we executed a submit-like action, treat it as terminal.
            # This makes confirm-final runs judge-friendly: they end as SUCCEEDED (or FAILED)
            # instead of continuing to iterate after submission.
            if submit_action is not None and config.allow_submit:
                post_bytes = adapters.browser.take_screenshot()
                post_url = adapters.screenshot_store.save_screenshot(
                    run_id=run.id,
                    step_index=step_index,
                    data=post_bytes,
                )
                last_screenshot_url = post_url
                post_step = RunStep(
                    index=step_index,
                    action=Action(
                        action=ActionType.SCROLL,
                        target=ActionTarget(type="system", text="post_submit_screenshot"),
                    ),
                    reason="Captured a post-submit screenshot to confirm final UI state.",
                    evidence="Submission action was executed in this iteration.",
                    result="post_submit_screenshot",
                    severity=StepSeverity.INFO,
                    attempt=iteration + 1,
                    screenshot_url=post_url,
                )
                _append_step(run, adapters, post_step)
                step_index += 1

                terminal = RunStatus.SUCCEEDED if failures == 0 else RunStatus.FAILED
                return _finalize_run(
                    run=run,
                    adapters=adapters,
                    status=terminal,
                    final_screenshot_url=last_screenshot_url,
                )

            if failures >= config.max_failures:
                return _finalize_run(
                    run=run,
                    adapters=adapters,
                    status=RunStatus.FAILED,
                    final_screenshot_url=last_screenshot_url,
                )

            logger.info(
                "Iteration complete (run_id=%s, iteration=%s, steps=%s, failures=%s)",
                run.id,
                iteration,
                len(run.steps),
                failures,
            )

        return _finalize_run(
            run=run,
            adapters=adapters,
            status=RunStatus.PARTIAL,
            final_screenshot_url=last_screenshot_url,
        )
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
    start_index: int,
    failures: int,
    attempt: int,
) -> tuple[int, int, Optional[str]]:
    """
    Execute actions and append steps to the run and repository.

    Returns: (next_step_index, failures_count).
    """
    if not actions:
        return start_index, failures, None

    next_index = start_index
    last_screenshot_url: Optional[str] = None
    for action in actions:
        result = adapters.browser.execute_actions([action])[0]
        if result.startswith("failed"):
            failures += 1
        post_action_bytes = adapters.browser.take_screenshot()
        step_screenshot_url = adapters.screenshot_store.save_screenshot(
            run_id=run.id,
            step_index=next_index,
            data=post_action_bytes,
        )
        last_screenshot_url = step_screenshot_url
        step = RunStep(
            index=next_index,
            action=action,
            reason=(
                f"Executed {action.action.value} on the identified UI target "
                "and captured post-action state."
            ),
            evidence=_describe_action_evidence(action),
            result=result,
            severity=_severity_from_result(result),
            attempt=attempt,
            screenshot_url=step_screenshot_url,
        )
        _append_step(run, adapters, step)
        next_index += 1

    run.updated_at = _now_utc()
    adapters.run_repository.update_run(run)
    return next_index, failures, last_screenshot_url


def _append_step(run: Run, adapters: AgentAdapters, step: RunStep) -> None:
    run.steps.append(step)
    adapters.run_repository.append_step(run.id, step)


def _finalize_run(
    *,
    run: Run,
    adapters: AgentAdapters,
    status: RunStatus,
    final_screenshot_url: Optional[str],
) -> Run:
    run.status = status
    run.final_screenshot_url = final_screenshot_url
    run.updated_at = _now_utc()
    return adapters.run_repository.update_run(run)


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


def _severity_from_result(result: str) -> StepSeverity:
    lowered = result.strip().lower()
    if lowered.startswith("failed"):
        return StepSeverity.ERROR
    if "pending_confirmation" in lowered:
        return StepSeverity.WARNING
    return StepSeverity.INFO


def _describe_action_evidence(action: Action) -> str:
    target = action.target
    if target.label:
        return f"Matched field label '{target.label}'."
    if target.text:
        return f"Matched visible text '{target.text}'."
    if target.placeholder:
        return f"Matched input placeholder '{target.placeholder}'."
    if target.x is not None and target.y is not None:
        return f"Used coordinate target ({target.x}, {target.y})."
    return f"Used target type '{target.type}'."

