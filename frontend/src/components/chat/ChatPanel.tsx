"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { AgentActivity } from "@/components/chat/AgentActivity";
import { fetchJson, API_BASE } from "@/lib/api";
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
  onCartUpdate?: (cart: Cart) => void;
}

export function ChatPanel({ sessionId, onProductsFound, onCartUpdate }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activity, setActivity] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      setActivity("Searching your catalog...");

      const data = await fetchJson("/agent/chat", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, message: userMessage.content }),
      });

      setActivity(null);

      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.response,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);

      if (data.products && data.products.length > 0) {
        onProductsFound?.(data.products);
      }

      if (data.cart) {
        onCartUpdate?.(data.cart);
      }
    } catch (error) {
      setActivity(null);
      const errorMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "I encountered an error. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/40 border-r border-slate-800">
      <div className="border-b border-slate-800 px-4 py-3 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-blue-400" />
        <h2 className="text-sm font-semibold text-white">SprintGear AI</h2>
        <Badge variant="outline" className="text-xs border-blue-500/30 text-blue-400 bg-blue-950/20 ml-auto">
          Online
        </Badge>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-slate-500">
            <Sparkles className="h-8 w-8 mb-3 text-slate-600" />
            <p className="text-sm">Ask about running shoes, trail gear, or accessories.</p>
            <p className="text-xs mt-1 text-slate-600">Example: "I need marathon shoes under ₹5,000"</p>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {activity && <AgentActivity message={activity} />}

        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-slate-800 p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage();
          }}
          className="flex gap-2"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about products..."
            disabled={loading}
            className="bg-slate-800 border-slate-700 text-white placeholder:text-slate-500"
          />
          <Button
            type="submit"
            disabled={loading || !input.trim()}
            size="icon"
            className="bg-blue-600 hover:bg-blue-500 text-white shrink-0"
          >
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}
