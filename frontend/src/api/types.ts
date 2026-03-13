/**
 * Frontend types mirroring backend Pydantic models (backend/app/domain/models.py)
 * and API request/response (backend/app/api/routes.py).
 */

export type RunStatus =
  | "pending"
  | "running"
  | "succeeded"
  | "failed"
  | "partial";

export type ActionType = "click" | "type" | "scroll";

export interface ActionTarget {
  type: string;
  text?: string | null;
  label?: string | null;
  placeholder?: string | null;
  x?: number | null;
  y?: number | null;
}

export interface Action {
  action: ActionType;
  target: ActionTarget;
  value?: string | null;
  press_enter?: boolean;
}

export interface RunStep {
  index: number;
  action: Action;
  reason?: string | null;
  evidence?: string | null;
  result: string;
  severity?: "info" | "warning" | "error";
  attempt?: number | null;
  screenshot_url?: string | null;
  created_at?: string;
}

export interface Run {
  id: string;
  task_type: string;
  parameters: Record<string, unknown>;
  status: RunStatus;
  planner_mode?: string | null;
  steps: RunStep[];
  final_screenshot_url?: string | null;
  created_at: string;
  updated_at: string;
}

/** Request body for POST /api/run-task (RunTaskRequest). */
export interface StartRunPayload {
  task_type?: string;
  goal?: string;
  parameters?: Record<string, unknown>;
  max_iterations?: number;
  max_failures?: number;
  allow_submit?: boolean;
}

/** Response for POST /api/run-task (202). */
export interface StartRunResponse {
  run_id: string;
  status: RunStatus;
}
