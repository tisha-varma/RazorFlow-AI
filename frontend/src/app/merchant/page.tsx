"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { AuditTrail } from "@/components/audit/AuditTrail";
import { ImpactChart } from "@/components/merchant/ImpactChart";
import { FunnelChart, type FunnelStage } from "@/components/merchant/FunnelChart";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  Banknote,
  Receipt,
  TrendingUp,
  Gift,
  Percent,
  Store,
  History,
} from "lucide-react";

interface PeriodStats {
  total_revenue_paise: number;
  order_count: number;
  ai_assisted_orders: number;
  upsell_revenue_paise: number;
  upsell_pct: number;
  avg_order_value_paise: number;
  baseline_label: string;
  baseline_revenue_paise: number;
  baseline_aov_paise: number;
  orders_with_upsell: number;
  aov_uplift_pct: number;
}

interface RecentOrder {
  id: number;
  order_number: string;
  product_names: string[];
  total_paise: number;
  is_ai_assisted: boolean;
  status: string;
  created_at?: string | null;
}

interface Summary {
  merchant_id: number;
  all_time: PeriodStats;
  today: PeriodStats;
  conversion_sessions: number;
  conversion_rate_pct: number;
  conversion_note: string;
  recent_orders: RecentOrder[];
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

function formatPaise(paise: number): string {
  return `₹${(paise / 100).toLocaleString("en-IN")}`;
}

function timeFor(timestamp?: string | null): string {
  if (!timestamp) return "—";
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

const STATUS_STYLES: Record<string, string> = {
  paid: "border-emerald-300 text-emerald-700 bg-emerald-50",
  pending: "border-amber-300 text-amber-700 bg-amber-50",
  failed: "border-red-300 text-red-700 bg-red-50",
  cancelled: "border-slate-300 text-slate-500 bg-slate-50",
};

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  tile,
  bar,
}: {
  icon: typeof Banknote;
  label: string;
  value: string;
  sub?: string;
  tile: string;
  bar: string;
}) {
  return (
    <div className="group relative overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-4 shadow-[0_8px_24px_-12px_rgba(15,23,42,0.25)] transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_16px_32px_-12px_rgba(15,23,42,0.3)]">
      <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${bar}`} aria-hidden="true" />
      <div className="flex items-center gap-2.5">
        <span className={`flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br ${tile} text-white shadow-md`}>
          <Icon className="h-4 w-4" aria-hidden="true" />
        </span>
        <span className="text-[13px] font-medium text-slate-500">{label}</span>
      </div>
      <p className="mt-2.5 bg-gradient-to-br from-slate-900 to-slate-700 bg-clip-text text-[26px] font-extrabold tabular-nums leading-none text-transparent">{value}</p>
      {sub && <p className="mt-1.5 text-xs tabular-nums text-slate-500">{sub}</p>}
    </div>
  );
}

export default function MerchantPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [funnel, setFunnel] = useState<FunnelStage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [seeding, setSeeding] = useState(false);
  const seededOnce = useRef(false);

  const loadDashboard = useCallback(async () => {
    const [summaryRes, funnelRes] = await Promise.all([
      fetch(`${API_BASE}/dashboard/summary?merchant_id=1`),
      fetch(`${API_BASE}/dashboard/funnel?merchant_id=1`),
    ]);
    if (!summaryRes.ok) throw new Error("Could not load dashboard");
    const data: Summary = await summaryRes.json();
    setSummary(data);
    if (funnelRes.ok) {
      setFunnel((await funnelRes.json()).stages ?? []);
    }
    return data;
  }, []);

  const fetchDashboard = useCallback(async () => {
    try {
      const data = await loadDashboard();
      setError(null);
      // Never show an empty dashboard: seed deterministic HIST-* history
      // once per visit when there are no paid orders (e.g. fresh DB or
      // after a merchant-wide demo reset). Idempotent server-side.
      if (!seededOnce.current && data.all_time.order_count === 0) {
        seededOnce.current = true;
        setSeeding(true);
        try {
          const seedRes = await fetch(`${API_BASE}/demo/seed-history?count=24`, {
            method: "POST",
          });
          if (seedRes.ok) {
            await loadDashboard();
          }
        } catch {
          /* seed is a bonus — empty state still renders */
        } finally {
          setSeeding(false);
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load dashboard");
    }
  }, [loadDashboard]);

  useEffect(() => {
    fetchDashboard();
    const timer = setInterval(fetchDashboard, 5000);
    return () => clearInterval(timer);
  }, [fetchDashboard]);

  const all = summary?.all_time;
  const today = summary?.today;
  const hasDemoData = (summary?.recent_orders ?? []).some((o) =>
    o.order_number.startsWith("HIST-")
  );

  return (
    <div className="relative min-h-screen text-slate-900 flex flex-col bg-stone-100">
      {/* Ambient mesh backdrop */}
      <div className="pointer-events-none absolute inset-0" aria-hidden="true">
        <div className="absolute -top-32 right-1/4 h-72 w-72 rounded-full bg-emerald-300/20 blur-[100px]" />
        <div className="absolute bottom-0 left-1/4 h-72 w-72 rounded-full bg-indigo-300/20 blur-[100px]" />
      </div>

      <header className="relative border-b border-slate-200/80 bg-white/85 backdrop-blur-md px-4 py-3 flex items-center gap-4 z-50 shadow-[0_1px_12px_rgba(15,23,42,0.06)]">
        <Link href="/">
          <Button variant="ghost" size="sm" className="rounded-full text-slate-500 hover:text-slate-900 hover:bg-slate-100">
            <ArrowLeft className="h-4 w-4 mr-1" aria-hidden="true" />
            Back
          </Button>
        </Link>
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-[0_4px_12px_-2px_rgba(5,150,105,0.5)]" aria-hidden="true">
            <Store className="h-4 w-4 text-white" />
          </div>
          <div className="leading-tight">
            <h1 className="font-semibold text-[15px] text-slate-900">Merchant Console</h1>
            <p className="text-[10px] font-medium uppercase tracking-widest text-slate-400">SprintGear India</p>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {hasDemoData && (
            <Badge variant="outline" className="gap-1 rounded-full border-amber-300 bg-amber-50 text-[11px] text-amber-800" title="HIST-* rows are deterministic demo history; live orders appear as RF-*">
              <History className="h-3 w-3" aria-hidden="true" />
              Demo history included
            </Badge>
          )}
          <Badge variant="outline" className="gap-1.5 rounded-full border-emerald-300 bg-emerald-50 text-xs text-emerald-700">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" aria-hidden="true" />
            Live
          </Badge>
        </div>
      </header>

      <div className="relative mx-auto w-full max-w-5xl space-y-4 p-4 md:p-6">
        {error && (
          <div className="rounded-2xl border border-red-300 bg-red-50 p-3 text-sm text-red-700 shadow-sm">
            {error}
          </div>
        )}
        {seeding && (
          <div className="rounded-2xl border border-indigo-200 bg-indigo-50 p-3 text-sm text-indigo-800 shadow-sm" aria-live="polite">
            Loading demo history so the dashboard never opens empty…
          </div>
        )}

        {/* Stat cards */}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard
            icon={Banknote}
            label="Total revenue"
            value={all ? formatPaise(all.total_revenue_paise) : "—"}
            sub={today ? `Today ${formatPaise(today.total_revenue_paise)}` : undefined}
            tile="from-emerald-500 to-teal-600"
            bar="from-emerald-500 to-teal-400"
          />
          <StatCard
            icon={Receipt}
            label="Avg order value"
            value={all ? formatPaise(all.avg_order_value_paise) : "—"}
            sub={all ? `${all.order_count} paid orders · ${all.ai_assisted_orders} AI-assisted` : undefined}
            tile="from-indigo-500 to-violet-600"
            bar="from-indigo-500 to-violet-400"
          />
          <StatCard
            icon={Percent}
            label="AI conversion"
            value={summary ? `${summary.conversion_rate_pct}%` : "—"}
            sub={summary ? `${summary.conversion_sessions} AI sessions (approx)` : undefined}
            tile="from-sky-500 to-cyan-500"
            bar="from-sky-500 to-cyan-400"
          />
          <StatCard
            icon={Gift}
            label="Upsell revenue"
            value={all ? formatPaise(all.upsell_revenue_paise) : "—"}
            sub={all ? `${all.upsell_pct}% of revenue` : undefined}
            tile="from-amber-500 to-orange-500"
            bar="from-amber-500 to-orange-400"
          />
        </div>

        {all && (
          <ImpactChart
            avgOrderValuePaise={all.avg_order_value_paise}
            baselineAovPaise={all.baseline_aov_paise}
            baselineLabel={all.baseline_label}
            totalRevenuePaise={all.total_revenue_paise}
            baselineRevenuePaise={all.baseline_revenue_paise}
            aovUpliftPct={all.aov_uplift_pct}
            orderCount={all.order_count}
            ordersWithUpsell={all.orders_with_upsell}
          />
        )}

        <FunnelChart stages={funnel} />

        {/* Audit trail — full width, recent actions on top */}
        <div className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-[0_8px_24px_-12px_rgba(15,23,42,0.2)]">
          <div className="h-[440px]">
            <AuditTrail merchantId={1} />
          </div>
        </div>

        <div className="grid gap-4">
          {/* Orders table */}
          <div className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-[0_8px_24px_-12px_rgba(15,23,42,0.2)]">
            <div className="flex items-center gap-2.5 border-b border-slate-100 bg-gradient-to-r from-white to-slate-50 px-4 py-3">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-slate-600 to-slate-800 shadow-sm" aria-hidden="true">
                <TrendingUp className="h-3.5 w-3.5 text-white" />
              </span>
              <h2 className="text-sm font-semibold text-slate-900">Recent orders</h2>
              <span className="ml-auto rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold tabular-nums text-slate-600">
                {(summary?.recent_orders ?? []).length}
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left">
                <caption className="sr-only">Recent orders</caption>
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/80 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    <th scope="col" className="px-4 py-2">Order</th>
                    <th scope="col" className="px-4 py-2">Items</th>
                    <th scope="col" className="px-4 py-2 text-right">Amount</th>
                    <th scope="col" className="px-4 py-2">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {(summary?.recent_orders ?? []).map((order) => (
                    <tr key={order.id} className="align-top transition-colors hover:bg-indigo-50/40">
                      <td className="px-4 py-2.5">
                        <p className={`inline-block rounded-md px-1.5 py-0.5 font-mono text-xs font-semibold ${
                          order.order_number.startsWith("HIST-")
                            ? "bg-amber-50 text-amber-800"
                            : "bg-emerald-50 text-emerald-800"
                        }`}>
                          {order.order_number}
                        </p>
                        <p className="mt-0.5 text-[11px] tabular-nums text-slate-400">
                          {timeFor(order.created_at)}
                        </p>
                      </td>
                      <td className="px-4 py-2.5">
                        <p className="text-[13px] leading-snug text-slate-700 break-words">
                          {order.product_names.join(", ") || "—"}
                        </p>
                        {order.is_ai_assisted && (
                          <Badge
                            variant="outline"
                            className="mt-1 border-indigo-200 bg-indigo-50 text-[10px] text-indigo-700 rounded-full"
                          >
                            AI-assisted
                          </Badge>
                        )}
                      </td>
                      <td className="whitespace-nowrap px-4 py-2.5 text-right text-sm font-bold tabular-nums text-slate-900">
                        {formatPaise(order.total_paise)}
                      </td>
                      <td className="px-4 py-2.5">
                        <Badge
                          variant="outline"
                          className={`rounded-full text-[11px] ${STATUS_STYLES[order.status] ?? STATUS_STYLES.cancelled}`}
                        >
                          {order.status}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                  {(summary?.recent_orders ?? []).length === 0 && (
                    <tr>
                      <td colSpan={4} className="px-4 py-8 text-center text-[13px] text-slate-500">
                        No orders yet — complete a purchase in the buyer view.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </div>

        <p className="text-xs text-slate-400" title={summary?.conversion_note}>
          Conversion is approximate — paid orders over distinct AI sessions. Hover for method.
        </p>
      </div>
    </div>
  );
}
