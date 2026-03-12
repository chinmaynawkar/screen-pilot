from fastapi.testclient import TestClient

from backend.app.domain.models import Action
from backend.app.main import app
from backend.app.infrastructure.in_memory_persistence import (
    InMemoryRunRepository,
    InMemoryScreenshotStore,
)


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


def test_run_task_start_and_logs(monkeypatch) -> None:
    # Override dependencies so we don't hit real Gemini/Playwright.
    from backend.app.api import routes
    from backend.app.config import get_settings

    monkeypatch.setenv("PERSISTENCE_BACKEND", "in_memory")
    get_settings.cache_clear()
    run_repo = InMemoryRunRepository()
    screenshot_store = InMemoryScreenshotStore(public_url_prefix="/api")
    app.dependency_overrides[routes.get_gemini_client] = lambda: FakeGemini()
    app.dependency_overrides[routes.get_browser_controller] = lambda: FakeBrowser()
    app.dependency_overrides[routes.get_run_repository] = lambda: run_repo
    app.dependency_overrides[routes.get_screenshot_store] = lambda: screenshot_store

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
    logs_json = logs.json()
    assert logs_json["id"] == run_id
    assert logs_json["status"] == "partial"
    assert len(logs_json["steps"]) == 1
    assert logs_json["steps"][0]["screenshot_url"] == f"/api/run-task/{run_id}/screenshots/0"
    assert logs_json["steps"][0]["severity"] == "warning"
    assert logs_json["steps"][0]["attempt"] == 1
    assert "evidence" in logs_json["steps"][0]

    screenshot = client.get(f"/api/run-task/{run_id}/screenshots/0")
    assert screenshot.status_code == 200
    assert screenshot.content == b"png"
    assert screenshot.headers["content-type"] == "image/png"

    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_confirm_final_starts_background_run(monkeypatch) -> None:
    from backend.app.api import routes
    from backend.app.config import get_settings

    monkeypatch.setenv("PERSISTENCE_BACKEND", "in_memory")
    get_settings.cache_clear()
    run_repo = InMemoryRunRepository()
    screenshot_store = InMemoryScreenshotStore(public_url_prefix="/api")
    app.dependency_overrides[routes.get_gemini_client] = lambda: FakeGemini()
    app.dependency_overrides[routes.get_browser_controller] = lambda: FakeBrowser()
    app.dependency_overrides[routes.get_run_repository] = lambda: run_repo
    app.dependency_overrides[routes.get_screenshot_store] = lambda: screenshot_store

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

    confirm = client.post(
        f"/api/run-task/{run_id}/confirm-final",
        json={"goal": "Fill weekly timesheet"},
    )
    assert confirm.status_code == 202
    assert confirm.json()["run_id"] == run_id

    # BackgroundTasks run after response; fetch logs. With allow_submit=True the loop
    # should terminalize as SUCCEEDED for this fake.
    logs = client.get(f"/api/run-task/{run_id}/logs")
    assert logs.status_code == 200
    assert logs.json()["status"] == "succeeded"

    app.dependency_overrides.clear()
    get_settings.cache_clear()

