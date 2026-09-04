"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  CheckCircle2,
  ShieldAlert,
  XCircle,
  TrendingUp,
  Loader2,
  Gavel,
  FlaskConical,
} from "lucide-react";
import { fetchJson } from "@/lib/api";

type ScenarioKey = "happy" | "policy" | "failure" | "impact";

interface ScenarioResult {
  title: string;
  lines: string[];
  facts: { label: string; value: string }[];
}

function formatPaise(paise: number): string {
  return `₹${(paise / 100).toLocaleString("en-IN")}`;
}

const SCENARIOS: {
  key: ScenarioKey;
  title: string;
  proves: string;
  icon: typeof CheckCircle2;
  tile: string;
}[] = [
  {
    key: "happy",
    title: "Happy path",
    proves: "Search → cart → upsell → policy → approval → captured payment, end to end.",
    icon: CheckCircle2,
    tile: "bg-emerald-600",
  },
  {
    key: "policy",
    title: "Policy blocked",
    proves: "An over-limit cart is refused before any approval artifact exists.",
    icon: ShieldAlert,
    tile: "bg-amber-600",
  },
  {
    key: "failure",
    title: "Payment failed",
    proves: "A gateway decline marks the order failed with zero budget consumed — retry reuses the approval.",
    icon: XCircle,
    tile: "bg-red-600",
  },
  {
    key: "impact",
    title: "Merchant impact",
    proves: "Live revenue, AOV lift, and funnel from real paid orders.",
    icon: TrendingUp,
    tile: "bg-blue-700",
  },
];

export default function JudgePage() {
  const [results, setResults] = useState<Partial<Record<ScenarioKey, ScenarioResult>>>({});
  const [errors, setErrors] = useState<Partial<Record<ScenarioKey, string>>>({});
  const [running, setRunning] = useState<ScenarioKey | null>(null);

  const run = async (key: ScenarioKey) => {
    setRunning(key);
    setErrors((e) => ({ ...e, [key]: undefined }));
    try {
      if (key === "happy") {
        const d = await fetchJson("/demo/run-successful-purchase?session_id=judge-happy", {
          method: "POST",
        });
        setResults((r) => ({
          ...r,
          happy: {
            title: `Paid ${d.order_number}`,
            lines: (d.steps as string[]) ?? [],
            facts: [
              { label: "Total", value: formatPaise(d.total_paise) },
              { label: "Razorpay order", value: d.razorpay_order_id },
              { label: "Duration", value: `${d.duration_ms} ms` },
            ],
          },
        }));
      } else if (key === "policy") {
        const d = await fetchJson("/demo/run-policy-block?session_id=judge-policy", {
          method: "POST",
        });
        setResults((r) => ({
          ...r,
          policy: {
            title: d.allowed ? "Allowed (limits cover it)" : "Blocked before approval",
            lines: (d.steps as string[]) ?? [],
            facts: [
              { label: "Cart total", value: formatPaise(d.cart_total_paise) },
              { label: "Verdict", value: d.allowed ? "allowed" : "blocked" },
            ],
          },
        }));
      } else if (key === "failure") {
        const d = await fetchJson("/demo/run-payment-failure?session_id=judge-failure", {
          method: "POST",
        });
        setResults((r) => ({
          ...r,
          failure: {
            title: `Failed ${d.order_number} — no charge`,
            lines: (d.steps as string[]) ?? [],
            facts: [
              { label: "Reason", value: d.reason },
              { label: "Retry", value: "Same approval → new Razorpay order (see buyer)" },
            ],
          },
        }));
      } else {
        const d = await fetchJson("/dashboard/summary?merchant_id=1");
        const all = d.all_time;
        setResults((r) => ({
          ...r,
          impact: {
            title: `${formatPaise(all.total_revenue_paise)} across ${all.order_count} paid orders`,
            lines: [
              `AOV lift from upsells: +${all.aov_uplift_pct}%`,
              `Upsell revenue: ${formatPaise(all.upsell_revenue_paise)} (${all.upsell_pct}% of revenue)`,
              `AI conversion: ${d.conversion_rate_pct}% over ${d.conversion_sessions} sessions`,
            ],
            facts: [
              { label: "Revenue", value: formatPaise(all.total_revenue_paise) },
              { label: "AOV lift", value: `+${all.aov_uplift_pct}%` },
              { label: "Orders", value: `${all.order_count}` },
            ],
          },
        }));
      }
    } catch (e) {
      setErrors((prev) => ({
        ...prev,
        [key]: e instanceof Error ? e.message : "Scenario failed",
      }));
    } finally {
      setRunning(null);
    }
  };

  return (
    <div className="min-h-screen bg-stone-100 text-slate-900 flex flex-col">
      <header className="border-b border-slate-200 bg-white px-4 py-3 flex items-center gap-3 shadow-sm">
        <Link href="/">
          <Button variant="ghost" size="sm" className="rounded-full text-slate-500 hover:text-slate-900 hover:bg-slate-100">
            <ArrowLeft className="h-4 w-4 mr-1" aria-hidden="true" />
            Back
          </Button>
        </Link>
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-slate-900 flex items-center justify-center" aria-hidden="true">
            <Gavel className="h-4 w-4 text-white" />
          </div>
          <div className="leading-tight">
            <span className="font-semibold text-[15px] text-slate-900">Judge mode</span>
            <p className="text-[10px] font-medium uppercase tracking-widest text-slate-400">One click per story</p>
          </div>
        </div>
        <Badge variant="outline" className="ml-auto gap-1 rounded-full border-amber-300 bg-amber-50 text-[11px] text-amber-800">
          <FlaskConical className="h-3 w-3" aria-hidden="true" />
          Scripted triggers — the live paths are /buyer and /merchant
        </Badge>
      </header>

      <main className="mx-auto w-full max-w-5xl p-4 md:p-6 grid gap-4 md:grid-cols-2">
        {SCENARIOS.map((s) => {
          const Icon = s.icon;
          const result = results[s.key];
          const error = errors[s.key];
          const busy = running === s.key;
          return (
            <section
              key={s.key}
              className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm flex flex-col"
            >
              <div className="flex items-center gap-2.5">
                <span className={`flex h-9 w-9 items-center justify-center rounded-lg ${s.tile} text-white`} aria-hidden="true">
                  <Icon className="h-4 w-4" />
                </span>
                <div>
                  <h2 className="text-[15px] font-semibold text-slate-900">{s.title}</h2>
                  <p className="text-xs text-slate-500">{s.proves}</p>
                </div>
              </div>
              <div className="mt-3">
                <Button
                  onClick={() => run(s.key)}
                  disabled={running !== null}
                  className="bg-slate-900 hover:bg-slate-800 text-white h-9 text-[13px] touch-manipulation"
                >
                  {busy && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" aria-hidden="true" />}
                  {busy ? "Running…" : `Run ${s.title.toLowerCase()}`}
                </Button>
                {s.key === "impact" && (
                  <Link href="/merchant" className="ml-2 text-[13px] font-medium text-blue-700 hover:underline">
                    Open merchant console →
                  </Link>
                )}
              </div>
              {error && (
                <p className="mt-3 rounded-lg border border-red-200 bg-red-50 p-2.5 text-[13px] text-red-700">
                  {error}
                </p>
              )}
              {result && (
                <div className="mt-3 rounded-lg border border-slate-200 bg-stone-50 p-3" aria-live="polite">
                  <p className="text-[13px] font-semibold text-slate-900">{result.title}</p>
                  <ol className="mt-2 space-y-1">
                    {result.lines.map((line, i) => (
                      <li key={i} className="flex gap-2 text-[13px] text-slate-600">
                        <span className="font-mono text-[11px] text-slate-400 tabular-nums">{i + 1}.</span>
                        <span className="break-words">{line}</span>
                      </li>
                    ))}
                  </ol>
                  <dl className="mt-2 space-y-1 border-t border-slate-200 pt-2">
                    {result.facts.map((f) => (
                      <div key={f.label} className="flex justify-between gap-2 text-xs">
                        <dt className="text-slate-500">{f.label}</dt>
                        <dd className="font-semibold tabular-nums text-slate-800 break-words text-right">{f.value}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              )}
            </section>
          );
        })}
      </main>
    </div>
  );
}
