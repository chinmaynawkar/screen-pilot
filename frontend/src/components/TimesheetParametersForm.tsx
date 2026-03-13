export interface TimesheetParameters {
  weekStart?: string;
  defaultHours?: number;
}

export interface TimesheetParametersFormProps {
  goal: string;
  parameters: TimesheetParameters;
  onGoalChange: (goal: string) => void;
  onParametersChange: (params: TimesheetParameters) => void;
  disabled?: boolean;
  errors?: string[];
}

export function TimesheetParametersForm({
  goal,
  parameters,
  onGoalChange,
  onParametersChange,
  disabled = false,
  errors = [],
}: TimesheetParametersFormProps) {
  const defaultHours = parameters.defaultHours;
  const weekStart = parameters.weekStart ?? "";

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label
          htmlFor="goal"
          className="block text-sm font-medium text-slate-700"
        >
          Goal
        </label>
        <textarea
          id="goal"
          value={goal}
          onChange={(e) => onGoalChange(e.target.value)}
          disabled={disabled}
          placeholder="e.g. Fill weekly timesheet"
          rows={2}
          className="w-full resize-y rounded-input border border-border bg-surface px-3 py-2.5 text-sm text-slate-800 shadow-card outline-none transition placeholder:text-muted-subtle focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-60"
        />
      </div>

      <div className="space-y-3 rounded-input border border-border/80 bg-surface-elevated/60 p-3">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-text">
          Optional parameters
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <label
              htmlFor="week-start"
              className="block text-sm text-slate-600"
            >
              Week start
            </label>
            <input
              id="week-start"
              type="date"
              value={weekStart}
              onChange={(e) =>
                onParametersChange({
                  ...parameters,
                  weekStart: e.target.value || undefined,
                })
              }
              disabled={disabled}
              className="w-full rounded-input border border-border bg-surface px-3 py-2 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:opacity-60 [color-scheme:light]"
            />
          </div>
          <div className="space-y-1.5">
            <label
              htmlFor="default-hours"
              className="block text-sm text-slate-600"
            >
              Default hours per day (0–24)
            </label>
            <input
              id="default-hours"
              type="number"
              min={0}
              max={24}
              step={0.5}
              value={defaultHours === undefined ? "" : defaultHours}
              onChange={(e) => {
                const v = e.target.value;
                const n = v === "" ? undefined : Number(v);
                onParametersChange({ ...parameters, defaultHours: n });
              }}
              disabled={disabled}
              placeholder="8"
              className="w-full rounded-input border border-border bg-surface px-3 py-2 text-sm text-slate-800 outline-none transition placeholder:text-muted-subtle focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:opacity-60"
            />
          </div>
        </div>
      </div>

      {errors.length > 0 && (
        <ul className="space-y-1 rounded-input bg-danger-muted px-3 py-2 text-sm text-danger">
          {errors.map((msg, i) => (
            <li key={i}>{msg}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
