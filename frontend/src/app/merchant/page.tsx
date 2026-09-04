"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { AuditTrail } from "@/components/audit/AuditTrail";
import { formatDateTimeIST } from "@/lib/time";
import { ImpactChart } from "@/components/merchant/ImpactChart";
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
  RefreshCw,
} from "lucide-react";

interface PeriodStats {
  total_revenue_paise: number;
  order_count: number;
  ai_assisted_orders: number;
  demo_order_count: number;
  demo_revenue_paise: number;
  live_order_count: number;
  live_revenue_paise: number;
  live_upsell_revenue_paise: number;
  live_upsell_pct: number;
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
  // Stored timestamps are UTC-naive — render IST (see lib/time).
  return formatDateTimeIST(timestamp);
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
}: {
  icon: typeof Banknote;
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm transition-colors hover:border-blue-300 hover:bg-blue-50/40">
      <div className="flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white">
          <Icon className="h-4 w-4" aria-hidden="true" />
        </span>
        <span className="text-xs font-medium text-slate-500">{label}</span>
      </div>
      <p className="mt-2 text-[22px] font-bold tabular-nums leading-none text-slate-900">{value}</p>
      {sub && <p className="mt-1 text-[11px] tabular-nums text-slate-500">{sub}</p>}
    </div>
  );
}

export default function MerchantPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadDashboard = useCallback(async () => {
    const summaryRes = await fetch(`${API_BASE}/dashboard/summary?merchant_id=1`);
    if (!summaryRes.ok) throw new Error("Could not load dashboard");
    const data: Summary = await summaryRes.json();
    setSummary(data);
    return data;
  }, []);

  // NOTE: this page deliberately does NOT auto-seed. An empty dashboard is
  // the honest fresh state — seed explicitly via POST /demo/seed-history,
  // the buyer Reset-demo button, or /judge. (Auto-seed once fought a
  // deliberate merchant-wide wipe by refilling HIST rows within seconds.)
  const fetchDashboard = useCallback(async () => {
    try {
      await loadDashboard();
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load dashboard");
    }
  }, [loadDashboard]);

  useEffect(() => {
    // Deferred so the effect body itself never synchronously reaches
    // setState: timer/subscription callbacks are the allowed context.
    const immediate = setTimeout(() => {
      void fetchDashboard();
    }, 0);
    const timer = setInterval(() => {
      void fetchDashboard();
    }, 5000);
    return () => {
      clearTimeout(immediate);
      clearInterval(timer);
    };
  }, [fetchDashboard]);

  const all = summary?.all_time;

  return (
    <div className="relative min-h-screen text-slate-900 flex flex-col bg-[#F9FAFB]">
      <div className="h-1 bg-blue-600" aria-hidden="true" />
      <header className="relative border-b border-slate-200/80 bg-white/85 backdrop-blur-md px-4 py-3 flex items-center gap-4 z-50 shadow-[0_1px_12px_rgba(15,23,42,0.06)]">
        <Link href="/">
          <Button variant="ghost" size="sm" className="rounded-full text-slate-500 hover:text-slate-900 hover:bg-slate-100">
            <ArrowLeft className="h-4 w-4 mr-1" aria-hidden="true" />
            Back
          </Button>
        </Link>
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-slate-900 flex items-center justify-center" aria-hidden="true">
            <Store className="h-4 w-4 text-white" />
          </div>
          <div className="leading-tight">
            <h1 className="font-semibold text-[15px] text-slate-900">Merchant Console</h1>
            <p className="text-[10px] font-medium uppercase tracking-widest text-slate-400">SprintGear India</p>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={async () => {
              setRefreshing(true);
              setError(null);
              try {
                await loadDashboard();
              } catch (e) {
                setError(e instanceof Error ? e.message : "Could not load dashboard");
              } finally {
                setRefreshing(false);
              }
            }}
            title="Reload dashboard now"
            className="rounded-full text-slate-500 hover:text-slate-900 hover:bg-slate-100"
          >
            <RefreshCw className={`h-3.5 w-3.5 mr-1 ${refreshing ? "animate-spin" : ""}`} aria-hidden="true" />
            Refresh
          </Button>
          <Badge variant="outline" className="gap-1.5 rounded-full border-emerald-300 bg-emerald-50 text-xs text-emerald-700">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" aria-hidden="true" />
            Live
          </Badge>
        </div>
      </header>

      <div className="relative mx-auto w-full max-w-6xl space-y-3 p-3 md:p-4">
        {error && (
          <div className="rounded-2xl border border-red-300 bg-red-50 p-3 text-sm text-red-700 shadow-sm">
            {error}
          </div>
        )}
        {all && all.order_count === 0 && !error && (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white p-4 text-center text-[13px] text-slate-500" aria-live="polite">
            Fresh database — no orders yet. Complete a purchase in the buyer view,
            or seed labeled demo history via <span className="font-mono">POST /demo/seed-history</span>.
          </div>
        )}

        {/* Stat cards — dense, single brand color */}
        <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
          <StatCard
            icon={Banknote}
            label="Total revenue"
            value={all ? formatPaise(all.total_revenue_paise) : "—"}
            sub={all ? `${all.order_count} paid orders` : undefined}
          />
          <StatCard
            icon={Receipt}
            label="Live revenue"
            value={all ? formatPaise(all.live_revenue_paise) : "—"}
            sub={all ? `${all.live_order_count} live orders` : undefined}
          />
          <StatCard
            icon={Percent}
            label="AI conversion"
            value={summary ? `${summary.conversion_rate_pct}%` : "—"}
            sub={summary ? `${summary.conversion_sessions} tracked sessions` : undefined}
          />
          <StatCard
            icon={Gift}
            label="Upsell revenue"
            value={all ? formatPaise(all.live_upsell_revenue_paise) : "—"}
            sub={all ? `${all.live_upsell_pct}% of live revenue` : undefined}
          />
        </div>

        {all && (
          <ImpactChart
            totalRevenuePaise={all.total_revenue_paise}
            baselineRevenuePaise={all.baseline_revenue_paise}
            baselineLabel={all.baseline_label}
          />
        )}

        {/* Audit trail — 3 rows by default, expands on demand */}
        <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
          <AuditTrail merchantId={1} />
        </div>

        <div className="grid gap-3">
          {/* Orders table */}
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="flex items-center gap-2.5 border-b border-slate-100 bg-white px-3 py-2.5">
              <span className="flex h-7 w-7 items-center justify-center rounded-md bg-slate-900" aria-hidden="true">
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

        <p className="text-[11px] text-slate-400" title={summary?.conversion_note}>
          Conversion = paid orders over tracked AI sessions.
        </p>
      </div>
    </div>
  );
}
