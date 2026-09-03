"use client";

import { useEffect, useState } from "react";
import { fetchJson } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Loader2, ShieldCheck } from "lucide-react";

interface PolicyPanelProps {
  sessionId: string;
  onChanged?: () => void;
}

function formatPaise(paise: number): string {
  return `₹${(paise / 100).toLocaleString("en-IN")}`;
}

const RUPEE_FIELDS = [
  { key: "max_transaction_amount_paise", label: "Max per transaction" },
  { key: "min_transaction_amount_paise", label: "Min per transaction (0 = none)" },
  { key: "spending_limit_paise", label: "Session spending limit" },
  { key: "max_upsell_amount_paise", label: "Max upsell total" },
] as const;

export function PolicyPanel({ sessionId, onChanged }: PolicyPanelProps) {
  const [policy, setPolicy] = useState<Record<string, unknown> | null>(null);
  const [usage, setUsage] = useState<{
    remaining_paise: number;
    used_paise: number;
    spending_limit_paise: number;
  } | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [qty, setQty] = useState("5");
  const [allowUpsell, setAllowUpsell] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const load = async () => {
    try {
      const p = await fetchJson("/policy");
      setPolicy(p);
      const d: Record<string, string> = {};
      for (const f of RUPEE_FIELDS) {
        d[f.key] = String((Number(p[f.key]) || 0) / 100);
      }
      setDraft(d);
      setQty(String(p.max_quantity_per_item ?? 5));
      setAllowUpsell(p.allow_upsell !== false);
    } catch {
      setPolicy(null);
    }
    try {
      const u = await fetchJson(
        `/policy/session-usage?session_id=${encodeURIComponent(sessionId)}`
      );
      setUsage(u);
    } catch {
      setUsage(null);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const save = async () => {
    if (!policy || typeof policy.id !== "number") return;
    setSaving(true);
    setMsg(null);
    try {
      const body: Record<string, unknown> = {
        // require_approval is intentionally never sent: the human gate is
        // hard-locked on (like /setup) — the toggle would be a lie, since
        // nothing in the checkout path branches on it.
        allow_upsell: allowUpsell,
        max_quantity_per_item: Math.max(1, parseInt(qty, 10) || 1),
      };
      for (const f of RUPEE_FIELDS) {
        const v = parseFloat(draft[f.key] ?? "");
        if (Number.isFinite(v) && v >= 0) {
          body[f.key] = Math.round(v * 100);
        }
      }
      const updated = await fetchJson(`/policy/${policy.id}`, {
        method: "PUT",
        body: JSON.stringify(body),
      });
      setPolicy(updated);
      setMsg("Policy saved — new limits apply to the next checkout.");
      onChanged?.();
      try {
        const u = await fetchJson(
          `/policy/session-usage?session_id=${encodeURIComponent(sessionId)}`
        );
        setUsage(u);
      } catch {
        /* usage refresh is a bonus */
      }
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Could not save policy.");
    } finally {
      setSaving(false);
    }
  };

  if (policy === null) {
    return (
      <div className="border-b border-slate-200 bg-white px-4 py-3 text-[13px] text-slate-500">
        No active policy — visit <span className="font-mono">/setup</span> once to
        create it, then edit limits here.
      </div>
    );
  }

  return (
    <div className="border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div className="mb-2 flex items-center gap-2">
        <ShieldCheck className="h-4 w-4 text-emerald-700" aria-hidden="true" />
        <h3 className="text-[13px] font-semibold text-slate-900">Policy settings</h3>
        {usage && (
          <span className="ml-auto text-xs text-slate-500 tabular-nums">
            Session: {formatPaise(usage.used_paise)} used ·{" "}
            <span className="font-semibold text-slate-800">
              {formatPaise(usage.remaining_paise)} left
            </span>
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-3 lg:grid-cols-6">
        {RUPEE_FIELDS.map((f) => (
          <label key={f.key} className="block">
            <span className="mb-0.5 block text-[11px] font-medium text-slate-500">
              {f.label} (₹)
            </span>
            <input
              type="number"
              min={0}
              value={draft[f.key] ?? ""}
              onChange={(e) => setDraft((d) => ({ ...d, [f.key]: e.target.value }))}
              className="h-9 w-full rounded-lg border border-slate-300 bg-white px-2 text-[13px] tabular-nums text-slate-900 focus:border-indigo-500 focus:outline-none"
            />
          </label>
        ))}
        <label className="block">
          <span className="mb-0.5 block text-[11px] font-medium text-slate-500">
            Max qty / item
          </span>
          <input
            type="number"
            min={1}
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            className="h-9 w-full rounded-lg border border-slate-300 bg-white px-2 text-[13px] tabular-nums text-slate-900 focus:border-indigo-500 focus:outline-none"
          />
        </label>
        <div className="flex items-end gap-3 pb-1">
          <span
            className="flex items-center gap-1.5 rounded-full border border-emerald-300 bg-emerald-50 px-2.5 py-1 text-[12px] font-medium text-emerald-700"
            title="The human approval gate cannot be disabled"
          >
            <input
              type="checkbox"
              checked
              disabled
              readOnly
              aria-label="Approval gate (always on)"
              className="h-4 w-4 accent-emerald-600"
            />
            Approval gate · locked on
          </span>
          <label className="flex items-center gap-1.5 text-[12px] text-slate-700">
            <input
              type="checkbox"
              checked={allowUpsell}
              onChange={(e) => setAllowUpsell(e.target.checked)}
              className="h-4 w-4 accent-amber-600"
            />
            Upsells
          </label>
        </div>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <Button
          size="sm"
          onClick={save}
          disabled={saving}
          className="bg-indigo-600 hover:bg-indigo-500 text-white h-8 text-xs touch-manipulation"
        >
          {saving && <Loader2 className="mr-1.5 h-3 w-3 animate-spin" aria-hidden="true" />}
          Save policy
        </Button>
        {msg && (
          <p className="text-xs text-slate-600" aria-live="polite">
            {msg}
          </p>
        )}
      </div>
    </div>
  );
}
