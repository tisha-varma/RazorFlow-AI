"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { CreditCard, Loader2, CheckCircle2, XCircle } from "lucide-react";

interface PaidOrder {
  order_id: number;
  order_number: string;
  total_paise: number;
}

interface PaymentBoxProps {
  approvalId: number;
  sessionId: string;
  onPaid?: (order: PaidOrder) => void;
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

type Phase = "idle" | "creating" | "checkout" | "verifying" | "success" | "failed";

let checkoutJsPromise: Promise<void> | null = null;
function loadCheckoutJs(): Promise<void> {
  if ((window as unknown as { Razorpay?: unknown }).Razorpay) {
    return Promise.resolve();
  }
  if (!checkoutJsPromise) {
    checkoutJsPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.onload = () => resolve();
      script.onerror = () =>
        reject(new Error("Could not load Razorpay Checkout. Check your connection."));
      document.body.appendChild(script);
    });
  }
  return checkoutJsPromise;
}

function formatPaise(paise: number): string {
  return `₹${(paise / 100).toLocaleString("en-IN")}`;
}

export function PaymentBox({ approvalId, sessionId, onPaid }: PaymentBoxProps) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [paidOrder, setPaidOrder] = useState<PaidOrder | null>(null);

  const startPayment = async () => {
    setPhase("creating");
    setError(null);
    try {
      // 1. Server-side order creation (never client-side).
      const res = await fetch(`${API_BASE}/payment/create-order/${approvalId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Could not create payment order");
      }
      const order = await res.json();

      await loadCheckoutJs();
      setPhase("checkout");

      // 2. Open Razorpay Checkout with the server-created order_id.
      const Razorpay = (window as unknown as { Razorpay: new (o: object) => { open: () => void; on: (e: string, cb: (r: { error?: { description?: string } }) => void) => void } }).Razorpay;
      const rzp = new Razorpay({
        key: order.key_id,
        amount: order.amount_paise,
        currency: order.currency || "INR",
        name: "SprintGear India",
        description: `Order ${order.order_number} (test mode)`,
        order_id: order.razorpay_order_id,
        theme: { color: "#7c3aed" },
        modal: { ondismiss: () => setPhase((p) => (p === "checkout" ? "idle" : p)) },
        handler: async (response: {
          razorpay_payment_id: string;
          razorpay_order_id: string;
          razorpay_signature: string;
        }) => {
          // 3. Server-side signature verification before fulfilment.
          setPhase("verifying");
          try {
            const vres = await fetch(`${API_BASE}/payment/verify`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
                session_id: sessionId,
              }),
            });
            if (!vres.ok) {
              const data = await vres.json().catch(() => ({}));
              throw new Error(data.detail || "Payment verification failed");
            }
            const paid: PaidOrder = await vres.json();
            setPaidOrder(paid);
            setPhase("success");
            onPaid?.(paid);
          } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Verification failed");
            setPhase("failed");
          }
        },
      });
      rzp.on("payment.failed", (resp: { error?: { description?: string } }) => {
        setError(resp.error?.description || "Payment failed at the gateway. You can retry.");
        setPhase("failed");
      });
      rzp.open();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Payment could not start");
      setPhase("failed");
    }
  };

  return (
    <div className="rounded-xl border border-violet-500/30 bg-violet-950/40 p-4">
      <div className="mb-2 flex items-center gap-2">
        <CreditCard className="h-4 w-4 text-violet-300" />
        <h3 className="text-sm font-semibold text-white">Payment</h3>
      </div>

      {phase === "success" && paidOrder ? (
        <div className="flex items-start gap-2 rounded-lg border border-emerald-500/30 bg-emerald-950/40 p-3">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
          <div className="text-sm">
            <p className="font-medium text-emerald-300">Payment successful</p>
            <p className="mt-0.5 font-mono text-xs text-emerald-400/80">
              {paidOrder.order_number} · {formatPaise(paidOrder.total_paise)}
            </p>
          </div>
        </div>
      ) : (
        <>
          <p className="mb-1 text-xs text-slate-400">
            Test mode — pay with a Razorpay test card or UPI to complete the order.
          </p>
          {(phase === "creating" || phase === "verifying") && (
            <div className="mb-2 flex items-center gap-2 rounded-lg border border-violet-500/20 bg-violet-950/60 p-2.5 text-xs text-violet-200">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              {phase === "creating"
                ? "Creating secure order on the server…"
                : "Verifying payment signature on the server…"}
            </div>
          )}
          {phase === "failed" && error && (
            <div className="mb-2 flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-950/40 p-2.5 text-xs text-red-300">
              <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}
          <Button
            onClick={startPayment}
            disabled={phase === "creating" || phase === "verifying" || phase === "checkout"}
            className="w-full bg-violet-600 hover:bg-violet-500 text-white"
          >
            {(phase === "creating" || phase === "verifying") && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            {phase === "failed"
              ? "Retry payment"
              : phase === "checkout"
                ? "Checkout open — complete payment…"
                : "Pay securely with Razorpay"}
          </Button>
        </>
      )}
    </div>
  );
}
