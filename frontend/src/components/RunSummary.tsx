import type { Run } from "../api/types";

export interface RunSummaryProps {
  run: Run;
}

function formatDuration(run: Run): string {
  const start = new Date(run.created_at).getTime();
  const end = new Date(run.updated_at).getTime();
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) return "n/a";
  const seconds = Math.round((end - start) / 1000);
  return `${seconds}s`;
}

export function RunSummary({ run }: RunSummaryProps) {
  const failedSteps = run.steps.filter((step) => step.result.startsWith("failed")).length;
  const confirmed = run.steps.some((step) => step.result === "post_submit_screenshot");
  const lastStep = run.steps[run.steps.length - 1];

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-slate-700">Run summary</h3>
      <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
        <div className="rounded-input border border-border bg-surface-elevated px-3 py-2">
          <p className="text-xs text-muted-text">Status</p>
          <p className="font-medium capitalize text-slate-800">{run.status}</p>
        </div>
        <div className="rounded-input border border-border bg-surface-elevated px-3 py-2">
          <p className="text-xs text-muted-text">Duration</p>
          <p className="font-medium text-slate-800">{formatDuration(run)}</p>
        </div>
        <div className="rounded-input border border-border bg-surface-elevated px-3 py-2">
          <p className="text-xs text-muted-text">Steps</p>
          <p className="font-medium text-slate-800">{run.steps.length}</p>
        </div>
        <div className="rounded-input border border-border bg-surface-elevated px-3 py-2">
          <p className="text-xs text-muted-text">Failed steps</p>
          <p className="font-medium text-slate-800">{failedSteps}</p>
        </div>
      </div>
      <p className="text-xs text-muted-text">
        Submit confirmation: {confirmed ? "confirmed and executed" : "not confirmed"}
      </p>
      {lastStep && (run.status === "failed" || run.status === "partial") && (
        <p className="rounded-input bg-partial-muted/35 px-3 py-2 text-xs text-slate-700">
          Last blocking result: {lastStep.result}
        </p>
      )}
    </div>
  );
}
