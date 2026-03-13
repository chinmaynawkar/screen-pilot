import type { Action, RunStep } from "../api/types";

export type StepTone = "info" | "warning" | "error";

export interface RunStepViewModel {
  index: number;
  title: string;
  actionLabel: string;
  outcome: string;
  reason: string;
  evidence: string;
  tone: StepTone;
  createdAtLabel: string;
  screenshotStepIndex: number;
  targetMode: "semantic" | "coordinates";
}

function formatTimeLabel(value?: string): string {
  if (!value) return "Unknown time";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown time";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function summarizeTarget(action: Action): string {
  const target = action.target;
  if (target.label) return `label "${target.label}"`;
  if (target.text) return `text "${target.text}"`;
  if (target.placeholder) return `placeholder "${target.placeholder}"`;
  if (target.x != null && target.y != null) return `coordinates (${target.x}, ${target.y})`;
  return `target type "${target.type}"`;
}

function getTargetMode(action: Action): "semantic" | "coordinates" {
  const target = action.target;
  if (target.x != null && target.y != null) return "coordinates";
  return "semantic";
}

function describeAction(action: Action): string {
  switch (action.action) {
    case "click":
      return `Click ${summarizeTarget(action)}.`;
    case "type":
      return `Type "${action.value ?? ""}" into ${summarizeTarget(action)}${action.press_enter ? " and press Enter" : ""}.`;
    case "scroll":
      return `Scroll using ${summarizeTarget(action)}.`;
    default:
      return `Execute ${action.action} on ${summarizeTarget(action)}.`;
  }
}

function normalizeOutcome(result: string): string {
  if (result === "ok") return "Action succeeded.";
  if (result.startsWith("pending_confirmation:")) {
    return "Paused for user confirmation before submit.";
  }
  if (result === "no_actions_returned") return "No further actions were required.";
  if (result === "post_submit_screenshot") return "Captured final screenshot after submit.";
  if (result.startsWith("failed")) return result;
  return result;
}

function deriveTone(step: RunStep): StepTone {
  if (step.severity) return step.severity;
  if (step.result.startsWith("failed")) return "error";
  if (step.result.startsWith("pending_confirmation:")) return "warning";
  return "info";
}

export function mapRunStep(step: RunStep): RunStepViewModel {
  const tone = deriveTone(step);
  return {
    index: step.index,
    title: `Step ${step.index + 1}`,
    actionLabel: describeAction(step.action),
    outcome: normalizeOutcome(step.result),
    reason: step.reason ?? "ScreenPilot selected this as the best next UI action.",
    evidence: step.evidence ?? "Grounded on the visible screenshot state.",
    tone,
    createdAtLabel: formatTimeLabel(step.created_at),
    screenshotStepIndex: step.index,
    targetMode: getTargetMode(step.action),
  };
}
