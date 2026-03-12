from datetime import datetime, timezone
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
from backend.app.infrastructure.gemini_client_impl import GeminiClientImpl
from backend.app.infrastructure.in_memory_persistence import (
    InMemoryRunRepository,
    InMemoryScreenshotStore,
)
from backend.app.infrastructure.run_repository_firestore import FirestoreRunRepository
from backend.app.infrastructure.screenshot_store_gcs import GcsScreenshotStore


router = APIRouter()

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


@router.get("/timesheet-demo", response_class=HTMLResponse)
def timesheet_demo() -> str:
    """
    Modern, professional timesheet demo page for local testing.

    All fields start at zero by default and UI is cleaner and more modern.
    """
    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>ScreenPilot Timesheet Demo</title>
    <style>
      :root {
        --bg: #101624;
        --card: #181f37;
        --text: #f7fafc;
        --muted: #b8cae2;
        --line: #1e2a44;
        --accent: #53e3c2;
        --danger: #ed6471;
        --shadow: 0 6px 32px rgba(34,38,56,0.15);
        --radius: 18px;
        --input-bg: #202d4a;
        --input-focus: #70f5e4;
        --input-placeholder: #8591ac;
      }
      body {
        margin: 0;
        padding: 0;
        min-height: 100vh;
        font-family: 'Inter', ui-sans-serif, system-ui, Segoe UI, sans-serif;
        background: linear-gradient(135deg, #253055 0%, #142044 100%);
        color: var(--text);
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .wrap {
        max-width: 420px;
        width: 100vw;
        margin: 0 auto;
        padding: 32px 0;
      }
      .header {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        margin-bottom: 28px;
      }
      h1 {
        margin: 0 0 4px 0;
        font-size: 1.45rem;
        font-weight: 700;
        letter-spacing: .3px;
      }
      .hint {
        color: var(--muted);
        font-size: 0.97rem;
        margin-bottom: 2px;
        letter-spacing: 0.05em;
      }
      .badge {
        font-size: 13px;
        padding: 6px 16px;
        border-radius: 24px;
        font-weight: 600;
        background: rgba(83,227,194,0.2);
        color: var(--accent);
        border: 1.5px solid rgba(83,227,194,0.45);
        box-shadow: var(--shadow);
        transition: all 0.2s;
        user-select: none;
      }
      .badge.bad {
        background: rgba(237,100,113,0.12);
        color: var(--danger);
        border-color: rgba(237,100,113,0.28);
      }
      .card {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: var(--radius);
        box-shadow: var(--shadow);
        overflow: hidden;
        transition: box-shadow 0.2s;
      }
      .cardHead {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 18px 22px 10px 22px;
        border-bottom: 1px solid var(--line);
      }
      .status {
        font-size: 14px;
        color: var(--muted);
        letter-spacing: 0.01em;
      }
      .grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 18px 20px;
        padding: 22px;
        background: var(--card);
      }
      label {
        display: block;
        font-size: 13px;
        color: var(--muted);
        margin-bottom: 7px;
        font-weight: 500;
        letter-spacing: 0.04em;
      }
      input {
        width: 100%;
        padding: 10px 14px;
        border-radius: 13px;
        border: 1.5px solid var(--line);
        background: var(--input-bg);
        color: var(--text);
        outline: none;
        font-size: 1rem;
        font-family: inherit;
        font-weight: 500;
        box-shadow: 0 2px 8px rgba(34,38,56,0.03);
        transition: border 0.2s, box-shadow 0.2s;
      }
      input:focus {
        border-color: var(--input-focus);
        box-shadow: 0 0 0 3px rgba(83,227,194,0.12);
        background: #263055;
      }
      input::placeholder {
        color: var(--input-placeholder);
        opacity: 0.38;
      }
      .footer {
        display: flex;
        gap: 14px;
        padding: 20px 22px 18px 22px;
        border-top: 1px solid var(--line);
        align-items: center;
        justify-content: space-between;
        background: var(--card);
      }
      .footer-actions {
        display: flex;
        gap: 12px;
      }
      button {
        border: none;
        background: var(--input-bg);
        color: var(--text);
        padding: 10px 20px;
        border-radius: 11px;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        outline: none;
        transition: background 0.15s, color 0.15s, box-shadow 0.15s;
        border: 1.2px solid var(--line);
        box-shadow: 0 2px 10px rgba(34,38,56,0.09);
      }
      button.primary {
        border-color: var(--accent);
        background: linear-gradient(90deg, #31cfb4 0%, #2ddebd 100%);
        color: #102524;
        box-shadow: 0 2px 12px rgba(83,227,194,0.13);
      }
      button:disabled {
        opacity: .45;
        cursor: not-allowed;
        background: var(--input-bg);
        color: var(--muted);
        border-color: var(--line);
      }
      @media (max-width: 560px) {
        .wrap { max-width: 98vw; }
        .card, .cardHead, .grid, .footer { padding-left: 6vw !important; padding-right: 6vw !important;}
      }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="header">
        <div>
          <h1>Timesheet Demo</h1>
          <div class="hint">Fill hours for each weekday. Submit is disabled until all fields are filled (zero is allowed).</div>
        </div>
        <div id="badge" class="badge bad">Not ready</div>
      </div>
      <div class="card">
        <div class="cardHead">
          <div class="status">Week: <span id="weekLabel">2026‑03‑02</span></div>
          <button id="clearBtn" title="Reset all fields">Clear</button>
        </div>
        <div class="grid">
          <div>
            <label for="mon">Monday hours</label>
            <input id="mon" aria-label="Monday hours" placeholder="0" inputmode="numeric" value="0" min="0" max="24" type="number" />
          </div>
          <div>
            <label for="tue">Tuesday hours</label>
            <input id="tue" aria-label="Tuesday hours" placeholder="0" inputmode="numeric" value="0" min="0" max="24" type="number" />
          </div>
          <div>
            <label for="wed">Wednesday hours</label>
            <input id="wed" aria-label="Wednesday hours" placeholder="0" inputmode="numeric" value="0" min="0" max="24" type="number" />
          </div>
          <div>
            <label for="thu">Thursday hours</label>
            <input id="thu" aria-label="Thursday hours" placeholder="0" inputmode="numeric" value="0" min="0" max="24" type="number" />
          </div>
          <div>
            <label for="fri">Friday hours</label>
            <input id="fri" aria-label="Friday hours" placeholder="0" inputmode="numeric" value="0" min="0" max="24" type="number" />
          </div>
        </div>
        <div class="footer">
          <div class="status" id="statusText">Waiting for input…</div>
          <div class="footer-actions">
            <button id="addBtn" title="Add this entry (demo)">Add Entry</button>
            <button id="submitBtn" class="primary" disabled>Submit</button>
          </div>
        </div>
      </div>
    </div>
    <script>
      // Set up fields and controls
      const ids = ["mon", "tue", "wed", "thu", "fri"];
      const inputs = ids.map(id => document.getElementById(id));
      const submitBtn = document.getElementById("submitBtn");
      const badge = document.getElementById("badge");
      const statusText = document.getElementById("statusText");
      const clearBtn = document.getElementById("clearBtn");
      const addBtn = document.getElementById("addBtn");

      // Modern floating validation: allow zero, require all non-empty & numeric [0-24]
      function allValid() {
        return inputs.every(i => {
          const val = i.value.trim();
          if (val === '') return false;
          const num = Number(val);
          return !isNaN(num) && num >= 0 && num <= 24;
        });
      }

      // Clamp numbers if user enters out of range
      function clampInputs() {
        inputs.forEach(i => {
          let v = Number(i.value);
          if (isNaN(v) || i.value.trim() === "") {
            i.value = "0";
            return;
          }
          if (v < 0) i.value = "0";
          else if (v > 24) i.value = "24";
        });
      }

      function update() {
        clampInputs();
        const ok = allValid();
        submitBtn.disabled = !ok;
        badge.textContent = ok ? "Ready" : "Not ready";
        badge.className = ok ? "badge" : "badge bad";
        statusText.textContent = ok
          ? "All weekdays filled. Ready to submit."
          : "Waiting for valid input…";
      }

      // Initial setup: set all fields to zero
      inputs.forEach(i => { i.value = "0"; });

      // Add event listeners
      inputs.forEach(i => {
        i.addEventListener("input", update);
        i.addEventListener("blur", clampInputs);
      });

      clearBtn.addEventListener("click", () => { 
        inputs.forEach(i => (i.value = "0")); 
        update(); 
      });

      addBtn.addEventListener("click", () => { 
        statusText.textContent = "Entry added (demo)."; 
        setTimeout(update, 1200);
      });

      submitBtn.addEventListener("click", () => { 
        statusText.textContent = "Submitted (demo).";
        setTimeout(update, 1500);
      });

      update();
    </script>
  </body>
</html>"""

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

