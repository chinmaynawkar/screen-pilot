import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  confirmFinal,
  getBaseUrl,
  getRun,
  startRun,
  type ApiError,
} from "./api/client";
import type { Run, RunStatus } from "./api/types";
import { ConfirmSubmitModal } from "./components/ConfirmSubmitModal";
import { FinalScreenshot } from "./components/FinalScreenshot";
import { RunLogList } from "./components/RunLogList";
import { RunSummary } from "./components/RunSummary";
import { RunStatusPanel } from "./components/RunStatusPanel";
import { TaskSelector } from "./components/TaskSelector";
import {
  TimesheetParametersForm,
  type TimesheetParameters,
} from "./components/TimesheetParametersForm";
import { validateTimesheetForm } from "./lib/validation";

const TERMINAL_STATUSES: RunStatus[] = ["succeeded", "failed", "partial"];
const POLL_INTERVAL_MS = 1500;

function isPendingConfirmation(run: Run): boolean {
  const last = run.steps[run.steps.length - 1];
  return (
    run.status === "partial" &&
    last != null &&
    last.result.startsWith("pending_confirmation:")
  );
}

function App() {
  const [selectedTask, setSelectedTask] = useState("fill_timesheet");
  const [goal, setGoal] = useState("Fill weekly timesheet");
  const [parameters, setParameters] = useState<TimesheetParameters>({
    defaultHours: undefined,
  });
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [currentRun, setCurrentRun] = useState<Run | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [confirmRequestedForRunId, setConfirmRequestedForRunId] = useState<string | null>(null);
  const [pollToken, setPollToken] = useState(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const validation = useMemo(
    () => validateTimesheetForm(goal, parameters),
    [goal, parameters],
  );

  const handleRun = useCallback(async () => {
    if (!validation.valid || isRunning) return;
    setErrorMessage(null);
    setIsRunning(true);
    setCurrentRun(null);
    setConfirmRequestedForRunId(null);
    try {
      const payload = {
        task_type: selectedTask,
        goal: goal.trim(),
        parameters: {
          ...(parameters.weekStart && { week_start: parameters.weekStart }),
          ...(parameters.defaultHours !== undefined && {
            default_hours: parameters.defaultHours,
          }),
        },
      };
      const res = await startRun(payload);
      setCurrentRunId(res.run_id);
    } catch (err) {
      const apiErr = err as ApiError;
      setErrorMessage(apiErr?.message ?? "Failed to start run");
      setIsRunning(false);
    }
  }, [validation.valid, isRunning, selectedTask, goal, parameters]);

  useEffect(() => {
    if (currentRunId == null) return;

    const poll = () => {
      getRun(currentRunId)
        .then((run) => {
          setCurrentRun(run);
          if (TERMINAL_STATUSES.includes(run.status)) {
            if (pollRef.current) {
              clearInterval(pollRef.current);
              pollRef.current = null;
            }
            setIsRunning(false);
            if (
              isPendingConfirmation(run) &&
              confirmRequestedForRunId !== run.id
            ) {
              setShowConfirmModal(true);
            }
          }
        })
        .catch((err: ApiError) => {
          setErrorMessage(err?.message ?? "Failed to fetch run");
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
          setIsRunning(false);
        });
    };

    poll();
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [currentRunId, pollToken, confirmRequestedForRunId]);

  const handleConfirmSubmit = useCallback(async () => {
    if (!currentRunId || isConfirming) return;
    setIsConfirming(true);
    setErrorMessage(null);
    setIsRunning(true);
    setConfirmRequestedForRunId(currentRunId);
    try {
      await confirmFinal(currentRunId, goal.trim());
      setShowConfirmModal(false);
      setPollToken((n) => n + 1);
    } catch (err) {
      const apiErr = err as ApiError;
      setErrorMessage(apiErr?.message ?? "Failed to confirm final action");
      setIsRunning(false);
    } finally {
      setIsConfirming(false);
    }
  }, [currentRunId, goal, isConfirming]);

  const handleCancelConfirm = useCallback(() => {
    setShowConfirmModal(false);
  }, []);

  const finalScreenshotUrl = useMemo(() => {
    if (!currentRunId || !currentRun || currentRun.steps.length === 0) {
      return currentRun?.final_screenshot_url ?? null;
    }
    const last = currentRun.steps[currentRun.steps.length - 1];
    return (
      last.screenshot_url ??
      `/api/run-task/${encodeURIComponent(currentRunId)}/screenshots/${last.index}`
    );
  }, [currentRunId, currentRun]);

  const screenshotUrls = useMemo(() => {
    if (!currentRunId || !currentRun) return [];
    return currentRun.steps.map((step) => ({
      index: step.index,
      url: step.screenshot_url
        ? step.screenshot_url.startsWith("http://") || step.screenshot_url.startsWith("https://")
          ? step.screenshot_url
          : `${getBaseUrl()}${step.screenshot_url}`
        : `${getBaseUrl()}/api/run-task/${encodeURIComponent(currentRunId)}/screenshots/${step.index}`,
    }));
  }, [currentRun, currentRunId]);

  const latestScreenshot = screenshotUrls[screenshotUrls.length - 1] ?? null;
  const failedSteps = useMemo(
    () => (currentRun ? currentRun.steps.filter((step) => step.result.startsWith("failed")).length : 0),
    [currentRun],
  );
  const elapsed = useMemo(() => {
    if (!currentRun) return "n/a";
    const start = new Date(currentRun.created_at).getTime();
    const end = new Date(currentRun.updated_at).getTime();
    if (Number.isNaN(start) || Number.isNaN(end) || end < start) return "n/a";
    return `${Math.round((end - start) / 1000)}s`;
  }, [currentRun]);

  return (
    <div className="min-h-screen bg-surface-muted font-sans">
      <header className="border-b border-border bg-surface shadow-card">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-2">
            <span className="text-lg font-semibold tracking-tight text-slate-800">
              ScreenPilot
            </span>
            <span className="rounded-pill bg-primary-muted px-2 py-0.5 text-xs font-medium text-primary">
              UI Navigator
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <section className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-input border border-border bg-surface px-3 py-2 shadow-card">
            <p className="text-xs text-muted-text">
              Status{currentRun?.planner_mode ? ` (${currentRun.planner_mode})` : ""}
            </p>
            <p className="text-sm font-medium capitalize text-slate-800">
              {currentRun?.status ?? "not started"}
            </p>
          </div>
          <div className="rounded-input border border-border bg-surface px-3 py-2 shadow-card">
            <p className="text-xs text-muted-text">Elapsed</p>
            <p className="text-sm font-medium text-slate-800">{elapsed}</p>
          </div>
          <div className="rounded-input border border-border bg-surface px-3 py-2 shadow-card">
            <p className="text-xs text-muted-text">Total steps</p>
            <p className="text-sm font-medium text-slate-800">{currentRun?.steps.length ?? 0}</p>
          </div>
          <div className="rounded-input border border-border bg-surface px-3 py-2 shadow-card">
            <p className="text-xs text-muted-text">Failures</p>
            <p className="text-sm font-medium text-slate-800">{failedSteps}</p>
          </div>
        </section>

        <div className="grid gap-6 lg:grid-cols-[1fr_1fr] lg:gap-8">
          <section className="space-y-4">
            <div className="rounded-card border border-border bg-surface p-5 shadow-card">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-text">
                Configure run
              </h2>
              <div className="space-y-4">
                <TaskSelector
                  value={selectedTask}
                  onChange={setSelectedTask}
                  disabled={isRunning}
                />
                <TimesheetParametersForm
                  goal={goal}
                  parameters={parameters}
                  onGoalChange={setGoal}
                  onParametersChange={setParameters}
                  disabled={isRunning}
                  errors={validation.errors}
                />
                <div className="pt-2">
                  {!validation.valid && validation.errors.length > 0 && (
                    <p className="mb-2 text-xs text-muted-text">
                      Fix the errors above to run.
                    </p>
                  )}
                  <button
                    type="button"
                    disabled={!validation.valid || isRunning}
                    onClick={handleRun}
                    className="w-full rounded-input bg-primary px-4 py-2.5 text-sm font-medium text-white shadow-card transition hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isRunning ? "Running…" : "Run"}
                  </button>
                </div>
              </div>
            </div>

            <div className="rounded-card border border-border bg-surface p-5 shadow-card">
              <h3 className="mb-2 text-sm font-medium text-slate-700">Live screenshot stage</h3>
              {latestScreenshot ? (
                <div className="space-y-2">
                  <a
                    href={latestScreenshot.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block overflow-hidden rounded-input border border-border"
                  >
                    <img
                      src={latestScreenshot.url}
                      alt={`Current screenshot step ${latestScreenshot.index + 1}`}
                      className="max-h-64 w-full object-contain"
                    />
                  </a>
                  <div className="flex gap-2 overflow-x-auto pb-1">
                    {screenshotUrls.slice(-6).map((item) => (
                      <img
                        key={item.index}
                        src={item.url}
                        alt={`Step ${item.index + 1}`}
                        className="h-14 w-20 shrink-0 rounded border border-border object-cover"
                      />
                    ))}
                  </div>
                </div>
              ) : (
                <p className="rounded-input border border-dashed border-border bg-surface-elevated/40 py-8 text-center text-sm text-muted-text">
                  Start a run to see live screenshots.
                </p>
              )}
            </div>
          </section>

          <section className="space-y-4">
            <div className="rounded-card border border-border bg-surface p-5 shadow-card">
              <RunStatusPanel
                status={currentRun?.status ?? null}
                errorMessage={errorMessage}
                isRunning={isRunning}
              />
            </div>
            <div className="rounded-card border border-border bg-surface p-5 shadow-card">
              <RunLogList
                steps={currentRun?.steps ?? []}
                runId={currentRunId}
              />
            </div>
            {currentRun && TERMINAL_STATUSES.includes(currentRun.status) && (
              <div className="rounded-card border border-border bg-surface p-5 shadow-card">
                <RunSummary run={currentRun} />
              </div>
            )}
            <div className="rounded-card border border-border bg-surface p-5 shadow-card">
              <FinalScreenshot url={finalScreenshotUrl} />
            </div>
          </section>
        </div>
      </main>

      <ConfirmSubmitModal
        open={showConfirmModal}
        runId={currentRunId}
        stepCount={currentRun?.steps.length ?? 0}
        screenshotUrl={latestScreenshot?.url ?? null}
        isConfirming={isConfirming}
        onConfirm={handleConfirmSubmit}
        onCancel={handleCancelConfirm}
      />
    </div>
  );
}

export default App;
