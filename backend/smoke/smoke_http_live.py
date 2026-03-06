"""
Live HTTP smoke test (hits a running server).

This script talks to a running FastAPI server (uvicorn) over HTTP.

WARNING:
- With current wiring, this will invoke real Gemini + real Playwright unless you
  override dependencies in the running server code.
- Use it when you *want* to validate real integration.

Run:
  BASE_URL=http://127.0.0.1:8000 .venv/bin/python backend/smoke/smoke_http_live.py

References:
- FastAPI BackgroundTasks: https://fastapi.tiangolo.com/tutorial/background-tasks/
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict

import httpx


def _format_step(step: Dict[str, Any]) -> str:
    idx = step.get("index")
    action = step.get("action", {})
    kind = action.get("action")
    target = action.get("target", {}) or {}
    label = target.get("label") or target.get("text") or target.get("type")
    result = step.get("result")
    return f"step {idx}: {kind} -> {label!r} = {result}"


def main() -> int:
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")

    with httpx.Client(timeout=30) as client:
        r = client.post(
            f"{base_url}/api/run-task",
            json={
                "task_type": "fill_timesheet",
                "goal": "Fill weekly timesheet",
                "parameters": {"week_start": "2026-03-02", "hours_per_day": 8},
                "max_iterations": 2,
                "max_failures": 2,
                "allow_submit": False,
            },
        )
        r.raise_for_status()
        run_id = r.json()["run_id"]
        print("Run ID:", run_id)

        # Poll logs briefly
        deadline = time.time() + 60
        last: Dict[str, Any] | None = None
        while time.time() < deadline:
            logs = client.get(f"{base_url}/api/run-task/{run_id}/logs")
            logs.raise_for_status()
            last = logs.json()
            if last.get("status") in ("succeeded", "failed", "partial"):
                break
            time.sleep(1.0)

        if last is None:
            raise RuntimeError("No logs received")

        print("Run status:", last.get("status"))
        steps = last.get("steps", []) or []
        print("Steps:", len(steps))
        for s in steps:
            print("  ", _format_step(s))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

