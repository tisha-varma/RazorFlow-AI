"use client";

import { useState, useEffect } from "react";
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
  const [cart, setCart] = useState<Cart | null>(null);
  const [policyActive, setPolicyActive] = useState(false);

  useEffect(() => {
    fetchJson("/agent/session", { method: "POST" })
      .then((data) => setSessionId(data.session_id))
      .catch(() => setSessionId("fallback-session-" + Date.now()));

    fetchJson("/policy")
      .then(() => setPolicyActive(true))
      .catch(() => setPolicyActive(false));
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
            sessionId={sessionId}
            onProductsFound={setProducts}
            onCartUpdate={setCart}
          />
        </div>
        <div className="w-1/2 min-w-0">
          <CommercePanel products={products} cart={cart} />
        </div>
      </div>
    </div>
  );
}
