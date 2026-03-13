import type { RunStatus } from "../api/types";

export interface RunStatusPanelProps {
  status: RunStatus | null;
  errorMessage: string | null;
  isRunning?: boolean;
}

function statusLabel(status: RunStatus): string {
  switch (status) {
    case "pending":
      return "Pending";
    case "running":
      return "Running";
    case "succeeded":
      return "Succeeded";
    case "failed":
      return "Failed";
    case "partial":
      return "Partial";
    default:
      return status;
  }
}

function statusPillClasses(status: RunStatus): string {
  const base =
    "inline-flex items-center rounded-pill px-2.5 py-1 text-xs font-medium";
  switch (status) {
    case "pending":
      return `${base} bg-slate-100 text-slate-600`;
    case "running":
      return `${base} bg-primary-muted text-primary`;
    case "succeeded":
      return `${base} bg-success-muted text-success`;
    case "failed":
      return `${base} bg-danger-muted text-danger`;
    case "partial":
      return `${base} bg-partial-muted text-partial`;
    default:
      return `${base} bg-slate-100 text-slate-600`;
  }
}

export function RunStatusPanel({
  status,
  errorMessage,
  isRunning = false,
}: RunStatusPanelProps) {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-slate-700">Status</h3>
      <div className="flex flex-wrap items-center gap-2">
        {status != null ? (
          <span className={statusPillClasses(status)}>
            {statusLabel(status)}
          </span>
        ) : (
          <span className="text-sm text-muted-text">No run yet</span>
        )}
        {isRunning && (
          <span className="inline-flex items-center gap-1.5 text-xs text-muted-text">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
            Live updates active
          </span>
        )}
      </div>
      {status === "partial" && (
        <p className="text-xs text-muted-text">
          Run paused intentionally for confirmation or max-iteration safety guard.
        </p>
      )}
      {errorMessage && (
        <div className="rounded-input bg-danger-muted px-3 py-2 text-sm text-danger">
          {errorMessage}
        </div>
      )}
    </div>
  );
}
