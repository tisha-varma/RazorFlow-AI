"use client";

import type { TurnTrace } from "@/components/chat/ChatPanel";
import { ArrowRight } from "lucide-react";

export interface FullTrace extends TurnTrace {
  paidOrderNumber?: string | null;
}

/** Compact protocol-style trace of the last agent turn:
 * intent → tools → policy → approval → payment → audit. */
export function TracePanel({ trace, sessionId }: { trace: FullTrace; sessionId: string }) {
  const steps: { label: string; value: string; tone: "ok" | "warn" | "bad" | "idle" }[] = [
    {
      label: "Intent",
      value: trace.intent.length > 42 ? trace.intent.slice(0, 42) + "…" : trace.intent,
      tone: "idle",
    },
    {
      label: "Tools",
      value:
        trace.tools.length > 0
          ? trace.tools.map((t) => t.name).join(" → ")
          : "none (direct answer)",
      tone: trace.tools.length > 0 ? "ok" : "idle",
    },
    {
      label: "Policy",
      value:
        trace.policyAllowed === null
          ? "not evaluated"
          : trace.policyAllowed
            ? "allowed"
            : `BLOCKED — ${trace.policyReason ?? "see reason"}`,
      tone:
        trace.policyAllowed === null ? "idle" : trace.policyAllowed ? "ok" : "bad",
    },
    {
      label: "Approval",
      value: trace.approvalId ? `#${trace.approvalId} minted` : "none",
      tone: trace.approvalId ? "warn" : "idle",
    },
    {
      label: "Payment",
      value: trace.paidOrderNumber ? `verified ${trace.paidOrderNumber}` : "not paid",
      tone: trace.paidOrderNumber ? "ok" : "idle",
    },
    {
      label: "Audit",
      value: `trail for ${sessionId.slice(0, 8)}…`,
      tone: "idle",
    },
  ];

  const tones: Record<string, string> = {
    ok: "border-emerald-300 bg-emerald-50 text-emerald-800",
    warn: "border-amber-300 bg-amber-50 text-amber-800",
    bad: "border-red-300 bg-red-50 text-red-700",
    idle: "border-slate-200 bg-white text-slate-500",
  };

  return (
    <div
      className="border-b border-slate-200 bg-white px-4 py-2.5"
      aria-live="polite"
      aria-label="Protocol trace of the last turn"
    >
      <div className="flex items-center gap-1.5 overflow-x-auto">
        {steps.map((s, i) => (
          <span key={s.label} className="flex items-center gap-1.5 shrink-0">
            {i > 0 && <ArrowRight className="h-3 w-3 shrink-0 text-slate-300" aria-hidden="true" />}
            <span
              className={`rounded-lg border px-2 py-1 text-[11px] leading-tight ${tones[s.tone]}`}
              title={`${s.label}: ${s.value}`}
            >
              <span className="block font-semibold uppercase tracking-wide opacity-70 text-[9px]">
                {s.label}
              </span>
              <span className="block max-w-[180px] truncate font-medium">{s.value}</span>
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
