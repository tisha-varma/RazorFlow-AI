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
  const [requireApproval, setRequireApproval] = useState(true);
  const [maxQty, setMaxQty] = useState("5");
  const [allowUpsell, setAllowUpsell] = useState(true);
  const [maxUpsell, setMaxUpsell] = useState("2000");
  const [allowRetry, setAllowRetry] = useState(false);
  const [spendingLimit, setSpendingLimit] = useState("10000");

  useEffect(() => {
    // Fetch policy to check if already exists
    fetch("http://localhost:8000/api/policy")
      .then((res) => {
        if (res.ok) {
          return res.json();
        }
        if (res.status === 404) {
          // Normal first-run scenario
          setLoading(false);
          return null;
        }
        throw new Error("Failed to fetch existing policy settings");
      })
      .then((data) => {
        if (data) {
          setPolicyId(data.id);
          setMaxTxn((data.max_transaction_amount_paise / 100).toString());
          setRequireApproval(data.require_approval);
          setMaxQty(data.max_quantity_per_item.toString());
          setAllowUpsell(data.allow_upsell);
          setMaxUpsell((data.max_upsell_amount_paise / 100).toString());
          setAllowRetry(data.allow_auto_retry);
          setSpendingLimit((data.spending_limit_paise / 100).toString());
          setLoading(false);
        }
      })
      .catch((err) => {
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
    const qtyAmount = parseInt(maxQty);
    const upsellAmount = parseFloat(maxUpsell);
    const limitAmount = parseFloat(spendingLimit);

    if (isNaN(txnAmount) || txnAmount <= 0 || txnAmount > 100000) {
      setError("Max transaction amount must be between ₹1 and ₹100,000");
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
      require_approval: requireApproval,
      max_quantity_per_item: qtyAmount,
      allow_upsell: allowUpsell,
      max_upsell_amount_paise: Math.round(upsellAmount * 100),
      allow_auto_retry: allowRetry,
      spending_limit_paise: Math.round(limitAmount * 100),
    };

    try {
      const url = policyId 
        ? `http://localhost:8000/api/policy/${policyId}`
        : "http://localhost:8000/api/policy?merchant_id=1";
        
      const method = policyId ? "PUT" : "POST";

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to save policy settings");
      }

      setSuccess(true);
      setTimeout(() => {
        router.push("/");
      }, 1500);
    } catch (err: any) {
      setError(err.message || "Failed to submit policy configuration");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-100">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-500 mb-4" />
        <p className="text-slate-400 text-sm">Loading policy settings...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-12 px-6 flex flex-col justify-center items-center relative overflow-hidden">
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-blue-600/5 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-violet-600/5 blur-[120px] pointer-events-none" />

      <div className="w-full max-w-xl relative z-10">
        <Button 
          variant="ghost" 
          onClick={() => router.push("/")}
          className="mb-6 text-slate-400 hover:text-white"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Home
        </Button>

        <form onSubmit={handleSubmit}>
          <Card className="bg-slate-900/40 border-slate-800 backdrop-blur-md">
            <CardHeader className="border-b border-slate-800/80 pb-6">
              <div className="flex justify-between items-center">
                <div className="h-10 w-10 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <Badge variant="outline" className="border-blue-500/30 text-blue-400 bg-blue-950/20 text-xs">
                  {policyId ? "Policy Active" : "First-Run Setup"}
                </Badge>
              </div>
              <CardTitle className="text-2xl font-bold mt-4 text-white">Commerce Policy Configuration</CardTitle>
              <CardDescription className="text-slate-400">
                Setup the spending limits and rules. Every money action will be checked against this configuration by the Policy Engine.
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-6 pt-6">
              {error && (
                <Alert variant="destructive" className="bg-red-950/20 border-red-500/30 text-red-400">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Error</AlertTitle>
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {success && (
                <Alert className="bg-emerald-950/20 border-emerald-500/30 text-emerald-400">
                  <ShieldCheck className="h-4 w-4 text-emerald-400" />
                  <AlertTitle>Success</AlertTitle>
                  <AlertDescription>Commerce Policy settings updated. Redirecting...</AlertDescription>
                </Alert>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="maxTxn" className="text-slate-200">Max Transaction (₹)</Label>
                  <Input 
                    id="maxTxn" 
                    type="number"
                    value={maxTxn}
                    onChange={(e) => setMaxTxn(e.target.value)}
                    className="bg-slate-950 border-slate-800 focus-visible:ring-blue-500 text-slate-100" 
                    placeholder="5000"
                    required
                  />
                  <p className="text-[10px] text-slate-500">Max per single transaction.</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="spendingLimit" className="text-slate-200">Session Limit (₹)</Label>
                  <Input 
                    id="spendingLimit" 
                    type="number"
                    value={spendingLimit}
                    onChange={(e) => setSpendingLimit(e.target.value)}
                    className="bg-slate-950 border-slate-800 focus-visible:ring-blue-500 text-slate-100" 
                    placeholder="10000"
                    required
                  />
                  <p className="text-[10px] text-slate-500">Total allowed per chat session.</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="maxQty" className="text-slate-200">Max Item Quantity</Label>
                  <Input 
                    id="maxQty" 
                    type="number"
                    value={maxQty}
                    onChange={(e) => setMaxQty(e.target.value)}
                    className="bg-slate-950 border-slate-800 focus-visible:ring-blue-500 text-slate-100" 
                    placeholder="5"
                    required
                  />
                  <p className="text-[10px] text-slate-500">Max units of a single product.</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="maxUpsell" className="text-slate-200">Max Upsell Total (₹)</Label>
                  <Input 
                    id="maxUpsell" 
                    type="number"
                    disabled={!allowUpsell}
                    value={maxUpsell}
                    onChange={(e) => setMaxUpsell(e.target.value)}
                    className="bg-slate-950 border-slate-800 focus-visible:ring-blue-500 text-slate-100 disabled:opacity-50" 
                    placeholder="2000"
                    required={allowUpsell}
                  />
                  <p className="text-[10px] text-slate-500">Limit on cross-sell items.</p>
                </div>
              </div>

              <div className="border-t border-slate-800/80 my-4" />

              {/* Switches */}
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/30 border border-slate-800/50">
                  <div className="space-y-0.5">
                    <Label htmlFor="requireApproval" className="text-slate-200 text-sm">Require Payment Approval</Label>
                    <p className="text-xs text-slate-500">Payment must be explicitly approved by user before checkout.</p>
                  </div>
                  <Switch 
                    id="requireApproval" 
                    checked={requireApproval} 
                    onCheckedChange={setRequireApproval}
                    disabled={true} // Hard lock recommended by problem statement
                  />
                </div>

                <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/30 border border-slate-800/50">
                  <div className="space-y-0.5">
                    <Label htmlFor="allowUpsell" className="text-slate-200 text-sm">Enable AI Upsell Recommendations</Label>
                    <p className="text-xs text-slate-500">Allow the AI to recommend logical accessories.</p>
                  </div>
                  <Switch 
                    id="allowUpsell" 
                    checked={allowUpsell} 
                    onCheckedChange={setAllowUpsell} 
                  />
                </div>

                <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/30 border border-slate-800/50">
                  <div className="space-y-0.5">
                    <Label htmlFor="allowRetry" className="text-slate-200 text-sm">Automatic Retry on Failure</Label>
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

            <CardFooter className="border-t border-slate-800/80 pt-6 flex justify-end gap-3">
              <Button 
                type="button" 
                variant="outline" 
                onClick={() => router.push("/")}
                disabled={saving}
                className="border-slate-800 text-slate-400 hover:text-white"
              >
                Cancel
              </Button>
              <Button 
                type="submit" 
                disabled={saving}
                className="bg-blue-600 hover:bg-blue-500 text-white font-semibold"
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
