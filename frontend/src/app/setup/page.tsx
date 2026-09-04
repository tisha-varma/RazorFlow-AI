"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck, ArrowLeft, Save, AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { fetchJson } from "@/lib/api";

export default function SetupPolicy() {
  const router = useRouter();

  // Loading states
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Policy ID if policy already exists
  const [policyId, setPolicyId] = useState<number | null>(null);

  // Form states (converted to UI input values in Rupees)
  const [maxTxn, setMaxTxn] = useState("5000");
  const [minTxn, setMinTxn] = useState("0");
  const [requireApproval, setRequireApproval] = useState(true);
  const [maxQty, setMaxQty] = useState("5");
  const [allowUpsell, setAllowUpsell] = useState(true);
  const [maxUpsell, setMaxUpsell] = useState("2000");
  const [allowRetry, setAllowRetry] = useState(false);
  const [spendingLimit, setSpendingLimit] = useState("10000");

  useEffect(() => {
    // Fetch policy to check if already exists
    fetchJson("/policy")
      .then((data) => {
        setPolicyId(data.id);
        setMaxTxn((data.max_transaction_amount_paise / 100).toString());
        setMinTxn(((data.min_transaction_amount_paise ?? 0) / 100).toString());
        setRequireApproval(data.require_approval);
        setMaxQty(data.max_quantity_per_item.toString());
        setAllowUpsell(data.allow_upsell);
        setMaxUpsell((data.max_upsell_amount_paise / 100).toString());
        setAllowRetry(data.allow_auto_retry);
        setSpendingLimit((data.spending_limit_paise / 100).toString());
        setLoading(false);
      })
      .catch((err) => {
        // Normal first-run scenario: backend 404s with "No active commerce
        // policy..." — show the blank form instead of an error.
        const msg = String(err.message || "");
        if (msg.includes("404") || msg.includes("No active commerce policy")) {
          setLoading(false);
          return;
        }
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(false);

    // Validate inputs
    const txnAmount = parseFloat(maxTxn);
    const minAmount = parseFloat(minTxn);
    const qtyAmount = parseInt(maxQty);
    const upsellAmount = parseFloat(maxUpsell);
    const limitAmount = parseFloat(spendingLimit);

    if (isNaN(txnAmount) || txnAmount <= 0 || txnAmount > 100000) {
      setError("Max transaction amount must be between ₹1 and ₹100,000");
      setSaving(false);
      return;
    }
    if (isNaN(minAmount) || minAmount < 0 || minAmount >= txnAmount) {
      setError("Min transaction amount must be ₹0 or more and below the max transaction amount");
      setSaving(false);
      return;
    }
    if (isNaN(qtyAmount) || qtyAmount <= 0 || qtyAmount > 100) {
      setError("Max quantity per item must be between 1 and 100");
      setSaving(false);
      return;
    }
    if (isNaN(upsellAmount) || upsellAmount < 0 || upsellAmount > txnAmount) {
      setError("Max upsell amount cannot be negative and cannot exceed the max transaction amount");
      setSaving(false);
      return;
    }
    if (isNaN(limitAmount) || limitAmount <= 0) {
      setError("Session spending limit must be a positive number");
      setSaving(false);
      return;
    }

    // Prepare payload in paise
    const payload = {
      max_transaction_amount_paise: Math.round(txnAmount * 100),
      min_transaction_amount_paise: Math.round(minAmount * 100),
      require_approval: requireApproval,
      max_quantity_per_item: qtyAmount,
      allow_upsell: allowUpsell,
      max_upsell_amount_paise: Math.round(upsellAmount * 100),
      allow_auto_retry: allowRetry,
      spending_limit_paise: Math.round(limitAmount * 100),
    };

    try {
      const endpoint = policyId ? `/policy/${policyId}` : "/policy?merchant_id=1";
      const method = policyId ? "PUT" : "POST";

      const data = await fetchJson(endpoint, {
        method,
        body: JSON.stringify(payload),
      });
      if (!policyId && data?.id) setPolicyId(data.id);

      setSuccess(true);
      setTimeout(() => {
        router.push("/buyer");
      }, 1500);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit policy configuration");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-stone-100 flex flex-col items-center justify-center text-slate-900">
        <RefreshCw className="h-8 w-8 animate-spin text-indigo-500 mb-4" />
        <p className="text-slate-500 text-sm">Loading policy settings...</p>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-stone-100 text-slate-900 py-12 px-6 flex flex-col justify-center items-center overflow-hidden">
      <div className="w-full max-w-xl relative z-10">
        <Button
          variant="ghost"
          onClick={() => router.push("/")}
          className="mb-6 rounded-full text-slate-500 hover:text-slate-900 hover:bg-white"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Home
        </Button>

        <form onSubmit={handleSubmit}>
          <Card className="bg-white border-slate-200/80 shadow-[0_16px_40px_-16px_rgba(15,23,42,0.25)] overflow-hidden">
            <div className="h-1 bg-slate-900" aria-hidden="true" />
            <CardHeader className="border-b border-slate-100 pb-6">
              <div className="flex justify-between items-center">
                <div className="h-10 w-10 rounded-lg bg-slate-900 flex items-center justify-center">
                  <ShieldCheck className="h-5 w-5 text-white" />
                </div>
                <Badge variant="outline" className="rounded-full border-emerald-300 text-emerald-700 bg-emerald-50 text-xs">
                  {policyId ? "Policy Active" : "First-Run Setup"}
                </Badge>
              </div>
              <CardTitle className="text-2xl font-bold mt-4 text-slate-900">Commerce Policy Configuration</CardTitle>
              <CardDescription className="text-slate-500">
                Setup the spending limits and rules. Every money action will be checked against this configuration by the Policy Engine.
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-6 pt-6">
              {error && (
                <Alert variant="destructive" className="bg-red-50 border-red-300 text-red-700">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Error</AlertTitle>
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {success && (
                <Alert className="bg-emerald-50 border-emerald-300 text-emerald-700">
                  <ShieldCheck className="h-4 w-4 text-emerald-600" />
                  <AlertTitle>Success</AlertTitle>
                  <AlertDescription>Commerce Policy settings updated. Taking you to the buyer…</AlertDescription>
                </Alert>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="maxTxn" className="text-slate-700">Max Transaction (₹)</Label>
                  <Input
                    id="maxTxn"
                    type="number"
                    value={maxTxn}
                    onChange={(e) => setMaxTxn(e.target.value)}
                    className="bg-white border-slate-300 focus-visible:ring-indigo-500 text-slate-900"
                    placeholder="5000"
                    required
                  />
                  <p className="text-[10px] text-slate-500">Max per single transaction.</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="minTxn" className="text-slate-700">Min Transaction (₹)</Label>
                  <Input
                    id="minTxn"
                    type="number"
                    value={minTxn}
                    onChange={(e) => setMinTxn(e.target.value)}
                    className="bg-white border-slate-300 focus-visible:ring-indigo-500 text-slate-900"
                    placeholder="0"
                    required
                  />
                  <p className="text-[10px] text-slate-500">Floor per transaction — 0 disables it.</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="spendingLimit" className="text-slate-700">Session Limit (₹)</Label>
                  <Input
                    id="spendingLimit"
                    type="number"
                    value={spendingLimit}
                    onChange={(e) => setSpendingLimit(e.target.value)}
                    className="bg-white border-slate-300 focus-visible:ring-indigo-500 text-slate-900"
                    placeholder="10000"
                    required
                  />
                  <p className="text-[10px] text-slate-500">Total allowed per chat session.</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="maxQty" className="text-slate-700">Max Item Quantity</Label>
                  <Input
                    id="maxQty"
                    type="number"
                    value={maxQty}
                    onChange={(e) => setMaxQty(e.target.value)}
                    className="bg-white border-slate-300 focus-visible:ring-indigo-500 text-slate-900"
                    placeholder="5"
                    required
                  />
                  <p className="text-[10px] text-slate-500">Max units of a single product.</p>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="maxUpsell" className="text-slate-700">Max Upsell Total (₹)</Label>
                <Input
                  id="maxUpsell"
                  type="number"
                  disabled={!allowUpsell}
                  value={maxUpsell}
                  onChange={(e) => setMaxUpsell(e.target.value)}
                  className="bg-white border-slate-300 focus-visible:ring-indigo-500 text-slate-900 disabled:opacity-50"
                  placeholder="2000"
                  required={allowUpsell}
                />
                <p className="text-[10px] text-slate-500">Limit on cross-sell items.</p>
              </div>

              <div className="border-t border-slate-100 my-4" />

              {/* Switches */}
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 rounded-xl bg-stone-50 border border-slate-200">
                  <div className="space-y-0.5">
                    <Label htmlFor="requireApproval" className="text-slate-800 text-sm">Require Payment Approval</Label>
                    <p className="text-xs text-slate-500">Payment must be explicitly approved by user before checkout.</p>
                  </div>
                  <Switch
                    id="requireApproval"
                    checked={requireApproval}
                    onCheckedChange={setRequireApproval}
                    disabled={true} // Hard lock recommended by problem statement
                  />
                </div>

                <div className="flex items-center justify-between p-3 rounded-xl bg-stone-50 border border-slate-200">
                  <div className="space-y-0.5">
                    <Label htmlFor="allowUpsell" className="text-slate-800 text-sm">Enable AI Upsell Recommendations</Label>
                    <p className="text-xs text-slate-500">Allow the AI to recommend logical accessories.</p>
                  </div>
                  <Switch
                    id="allowUpsell"
                    checked={allowUpsell}
                    onCheckedChange={setAllowUpsell}
                  />
                </div>

                <div className="flex items-center justify-between p-3 rounded-xl bg-stone-50 border border-slate-200">
                  <div className="space-y-0.5">
                    <Label htmlFor="allowRetry" className="text-slate-800 text-sm">Automatic Retry on Failure</Label>
                    <p className="text-xs text-slate-500">Try checking out again automatically on transient failures.</p>
                  </div>
                  <Switch
                    id="allowRetry"
                    checked={allowRetry}
                    onCheckedChange={setAllowRetry}
                  />
                </div>
              </div>
            </CardContent>

            <CardFooter className="border-t border-slate-100 pt-6 flex justify-end gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => router.push("/")}
                disabled={saving}
                className="rounded-full"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={saving}
                className="rounded-full bg-blue-700 hover:bg-blue-600 text-white font-semibold"
              >
                <Save className="mr-2 h-4 w-4" />
                {saving ? "Saving Configuration..." : "Save Policy Config"}
              </Button>
            </CardFooter>
          </Card>
        </form>
      </div>
    </div>
  );
}
