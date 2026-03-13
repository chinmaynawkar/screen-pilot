from datetime import datetime, timezone

from backend.app.domain.models import Action, ActionTarget, ActionType, Run, RunStatus, RunStep
from backend.app.infrastructure.run_repository_firestore import FirestoreRunRepository


def _repo_without_client() -> FirestoreRunRepository:
    # Mapping helpers do not need a live Firestore client.
    return object.__new__(FirestoreRunRepository)


def test_run_mapping_includes_chunk4_fields() -> None:
    repo = _repo_without_client()
    run = Run(
        id="run-1",
        task_type="fill_timesheet",
        parameters={"week": "2026-03-09"},
        status=RunStatus.RUNNING,
        planner_mode="computer_use",
        steps=[],
        final_screenshot_url="https://signed.example/last.png",
        created_at=datetime(2026, 3, 10, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 10, tzinfo=timezone.utc),
    )

    data = repo._run_to_firestore_dict(run)

    assert data["status"] == "running"
    assert data["taskType"] == "fill_timesheet"
    assert data["parameters"] == {"week": "2026-03-09"}
    assert data["plannerMode"] == "computer_use"
    assert data["stepsCount"] == 0
    assert data["finalScreenshotUrl"] == "https://signed.example/last.png"


def test_step_mapping_round_trip_uses_screenshot_url_field() -> None:
    repo = _repo_without_client()
    step = RunStep(
        index=0,
        action=Action(
            action=ActionType.CLICK,
            target=ActionTarget(type="text_button", text="Add Entry"),
        ),
        reason="Click add entry",
        evidence="Matched visible text 'Add Entry'.",
        result="ok",
        severity="info",
        attempt=1,
        screenshot_url="https://signed.example/0.png",
        created_at=datetime(2026, 3, 10, 10, 30, tzinfo=timezone.utc),
    )

    serialized = repo._step_to_firestore_dict(step)
    restored = repo._step_from_firestore_dict(serialized)

    assert serialized["screenshotUrl"] == "https://signed.example/0.png"
    assert serialized["severity"] == "info"
    assert serialized["attempt"] == 1
    assert serialized["evidence"] == "Matched visible text 'Add Entry'."
    assert serialized["action"]["pressEnter"] is False
    assert restored.index == 0
    assert restored.action.action == ActionType.CLICK
    assert restored.action.target.text == "Add Entry"
    assert restored.result == "ok"
    assert restored.severity.value == "info"
    assert restored.attempt == 1
    assert restored.evidence == "Matched visible text 'Add Entry'."
    assert restored.action.press_enter is False
    assert restored.screenshot_url == "https://signed.example/0.png"
