import { getBaseUrl } from "../api/client";
import type { RunStep } from "../api/types";
import { useEffect, useMemo, useRef, useState } from "react";
import { mapRunStep } from "../lib/runLogViewModel";
import { RunStepCard } from "./RunStepCard";

export interface RunLogListProps {
  steps: RunStep[];
  runId: string | null;
}

/**
 * Resolve step screenshot URL for display.
 * To avoid GCS CORS issues when embedding signed URLs in the page, we always
 * prefer serving screenshots via the backend endpoint:
 *   GET /api/run-task/{runId}/screenshots/{stepIndex}
 */
function getScreenshotUrl(runId: string | null, step: RunStep): string | null {
  const stepUrl = step.screenshot_url;
  if (stepUrl) {
    if (stepUrl.startsWith("http://") || stepUrl.startsWith("https://")) return stepUrl;
    return `${getBaseUrl()}${stepUrl}`;
  }
  if (!runId) return null;
  return `${getBaseUrl()}/api/run-task/${encodeURIComponent(runId)}/screenshots/${step.index}`;
}

export function RunLogList({ steps, runId }: RunLogListProps) {
  const [autoScroll, setAutoScroll] = useState(true);
  const listRef = useRef<HTMLUListElement | null>(null);
  const mappedSteps = useMemo(
    () => steps.map((step) => ({ sourceStep: step, view: mapRunStep(step) })),
    [steps],
  );

  useEffect(() => {
    if (!autoScroll || !listRef.current) return;
    listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [autoScroll, mappedSteps.length]);

  if (steps.length === 0) {
    return (
      <div className="space-y-2">
        <h3 className="text-sm font-medium text-slate-700">Live timeline</h3>
        <p className="rounded-input border border-dashed border-border bg-surface-elevated/50 py-6 text-center text-sm text-muted-text">
          {runId ? "Waiting for steps…" : "Start a run to see steps here."}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-slate-700">Live timeline</h3>
        <label className="flex items-center gap-2 text-xs text-muted-text">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
            className="h-3.5 w-3.5 rounded border-border text-primary focus:ring-primary"
          />
          Auto-scroll
        </label>
      </div>
      <ul ref={listRef} className="max-h-[420px] space-y-2 overflow-y-auto pr-1">
        {mappedSteps.map(({ sourceStep, view }) => {
          const screenshotUrl = getScreenshotUrl(runId, sourceStep);
          return <RunStepCard key={`${view.index}-${view.createdAtLabel}`} step={view} screenshotUrl={screenshotUrl} />;
        })}
      </ul>
    </div>
  );
}
