"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { CreditCard, Loader2, CheckCircle2, XCircle } from "lucide-react";

interface PaidOrder {
  order_id: number;
  order_number: string;
  total_paise: number;
  razorpay_payment_id?: string | null;
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
    <div className="rounded-xl border border-slate-200 bg-white shadow-md p-5">
      <div className="mb-2 flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-emerald-100 flex items-center justify-center">
          <CreditCard className="h-3.5 w-3.5 text-emerald-700" aria-hidden="true" />
        </div>
        <h3 className="text-[15px] font-semibold text-slate-900">Payment</h3>
      </div>

      {phase === "success" && paidOrder ? (
        <div className="rounded-xl border border-emerald-300 bg-emerald-50 px-6 py-8 text-center shadow-sm" aria-live="polite">
          <CheckCircle2 className="mx-auto h-10 w-10 text-emerald-600" aria-hidden="true" />
          <h3 className="mt-3 text-lg font-bold tracking-wide text-emerald-800">
            PAYMENT SUCCESS ✓
          </h3>
          <p className="mt-2 text-3xl font-bold tabular-nums text-slate-900">
            {formatPaise(paidOrder.total_paise)}
          </p>
          <div className="mt-3 space-y-1 text-sm text-slate-600">
            <p>
              Order: <span className="font-mono font-semibold text-slate-800">{paidOrder.order_number}</span>
            </p>
            {paidOrder.razorpay_payment_id && (
              <p>
                Razorpay Payment:{" "}
                <span className="font-mono text-slate-800">{paidOrder.razorpay_payment_id}</span>
              </p>
            )}
          </div>
          <p className="mt-3 text-sm text-slate-600">Your order has been confirmed.</p>
          <Link
            href="/merchant"
            className="mt-4 inline-flex h-10 items-center justify-center rounded-lg bg-emerald-600 px-6 text-sm font-semibold text-white shadow-sm hover:bg-emerald-500 touch-manipulation"
          >
            View Order
          </Link>
        </div>
      ) : (
        <>
          <p className="mb-2 text-[13px] text-slate-500">
            Test mode — pay with a Razorpay test card or UPI to complete the order.
          </p>
          {(phase === "creating" || phase === "verifying") && (
            <div className="mb-2 flex items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 p-2.5 text-[13px] text-indigo-800" aria-live="polite">
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              {phase === "creating"
                ? "Creating secure order on the server…"
                : "Verifying payment signature on the server…"}
            </div>
          )}
          {phase === "failed" && (
            <div className="mb-2 flex items-start gap-2 rounded-lg border border-red-300 bg-red-50 p-2.5 text-[13px] text-red-700" aria-live="polite">
              <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              <span>
                Payment didn&apos;t go through — no charge was made.
                {error ? ` ${error}` : " You can safely try again."}
              </span>
            </div>
          )}
          <Button
            onClick={startPayment}
            disabled={phase === "creating" || phase === "verifying" || phase === "checkout"}
            className="w-full bg-emerald-600 hover:bg-emerald-500 text-white text-[15px] font-semibold h-11 shadow-sm touch-manipulation"
          >
            {(phase === "creating" || phase === "verifying") && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
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
