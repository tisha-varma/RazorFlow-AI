"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { CommercePanel } from "@/components/commerce/CommercePanel";
import { AuditTrail } from "@/components/audit/AuditTrail";
import { SessionLimitBar } from "@/components/commerce/SessionLimitBar";
import { DemoControls } from "@/components/demo/DemoControls";
import { Product, Cart } from "@/lib/types";
import { fetchJson } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, ShieldCheck, Activity } from "lucide-react";

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

  const handlePaid = useCallback((order: { order_id: number; order_number: string; total_paise: number }) => {
    setApprovedId(null);
    setCart(null);
    if (chatRef.current) {
      chatRef.current.sendMessage(
        `Payment successful for order ${order.order_number}. What's next?`
      );
    }
  }, []);

  const handleDemoResult = useCallback(async (result: Record<string, unknown>) => {
    // Reset: wipe all local commerce state for a clean restart.
    if (typeof result.scope === "string") {
      setCart(null);
      setProducts([]);
      setUpsellProducts([]);
      setApprovalId(null);
      setApprovedId(null);
      return;
    }
    // Triggers: refresh the cart view; upsell scenarios also set candidates.
    const cartId = result.cart_id;
    if (typeof cartId === "number") {
      await fetchCart(cartId);
    }
    if (Array.isArray(result.upsell)) {
      setUpsellProducts(result.upsell as Product[]);
    }
    if (result.status === "paid" || result.status === "failed") {
      setApprovalId(null);
      setApprovedId(null);
    }
  }, [fetchCart]);

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
    <div className="h-screen bg-stone-100 text-slate-900 flex flex-col">
      <header className="border-b border-slate-200 bg-white px-4 py-3 flex items-center gap-3 z-50 shadow-sm">
        <Link href="/">
          <Button variant="ghost" size="sm" className="text-slate-500 hover:text-slate-900">
            <ArrowLeft className="h-4 w-4 mr-1" aria-hidden="true" />
            Back
          </Button>
        </Link>

        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-lg bg-indigo-600 flex items-center justify-center text-xs font-bold text-white">
            R
          </div>
          <span className="font-semibold text-[15px] text-slate-900">RazorFlow AI</span>
        </div>

        <Badge variant="outline" className="border-slate-300 text-slate-600 bg-slate-50 text-xs">
          Test Mode
        </Badge>

        {policyActive && (
          <Badge variant="outline" className="border-emerald-300 text-emerald-700 bg-emerald-50 text-xs gap-1">
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

        <div className="ml-auto flex items-center gap-3">
          <SessionLimitBar
            sessionId={sessionId}
            refreshKey={`${cart?.id ?? 0}-${approvalId ?? 0}-${approvedId ?? 0}`}
          />
          <span className="text-xs text-slate-400 font-mono tabular-nums">
            {sessionId.slice(0, 8)}…
          </span>
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

      <DemoControls sessionId={sessionId} onDone={handleDemoResult} />

      {showAudit && (
        <div className="h-72 shrink-0 overflow-hidden border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
          <AuditTrail
            sessionId={sessionId}
            refreshKey={`${cart?.id ?? 0}-${approvalId ?? 0}-${approvedId ?? 0}`}
          />
        </div>
      )}

      <div className="flex-1 flex overflow-hidden">
        <div className="w-1/2 min-w-0">
          <ChatPanel
            ref={chatRef}
            sessionId={sessionId}
            onProductsFound={setProducts}
            onUpsellFound={setUpsellProducts}
            onCartUpdate={setCart}
            onApprovalNeeded={handleApprovalNeeded}
          />
        </div>
        <div className="w-1/2 min-w-0">
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
