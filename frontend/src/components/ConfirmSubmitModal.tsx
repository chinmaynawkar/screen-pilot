export interface ConfirmSubmitModalProps {
  open: boolean;
  runId: string | null;
  stepCount: number;
  screenshotUrl: string | null;
  isConfirming?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * Shown when the run ended with status partial and the last step indicates
 * "pending_confirmation: submit requested". Lets the user confirm or cancel
 * before a future backend confirm endpoint would be called.
 * See backend/app/domain/agent.py: result="pending_confirmation: submit requested"
 */
export function ConfirmSubmitModal({
  open,
  runId,
  stepCount,
  screenshotUrl,
  isConfirming = false,
  onConfirm,
  onCancel,
}: ConfirmSubmitModalProps) {
  if (!open) return null;

  const shortRunId = runId ? runId.slice(0, 8) : "n/a";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-submit-title"
    >
      <div className="w-full max-w-md rounded-card border border-border bg-surface p-5 shadow-card">
        <h2
          id="confirm-submit-title"
          className="text-base font-semibold text-slate-800"
        >
          Ready to submit
        </h2>
        <p className="mt-2 text-sm text-muted-text">
          ScreenPilot is ready to submit your timesheet. This is an irreversible action.
          Review the latest screenshot and confirm only if it looks correct.
        </p>
        <div className="mt-3 rounded-input border border-border bg-surface-elevated p-3">
          <p className="text-xs text-muted-text">Run #{shortRunId}</p>
          <p className="text-xs text-muted-text">Steps completed: {stepCount}</p>
          {screenshotUrl ? (
            <img
              src={screenshotUrl}
              alt="Latest run screenshot before submit"
              className="mt-2 max-h-36 w-full rounded border border-border object-contain"
            />
          ) : (
            <p className="mt-2 text-xs text-muted-text">Latest screenshot unavailable.</p>
          )}
        </div>
        <div className="mt-4 flex gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={isConfirming}
            className="flex-1 rounded-input border border-border bg-surface-elevated px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-surface-muted focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isConfirming}
            className="flex-1 rounded-input bg-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          >
            {isConfirming ? "Confirming..." : "Confirm submit"}
          </button>
        </div>
      </div>
    </div>
  );
}
