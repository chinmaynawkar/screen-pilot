export interface TaskSelectorProps {
  value: string;
  onChange: (taskType: string) => void;
  disabled?: boolean;
}

const TASKS = [
  { value: "fill_timesheet", label: "Fill weekly timesheet" },
] as const;

export function TaskSelector({
  value,
  onChange,
  disabled = false,
}: TaskSelectorProps) {
  return (
    <div className="space-y-2">
      <label
        htmlFor="task-select"
        className="block text-sm font-medium text-slate-700"
      >
        Task
      </label>
      <select
        id="task-select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="w-full rounded-input border border-border bg-surface px-3 py-2.5 text-sm text-slate-800 shadow-card outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {TASKS.map((t) => (
          <option key={t.value} value={t.value}>
            {t.label}
          </option>
        ))}
      </select>
    </div>
  );
}
