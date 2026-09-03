"use client";

interface ImpactChartProps {
  avgOrderValuePaise: number;
  baselineAovPaise: number;
  baselineLabel: string;
  totalRevenuePaise: number;
  baselineRevenuePaise: number;
  aovUpliftPct: number;
  orderCount: number;
  ordersWithUpsell: number;
}

function formatPaise(paise: number): string {
  return `₹${(paise / 100).toLocaleString("en-IN")}`;
}

function BarPair({
  label,
  withValue,
  withoutValue,
  withoutCaption,
}: {
  label: string;
  withValue: number;
  withoutValue: number;
  withoutCaption: string;
}) {
  const max = Math.max(withValue, withoutValue, 1);
  return (
    <div>
      <p className="mb-1.5 text-[13px] font-semibold text-slate-700">{label}</p>
      <div className="space-y-1.5">
        <div>
          <div className="mb-0.5 flex items-baseline justify-between text-xs">
            <span className="text-slate-500">With upsell</span>
            <span className="font-bold tabular-nums text-emerald-700">
              {formatPaise(withValue)}
            </span>
          </div>
          <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400 shadow-[0_0_8px_rgba(16,185,129,0.5)] transition-[width] duration-500"
              style={{ width: `${(withValue / max) * 100}%` }}
            />
          </div>
        </div>
        <div>
          <div className="mb-0.5 flex items-baseline justify-between text-xs">
            <span className="text-slate-500">{withoutCaption}</span>
            <span className="font-semibold tabular-nums text-slate-600">
              {formatPaise(withoutValue)}
            </span>
          </div>
          <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-slate-300 transition-[width] duration-500"
              style={{ width: `${(withoutValue / max) * 100}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export function ImpactChart({
  avgOrderValuePaise,
  baselineAovPaise,
  baselineLabel,
  totalRevenuePaise,
  baselineRevenuePaise,
  aovUpliftPct,
  orderCount,
  ordersWithUpsell,
}: ImpactChartProps) {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_8px_24px_-12px_rgba(15,23,42,0.2)]">
      <div className="flex items-center gap-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 text-sm font-bold text-white shadow-sm" aria-hidden="true">
          ₹
        </span>
        <h2 className="text-sm font-semibold text-slate-900">Revenue impact</h2>
      </div>
      <p className="mt-1 text-[13px] leading-relaxed text-slate-600" aria-live="polite">
        {orderCount === 0 ? (
          "No paid orders yet — complete a purchase to see the upsell lift."
        ) : (
          <>
            Upsells increased average order value by{" "}
            <strong className="text-emerald-700">{aovUpliftPct}%</strong> across{" "}
            <strong>{orderCount}</strong> order{orderCount === 1 ? "" : "s"}
            {ordersWithUpsell > 0 &&
              ` (${ordersWithUpsell} with upsell items)`}
            .
          </>
        )}
      </p>

      {orderCount > 0 && (
        <div className="mt-4 space-y-4">
          <BarPair
            label="Average order value"
            withValue={avgOrderValuePaise}
            withoutValue={baselineAovPaise}
            withoutCaption="Baseline (no upsell)"
          />
          <BarPair
            label="Total revenue"
            withValue={totalRevenuePaise}
            withoutValue={baselineRevenuePaise}
            withoutCaption="Baseline (no upsell)"
          />
          <p className="text-[11px] leading-relaxed text-slate-400">{baselineLabel} — derived from real orders, not a separate control group.</p>
        </div>
      )}
    </div>
  );
}
