"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ShieldCheck, ShoppingBag, LayoutDashboard, Settings, ArrowRight, Activity, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function Home() {
  const [policyStatus, setPolicyStatus] = useState<"loading" | "setup_required" | "configured">("loading");
  const [policyDetails, setPolicyDetails] = useState<any>(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/policy")
      .then((res) => {
        if (res.status === 404 || !res.ok) {
          setPolicyStatus("setup_required");
        } else {
          return res.json();
        }
      })
      .then((data) => {
        if (data) {
          setPolicyDetails(data);
          setPolicyStatus("configured");
        }
      })
      .catch(() => {
        // API offline or error
        setPolicyStatus("setup_required");
      });
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between relative overflow-hidden">
      {/* Background gradients for fintech premium glow */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-blue-600/10 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-violet-600/10 blur-[120px] pointer-events-none" />

      {/* Header */}
      <header className="border-b border-slate-900 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white shadow-[0_0_15px_rgba(37,99,235,0.4)]">
              R
            </div>
            <span className="font-extrabold text-xl tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
              RazorFlow AI
            </span>
            <Badge variant="outline" className="border-blue-500/30 text-blue-400 bg-blue-950/20 text-xs gap-1 py-0.5">
              <Activity className="h-3 w-3 animate-pulse" />
              Test Mode
            </Badge>
          </div>
          
          <div className="flex items-center gap-4">
            {policyStatus === "configured" ? (
              <Badge variant="outline" className="border-emerald-500/30 text-emerald-400 bg-emerald-950/20 gap-1.5 py-1 px-3">
                <ShieldCheck className="h-3.5 w-3.5" />
                Commerce Policy Active
              </Badge>
            ) : policyStatus === "loading" ? (
              <Badge variant="outline" className="border-slate-800 text-slate-400 py-1 px-3">
                Checking policy...
              </Badge>
            ) : (
              <Badge variant="outline" className="border-amber-500/30 text-amber-400 bg-amber-950/20 gap-1.5 py-1 px-3 animate-pulse">
                <AlertTriangle className="h-3.5 w-3.5" />
                Setup Required
              </Badge>
            )}
          </div>
        </div>
      </header>

      {/* Hero section */}
      <main className="max-w-7xl mx-auto px-6 py-12 flex-1 flex flex-col justify-center items-center relative z-10 w-full">
        <div className="text-center max-w-3xl mb-12">
          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-white mb-6 leading-tight">
            Safe, Explainable & Bounded <br />
            <span className="bg-gradient-to-r from-blue-400 via-indigo-400 to-violet-400 bg-clip-text text-transparent">
              Agentic Commerce
            </span>
          </h1>
          <p className="text-lg text-slate-400 leading-relaxed">
            Welcome to RazorFlow AI, an intelligent buyer agent that interfaces with merchant catalogs
            and executes transactions securely via Razorpay Test Mode under a strict, user-approved Policy Engine.
          </p>
        </div>

        {/* Option Cards */}
        <div className="grid md:grid-cols-3 gap-6 w-full max-w-5xl mt-4">
          
          {/* Card 1: Setup Policy (Phase 1-2 Requirement) */}
          <Card className="bg-slate-900/40 border-slate-800/80 backdrop-blur-sm hover:border-slate-700/80 transition-all duration-300 flex flex-col group relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-amber-500/0 via-amber-500/40 to-amber-500/0 opacity-0 group-hover:opacity-100 transition-opacity" />
            <CardHeader>
              <div className="h-12 w-12 rounded-xl bg-amber-950/40 border border-amber-500/20 flex items-center justify-center text-amber-400 mb-2">
                <Settings className="h-6 w-6" />
              </div>
              <CardTitle className="text-xl text-white">1. Configure Policy</CardTitle>
              <CardDescription className="text-slate-400">
                Define the rules: max amounts, session spending limits, item quantities, and upsell configurations.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-1 text-sm text-slate-400">
              {policyDetails ? (
                <div className="space-y-1.5 p-3 rounded-lg bg-slate-950/50 border border-slate-800 text-xs font-mono">
                  <div>Max Txn: ₹{policyDetails.max_transaction_amount_paise / 100}</div>
                  <div>Limit: ₹{policyDetails.spending_limit_paise / 100}</div>
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

          {/* Card 2: AI Buyer */}
          <Card className="bg-slate-900/40 border-slate-800/80 backdrop-blur-sm hover:border-slate-700/80 transition-all duration-300 flex flex-col group relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-blue-500/0 via-blue-500/40 to-blue-500/0 opacity-0 group-hover:opacity-100 transition-opacity" />
            <CardHeader>
              <div className="h-12 w-12 rounded-xl bg-blue-950/40 border border-blue-500/20 flex items-center justify-center text-blue-400 mb-2">
                <ShoppingBag className="h-6 w-6" />
              </div>
              <CardTitle className="text-xl text-white">2. AI Buyer Client</CardTitle>
              <CardDescription className="text-slate-400">
                Engage in natural-language commerce. Discover running gear, get recommended items, and approve purchases.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-1 text-sm text-slate-400">
              <p>Experience safe agentic checkout with Razorpay. Try searching: <i>"I need daily trainers under ₹5,000"</i>.</p>
            </CardContent>
            <CardFooter className="pt-2">
              <Link href="/buyer" className="w-full">
                <Button disabled={policyStatus === "setup_required"} className="w-full bg-blue-600 hover:bg-blue-500 text-white group/btn">
                  Launch AI Buyer
                  <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover/btn:translate-x-1" />
                </Button>
              </Link>
            </CardFooter>
          </Card>

          {/* Card 3: Merchant Dashboard */}
          <Card className="bg-slate-900/40 border-slate-800/80 backdrop-blur-sm hover:border-slate-700/80 transition-all duration-300 flex flex-col group relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-violet-500/0 via-violet-500/40 to-violet-500/0 opacity-0 group-hover:opacity-100 transition-opacity" />
            <CardHeader>
              <div className="h-12 w-12 rounded-xl bg-violet-950/40 border border-violet-500/20 flex items-center justify-center text-violet-400 mb-2">
                <LayoutDashboard className="h-6 w-6" />
              </div>
              <CardTitle className="text-xl text-white">3. Merchant Portal</CardTitle>
              <CardDescription className="text-slate-400">
                Inspect AI-driven sales, live orders, transaction audit trails, CSV imports, and revenue metrics.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-1 text-sm text-slate-400">
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
      <footer className="border-t border-slate-900 bg-slate-950 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-4">
          <p>© 2026 RazorFlow AI. Razorpay Test Mode Demo.</p>
          <div className="flex gap-4">
            <Link href="/setup" className="hover:text-slate-300 transition-colors">Setup Policy</Link>
            <span className="text-slate-800">|</span>
            <Link href="/buyer" className="hover:text-slate-300 transition-colors">AI Chat</Link>
            <span className="text-slate-800">|</span>
            <Link href="/merchant" className="hover:text-slate-300 transition-colors">Merchant Portal</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
