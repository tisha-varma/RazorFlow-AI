"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { ChatPanel, type TurnTrace } from "@/components/chat/ChatPanel";
import { TracePanel, type FullTrace } from "@/components/chat/TracePanel";
import { CommercePanel } from "@/components/commerce/CommercePanel";
import { PolicyPanel } from "@/components/commerce/PolicyPanel";
import { AuditTrail } from "@/components/audit/AuditTrail";
import { SessionLimitBar } from "@/components/commerce/SessionLimitBar";
import { Product, Cart } from "@/lib/types";
import { fetchJson } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, ShieldCheck, Activity, Settings2, RotateCcw, XCircle, ListTree } from "lucide-react";

export default function BuyerPage() {
  // Lazy init from storage: reading localStorage during render (not in an
  // effect) keeps the mount effect free of synchronous setState.
  const [sessionId, setSessionId] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("razorflow_session_id");
  });
  const [products, setProducts] = useState<Product[]>([]);
  const [upsellProducts, setUpsellProducts] = useState<Product[]>([]);
  const [cart, setCart] = useState<Cart | null>(null);
  const [policyActive, setPolicyActive] = useState(false);
  const [approvalId, setApprovalId] = useState<number | null>(null);
  const [approvalToken, setApprovalToken] = useState<string | null>(null);
  const [approvedId, setApprovedId] = useState<number | null>(null);
  const [showAudit, setShowAudit] = useState(false);
  const [showTrace, setShowTrace] = useState(false);
  const [trace, setTrace] = useState<FullTrace | null>(null);
  const [showPolicy, setShowPolicy] = useState(false);
  const [policyVersion, setPolicyVersion] = useState(0);
  const [recovery, setRecovery] = useState<
    null | { kind: "stale" } | { kind: "failed"; orderNumber?: string; reason?: string }
  >(null);
  const [demoEnabled, setDemoEnabled] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const chatRef = useRef<{ sendMessage: (msg: string) => void } | null>(null);
  const cartRef = useRef<Cart | null>(null);

  // Keep cartRef in sync
  useEffect(() => {
    cartRef.current = cart;
  }, [cart]);

  // Extracted primitive for effect deps (declared before the effects that
  // use it — no use-before-declare, no complex dep expressions).
  const cartItemCount = (cart?.items ?? []).length;

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
    if (sessionId) {
      // Restore cart for persisted session, then check whether the
      // session needs recovery (failed payment or pre-reload approval
      // whose single-use token is gone with the old page).
      fetchJson(`/agent/session/${sessionId}`)
        .then(async (data) => {
          if (data.cart_id) {
            await fetchCart(data.cart_id);
            if (data.state === "PAYMENT_FAILED") {
              setRecovery({ kind: "failed" });
              return;
            }
            try {
              const summary = await fetchJson(
                `/checkout/summary/${data.cart_id}?session_id=${encodeURIComponent(sessionId)}`
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
    // Demo-only failure simulator lives behind the same flag as the
    // /api/demo routes — invisible in anything resembling production.
    fetchJson("/demo/status")
      .then((d) => setDemoEnabled(d?.demo_mode === true))
      .catch(() => setDemoEnabled(false));
  }, [fetchCart, sessionId]);

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
    setTrace((t) => (t ? { ...t, approvalId: id } : t));
  }, []);

  const handleTraceFound = useCallback((t: TurnTrace) => {
    setTrace({ ...t, paidOrderNumber: null });
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

  // Approval gate polling: the Approval is minted deterministically the
  // moment the LLM calls initiate_checkout — potentially ~35s before its
  // turn finishes streaming back. Poll the summary while a non-empty cart
  // has no gate showing, and render approval the instant it exists instead
  // of waiting on LLM latency. Token-gated: a pending approval WITHOUT a
  // live token surfaces the stale-recovery banner, never the gate.
  useEffect(() => {
    if (!sessionId || !cart?.id || cartItemCount === 0) return;
    if (approvalId !== null || approvedId !== null) return;
    let cancelled = false;
    const check = async () => {
      try {
        const s = await fetchJson(
          `/checkout/summary/${cart.id}?session_id=${encodeURIComponent(sessionId)}`
        );
        if (cancelled) return;
        if (s.status === "pending" && s.approval_id) {
          if (s.approval_token) {
            handleApprovalNeeded(s.approval_id, s.approval_token);
          } else {
            setRecovery((r) => r ?? { kind: "stale" });
          }
        }
      } catch {
        /* summary is advisory — chat path still delivers the gate */
      }
    };
    check();
    const timer = setInterval(check, 2500);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [sessionId, cart?.id, cartItemCount, approvalId, approvedId, handleApprovalNeeded]);

  // Deterministic judge-state reset: clears this session's carts, orders,
  // approvals, and trail rows and restores policy defaults (server-side) —
  // then mints a fresh session so budget, cart, and gate all start perfect.
  // Deliberately does NOT reseed demo history: after a wipe the dashboard
  // stays honestly empty until real purchases land.
  const [resetting, setResetting] = useState(false);
  const handleNewSession = useCallback(async () => {
    setResetting(true);
    if (sessionId) {
      try {
        await fetchJson(`/demo/reset?session_id=${encodeURIComponent(sessionId)}`, {
          method: "POST",
        });
      } catch {
        /* session cleanup is a bonus — the reload still gives a clean client */
      }
    }
    localStorage.removeItem("razorflow_session_id");
    window.location.reload();
  }, [sessionId]);

  // In-browser failure path: runs a gateway decline against THIS session
  // (no terminal needed), then surfaces the failed-payment card below.
  // Retry is the existing recovery banner's "Checkout again" — fresh
  // approval, same cart, real Razorpay order.
  const handleSimulateDecline = useCallback(async () => {
    if (!sessionId || simulating) return;
    setSimulating(true);
    try {
      const result = await fetchJson(
        `/demo/run-payment-failure?session_id=${encodeURIComponent(sessionId)}`,
        { method: "POST" }
      );
      try {
        const sess = await fetchJson(
          `/agent/session/${encodeURIComponent(sessionId)}`
        );
        if (sess?.cart_id) await fetchCart(sess.cart_id);
      } catch {
        /* cart refresh is a bonus — the card shows regardless */
      }
      setApprovalId(null);
      setApprovedId(null);
      setRecovery({
        kind: "failed",
        orderNumber: typeof result?.order_number === "string" ? result.order_number : undefined,
        reason: typeof result?.reason === "string" ? result.reason : undefined,
      });
    } catch (e) {
      setRecovery({ kind: "failed", reason: e instanceof Error ? e.message : undefined });
    } finally {
      setSimulating(false);
    }
  }, [sessionId, simulating, fetchCart]);

  const handlePaid = useCallback((order: { order_id: number; order_number: string; total_paise: number }) => {
    setApprovedId(null);
    setCart(null);
    setTrace((t) => (t ? { ...t, paidOrderNumber: order.order_number } : t));
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
      <header className="relative border-b border-slate-200/80 bg-white/85 backdrop-blur-md px-4 py-3 flex flex-wrap items-center gap-x-3 gap-y-2 z-50 shadow-[0_1px_12px_rgba(15,23,42,0.06)]">
        <Link href="/">
          <Button variant="ghost" size="sm" className="rounded-full text-slate-500 hover:text-slate-900 hover:bg-slate-100">
            <ArrowLeft className="h-4 w-4 mr-1" aria-hidden="true" />
            Back
          </Button>
        </Link>

        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-slate-900 flex items-center justify-center text-xs font-bold text-white">
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

        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowTrace((v) => !v)}
          aria-expanded={showTrace}
          title="Protocol trace of the last turn: intent, tools, policy, approval, payment"
          className={showTrace ? "text-indigo-700 bg-indigo-50" : "text-slate-500 hover:text-slate-900"}
        >
          <ListTree className="h-4 w-4 mr-1" aria-hidden="true" />
          Trace
        </Button>

        <div className="ml-auto flex items-center gap-3">
          {demoEnabled && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleSimulateDecline}
              disabled={simulating}
              title="Run a gateway decline on this session — shows the failed-payment card and retry path"
              className="rounded-full border border-red-200 bg-white text-[12px] text-red-700 hover:bg-red-50 hover:text-red-800"
            >
              <XCircle className={`h-3.5 w-3.5 mr-1 ${simulating ? "animate-spin" : ""}`} aria-hidden="true" />
              {simulating ? "Declining…" : "Simulate decline"}
            </Button>
          )}
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
            disabled={resetting}
            title="Fresh session + default limits. Paid orders and audit history are preserved."
            className="rounded-full border border-amber-300 bg-amber-50 text-amber-800 hover:text-amber-900 hover:bg-amber-100"
          >
            <RotateCcw className={`h-3.5 w-3.5 mr-1 ${resetting ? "animate-spin" : ""}`} aria-hidden="true" />
            {resetting ? "Resetting…" : "Reset demo"}
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
          {recovery.kind === "failed" && (
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-red-600 shadow-md" aria-hidden="true">
              <XCircle className="h-5 w-5 text-white" />
            </span>
          )}
          <div className="min-w-0 flex-1">
            <p className={`text-sm font-semibold ${
              recovery.kind === "failed" ? "text-red-800" : "text-amber-900"
            }`}>
              {recovery.kind === "failed"
                ? "Payment failed — no charge was made."
                : "Unfinished approval from before this reload."}
              {recovery.kind === "failed" && recovery.orderNumber && (
                <span className="ml-2 rounded-md bg-white/80 px-1.5 py-0.5 font-mono text-xs font-bold text-red-800">
                  {recovery.orderNumber}
                </span>
              )}
            </p>
            <p className={`text-[13px] ${
              recovery.kind === "failed" ? "text-red-700" : "text-amber-800"
            }`}>
              {recovery.kind === "failed"
                ? recovery.reason
                  ? `Gateway said: ${recovery.reason}. Your cart is intact — retry below for a fresh approval.`
                  : "Your cart is intact. Checkout again for a fresh approval, then pay."
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
            {recovery.kind === "failed" ? "Retry payment" : "Checkout again"}
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

      {showTrace && trace && (
        <TracePanel trace={trace} sessionId={sessionId} />
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
            onTraceFound={handleTraceFound}
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
