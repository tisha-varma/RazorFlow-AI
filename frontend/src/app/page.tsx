"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ShieldCheck, ShoppingBag, LayoutDashboard, Settings, ArrowRight, Activity, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { fetchJson } from "@/lib/api";

export default function Home() {
  const [policyStatus, setPolicyStatus] = useState<"loading" | "setup_required" | "configured">("loading");
  const [policyDetails, setPolicyDetails] = useState<{
    max_transaction_amount_paise: number;
    spending_limit_paise: number;
    require_approval: boolean;
  } | null>(null);
  const [stats, setStats] = useState<{
    order_count: number;
    total_revenue_paise: number;
    aov_uplift_pct: number;
    upsell_revenue_paise: number;
  } | null>(null);

  useEffect(() => {
    fetchJson("/policy")
      .then((data) => {
        setPolicyDetails(data);
        setPolicyStatus("configured");
      })
      .catch(() => {
        // API offline or no active policy yet
        setPolicyStatus("setup_required");
      });
    // Live merchant proof for the first screen — silent when unreachable.
    fetchJson("/dashboard/summary?merchant_id=1")
      .then((data) => {
        if (data?.all_time) setStats(data.all_time);
      })
      .catch(() => {});
  }, []);

  return (
    <div className="min-h-screen bg-stone-100 text-slate-900 flex flex-col justify-between">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white">
              R
            </div>
            <span className="font-semibold text-xl tracking-tight text-slate-900">
              RazorFlow AI
            </span>
            <Badge variant="outline" className="border-slate-300 text-slate-600 bg-slate-50 text-xs gap-1 py-0.5">
              <Activity className="h-3 w-3 animate-pulse" />
              Test Mode
            </Badge>
          </div>

          <div className="flex items-center gap-4">
            {policyStatus === "configured" ? (
              <Badge variant="outline" className="border-emerald-300 text-emerald-700 bg-emerald-50 gap-1.5 py-1 px-3">
                <ShieldCheck className="h-3.5 w-3.5" />
                Commerce Policy Active
              </Badge>
            ) : policyStatus === "loading" ? (
              <Badge variant="outline" className="border-slate-300 text-slate-500 py-1 px-3">
                Checking policy...
              </Badge>
            ) : (
              <Badge variant="outline" className="border-amber-300 text-amber-800 bg-amber-50 gap-1.5 py-1 px-3 animate-pulse">
                <AlertTriangle className="h-3.5 w-3.5" />
                Setup Required
              </Badge>
            )}
          </div>
        </div>
      </header>

      {/* Hero section */}
      <main className="max-w-7xl mx-auto px-6 py-12 flex-1 flex flex-col justify-center items-center w-full">
        <div className="text-center max-w-3xl mb-12">
          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-slate-900 mb-6 leading-tight">
            Safe, Explainable & Bounded <br />
            <span className="text-blue-700">
              Agentic Commerce
            </span>
          </h1>
          <p className="text-lg text-slate-500 leading-relaxed">
            Welcome to RazorFlow AI, an intelligent buyer agent that interfaces with merchant catalogs
            and executes transactions securely via Razorpay Test Mode under a strict, user-approved Policy Engine.
          </p>
          <p className="mt-3 text-[15px] font-semibold text-slate-700">
            AI chat increases average order value through explainable upsells —
            every rupee gated by policy, approved by a human, paid on Razorpay test mode.
          </p>
          {stats && stats.order_count > 0 && (
            <div className="mx-auto mt-6 flex max-w-xl items-stretch justify-center gap-3" aria-live="polite">
              {[
                {
                  value: `${stats.order_count}`,
                  label: "paid orders",
                },
                {
                  value: `₹${(stats.total_revenue_paise / 100).toLocaleString("en-IN")}`,
                  label: "merchant revenue",
                },
                {
                  value: `+${stats.aov_uplift_pct}%`,
                  label: "AOV lift from upsells",
                },
              ].map((s) => (
                <div
                  key={s.label}
                  className="flex-1 rounded-2xl border border-slate-200/80 bg-white px-3 py-3 shadow-[0_8px_24px_-12px_rgba(15,23,42,0.25)]"
                >
                  <p className="text-xl font-extrabold tabular-nums text-slate-900">
                    {s.value}
                  </p>
                  <p className="mt-0.5 text-[11px] font-medium text-slate-500">{s.label}</p>
                </div>
              ))}
            </div>
          )}
          <Link href="/buyer" className="mt-8 inline-flex">
            <Button className="h-12 px-8 text-base bg-blue-700 hover:bg-blue-600 text-white shadow-sm touch-manipulation">
              Start buying with AI
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
          </Link>
        </div>

        {/* Option Cards */}
        <div className="grid md:grid-cols-3 gap-6 w-full max-w-5xl mt-4">

          {/* Card 1: AI Buyer */}
          <Card className="bg-white border-slate-200 shadow-md hover:shadow-lg transition-all duration-300 flex flex-col group relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-[3px] bg-blue-600" />
            <CardHeader>
              <div className="h-12 w-12 rounded-xl bg-indigo-100 flex items-center justify-center text-indigo-700 mb-2">
                <ShoppingBag className="h-6 w-6" />
              </div>
              <CardTitle className="text-xl text-slate-900">1. AI Buyer Client</CardTitle>
              <CardDescription className="text-slate-500">
                Engage in natural-language commerce. Discover running gear, get recommended items, and approve purchases.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-1 text-sm text-slate-500">
              <p>Experience safe agentic checkout with Razorpay. Try searching: <i>&ldquo;I need daily trainers under ₹5,000&rdquo;</i>.</p>
            </CardContent>
            <CardFooter className="pt-2">
              <Link href="/buyer" className="w-full">
                <Button className="w-full bg-blue-700 hover:bg-blue-600 text-white group/btn">
                  Launch AI Buyer
                  <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover/btn:translate-x-1" />
                </Button>
              </Link>
            </CardFooter>
          </Card>

          {/* Card 2: Setup Policy (Phase 1-2 Requirement) */}
          <Card className="bg-white border-slate-200 shadow-md hover:shadow-lg transition-all duration-300 flex flex-col group relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-[3px] bg-amber-500" />
            <CardHeader>
              <div className="h-12 w-12 rounded-xl bg-amber-100 flex items-center justify-center text-amber-700 mb-2">
                <Settings className="h-6 w-6" />
              </div>
              <CardTitle className="text-xl text-slate-900">2. Configure Policy</CardTitle>
              <CardDescription className="text-slate-500">
                Define the rules: max amounts, session spending limits, item quantities, and upsell configurations.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-1 text-sm text-slate-500">
              {policyDetails ? (
                <div className="space-y-1.5 p-3 rounded-lg bg-stone-100 border border-slate-200 text-xs font-mono text-slate-700">
                  <div>Max Txn: ₹{(policyDetails.max_transaction_amount_paise / 100).toLocaleString("en-IN")}</div>
                  <div>Limit: ₹{(policyDetails.spending_limit_paise / 100).toLocaleString("en-IN")}</div>
                  <div>Approval Required: {policyDetails.require_approval ? "Yes" : "No"}</div>
                </div>
              ) : (
                <p>Run the first-run configuration to activate safety limits before transacting.</p>
              )}
            </CardContent>
            <CardFooter className="pt-2">
              <Link href="/setup" className="w-full">
                <Button variant={policyStatus === "setup_required" ? "default" : "secondary"} className={`w-full group/btn ${policyStatus === "setup_required" ? "bg-amber-600 hover:bg-amber-500 text-white" : ""}`}>
                  {policyStatus === "setup_required" ? "Start Policy Setup" : "Edit Policy Settings"}
                  <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover/btn:translate-x-1" />
                </Button>
              </Link>
            </CardFooter>
          </Card>

          {/* Card 3: Merchant Dashboard */}
          <Card className="bg-white border-slate-200 shadow-md hover:shadow-lg transition-all duration-300 flex flex-col group relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-[3px] bg-emerald-500" />
            <CardHeader>
              <div className="h-12 w-12 rounded-xl bg-emerald-100 flex items-center justify-center text-emerald-700 mb-2">
                <LayoutDashboard className="h-6 w-6" />
              </div>
              <CardTitle className="text-xl text-slate-900">3. Merchant Portal</CardTitle>
              <CardDescription className="text-slate-500">
                Inspect AI-driven sales, live orders, transaction audit trails, and revenue metrics.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-1 text-sm text-slate-500">
              <p>Review the comprehensive timeline of events showcasing the full audit trail of AI agent actions.</p>
            </CardContent>
            <CardFooter className="pt-2">
              <Link href="/merchant" className="w-full">
                <Button variant="secondary" className="w-full group/btn">
                  Merchant Console
                  <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover/btn:translate-x-1" />
                </Button>
              </Link>
            </CardFooter>
          </Card>

        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-4">
          <p>© 2026 RazorFlow AI. Razorpay Test Mode Demo.</p>
          <div className="flex gap-4">
            <Link href="/setup" className="hover:text-slate-900 transition-colors">Setup Policy</Link>
            <span className="text-slate-300">|</span>
            <Link href="/buyer" className="hover:text-slate-900 transition-colors">AI Chat</Link>
            <span className="text-slate-300">|</span>
            <Link href="/merchant" className="hover:text-slate-900 transition-colors">Merchant Portal</Link>
            <span className="text-slate-300">|</span>
            <Link href="/judge" className="hover:text-slate-900 transition-colors">Judge Mode</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
