from datetime import datetime, timezone
import logging
from typing import Any, List, Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from backend.app.config import get_settings
from backend.app.domain.agent import AgentLoopConfig, execute_timesheet_run
from backend.app.domain.models import Run, RunStatus
from backend.app.domain.ports import (
    AgentAdapters,
    IBrowserController,
    IGeminiClient,
    IRunRepository,
    IScreenshotStore,
)
from backend.app.genai_client import GeminiClient, GeminiPingResult
from backend.app.infrastructure.browser_controller_impl import BrowserControllerImpl
from backend.app.infrastructure.gemini_computer_use_client import GeminiComputerUseClient
from backend.app.infrastructure.gemini_client_impl import GeminiClientImpl
from backend.app.infrastructure.gemini_planner_fallback import GeminiPlannerFallbackClient
from backend.app.infrastructure.in_memory_persistence import (
    InMemoryRunRepository,
    InMemoryScreenshotStore,
)
from backend.app.infrastructure.run_repository_firestore import FirestoreRunRepository
from backend.app.infrastructure.screenshot_store_gcs import GcsScreenshotStore
from backend.app.templates.loader import get_timesheet_demo_html


router = APIRouter()
logger = logging.getLogger(__name__)

_run_repo_singleton = InMemoryRunRepository()
_screenshot_store_singleton = InMemoryScreenshotStore(public_url_prefix="/api")
_firestore_run_repo: Optional[IRunRepository] = None
_gcs_screenshot_store: Optional[IScreenshotStore] = None


def get_run_repository() -> IRunRepository:
    settings = get_settings()
    if settings.persistence_backend == "gcp":
        global _firestore_run_repo
        if _firestore_run_repo is None:
            _firestore_run_repo = FirestoreRunRepository()
        return _firestore_run_repo
    return _run_repo_singleton


def get_screenshot_store() -> IScreenshotStore:
    settings = get_settings()
    if settings.persistence_backend == "gcp":
        global _gcs_screenshot_store
        if _gcs_screenshot_store is None:
            _gcs_screenshot_store = GcsScreenshotStore()
        return _gcs_screenshot_store
    return _screenshot_store_singleton


def get_gemini_client() -> IGeminiClient:
    settings = get_settings()
    json_planner = GeminiClientImpl()
    planner_mode = settings.action_planner_mode.strip().lower()
    if planner_mode == "computer_use":
        return GeminiPlannerFallbackClient(
            primary=GeminiComputerUseClient(),
            fallback=json_planner,
        )
    return json_planner


def get_browser_controller() -> IBrowserController:
    settings = get_settings()
    return BrowserControllerImpl(headless=not settings.debug_headful)


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


@router.get("/timesheet-demo", response_class=HTMLResponse)
def timesheet_demo() -> str:
    """
    Modern, professional timesheet demo page for local testing.

    All fields start at zero by default; UI and field styles are kept
    as in the original template. Served from a separate template file.
    """
    return get_timesheet_demo_html()

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
    screenshot_store: IScreenshotStore = Depends(get_screenshot_store),
    gemini: IGeminiClient = Depends(get_gemini_client),
    browser: IBrowserController = Depends(get_browser_controller),
) -> RunTaskStartResponse:
    """
    Start a run in the background and return run_id immediately.

    Uses in-memory persistence for MVP; later will be Firestore/GCS.
    """
    now = datetime.now(tz=timezone.utc)
    planner_mode = get_settings().action_planner_mode.strip().lower()
    run = Run(
        id=str(uuid4()),
        task_type=body.task_type,
        parameters=body.parameters,
        status=RunStatus.PENDING,
        planner_mode=planner_mode,
        created_at=now,
        updated_at=now,
    )
    run_repository.create_run(run)
    logger.info("Selected planner_mode=%s for run_id=%s", planner_mode, run.id)

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


class ConfirmFinalRequest(BaseModel):
    goal: str = Field(..., min_length=1)
    max_iterations: int = 10
    max_failures: int = 5


@router.post("/run-task/{run_id}/confirm-final", response_model=RunTaskStartResponse, status_code=202)
def confirm_final(
    run_id: str,
    body: ConfirmFinalRequest,
    background_tasks: BackgroundTasks,
    run_repository: IRunRepository = Depends(get_run_repository),
    screenshot_store: IScreenshotStore = Depends(get_screenshot_store),
    gemini: IGeminiClient = Depends(get_gemini_client),
    browser: IBrowserController = Depends(get_browser_controller),
) -> RunTaskStartResponse:
    """
    Confirm a guarded final action (e.g. submit).

    Implementation note: the agent loop currently cannot "resume" a paused browser session.
    This endpoint re-runs the loop for the existing run id with allow_submit=True so the
    flow can complete end-to-end for demos and judgeability.
    """
    run = run_repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    if run.status in {RunStatus.RUNNING, RunStatus.SUCCEEDED}:
        logger.info(
            "Ignoring duplicate confirm-final for run_id=%s status=%s",
            run.id,
            run.status.value,
        )
        return RunTaskStartResponse(run_id=run.id, status=run.status)

    run.status = RunStatus.RUNNING
    run.updated_at = datetime.now(tz=timezone.utc)
    run_repository.update_run(run)

    adapters = AgentAdapters(
        gemini=gemini,
        browser=browser,
        run_repository=run_repository,
        screenshot_store=screenshot_store,
    )
    loop_config = AgentLoopConfig(
        max_iterations=body.max_iterations,
        max_failures=body.max_failures,
        allow_submit=True,
    )

    background_tasks.add_task(
        execute_timesheet_run,
        run=run,
        goal=body.goal,
        parameters=run.parameters,
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
    screenshot_store: IScreenshotStore = Depends(get_screenshot_store),
) -> Response:
    """
    Return screenshot bytes for a run step.

    Works in both persistence modes:
    - in_memory: served from InMemoryScreenshotStore
    - gcp: fetched from GCS via GcsScreenshotStore
    """
    data = screenshot_store.get_screenshot(run_id, step_index)
    if data is None:
        raise HTTPException(status_code=404, detail="screenshot not found")
    return Response(content=data, media_type="image/png")

