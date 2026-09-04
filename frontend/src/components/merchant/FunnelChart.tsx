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
    <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_8px_24px_-12px_rgba(15,23,42,0.2)]">
      <div className="flex items-center gap-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-md bg-blue-700" aria-hidden="true">
          <Filter className="h-3.5 w-3.5 text-white" />
        </span>
        <h2 className="text-sm font-semibold text-slate-900">AI commerce funnel</h2>
      </div>
      <p className="mt-1 text-xs text-slate-500">
        Live demo sessions only — grows as you chat in the buyer view. No sampled data.
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
                <div className="h-7 flex-1 overflow-hidden rounded-lg bg-slate-100">
                  <div
                    className={`flex h-full items-center justify-end rounded-lg pr-2 text-[11px] font-bold tabular-nums text-white transition-[width] duration-700 ${
                      i === stages.length - 1 ? "bg-emerald-600" : "bg-blue-600"
                    }`}
                    style={{ width: `${Math.max(s.sessions > 0 ? 10 : 0, (s.sessions / max) * 100)}%` }}
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
