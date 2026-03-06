from fastapi.testclient import TestClient

from backend.app.domain.models import Action
from backend.app.main import app


class FakeGemini:
    def plan_actions(self, goal, parameters, screenshot_bytes):
        # One action, then submit (should trigger PARTIAL unless allow_submit=True)
        return [
            Action.model_validate(
                {"action": "click", "target": {"type": "text_button", "text": "Submit"}}
            )
        ]


class FakeBrowser:
    def open_timesheet_page(self) -> None:
        return None

    def take_screenshot(self) -> bytes:
        return b"png"

    def execute_actions(self, actions):
        return ["ok" for _ in actions]

    def close(self) -> None:
        return None


def test_run_task_start_and_logs() -> None:
    # Override dependencies so we don't hit real Gemini/Playwright.
    from backend.app.api import routes

    app.dependency_overrides[routes.get_gemini_client] = lambda: FakeGemini()
    app.dependency_overrides[routes.get_browser_controller] = lambda: FakeBrowser()

    client = TestClient(app)
    resp = client.post(
        "/api/run-task",
        json={
            "task_type": "fill_timesheet",
            "goal": "Fill weekly timesheet",
            "parameters": {},
            "max_iterations": 2,
            "allow_submit": False,
        },
    )
    assert resp.status_code == 202
    run_id = resp.json()["run_id"]

    # BackgroundTasks run after response; fetch logs.
    logs = client.get(f"/api/run-task/{run_id}/logs")
    assert logs.status_code == 200
    assert logs.json()["id"] == run_id

