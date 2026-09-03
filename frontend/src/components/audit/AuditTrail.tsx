"use client";

import { useState, useEffect, useCallback } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ScrollText,
  RefreshCw,
  MessageSquare,
  Search,
  Sparkles,
  ShoppingBag,
  Trash2,
  ShieldCheck,
  ShieldAlert,
  SlidersHorizontal,
  ClipboardCheck,
  CheckCircle2,
  XCircle,
  Receipt,
  AlertTriangle,
  BadgeCheck,
  PackageCheck,
  CircleDot,
} from "lucide-react";

interface AuditEvent {
  id: number;
  session_id?: string | null;
  merchant_id: number;
  event_type: string;
  event_data: Record<string, unknown>;
  actor: string;
  timestamp?: string | null;
  related_entity_type?: string | null;
  related_entity_id?: number | null;
}

interface AuditTrailProps {
  sessionId?: string | null;
  merchantId?: number | null;
  refreshKey?: string | number;
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

const LABELS: Record<string, string> = {
  USER_INTENT_RECEIVED: "Message received",
  SEARCH_PERFORMED: "Catalog search",
  RECOMMENDATION_MADE: "Recommended for you",
  CART_ITEM_ADDED: "Added to cart",
  CART_ITEM_REMOVED: "Removed from cart",
  POLICY_CHECK_PASSED: "Policy check passed",
  POLICY_CHECK_FAILED: "Policy check failed",
  POLICY_CHANGED: "Policy updated",
  PAYMENT_APPROVAL_REQUESTED: "Approval requested",
  PAYMENT_APPROVED: "Purchase approved",
  PAYMENT_APPROVAL_REJECTED: "Purchase rejected",
  PAYMENT_ORDER_CREATED: "Payment order created",
  PAYMENT_ORDER_FAILED: "Payment order failed",
  PAYMENT_SUCCESS: "Payment verified",
  ORDER_CONFIRMED: "Order confirmed",
  PAYMENT_FAILED: "Payment failed",
};

const ACTOR_STYLES: Record<string, string> = {
  user: "border-sky-300 text-sky-700 bg-sky-50",
  ai: "border-indigo-300 text-indigo-700 bg-indigo-50",
  system: "border-slate-300 text-slate-600 bg-slate-100",
  merchant: "border-emerald-300 text-emerald-700 bg-emerald-50",
  customer: "border-amber-300 text-amber-700 bg-amber-50",
};

const EVENT_ICONS: Record<string, typeof Search> = {
  USER_INTENT_RECEIVED: MessageSquare,
  SEARCH_PERFORMED: Search,
  RECOMMENDATION_MADE: Sparkles,
  CART_ITEM_ADDED: ShoppingBag,
  CART_ITEM_REMOVED: Trash2,
  POLICY_CHECK_PASSED: ShieldCheck,
  POLICY_CHECK_FAILED: ShieldAlert,
  POLICY_CHANGED: SlidersHorizontal,
  PAYMENT_APPROVAL_REQUESTED: ClipboardCheck,
  PAYMENT_APPROVED: CheckCircle2,
  PAYMENT_APPROVAL_REJECTED: XCircle,
  PAYMENT_ORDER_CREATED: Receipt,
  PAYMENT_ORDER_FAILED: AlertTriangle,
  PAYMENT_SUCCESS: BadgeCheck,
  ORDER_CONFIRMED: PackageCheck,
  PAYMENT_FAILED: XCircle,
};

const EVENT_CHIP: Record<string, string> = {
  USER_INTENT_RECEIVED: "bg-sky-100 text-sky-700",
  SEARCH_PERFORMED: "bg-sky-100 text-sky-700",
  RECOMMENDATION_MADE: "bg-indigo-100 text-indigo-700",
  CART_ITEM_ADDED: "bg-indigo-100 text-indigo-700",
  CART_ITEM_REMOVED: "bg-slate-200 text-slate-600",
  POLICY_CHECK_PASSED: "bg-emerald-100 text-emerald-700",
  POLICY_CHECK_FAILED: "bg-red-100 text-red-700",
  POLICY_CHANGED: "bg-slate-200 text-slate-600",
  PAYMENT_APPROVAL_REQUESTED: "bg-amber-100 text-amber-800",
  PAYMENT_APPROVED: "bg-emerald-100 text-emerald-700",
  PAYMENT_APPROVAL_REJECTED: "bg-red-100 text-red-700",
  PAYMENT_ORDER_CREATED: "bg-indigo-100 text-indigo-700",
  PAYMENT_ORDER_FAILED: "bg-red-100 text-red-700",
  PAYMENT_SUCCESS: "bg-emerald-100 text-emerald-700",
  ORDER_CONFIRMED: "bg-emerald-100 text-emerald-700",
  PAYMENT_FAILED: "bg-red-100 text-red-700",
};

function paise(value: unknown): string | null {
  if (typeof value !== "number") return null;
  return `₹${(value / 100).toLocaleString("en-IN")}`;
}

function str(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function names(value: unknown): string | null {
  if (!Array.isArray(value)) return null;
  const list = value.filter((v): v is string => typeof v === "string");
  return list.length > 0 ? list.join(", ") : null;
}

function detailFor(event: AuditEvent): string | null {
  const d = event.event_data || {};
  switch (event.event_type) {
    case "USER_INTENT_RECEIVED": {
      const msg = str(d.message);
      return msg ? `“${msg.length > 90 ? msg.slice(0, 90) + "…" : msg}”` : null;
    }
    case "SEARCH_PERFORMED": {
      const q = str(d.query) ?? "catalog";
      const n = typeof d.result_count === "number" ? d.result_count : null;
      const list = names(d.product_names);
      return `“${q}” → ${n ?? "?"} result${n === 1 ? "" : "s"}${list ? `: ${list}` : ""}`;
    }
    case "RECOMMENDATION_MADE": {
      const list = names(d.product_names);
      const reason = str(d.reason);
      return `${list ?? "items"}${reason ? ` — ${reason}` : ""}`;
    }
    case "CART_ITEM_ADDED": {
      const name = str(d.product_name) ?? `product #${String(d.product_id ?? "?")}`;
      const qty = typeof d.quantity === "number" ? ` × ${d.quantity}` : "";
      return `${name}${qty}${d.is_upsell ? " (upsell)" : ""}`;
    }
    case "CART_ITEM_REMOVED": {
      const name = str(d.product_name) ?? `item #${String(d.item_id ?? "?")}`;
      return name;
    }
    case "POLICY_CHECK_PASSED":
    case "POLICY_CHECK_FAILED": {
      return str(d.reason) ?? (event.event_type === "POLICY_CHECK_PASSED" ? "within limits" : null);
    }
    case "POLICY_CHANGED": {
      const action = str(d.action);
      return action ? `policy ${action}` : "policy changed";
    }
    case "PAYMENT_APPROVAL_REQUESTED":
    case "PAYMENT_APPROVED":
    case "PAYMENT_APPROVAL_REJECTED": {
      const amount = paise(d.amount_paise);
      return `approval #${String(d.approval_id ?? "?")}${amount ? ` · ${amount}` : ""}`;
    }
    case "PAYMENT_ORDER_CREATED": {
      const amount = paise(d.amount_paise);
      return `${str(d.order_number) ?? "order"} · Razorpay ${str(d.razorpay_order_id) ?? ""}${amount ? ` · ${amount}` : ""}`.trim();
    }
    case "PAYMENT_ORDER_FAILED":
      return str(d.reason);
    case "PAYMENT_SUCCESS": {
      const amount = paise(d.amount_paise);
      return `${str(d.order_number) ?? "order"} · ${str(d.razorpay_payment_id) ?? ""}${amount ? ` · ${amount}` : ""}`.trim();
    }
    case "ORDER_CONFIRMED": {
      const amount = paise(d.total_paise);
      return `${str(d.order_number) ?? "order"}${amount ? ` · ${amount}` : ""}`;
    }
    case "PAYMENT_FAILED":
      return str(d.reason);
    default:
      return null;
  }
}

function labelFor(eventType: string): string {
  return (
    LABELS[eventType] ??
    eventType.toLowerCase().split("_").map((w) => w[0].toUpperCase() + w.slice(1)).join(" ")
  );
}

function timeFor(timestamp?: string | null): string {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString("en-IN", { hour12: false });
}

export function AuditTrail({ sessionId, merchantId, refreshKey }: AuditTrailProps) {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTrail = useCallback(async () => {
    const params = new URLSearchParams();
    if (sessionId) params.set("session_id", sessionId);
    if (merchantId !== undefined && merchantId !== null) {
      params.set("merchant_id", String(merchantId));
    }
    if ([...params.keys()].length === 0) {
      setEvents([]);
      setLoading(false);
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/audit?${params.toString()}`);
      if (!res.ok) throw new Error("Could not load audit trail");
      setEvents(await res.json());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load audit trail");
    } finally {
      setLoading(false);
    }
  }, [sessionId, merchantId, refreshKey]);

  useEffect(() => {
    fetchTrail();
    const timer = setInterval(fetchTrail, 4000);
    return () => clearInterval(timer);
  }, [fetchTrail]);

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex items-center gap-2">
        <ScrollText className="h-4 w-4 text-slate-500" aria-hidden="true" />
        <h3 className="text-[13px] font-semibold uppercase tracking-wider text-slate-600">
          Audit trail
        </h3>
        <Badge variant="outline" className="border-slate-300 text-[11px] tabular-nums text-slate-600 bg-slate-50">
          {events.length}
        </Badge>
        <Button
          variant="ghost"
          size="icon"
          onClick={fetchTrail}
          aria-label="Refresh audit trail"
          title="Refresh trail"
          className="ml-auto h-7 w-7 text-slate-400 hover:text-slate-900 hover:bg-slate-100"
        >
          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto pr-1">
        {loading && events.length === 0 && (
          <p className="py-6 text-center text-[13px] text-slate-500">Loading trail…</p>
        )}
        {error && (
          <p className="py-6 text-center text-[13px] text-red-600">{error}</p>
        )}
        {!loading && !error && events.length === 0 && (
          <p className="py-6 text-center text-[13px] text-slate-500">
            No events yet — chat to start the trail.
          </p>
        )}
        <ol className="relative space-y-2">
          {events.map((event) => {
            const detail = detailFor(event);
            const Icon = EVENT_ICONS[event.event_type] ?? CircleDot;
            const chip = EVENT_CHIP[event.event_type] ?? "bg-slate-200 text-slate-600";
            return (
              <li
                key={event.id}
                className="relative flex gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm"
              >
                <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${chip}`}>
                  <Icon className="h-4 w-4" aria-hidden="true" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span className="text-sm font-semibold text-slate-900">
                      {labelFor(event.event_type)}
                    </span>
                    <Badge
                      variant="outline"
                      className={`text-[11px] ${ACTOR_STYLES[event.actor] ?? ACTOR_STYLES.system}`}
                    >
                      {event.actor}
                    </Badge>
                    <span className="ml-auto font-mono text-[11px] tabular-nums text-slate-400">
                      {timeFor(event.timestamp)}
                    </span>
                  </div>
                  {detail && (
                    <p className="mt-1 text-[13px] leading-relaxed text-slate-600 break-words">{detail}</p>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}
