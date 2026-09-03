"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { CommercePanel } from "@/components/commerce/CommercePanel";
import { Product, Cart } from "@/lib/types";
import { fetchJson } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, ShieldCheck } from "lucide-react";

export default function BuyerPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [upsellProducts, setUpsellProducts] = useState<Product[]>([]);
  const [cart, setCart] = useState<Cart | null>(null);
  const [policyActive, setPolicyActive] = useState(false);
  const [approvalId, setApprovalId] = useState<number | null>(null);
  const chatRef = useRef<{ sendMessage: (msg: string) => void } | null>(null);
  const cartRef = useRef<Cart | null>(null);

  // Keep cartRef in sync
  useEffect(() => {
    cartRef.current = cart;
  }, [cart]);

  useEffect(() => {
    const savedSession = localStorage.getItem("razorflow_session_id");
    if (savedSession) {
      setSessionId(savedSession);
      // Restore cart for persisted session
      fetchJson(`/agent/session/${savedSession}`)
        .then((data) => {
          if (data.cart_id) fetchCart(data.cart_id);
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

  const handleUpdateQuantity = useCallback(async (itemId: number, quantity: number) => {
    const currentCart = cartRef.current;
    if (!currentCart) return;

    const item = currentCart.items?.find((i) => i.id === itemId);
    if (!item) return;

    const oldQty = item.quantity;
    const action = quantity > oldQty ? "increased" : "decreased";

    try {
      // Update quantity
      await fetchJson(`/cart/${currentCart.id}/items/${itemId}`, {
        method: "PUT",
        body: JSON.stringify({ quantity }),
      });

      // Fetch updated cart
      const updatedCart = await fetchCart(currentCart.id);

      // Send chat confirmation AFTER cart is updated
      if (chatRef.current && updatedCart) {
        chatRef.current.sendMessage(`I ${action} the quantity of ${item.product_name} to ${quantity}. What's the new total?`);
      }
    } catch (e) {
      console.error("Failed to update quantity:", e);
    }
  }, [fetchCart]);

  const handleRemoveItem = useCallback(async (itemId: number) => {
    const currentCart = cartRef.current;
    if (!currentCart) return;

    const item = currentCart.items?.find((i) => i.id === itemId);
    if (!item) return;

    try {
      await fetchJson(`/cart/${currentCart.id}/items/${itemId}`, {
        method: "DELETE",
      });

      const updatedCart = await fetchCart(currentCart.id);

      if (chatRef.current) {
        chatRef.current.sendMessage(`I removed ${item.product_name} from my cart`);
      }
    } catch (e) {
      console.error("Failed to remove item:", e);
    }
  }, [fetchCart]);

  const handleAddToCart = useCallback(async (product: Product) => {
    const currentCart = cartRef.current;

    try {
      if (!currentCart) {
        // Create cart first
        const newCart = await fetchJson("/cart", {
          method: "POST",
          body: JSON.stringify({ session_id: sessionId, merchant_id: 1 }),
        });
        setCart(newCart);
        cartRef.current = newCart;

        await fetchJson(`/cart/${newCart.id}/items`, {
          method: "POST",
          body: JSON.stringify({ product_id: product.id, quantity: 1 }),
        });

        const updatedCart = await fetchCart(newCart.id);

        if (chatRef.current) {
          chatRef.current.sendMessage(`I added ${product.name} to my cart`);
        }
      } else {
        await fetchJson(`/cart/${currentCart.id}/items`, {
          method: "POST",
          body: JSON.stringify({ product_id: product.id, quantity: 1 }),
        });

        const updatedCart = await fetchCart(currentCart.id);

        if (chatRef.current) {
          chatRef.current.sendMessage(`I added ${product.name} to my cart`);
        }
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

  const handleApprovalComplete = useCallback(() => {
    setApprovalId(null);
    if (chatRef.current) {
      chatRef.current.sendMessage("Approval completed");
    }
  }, []);

  if (!sessionId) {
    return (
      <div className="h-screen bg-slate-950 text-white flex items-center justify-center">
        <div className="text-slate-400">Initializing session...</div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-slate-950 text-white flex flex-col">
      <header className="border-b border-slate-900 bg-slate-950/80 backdrop-blur-md px-4 py-3 flex items-center gap-4 z-50">
        <Link href="/">
          <Button variant="ghost" size="sm" className="text-slate-400 hover:text-white">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
        </Link>

        <div className="flex items-center gap-2">
          <div className="h-6 w-6 rounded bg-blue-600 flex items-center justify-center text-xs font-bold text-white">
            R
          </div>
          <span className="font-semibold text-sm">RazorFlow AI</span>
        </div>

        <Badge variant="outline" className="border-blue-500/30 text-blue-400 bg-blue-950/20 text-xs">
          Test Mode
        </Badge>

        {policyActive && (
          <Badge variant="outline" className="border-emerald-500/30 text-emerald-400 bg-emerald-950/20 text-xs gap-1">
            <ShieldCheck className="h-3 w-3" />
            Policy Active
          </Badge>
        )}

        <span className="ml-auto text-xs text-slate-500 font-mono">
          Session: {sessionId.slice(0, 8)}...
        </span>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-1/2 min-w-0">
          <ChatPanel
            ref={chatRef}
            sessionId={sessionId}
            onProductsFound={setProducts}
            onUpsellFound={setUpsellProducts}
            onCartUpdate={setCart}
            onApprovalNeeded={setApprovalId}
          />
        </div>
        <div className="w-1/2 min-w-0">
          <CommercePanel
            products={products}
            cart={cart}
            upsellProducts={upsellProducts}
            approvalId={approvalId}
            sessionId={sessionId || ""}
            onAddToCart={handleAddToCart}
            onUpdateQuantity={handleUpdateQuantity}
            onRemoveItem={handleRemoveItem}
            onCheckout={handleCheckout}
            onApprovalComplete={handleApprovalComplete}
          />
        </div>
      </div>
    </div>
  );
}
