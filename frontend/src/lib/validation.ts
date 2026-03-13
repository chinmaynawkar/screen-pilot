import type { TimesheetParameters } from "../components/TimesheetParametersForm";

export interface FormValidation {
  valid: boolean;
  errors: string[];
}

export function validateTimesheetForm(
  goal: string,
  parameters: TimesheetParameters,
): FormValidation {
  const errors: string[] = [];

  const trimmedGoal = goal.trim();
  if (trimmedGoal.length === 0) {
    errors.push("Goal is required.");
  }

  const defaultHours = parameters.defaultHours;
  if (defaultHours !== undefined && (defaultHours < 0 || defaultHours > 24)) {
    errors.push("Default hours per day must be between 0 and 24.");
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}
