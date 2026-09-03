"use client";

import { useState, useRef, useEffect, useCallback, forwardRef, useImperativeHandle } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { AgentActivity } from "@/components/chat/AgentActivity";
import { fetchJson } from "@/lib/api";
import { Product, Cart } from "@/lib/types";
import { Send, Sparkles } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface ChatPanelProps {
  sessionId: string;
  onProductsFound?: (products: Product[]) => void;
  onUpsellFound?: (products: Product[]) => void;
  onCartUpdate?: (cart: Cart) => void;
  onApprovalNeeded?: (approvalId: number, approvalToken?: string | null) => void;
}

export interface ChatPanelHandle {
  sendMessage: (msg: string) => void;
}

export const ChatPanel = forwardRef<ChatPanelHandle, ChatPanelProps>(
  ({ sessionId, onProductsFound, onUpsellFound, onCartUpdate, onApprovalNeeded }, ref) => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [activity, setActivity] = useState<string | null>(null);
    const activityTimer = useRef<ReturnType<typeof setInterval> | null>(null);

    // Optimistic staged feedback while the agent works: the tool_calls list
    // only arrives post-hoc, so rotate plausible stages client-side until
    // the response lands. Cleared the moment data arrives. Stages are picked
    // from the message intent so checkout never reads as "Searching catalog".
    const startActivityCycle = useCallback((message: string) => {
      const m = (message || "").toLowerCase();
      let stages: string[];
      if (/(checkout|check out|approve|approval|pay|payment|order|buy|place)/.test(m)) {
        stages = [
          "Verifying policy…",
          "Creating approval…",
          "Locking order total…",
          "Preparing answer…",
        ];
      } else if (/(cart|add|remove|quantity|qty)/.test(m)) {
        stages = [
          "Updating cart…",
          "Rechecking policy…",
          "Refreshing totals…",
          "Preparing answer…",
        ];
      } else {
        stages = [
          "Searching catalog…",
          "Comparing products…",
          "Checking stock…",
          "Verifying policy…",
          "Preparing answer…",
        ];
      }
      let i = 0;
      setActivity(stages[0]);
      if (activityTimer.current) clearInterval(activityTimer.current);
      activityTimer.current = setInterval(() => {
        i = (i + 1) % stages.length;
        setActivity(stages[i]);
      }, 1400);
    }, []);

    const stopActivityCycle = useCallback(() => {
      if (activityTimer.current) {
        clearInterval(activityTimer.current);
        activityTimer.current = null;
      }
      setActivity(null);
    }, []);

    useEffect(() => {
      return () => {
        if (activityTimer.current) clearInterval(activityTimer.current);
      };
    }, []);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const accumulatedProducts = useRef<Product[]>([]);
    const accumulatedUpsell = useRef<Product[]>([]);
    const loadingRef = useRef(false);

    useEffect(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const fetchCart = useCallback(async (cartId: number) => {
      try {
        const cart = await fetchJson(`/cart/${cartId}`);
        onCartUpdate?.(cart);
      } catch (e) {
        console.error("Failed to fetch cart:", e);
      }
    }, [onCartUpdate]);

    const sendToAgent = useCallback(async (message: string) => {
      if (loadingRef.current) return; // Prevent concurrent calls
      loadingRef.current = true;

      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: message,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setLoading(true);

      try {
        startActivityCycle(message);

        const data = await fetchJson("/agent/chat", {
          method: "POST",
          body: JSON.stringify({ session_id: sessionId, message }),
        });

        stopActivityCycle();

        const assistantMessage: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: data.response,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMessage]);

        // Latest turn wins: the panel shows what the agent just talked
        // about, not everything ever mentioned. Empty turns keep the list.
        if (data.products && data.products.length > 0) {
          accumulatedProducts.current = data.products;
          onProductsFound?.(accumulatedProducts.current);
        }

        if (data.upsell_products && data.upsell_products.length > 0) {
          accumulatedUpsell.current = data.upsell_products;
          onUpsellFound?.(accumulatedUpsell.current);
        }

        // Fetch full cart
        if (data.cart && data.cart.cart_id) {
          await fetchCart(data.cart.cart_id);
        }

        // Check for approval state
        if (data.state === "AWAITING_APPROVAL" && data.cart?.approval_id) {
          onApprovalNeeded?.(data.cart.approval_id, data.cart.approval_token ?? null);
        }
      } catch (error) {
        stopActivityCycle();
        const errorMessage: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "I encountered an error. Please try again.",
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      } finally {
        setLoading(false);
        loadingRef.current = false;
      }
    }, [sessionId, onProductsFound, onUpsellFound, fetchCart, onApprovalNeeded, startActivityCycle, stopActivityCycle]);

    useImperativeHandle(ref, () => ({
      sendMessage: sendToAgent,
    }));

    const sendMessage = async () => {
      if (!input.trim() || loading) return;
      const msg = input.trim();
      setInput("");
      await sendToAgent(msg);
    };

    const suggestions = [
      "Marathon shoes under ₹5,000",
      "Trail shoes for beginners",
      "Show running accessories",
    ];

    return (
      <div className="flex flex-col h-full bg-white/80 backdrop-blur-sm border-r border-slate-200/80">
        <div className="border-b border-slate-200/80 px-4 py-3 flex items-center gap-2.5 bg-white/90">
          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-[0_4px_12px_-2px_rgba(79,70,229,0.5)]" aria-hidden="true">
            <Sparkles className="h-4 w-4 text-white" />
          </span>
          <div className="leading-tight">
            <h2 className="text-[15px] font-semibold text-slate-900">SprintGear AI</h2>
            <p className="text-[11px] text-slate-500">Bounded · explainable · gated</p>
          </div>
          <Badge variant="outline" className="text-xs border-emerald-200 text-emerald-700 bg-emerald-50 ml-auto gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" aria-hidden="true" />
            Online
          </Badge>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[radial-gradient(ellipse_at_top,rgba(99,102,241,0.06),transparent_60%)]">
          {messages.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center h-full text-center px-2">
              <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-[0_8px_24px_-6px_rgba(79,70,229,0.5)] mb-4" aria-hidden="true">
                <Sparkles className="h-6 w-6 text-white" />
              </span>
              <p className="text-[16px] font-semibold text-slate-800">What are you training for?</p>
              <p className="text-[13px] mt-1.5 text-slate-500 max-w-[280px] leading-relaxed">
                Ask about running shoes, trail gear, or accessories — I&apos;ll check policy before anything costs money.
              </p>
              <div className="mt-4 flex flex-col gap-2 w-full max-w-[280px]">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => sendToAgent(s)}
                    className="rounded-xl border border-indigo-200/80 bg-white px-3 py-2 text-left text-[13px] text-indigo-800 shadow-sm transition-all hover:-translate-y-px hover:border-indigo-300 hover:shadow-md active:translate-y-0"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

          {activity && <AgentActivity message={activity} />}

          <div ref={messagesEndRef} />
        </div>

        <div className="border-t border-slate-200/80 bg-white/90 p-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sendMessage();
            }}
            className="flex items-center gap-2 rounded-full border border-slate-300 bg-white py-1.5 pl-4 pr-1.5 shadow-sm transition-colors focus-within:border-indigo-400 focus-within:ring-2 focus-within:ring-indigo-100"
          >
            <label htmlFor="chat-input" className="sr-only">
              Ask about products
            </label>
            <Input
              id="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about products…"
              disabled={loading}
              autoComplete="off"
              className="border-0 bg-transparent p-0 text-slate-900 text-[14px] placeholder:text-slate-400 shadow-none focus-visible:ring-0"
            />
            <Button
              type="submit"
              disabled={loading || !input.trim()}
              size="icon"
              aria-label="Send message"
              className="h-9 w-9 shrink-0 rounded-full bg-gradient-to-br from-indigo-600 to-violet-600 text-white shadow-md transition-transform hover:scale-105 active:scale-95 disabled:opacity-40 disabled:hover:scale-100 touch-manipulation"
            >
              <Send className="h-4 w-4" aria-hidden="true" />
            </Button>
          </form>
        </div>
      </div>
    );
  }
);

ChatPanel.displayName = "ChatPanel";
