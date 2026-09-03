"use client";

import { Filter } from "lucide-react";

export interface FunnelStage {
  stage: string;
  sessions: number;
  dropoff_pct_from_prev: number;
}

const STAGE_LABELS: Record<string, string> = {
  DISCOVERING: "Discovering",
  RECOMMENDING: "Recommending",
  CART_BUILDING: "Cart building",
  AWAITING_APPROVAL: "Awaiting approval",
  PAYMENT_PENDING: "Payment pending",
  ORDER_CONFIRMED: "Order confirmed",
};

export function FunnelChart({ stages }: { stages: FunnelStage[] }) {
  const max = Math.max(1, ...stages.map((s) => s.sessions));

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2">
        <Filter className="h-4 w-4 text-slate-500" aria-hidden="true" />
        <h2 className="text-sm font-semibold text-slate-900">AI commerce funnel</h2>
      </div>
      <p className="mt-1 text-xs text-slate-500">
        Sessions reaching each stage (cumulative) — drop-off shown between steps.
      </p>

      {max <= 1 && stages.every((s) => s.sessions === 0) ? (
        <p className="py-6 text-center text-[13px] text-slate-500">
          No sessions yet — chat in the buyer view to fill the funnel.
        </p>
      ) : (
        <div className="mt-3 space-y-2.5">
          {stages.map((s, i) => (
            <div key={s.stage}>
              {i > 0 && s.dropoff_pct_from_prev > 0 && (
                <p className="mb-1 text-right text-[11px] tabular-nums text-red-500">
                  −{s.dropoff_pct_from_prev}% drop-off
                </p>
              )}
              <div className="flex items-center gap-2">
                <span className="w-32 shrink-0 truncate text-xs font-medium text-slate-600">
                  {STAGE_LABELS[s.stage] ?? s.stage}
                </span>
                <div className="h-6 flex-1 overflow-hidden rounded-md bg-slate-100">
                  <div
                    className={`flex h-full items-center justify-end rounded-md pr-1.5 text-[11px] font-bold tabular-nums transition-[width] duration-500 ${
                      i === stages.length - 1
                        ? "bg-emerald-500 text-white"
                        : "bg-indigo-400 text-white"
                    }`}
                    style={{ width: `${Math.max(s.sessions > 0 ? 8 : 0, (s.sessions / max) * 100)}%` }}
                  >
                    {s.sessions > 0 ? s.sessions : ""}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
