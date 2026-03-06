"""
In-process API smoke test (no external services).

Runs the FastAPI app using TestClient with dependency overrides so we don't hit:
- real Gemini API calls
- real Playwright browser automation

This validates:
- routing and request/response schemas
- BackgroundTasks wiring
- in-memory run repository + screenshot store endpoints

Run:
  .venv/bin/python backend/smoke/smoke_api_inprocess.py

References:
- FastAPI Testing: https://fastapi.tiangolo.com/tutorial/testing/
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient


# Ensure repo root is on sys.path so `import backend.*` works.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    from backend.app.main import app
    from backend.app.api import routes
    from backend.app.domain.models import Action

    class FakeGemini:
        def plan_actions(self, goal, parameters, screenshot_bytes):
            # Always asks to submit, so agent loop should pause for confirmation (PARTIAL).
            return [
                Action.model_validate(
                    {"action": "click", "target": {"type": "text_button", "text": "Submit"}}
                )
            ]

    class FakeBrowser:
        def open_timesheet_page(self) -> None:
            return None

        def take_screenshot(self) -> bytes:
            return b"\x89PNG\r\n\x1a\n" + b"fake"

        def execute_actions(self, actions):
            return ["ok" for _ in actions]

        def close(self) -> None:
            return None

    app.dependency_overrides[routes.get_gemini_client] = lambda: FakeGemini()
    app.dependency_overrides[routes.get_browser_controller] = lambda: FakeBrowser()

    client = TestClient(app)

    # 1) Start run
    r = client.post(
        "/api/run-task",
        json={
            "task_type": "fill_timesheet",
            "goal": "Fill weekly timesheet",
            "parameters": {"week_start": "2026-03-02", "hours_per_day": 8},
            "max_iterations": 2,
            "max_failures": 2,
            "allow_submit": False,
        },
    )
    assert r.status_code == 202, r.text
    run_id = r.json()["run_id"]

    # 2) Fetch logs
    logs = client.get(f"/api/run-task/{run_id}/logs")
    assert logs.status_code == 200, logs.text
    run = logs.json()
    assert run["id"] == run_id

    # Because we always propose Submit and allow_submit=False, we should be PARTIAL.
    assert run["status"] == "partial", run
    assert run["steps"], "Expected at least one step recorded"

    # 3) Screenshot endpoint (step 0)
    img = client.get(f"/api/run-task/{run_id}/screenshots/0")
    assert img.status_code == 200, img.text
    assert img.headers["content-type"].startswith("image/png")

    print("OK: in-process API smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

