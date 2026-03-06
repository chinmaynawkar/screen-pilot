from datetime import datetime, timezone
from typing import Any, List, Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from backend.app.config import get_settings
from backend.app.domain.agent import AgentLoopConfig, execute_timesheet_run
from backend.app.domain.models import Run, RunStatus
from backend.app.domain.ports import AgentAdapters, IBrowserController, IGeminiClient, IRunRepository
from backend.app.genai_client import GeminiClient, GeminiPingResult
from backend.app.infrastructure.browser_controller_impl import BrowserControllerImpl
from backend.app.infrastructure.gemini_client_impl import GeminiClientImpl
from backend.app.infrastructure.in_memory_persistence import (
    InMemoryRunRepository,
    InMemoryScreenshotStore,
)


router = APIRouter()

_run_repo_singleton = InMemoryRunRepository()
_screenshot_store_singleton = InMemoryScreenshotStore(public_url_prefix="/api")


def get_run_repository() -> IRunRepository:
    return _run_repo_singleton


def get_screenshot_store() -> InMemoryScreenshotStore:
    return _screenshot_store_singleton


def get_gemini_client() -> IGeminiClient:
    return GeminiClientImpl()


def get_browser_controller() -> IBrowserController:
    return BrowserControllerImpl(headless=True)


class HealthCheck(BaseModel):
    name: str
    status: Literal["ok", "error"]
    details: Optional[str] = None


class HealthResponse(BaseModel):
    status: Literal["ok", "error"]
    checks: List[HealthCheck]


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """
    Basic health check endpoint.

    Verifies configuration is loaded and, when possible, that the
    GenAI client can be instantiated and a lightweight ping can be
    executed without raising unexpected exceptions.
    """
    checks: list[HealthCheck] = []

    settings = get_settings()

    if settings.gemini_api_key:
        config_status: Literal["ok", "error"] = "ok"
        config_details = "GEMINI_API_KEY configured"
    else:
        config_status = "error"
        config_details = "GEMINI_API_KEY not configured"

    checks.append(
        HealthCheck(
            name="config",
            status=config_status,
            details=config_details,
        )
    )

    if config_status == "ok":
        try:
            client = GeminiClient()
            ping: GeminiPingResult = client.ping_model()
            if ping.ok:
                checks.append(
                    HealthCheck(
                        name="genai_client",
                        status="ok",
                        details=f"model={ping.model_id}",
                    )
                )
            else:
                # Avoid leaking sensitive details, but surface a concise reason.
                truncated_error = (
                    ping.error[:200] if ping.error is not None else "ping_model failed"
                )
                checks.append(
                    HealthCheck(
                        name="genai_client",
                        status="error",
                        details=truncated_error,
                    )
                )
        except Exception:
            checks.append(
                HealthCheck(
                    name="genai_client",
                    status="error",
                    details="exception while initializing or pinging GenAI client",
                )
            )
    else:
        checks.append(
            HealthCheck(
                name="genai_client",
                status="error",
                details="skipped GenAI ping because GEMINI_API_KEY is not configured",
            )
        )

    overall_status: Literal["ok", "error"] = (
        "ok" if all(check.status == "ok" for check in checks) else "error"
    )

    return HealthResponse(status=overall_status, checks=checks)


class RunTaskRequest(BaseModel):
    task_type: str = "fill_timesheet"
    goal: str = "Fill weekly timesheet"
    parameters: dict[str, Any] = Field(default_factory=dict)
    max_iterations: int = 10
    max_failures: int = 5
    allow_submit: bool = False


class RunTaskStartResponse(BaseModel):
    run_id: str
    status: RunStatus


@router.post("/run-task", response_model=RunTaskStartResponse, status_code=202)
def run_task(
    body: RunTaskRequest,
    background_tasks: BackgroundTasks,
    run_repository: IRunRepository = Depends(get_run_repository),
    screenshot_store: InMemoryScreenshotStore = Depends(get_screenshot_store),
    gemini: IGeminiClient = Depends(get_gemini_client),
    browser: IBrowserController = Depends(get_browser_controller),
) -> RunTaskStartResponse:
    """
    Start a run in the background and return run_id immediately.

    Uses in-memory persistence for MVP; later will be Firestore/GCS.
    """
    now = datetime.now(tz=timezone.utc)
    run = Run(
        id=str(uuid4()),
        task_type=body.task_type,
        parameters=body.parameters,
        status=RunStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    run_repository.create_run(run)

    adapters = AgentAdapters(
        gemini=gemini,
        browser=browser,
        run_repository=run_repository,
        screenshot_store=screenshot_store,
    )
    loop_config = AgentLoopConfig(
        max_iterations=body.max_iterations,
        max_failures=body.max_failures,
        allow_submit=body.allow_submit,
    )

    background_tasks.add_task(
        execute_timesheet_run,
        run=run,
        goal=body.goal,
        parameters=body.parameters,
        adapters=adapters,
        config=loop_config,
    )

    return RunTaskStartResponse(run_id=run.id, status=run.status)


@router.get("/run-task/{run_id}/logs", response_model=Run)
def get_run_logs(
    run_id: str,
    run_repository: IRunRepository = Depends(get_run_repository),
) -> Run:
    run = run_repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.get("/run-task/{run_id}/screenshots/{step_index}")
def get_run_screenshot(
    run_id: str,
    step_index: int,
    screenshot_store: InMemoryScreenshotStore = Depends(get_screenshot_store),
) -> Response:
    data = screenshot_store.get_screenshot(run_id, step_index)
    if data is None:
        raise HTTPException(status_code=404, detail="screenshot not found")
    return Response(content=data, media_type="image/png")

