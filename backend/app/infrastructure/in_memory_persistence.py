"""
In-memory persistence adapters (local/dev only).

These are used to keep the MVP runnable without Firestore/GCS.
They are NOT suitable for Cloud Run multi-instance deployments.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Dict, Optional, Tuple

from backend.app.domain.models import Run, RunStep
from backend.app.domain.ports import IRunRepository, IScreenshotStore


class InMemoryRunRepository(IRunRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._runs: Dict[str, Run] = {}

    def create_run(self, run: Run) -> Run:
        with self._lock:
            self._runs[run.id] = run
            return run

    def update_run(self, run: Run) -> Run:
        with self._lock:
            self._runs[run.id] = run
            return run

    def append_step(self, run_id: str, step: RunStep) -> None:
        # The domain agent loop already appends to run.steps.
        # This method exists to support repositories that persist steps separately.
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return
            if run.steps and run.steps[-1].index == step.index:
                return
            run.steps.append(step)

    def get_run(self, run_id: str) -> Optional[Run]:
        with self._lock:
            return self._runs.get(run_id)


@dataclass(frozen=True)
class ScreenshotKey:
    run_id: str
    step_index: int


class InMemoryScreenshotStore(IScreenshotStore):
    """
    Stores screenshots in memory and returns a stable API URL.
    """

    def __init__(self, public_url_prefix: str = "/api") -> None:
        self._lock = Lock()
        self._images: Dict[Tuple[str, int], bytes] = {}
        self._public_url_prefix = public_url_prefix.rstrip("/")

    def save_screenshot(self, run_id: str, step_index: int, data: bytes) -> str:
        with self._lock:
            self._images[(run_id, step_index)] = data
        return f"{self._public_url_prefix}/run-task/{run_id}/screenshots/{step_index}"

    def get_screenshot(self, run_id: str, step_index: int) -> Optional[bytes]:
        with self._lock:
            return self._images.get((run_id, step_index))

