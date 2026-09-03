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
  Gift,
  ThumbsUp,
  CircleDot,
  Check,
  X,
} from "lucide-react";

interface AuditEvent {
  id: number;
  session_id?: string | null;
  merchant_id: number;
  event_type: string;
  event_data: Record<string, unknown>;
  llm_reason_text?: string | null;
  policy_snapshot_id?: string | null;
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
  RECOMMENDATION_MADE: "Product recommended",
  UPSELL_OFFERED: "Upsell offered",
  UPSELL_ACCEPTED: "Upsell accepted",
  CART_ITEM_ADDED: "Added to cart",
  CART_ITEM_REMOVED: "Removed from cart",
  POLICY_CHECK_PASSED: "Policy check",
  POLICY_CHECK_FAILED: "Policy check",
  POLICY_CHANGED: "Policy updated",
  PAYMENT_APPROVAL_REQUESTED: "Approval requested",
  PAYMENT_APPROVED: "Payment approved",
  PAYMENT_APPROVAL_REJECTED: "Purchase rejected",
  PAYMENT_ORDER_CREATED: "Razorpay order created",
  PAYMENT_ORDER_FAILED: "Payment order failed",
  PAYMENT_SUCCESS: "Payment success",
  ORDER_CONFIRMED: "Order confirmed",
  PAYMENT_FAILED: "Payment failed",
};

const FAILED_TYPES = new Set([
  "POLICY_CHECK_FAILED",
  "PAYMENT_APPROVAL_REJECTED",
  "PAYMENT_ORDER_FAILED",
  "PAYMENT_FAILED",
]);

const EVENT_ICONS: Record<string, typeof Search> = {
  USER_INTENT_RECEIVED: MessageSquare,
  SEARCH_PERFORMED: Search,
  RECOMMENDATION_MADE: Sparkles,
  UPSELL_OFFERED: Gift,
  UPSELL_ACCEPTED: ThumbsUp,
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
  UPSELL_OFFERED: "bg-amber-100 text-amber-800",
  UPSELL_ACCEPTED: "bg-emerald-100 text-emerald-700",
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
      const reason = str(event.llm_reason_text) ?? str(d.llm_reason_text) ?? str(d.reason);
      return `${list ?? "items"}${reason ? ` — ${reason}` : ""}`;
    }
    case "UPSELL_OFFERED": {
      const list = names(d.product_names);
      const amounts = Array.isArray(d.amounts_paise)
        ? (d.amounts_paise as unknown[]).filter((v): v is number => typeof v === "number")
        : [];
      const suffix = amounts.length > 0 ? ` — ${amounts.map((a) => paise(a)).join(", ")}` : "";
      return `${list ?? "items"}${suffix}`;
    }
    case "UPSELL_ACCEPTED": {
      const name = str(d.product_name);
      const qty = typeof d.quantity === "number" ? ` × ${d.quantity}` : "";
      return `${name ?? "item"}${qty}`;
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
      const total = paise(d.cart_total_paise);
      const limit = paise(d.max_transaction_paise);
      if (total && limit) {
        const verdict = `₹${(Number(d.cart_total_paise) / 100).toLocaleString("en-IN")} ≤ ₹${(Number(d.max_transaction_paise) / 100).toLocaleString("en-IN")}`;
        const snapshot = event.policy_snapshot_id ? ` · ${event.policy_snapshot_id}` : "";
        return event.event_type === "POLICY_CHECK_FAILED" && str(d.reason)
          ? `${verdict} — ${str(d.reason)}${snapshot}`
          : `${verdict}${snapshot}`;
      }
      const snapshot = event.policy_snapshot_id ? ` · ${event.policy_snapshot_id}` : "";
      const fallback = str(d.reason) ?? (event.event_type === "POLICY_CHECK_PASSED" ? "within limits" : null);
      return fallback ? `${fallback}${snapshot}` : null;
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
    void refreshKey;
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
      const rows: AuditEvent[] = await res.json();
      // Newest first: recent actions on top, no scrolling to find them.
      setEvents([...rows].reverse());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load audit trail");
    } finally {
      setLoading(false);
    }
  }, [sessionId, merchantId, refreshKey]);

  useEffect(() => {
    const immediate = setTimeout(fetchTrail, 0);
    const timer = setInterval(fetchTrail, 4000);
    return () => {
      clearTimeout(immediate);
      clearInterval(timer);
    };
  }, [fetchTrail]);

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex items-center gap-2">
        <ScrollText className="h-4 w-4 text-slate-500" aria-hidden="true" />
        <h3 className="text-[13px] font-semibold uppercase tracking-wider text-slate-600">
          Audit trail
        </h3>
        <span className="text-[11px] text-slate-400">newest first</span>
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
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">
              Transaction audit trail, chronological
            </caption>
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                <th scope="col" className="w-10 px-3 py-2 text-center">✓</th>
                <th scope="col" className="px-3 py-2 whitespace-nowrap">Time</th>
                <th scope="col" className="px-3 py-2">Event</th>
                <th scope="col" className="px-3 py-2">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {events.map((event) => {
                const detail = detailFor(event);
                const Icon = EVENT_ICONS[event.event_type] ?? CircleDot;
                const chip = EVENT_CHIP[event.event_type] ?? "bg-slate-200 text-slate-600";
                const failed = FAILED_TYPES.has(event.event_type);
                return (
                  <tr key={event.id} className="align-top hover:bg-slate-50">
                    <td className="px-3 py-2.5 text-center">
                      {failed ? (
                        <X className="inline h-4 w-4 text-red-500" aria-label="failed" />
                      ) : (
                        <Check className="inline h-4 w-4 text-emerald-600" aria-label="ok" />
                      )}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 font-mono text-[11px] tabular-nums text-slate-500">
                      {timeFor(event.timestamp)}
                    </td>
                    <td className="px-3 py-2.5">
                      <span className="flex items-center gap-1.5">
                        <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-md ${chip}`}>
                          <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                        </span>
                        <span className="text-[13px] font-semibold text-slate-900">
                          {labelFor(event.event_type)}
                        </span>
                      </span>
                      <span className="mt-1 block text-[11px] text-slate-400">{event.actor}</span>
                    </td>
                    <td className="px-3 py-2.5 text-[13px] leading-relaxed text-slate-600 break-words">
                      {detail ?? <span className="text-slate-300">—</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
