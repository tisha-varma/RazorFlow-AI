"use client";

import { useState, useEffect } from "react";

interface SummaryItem {
  item_id: number;
  product_id: number;
  product_name: string;
  category?: string | null;
  quantity: number;
  unit_price_paise: number;
  total_paise: number;
  is_upsell: boolean;
  reason?: string | null;
}

interface PolicyDetails {
  max_transaction?: number;
  cart_total?: number;
  session_spent?: number;
  spending_limit_paise?: number;
  max_upsell_amount_paise?: number;
  upsell_total_paise?: number;
  remaining_budget?: number;
  approval_required?: boolean;
}

interface Summary {
  approval_id: number;
  cart_id: number;
  session_id: string;
  items: SummaryItem[];
  subtotal_paise: number;
  upsell_total_paise: number;
  total_paise: number;
  status: string;
  policy_allowed?: boolean | null;
  policy_reason?: string | null;
  policy_details?: PolicyDetails | null;
}

interface ApprovalScreenProps {
  approvalId: number;
  approvalToken?: string | null;
  sessionId: string;
  onApprove: () => void;
  onReject: () => void;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

function formatPaise(paise: number): string {
  return `₹${(paise / 100).toLocaleString("en-IN")}`;
}

export default function ApprovalScreen({
  approvalId,
  approvalToken,
  sessionId,
  onApprove,
  onReject,
}: ApprovalScreenProps) {
  const [busy, setBusy] = useState<null | "approve" | "reject">(null);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/checkout/approval/${approvalId}/summary?session_id=${sessionId}`)
      .then((res) => {
        if (!res.ok) throw new Error("Could not load order summary");
        return res.json();
      })
      .then((data: Summary) => {
        if (!cancelled) setSummary(data);
      })
      .catch((e) => {
        if (!cancelled) setSummaryError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [approvalId, sessionId]);

  const handleAction = async (action: "approve" | "reject") => {
    setBusy(action);
    setError(null);
    try {
      if (!approvalToken) {
        throw new Error("Missing approval token — please checkout again to get a fresh approval.");
      }
      const res = await fetch(
        `${API_BASE}/checkout/${action}/${approvalId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId, approval_token: approvalToken }),
        }
      );
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || `Failed to ${action}`);
      }
      if (action === "approve") onApprove();
      else onReject();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  };

  const details = summary?.policy_details;

  return (
    <div className="overflow-hidden rounded-2xl border border-amber-200/80 bg-gradient-to-br from-amber-50 to-orange-50/60 shadow-[0_8px_24px_-12px_rgba(217,119,6,0.35)]">
      <div className="h-1 bg-gradient-to-r from-amber-500 to-orange-400" aria-hidden="true" />
      <div className="p-5">
      <div className="mb-4 flex items-center gap-2.5">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 text-sm font-bold text-white shadow-md" aria-hidden="true">
          !
        </span>
        <div className="leading-tight">
          <h3 className="text-[16px] font-semibold text-amber-900">
            Approval Required
          </h3>
          <p className="text-[11px] text-amber-700">Human gate — nothing moves until you decide</p>
        </div>
      </div>

      {/* What am I buying */}
      {summary ? (
        <div className="mb-4">
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-amber-700">
            Order summary
          </h4>
          <div className="divide-y divide-amber-100 rounded-lg border border-amber-200 bg-white">
            {summary.items.map((item) => (
              <div key={item.item_id} className="px-3 py-2.5">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-sm font-medium text-slate-800">
                    {item.product_name}
                  </span>
                  <span className="text-sm font-semibold text-slate-900">
                    {formatPaise(item.total_paise)}
                  </span>
                </div>
                <div className="mt-0.5 flex items-center gap-2 text-xs text-slate-500">
                  {item.category && <span>{item.category}</span>}
                  <span>
                    Qty {item.quantity} × {formatPaise(item.unit_price_paise)}
                  </span>
                  {item.is_upsell && (
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 font-medium text-amber-700">
                      Upsell
                    </span>
                  )}
                </div>
                {item.reason && (
                  <p className="mt-0.5 text-xs italic text-slate-500">
                    Why: {item.reason}
                  </p>
                )}
              </div>
            ))}
          </div>

          <div className="mt-2 space-y-1 rounded-lg border border-amber-200 bg-white px-3 py-2.5 text-sm">
            <div className="flex justify-between text-slate-600">
              <span>Subtotal</span>
              <span>{formatPaise(summary.subtotal_paise)}</span>
            </div>
            {summary.upsell_total_paise > 0 && (
              <div className="flex justify-between text-slate-600">
                <span>Upsell amount</span>
                <span>{formatPaise(summary.upsell_total_paise)}</span>
              </div>
            )}
            <div className="flex justify-between border-t border-amber-100 pt-1 font-semibold text-slate-900">
              <span>Total</span>
              <span>{formatPaise(summary.total_paise)}</span>
            </div>
          </div>
        </div>
      ) : summaryError ? (
        <p className="mb-4 text-sm text-red-600">
          Could not load the order breakdown ({summaryError}). You can still
          approve or reject below.
        </p>
      ) : (
        <p className="mb-4 text-sm text-amber-700">Loading order summary…</p>
      )}

      {/* What limit does it respect */}
      {details && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-white px-3 py-2.5 text-sm">
          <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-amber-700">
            Policy check
          </h4>
          <div className="space-y-1 text-slate-600">
            <div className="flex justify-between gap-2">
              <span>Status</span>
              <span
                className={
                  summary?.policy_allowed === false
                    ? "font-medium text-red-600"
                    : "font-medium text-green-700"
                }
              >
                {summary?.policy_allowed === false ? "Blocked" : "Allowed"}
              </span>
            </div>
            {summary?.policy_reason && (
              <p className="text-xs italic text-slate-500">{summary.policy_reason}</p>
            )}
            {details.spending_limit_paise !== undefined && (
              <div className="flex justify-between gap-2">
                <span>Session spending limit</span>
                <span>{formatPaise(details.spending_limit_paise)}</span>
              </div>
            )}
            {details.remaining_budget !== undefined && (
              <div className="flex justify-between gap-2">
                <span>Remaining after this purchase</span>
                <span>{formatPaise(details.remaining_budget)}</span>
              </div>
            )}
            {details.max_transaction !== undefined && (
              <div className="flex justify-between gap-2">
                <span>Max per transaction</span>
                <span>{formatPaise(details.max_transaction)}</span>
              </div>
            )}
            <div className="flex justify-between gap-2">
              <span>Approval required</span>
              <span className="font-medium text-slate-800">
                {details.approval_required === false ? "No" : "Yes"}
              </span>
            </div>
          </div>
        </div>
      )}

      <p className="mb-4 text-sm text-amber-800">
        Please review and explicitly approve this purchase before payment
        processing.
      </p>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={() => handleAction("reject")}
          disabled={busy !== null}
          className="h-11 flex-1 rounded-xl border border-red-300 bg-white px-4 text-sm font-semibold text-red-700 shadow-sm transition-all hover:bg-red-50 active:scale-[0.99] disabled:opacity-50 touch-manipulation"
        >
          {busy === "reject" ? "Rejecting…" : "Reject"}
        </button>
        <button
          onClick={() => handleAction("approve")}
          disabled={busy !== null}
          className="h-11 flex-1 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-4 text-sm font-semibold text-white shadow-[0_6px_16px_-4px_rgba(5,150,105,0.5)] transition-all hover:from-emerald-500 hover:to-teal-500 active:scale-[0.99] disabled:opacity-50 touch-manipulation"
        >
          {busy === "approve" ? "Approving…" : "Approve Purchase"}
        </button>
      </div>
      </div>
    </div>
  );
}
