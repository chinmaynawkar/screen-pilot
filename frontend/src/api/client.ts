/**
 * Typed API client for the ScreenPilot backend.
 * All HTTP lives here; components call startRun() and getRun() only.
 */

import type { Run, StartRunPayload, StartRunResponse } from "./types";

const DEFAULT_BASE_URL = "http://127.0.0.1:8000";

/** Base URL of the backend (for building screenshot URLs in in_memory mode). */
export function getBaseUrl(): string {
  const env = import.meta.env?.VITE_BACKEND_BASE_URL;
  if (typeof env === "string" && env.trim() !== "") {
    return env.trim().replace(/\/$/, "");
  }
  return DEFAULT_BASE_URL;
}

export interface ApiError {
  status: number;
  message: string;
}

async function parseJson<T>(res: Response): Promise<T> {
  const text = await res.text();
  if (text.length === 0) {
    throw { status: res.status, message: "Empty response" } satisfies ApiError;
  }
  try {
    return JSON.parse(text) as T;
  } catch {
    throw {
      status: res.status,
      message: `Invalid JSON: ${text.slice(0, 100)}`,
    } satisfies ApiError;
  }
}

/**
 * Start a run. Returns run_id and status on 202; throws ApiError on non-2xx.
 */
export async function startRun(
  payload: StartRunPayload,
): Promise<StartRunResponse> {
  const base = getBaseUrl();
  const res = await fetch(`${base}/api/run-task`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      task_type: payload.task_type ?? "fill_timesheet",
      goal: payload.goal ?? "Fill weekly timesheet",
      parameters: payload.parameters ?? {},
      max_iterations: payload.max_iterations ?? 10,
      max_failures: payload.max_failures ?? 5,
      allow_submit: payload.allow_submit ?? false,
    }),
  });

  if (res.status === 202) {
    return parseJson<StartRunResponse>(res);
  }

  const err = await parseJson<{ detail?: string }>(res).catch(() => ({
    detail: res.statusText,
  }));
  throw {
    status: res.status,
    message: typeof err.detail === "string" ? err.detail : res.statusText,
  } satisfies ApiError;
}

/**
 * Fetch run (logs and steps). Throws ApiError on 404 or other errors.
 */
export async function getRun(runId: string): Promise<Run> {
  const base = getBaseUrl();
  const res = await fetch(`${base}/api/run-task/${encodeURIComponent(runId)}/logs`);

  if (res.ok) {
    return parseJson<Run>(res);
  }

  if (res.status === 404) {
    throw { status: 404, message: "Run not found" } satisfies ApiError;
  }

  const err = await parseJson<{ detail?: string }>(res).catch(() => ({
    detail: res.statusText,
  }));
  throw {
    status: res.status,
    message: typeof err.detail === "string" ? err.detail : res.statusText,
  } satisfies ApiError;
}

/**
 * Confirm a guarded final action (e.g. submit) for an existing run.
 */
export async function confirmFinal(
  runId: string,
  goal: string,
): Promise<StartRunResponse> {
  const base = getBaseUrl();
  const res = await fetch(
    `${base}/api/run-task/${encodeURIComponent(runId)}/confirm-final`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal }),
    },
  );

  if (res.status === 202) {
    return parseJson<StartRunResponse>(res);
  }

  const err = await parseJson<{ detail?: string }>(res).catch(() => ({
    detail: res.statusText,
  }));
  throw {
    status: res.status,
    message: typeof err.detail === "string" ? err.detail : res.statusText,
  } satisfies ApiError;
}
