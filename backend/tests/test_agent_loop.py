from backend.app.domain.agent import AgentLoopConfig, execute_timesheet_run
from backend.app.domain.models import Action, Run, RunStatus
from backend.app.domain.ports import AgentAdapters


class FakeGemini:
    def __init__(self) -> None:
        self.calls = 0

    def plan_actions(self, goal, parameters, screenshot_bytes):
        self.calls += 1
        if self.calls == 1:
            return [
                Action.model_validate(
                    {
                        "action": "click",
                        "target": {"type": "text_button", "text": "Add"},
                    }
                )
            ]
        return []


class FakeBrowser:
    def open_timesheet_page(self) -> None:
        return None

    def take_screenshot(self) -> bytes:
        return b"png"

    def execute_actions(self, actions):
        return ["ok" for _ in actions]

    def close(self) -> None:
        return None


class FakeRepo:
    def create_run(self, run: Run) -> Run:
        return run

    def update_run(self, run: Run) -> Run:
        return run

    def append_step(self, run_id: str, step) -> None:
        return None

    def get_run(self, run_id: str):
        return None


class FakeStore:
    def save_screenshot(self, run_id: str, step_index: int, data: bytes) -> str:
        return f"mem://{run_id}/{step_index}.png"


def test_execute_timesheet_run_succeeds_when_actions_then_empty() -> None:
    run = Run(id="r1", task_type="fill_timesheet", parameters={})
    adapters = AgentAdapters(
        gemini=FakeGemini(),
        browser=FakeBrowser(),
        run_repository=FakeRepo(),
        screenshot_store=FakeStore(),
    )
    out = execute_timesheet_run(
        run=run,
        goal="fill",
        parameters={},
        adapters=adapters,
        config=AgentLoopConfig(max_iterations=3),
    )
    assert out.status == RunStatus.SUCCEEDED


def test_execute_timesheet_run_fails_if_browser_cannot_start() -> None:
    class FailingBrowser(FakeBrowser):
        def open_timesheet_page(self) -> None:
            raise RuntimeError("browser launch failed")

    run = Run(id="r2", task_type="fill_timesheet", parameters={})
    adapters = AgentAdapters(
        gemini=FakeGemini(),
        browser=FailingBrowser(),
        run_repository=FakeRepo(),
        screenshot_store=FakeStore(),
    )
    out = execute_timesheet_run(run=run, goal="fill", parameters={}, adapters=adapters)
    assert out.status == RunStatus.FAILED

