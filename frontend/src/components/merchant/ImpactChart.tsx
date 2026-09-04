"use client";

interface ImpactChartProps {
  totalRevenuePaise: number;
  baselineRevenuePaise: number;
  baselineLabel: string;
}

function formatPaise(paise: number): string {
  return `₹${(paise / 100).toLocaleString("en-IN")}`;
}

/** Compact With-AI vs Without-AI revenue diff. Single row, max ~120px tall. */
export function ImpactChart({
  totalRevenuePaise,
  baselineRevenuePaise,
  baselineLabel,
}: ImpactChartProps) {
  const uplift =
    baselineRevenuePaise > 0
      ? ((totalRevenuePaise - baselineRevenuePaise) / baselineRevenuePaise) * 100
      : 0;
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-1">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
            With AI
          </p>
          <p className="text-xl font-bold tabular-nums leading-tight text-slate-900">
            {formatPaise(totalRevenuePaise)}
          </p>
        </div>
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-bold tabular-nums ${
            uplift >= 0
              ? "bg-emerald-600 text-white"
              : "bg-red-600 text-white"
          }`}
          aria-label={`Revenue delta ${uplift >= 0 ? "+" : ""}${uplift.toFixed(1)} percent`}
        >
          {uplift >= 0 ? "+" : ""}
          {uplift.toFixed(1)}%
        </span>
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
            Without AI
          </p>
          <p className="text-xl font-bold tabular-nums leading-tight text-slate-500">
            {formatPaise(baselineRevenuePaise)}
          </p>
        </div>
        <p className="ml-auto max-w-[280px] text-[10px] leading-snug text-slate-400">
          {baselineLabel} — derived from real orders, not a separate control group.
        </p>
      </div>
    </div>
  );
}
