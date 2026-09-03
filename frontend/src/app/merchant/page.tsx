"use client";

import { useState, useEffect, useCallback } from "react";
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
  accent,
}: {
  icon: typeof Banknote;
  label: string;
  value: string;
  sub?: string;
  accent: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2">
        <span className={`flex h-8 w-8 items-center justify-center rounded-lg ${accent}`}>
          <Icon className="h-4 w-4" aria-hidden="true" />
        </span>
        <span className="text-[13px] font-medium text-slate-500">{label}</span>
      </div>
      <p className="mt-2 text-2xl font-bold tabular-nums text-slate-900">{value}</p>
      {sub && <p className="mt-0.5 text-xs tabular-nums text-slate-500">{sub}</p>}
    </div>
  );
}

export default function MerchantPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [funnel, setFunnel] = useState<FunnelStage[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = useCallback(async () => {
    try {
      const [summaryRes, funnelRes] = await Promise.all([
        fetch(`${API_BASE}/dashboard/summary?merchant_id=1`),
        fetch(`${API_BASE}/dashboard/funnel?merchant_id=1`),
      ]);
      if (!summaryRes.ok) throw new Error("Could not load dashboard");
      setSummary(await summaryRes.json());
      if (funnelRes.ok) {
        setFunnel((await funnelRes.json()).stages ?? []);
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load dashboard");
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
    const timer = setInterval(fetchDashboard, 5000);
    return () => clearInterval(timer);
  }, [fetchDashboard]);

  const all = summary?.all_time;
  const today = summary?.today;

  return (
    <div className="min-h-screen bg-stone-100 text-slate-900 flex flex-col">
      <header className="border-b border-slate-200 bg-white px-4 py-3 flex items-center gap-4 shadow-sm">
        <Link href="/">
          <Button variant="ghost" size="sm" className="text-slate-500 hover:text-slate-900">
            <ArrowLeft className="h-4 w-4 mr-1" aria-hidden="true" />
            Back
          </Button>
        </Link>
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-lg bg-emerald-600 flex items-center justify-center text-xs font-bold text-white">
            M
          </div>
          <h1 className="font-semibold text-[15px] text-slate-900">Merchant Console</h1>
        </div>
        <span className="ml-auto text-xs text-slate-500">
          SprintGear India · live
        </span>
      </header>

      <div className="mx-auto w-full max-w-5xl space-y-4 p-4 md:p-6">
        {error && (
          <div className="rounded-xl border border-red-300 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Stat cards */}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard
            icon={Banknote}
            label="Total revenue"
            value={all ? formatPaise(all.total_revenue_paise) : "—"}
            sub={today ? `Today ${formatPaise(today.total_revenue_paise)}` : undefined}
            accent="bg-emerald-100 text-emerald-700"
          />
          <StatCard
            icon={Receipt}
            label="Avg order value"
            value={all ? formatPaise(all.avg_order_value_paise) : "—"}
            sub={all ? `${all.order_count} paid orders · ${all.ai_assisted_orders} AI-assisted` : undefined}
            accent="bg-indigo-100 text-indigo-700"
          />
          <StatCard
            icon={Percent}
            label="AI conversion"
            value={summary ? `${summary.conversion_rate_pct}%` : "—"}
            sub={summary ? `${summary.conversion_sessions} AI sessions (approx)` : undefined}
            accent="bg-sky-100 text-sky-700"
          />
          <StatCard
            icon={Gift}
            label="Upsell revenue"
            value={all ? formatPaise(all.upsell_revenue_paise) : "—"}
            sub={all ? `${all.upsell_pct}% of revenue` : undefined}
            accent="bg-amber-100 text-amber-800"
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

        <div className="grid gap-4 lg:grid-cols-5">
          {/* Orders table */}
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm lg:col-span-3">
            <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3">
              <TrendingUp className="h-4 w-4 text-slate-500" aria-hidden="true" />
              <h2 className="text-sm font-semibold text-slate-900">Recent orders</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left">
                <caption className="sr-only">Recent orders</caption>
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    <th scope="col" className="px-4 py-2">Order</th>
                    <th scope="col" className="px-4 py-2">Items</th>
                    <th scope="col" className="px-4 py-2 text-right">Amount</th>
                    <th scope="col" className="px-4 py-2">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {(summary?.recent_orders ?? []).map((order) => (
                    <tr key={order.id} className="align-top hover:bg-slate-50">
                      <td className="px-4 py-2.5">
                        <p className="font-mono text-xs font-semibold text-slate-800">
                          {order.order_number}
                        </p>
                        <p className="mt-0.5 text-[11px] text-slate-400">
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
                            className="mt-1 border-indigo-200 bg-indigo-50 text-[10px] text-indigo-700"
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
                          className={`text-[11px] ${STATUS_STYLES[order.status] ?? STATUS_STYLES.cancelled}`}
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

          {/* Audit trail */}
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm lg:col-span-2">
            <div className="h-[420px]">
              <AuditTrail merchantId={1} />
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
