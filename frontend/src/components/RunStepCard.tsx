import type { RunStepViewModel } from "../lib/runLogViewModel";

export interface RunStepCardProps {
  step: RunStepViewModel;
  screenshotUrl: string | null;
}

function toneClasses(tone: RunStepViewModel["tone"]): string {
  switch (tone) {
    case "error":
      return "border-danger/40 bg-danger-muted/40";
    case "warning":
      return "border-partial/40 bg-partial-muted/35";
    default:
      return "border-border bg-surface";
  }
}

export function RunStepCard({ step, screenshotUrl }: RunStepCardProps) {
  return (
    <li className={`rounded-input border px-3 py-3 shadow-card ${toneClasses(step.tone)}`}>
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-semibold text-slate-800">{step.title}</p>
        <div className="text-right">
          <span className="block text-xs text-muted-text">{step.createdAtLabel}</span>
          <span className="text-[11px] uppercase tracking-wide text-muted-text">
            {step.targetMode === "coordinates" ? "Coordinate target" : "Semantic target"}
          </span>
        </div>
      </div>
      <div className="mt-2 space-y-1.5 text-sm">
        <p>
          <span className="font-medium text-slate-700">Decision:</span>{" "}
          <span className="text-slate-700">{step.reason}</span>
        </p>
        <p>
          <span className="font-medium text-slate-700">Why:</span>{" "}
          <span className="text-muted-text">{step.evidence}</span>
        </p>
        <p>
          <span className="font-medium text-slate-700">Action:</span>{" "}
          <span className="text-slate-700">{step.actionLabel}</span>
        </p>
        <p>
          <span className="font-medium text-slate-700">Outcome:</span>{" "}
          <span className="text-slate-700">{step.outcome}</span>
        </p>
      </div>
      {screenshotUrl && (
        <div className="mt-2 flex items-center gap-2">
          <a
            href={screenshotUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-primary hover:underline"
          >
            Open screenshot
          </a>
          <img
            src={screenshotUrl}
            alt={step.title}
            className="max-h-16 rounded border border-border object-contain"
          />
        </div>
      )}
    </li>
  );
}
