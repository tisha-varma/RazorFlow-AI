"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { CommercePanel } from "@/components/commerce/CommercePanel";
import { PolicyPanel } from "@/components/commerce/PolicyPanel";
import { AuditTrail } from "@/components/audit/AuditTrail";
import { SessionLimitBar } from "@/components/commerce/SessionLimitBar";
import { Product, Cart } from "@/lib/types";
import { fetchJson } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, ShieldCheck, Activity, Settings2, RotateCcw } from "lucide-react";

export default function BuyerPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [upsellProducts, setUpsellProducts] = useState<Product[]>([]);
  const [cart, setCart] = useState<Cart | null>(null);
  const [policyActive, setPolicyActive] = useState(false);
  const [approvalId, setApprovalId] = useState<number | null>(null);
  const [approvalToken, setApprovalToken] = useState<string | null>(null);
  const [approvedId, setApprovedId] = useState<number | null>(null);
  const [showAudit, setShowAudit] = useState(false);
  const [showPolicy, setShowPolicy] = useState(false);
  const [policyVersion, setPolicyVersion] = useState(0);
  const [recovery, setRecovery] = useState<null | { kind: "failed" | "stale" }>(null);
  const chatRef = useRef<{ sendMessage: (msg: string) => void } | null>(null);
  const cartRef = useRef<Cart | null>(null);

  // Keep cartRef in sync
  useEffect(() => {
    cartRef.current = cart;
  }, [cart]);

  const fetchCart = useCallback(async (cartId: number) => {
    try {
      const cartData = await fetchJson(`/cart/${cartId}`);
      setCart(cartData);
      return cartData;
    } catch (e) {
      console.error("Failed to fetch cart:", e);
      return null;
    }
  }, []);

  useEffect(() => {
    const savedSession = localStorage.getItem("razorflow_session_id");
    if (savedSession) {
      setSessionId(savedSession);
      // Restore cart for persisted session, then check whether the
      // session needs recovery (failed payment or pre-reload approval
      // whose single-use token is gone with the old page).
      fetchJson(`/agent/session/${savedSession}`)
        .then(async (data) => {
          if (data.cart_id) {
            await fetchCart(data.cart_id);
            if (data.state === "PAYMENT_FAILED") {
              setRecovery({ kind: "failed" });
              return;
            }
            try {
              const summary = await fetchJson(
                `/checkout/summary/${data.cart_id}?session_id=${encodeURIComponent(savedSession)}`
              );
              if (summary.status === "pending" && summary.approval_id) {
                setRecovery({ kind: "stale" });
              }
            } catch {
              /* no summary -> nothing to recover */
            }
          }
        })
        .catch(() => {});
    } else {
      fetchJson("/agent/session", { method: "POST" })
        .then((data) => {
          localStorage.setItem("razorflow_session_id", data.session_id);
          setSessionId(data.session_id);
        })
        .catch(() => {
          const fallback = "fallback-session-" + Date.now();
          localStorage.setItem("razorflow_session_id", fallback);
          setSessionId(fallback);
        });
    }

    fetchJson("/policy")
      .then(() => setPolicyActive(true))
      .catch(() => setPolicyActive(false));
  }, [fetchCart]);

  // UI cart actions hit the API directly and NEVER go through the agent:
  // no LLM calls, no conversational waiting. The panel updates from the
  // API response alone.
  const handleUpdateQuantity = useCallback(async (itemId: number, quantity: number) => {
    const currentCart = cartRef.current;
    if (!currentCart) return;

    try {
      await fetchJson(`/cart/${currentCart.id}/items/${itemId}`, {
        method: "PUT",
        body: JSON.stringify({ quantity }),
      });
      await fetchCart(currentCart.id);
    } catch (e) {
      console.error("Failed to update quantity:", e);
    }
  }, [fetchCart]);

  const handleRemoveItem = useCallback(async (itemId: number) => {
    const currentCart = cartRef.current;
    if (!currentCart) return;

    try {
      await fetchJson(`/cart/${currentCart.id}/items/${itemId}`, {
        method: "DELETE",
      });
      await fetchCart(currentCart.id);
    } catch (e) {
      console.error("Failed to remove item:", e);
    }
  }, [fetchCart]);

  const handleAddToCart = useCallback(async (product: Product) => {
    let cartId: number | undefined = cartRef.current?.id;

    try {
      if (!cartId) {
        // Create cart first
        const newCart = await fetchJson("/cart", {
          method: "POST",
          body: JSON.stringify({ session_id: sessionId, merchant_id: 1 }),
        });
        cartId = newCart.id;
      }
      if (!cartId) return;

      await fetchJson(`/cart/${cartId}/items`, {
        method: "POST",
        body: JSON.stringify({ product_id: product.id, quantity: 1 }),
      });
      await fetchCart(cartId);

      // Upsell via direct catalog call — no agent round trip.
      try {
        const related = await fetchJson(`/catalog/products/${product.id}/related`);
        if (Array.isArray(related) && related.length > 0) {
          setUpsellProducts(related);
        }
      } catch {
        /* upsell is a bonus — cart already updated */
      }
    } catch (e) {
      console.error("Failed to add to cart:", e);
    }
  }, [sessionId, fetchCart]);

  const handleCheckout = useCallback(() => {
    if (chatRef.current) {
      chatRef.current.sendMessage("I want to checkout now");
    }
  }, []);

  const handleApprovalNeeded = useCallback((id: number, token?: string | null) => {
    setApprovalId(id);
    setApprovalToken(token ?? null);
  }, []);

  const handleApprovalComplete = useCallback(() => {
    // Approve path: move the approval into the payment step.
    setApprovalId((current) => {
      if (current) setApprovedId(current);
      return null;
    });
    setApprovalToken(null);
    if (chatRef.current) {
      chatRef.current.sendMessage("Approval completed");
    }
  }, []);

  const handleApprovalRejected = useCallback(() => {
    // Reject path: clear the gate, no payment step.
    setApprovalId(null);
    setApprovalToken(null);
    if (chatRef.current) {
      chatRef.current.sendMessage("I rejected the purchase");
    }
  }, []);

  // Fresh budget, fresh thread: spending limits are per-session, so a new
  // session restores the full ₹10,000. Old session rows are cleaned up
  // best-effort (demo endpoint); the reload mints the new session.
  const handleNewSession = useCallback(async () => {
    if (sessionId) {
      try {
        await fetchJson(`/demo/reset?session_id=${encodeURIComponent(sessionId)}`, {
          method: "POST",
        });
      } catch {
        /* cleanup is a bonus — the new session is what resets budget */
      }
    }
    localStorage.removeItem("razorflow_session_id");
    window.location.reload();
  }, [sessionId]);

  const handlePaid = useCallback((order: { order_id: number; order_number: string; total_paise: number }) => {
    setApprovedId(null);
    setCart(null);
    if (chatRef.current) {
      chatRef.current.sendMessage(
        `Payment successful for order ${order.order_number}. What's next?`
      );
    }
  }, []);

  // Products already in the cart are hidden from discovery lists —
  // the panel shows what you can still add, latest recommendations first.
  const cartProductIds = new Set((cart?.items ?? []).map((i) => i.product_id));
  const visibleProducts = products.filter((p) => !cartProductIds.has(p.id));
  const visibleUpsell = upsellProducts.filter((p) => !cartProductIds.has(p.id));

  if (!sessionId) {
    return (
      <div className="h-screen bg-stone-100 text-slate-900 flex items-center justify-center">
        <div className="text-slate-500">Initializing session…</div>
      </div>
    );
  }

  return (
    <div className="relative h-screen text-slate-900 flex flex-col bg-stone-100">
      {/* Ambient mesh backdrop */}
      <div className="pointer-events-none absolute inset-0" aria-hidden="true">
        <div className="absolute -top-32 left-1/4 h-72 w-72 rounded-full bg-indigo-300/20 blur-[100px]" />
        <div className="absolute bottom-0 right-1/4 h-72 w-72 rounded-full bg-violet-300/20 blur-[100px]" />
      </div>
      <header className="relative border-b border-slate-200/80 bg-white/85 backdrop-blur-md px-4 py-3 flex flex-wrap items-center gap-x-3 gap-y-2 z-50 shadow-[0_1px_12px_rgba(15,23,42,0.06)]">
        <Link href="/">
          <Button variant="ghost" size="sm" className="rounded-full text-slate-500 hover:text-slate-900 hover:bg-slate-100">
            <ArrowLeft className="h-4 w-4 mr-1" aria-hidden="true" />
            Back
          </Button>
        </Link>

        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 flex items-center justify-center text-xs font-bold text-white shadow-[0_4px_12px_-2px_rgba(79,70,229,0.5)]">
            R
          </div>
          <div className="leading-tight">
            <span className="font-semibold text-[15px] text-slate-900">RazorFlow AI</span>
            <p className="text-[10px] font-medium uppercase tracking-widest text-slate-400">AI Buyer</p>
          </div>
        </div>

        <Badge variant="outline" className="border-slate-300 text-slate-600 bg-slate-50 text-xs rounded-full">
          Test Mode
        </Badge>

        {policyActive && (
          <Badge variant="outline" className="border-emerald-300 text-emerald-700 bg-emerald-50 text-xs gap-1 rounded-full shadow-sm">
            <ShieldCheck className="h-3 w-3" aria-hidden="true" />
            Policy Active
          </Badge>
        )}

        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowAudit((v) => !v)}
          aria-expanded={showAudit}
          className={showAudit ? "text-indigo-700 bg-indigo-50" : "text-slate-500 hover:text-slate-900"}
        >
          <Activity className="h-4 w-4 mr-1" aria-hidden="true" />
          Audit trail
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowPolicy((v) => !v)}
          aria-expanded={showPolicy}
          className={showPolicy ? "text-indigo-700 bg-indigo-50" : "text-slate-500 hover:text-slate-900"}
        >
          <Settings2 className="h-4 w-4 mr-1" aria-hidden="true" />
          Policy settings
        </Button>

        <div className="ml-auto flex items-center gap-3">
          <SessionLimitBar
            sessionId={sessionId}
            refreshKey={`${cart?.id ?? 0}-${approvalId ?? 0}-${approvedId ?? 0}-${policyVersion}`}
          />
          <span className="hidden sm:inline text-xs text-slate-400 font-mono tabular-nums">
            {sessionId.slice(0, 8)}…
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleNewSession}
            title="Start a fresh session — restores the full spending limit"
            className="rounded-full text-slate-500 hover:text-slate-900 hover:bg-slate-100"
          >
            <RotateCcw className="h-3.5 w-3.5 mr-1" aria-hidden="true" />
            Reset
          </Button>
        </div>
      </header>

      {recovery && (
        <div
          className={`px-4 py-3 flex flex-wrap items-center gap-3 border-b ${
            recovery.kind === "failed"
              ? "bg-red-50 border-red-200"
              : "bg-amber-50 border-amber-200"
          }`}
          aria-live="polite"
        >
          <div className="min-w-0 flex-1">
            <p className={`text-sm font-semibold ${
              recovery.kind === "failed" ? "text-red-800" : "text-amber-900"
            }`}>
              {recovery.kind === "failed"
                ? "Payment didn't go through — no charge was made."
                : "Unfinished approval from before this reload."}
            </p>
            <p className={`text-[13px] ${
              recovery.kind === "failed" ? "text-red-700" : "text-amber-800"
            }`}>
              {recovery.kind === "failed"
                ? "Your cart is intact. Checkout again for a fresh approval, then pay."
                : "Its single-use token expired with the old page. Checkout again for a fresh approval."}
            </p>
          </div>
          <Button
            size="sm"
            onClick={() => {
              setRecovery(null);
              setApprovalId(null);
              setApprovedId(null);
              handleCheckout();
            }}
            className="bg-emerald-600 hover:bg-emerald-500 text-white touch-manipulation"
          >
            Checkout again
          </Button>
          <Button
            variant="ghost"
            size="sm"
            aria-label="Dismiss recovery notice"
            onClick={() => setRecovery(null)}
            className="text-slate-500 hover:text-slate-900"
          >
            Dismiss
          </Button>
        </div>
      )}

      {showPolicy && (
        <PolicyPanel
          sessionId={sessionId}
          onChanged={() => setPolicyVersion((v) => v + 1)}
        />
      )}

      {showAudit && (
        <div className="h-72 shrink-0 overflow-hidden border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
          <AuditTrail
            sessionId={sessionId}
            refreshKey={`${cart?.id ?? 0}-${approvalId ?? 0}-${approvedId ?? 0}`}
          />
        </div>
      )}

      <div className="relative flex-1 flex flex-col md:flex-row overflow-hidden gap-3 p-3 min-h-0">
        <div className="min-h-0 flex-1 md:w-1/2 w-full rounded-2xl overflow-hidden border border-slate-200/80 shadow-[0_8px_24px_-12px_rgba(15,23,42,0.2)]">
          <ChatPanel
            ref={chatRef}
            sessionId={sessionId}
            onProductsFound={setProducts}
            onUpsellFound={setUpsellProducts}
            onCartUpdate={setCart}
            onApprovalNeeded={handleApprovalNeeded}
          />
        </div>
        <div className="min-h-0 flex-1 md:w-1/2 w-full rounded-2xl overflow-hidden border border-slate-200/80 shadow-[0_8px_24px_-12px_rgba(15,23,42,0.2)]">
          <CommercePanel
            products={visibleProducts}
            cart={cart}
            upsellProducts={visibleUpsell}
            approvalId={approvalId}
            approvalToken={approvalToken}
            approvedId={approvedId}
            sessionId={sessionId || ""}
            onAddToCart={handleAddToCart}
            onUpdateQuantity={handleUpdateQuantity}
            onRemoveItem={handleRemoveItem}
            onCheckout={handleCheckout}
            onApprovalComplete={handleApprovalComplete}
            onApprovalRejected={handleApprovalRejected}
            onPaid={handlePaid}
          />
        </div>
      </div>
    </div>
  );
}
