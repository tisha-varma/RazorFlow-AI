"use client";

import { useState, useEffect } from "react";

interface SummaryItem {
  item_id: number;
  product_id: number;
  product_name: string;
  quantity: number;
  unit_price_paise: number;
  total_paise: number;
  is_upsell: boolean;
}

interface ApprovalScreenProps {
  approvalId: number;
  sessionId: string;
  onApprove: () => void;
  onReject: () => void;
}

function formatPaise(paise: number): string {
  return `₹${(paise / 100).toLocaleString("en-IN")}`;
}

export default function ApprovalScreen({
  approvalId,
  sessionId,
  onApprove,
  onReject,
}: ApprovalScreenProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAction = async (action: "approve" | "reject") => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `http://localhost:8000/api/checkout/${action}/${approvalId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId }),
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
      setLoading(false);
    }
  };

  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-6">
      <div className="mb-4 flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-amber-500 text-white text-sm font-bold">
          !
        </div>
        <h3 className="text-lg font-semibold text-amber-900">
          Approval Required
        </h3>
      </div>
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
          disabled={loading}
          className="flex-1 rounded-lg border border-red-300 bg-white px-4 py-2.5 text-sm font-medium text-red-700 transition-colors hover:bg-red-50 disabled:opacity-50"
        >
          {loading ? "Processing..." : "Reject"}
        </button>
        <button
          onClick={() => handleAction("approve")}
          disabled={loading}
          className="flex-1 rounded-lg bg-green-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-green-700 disabled:opacity-50"
        >
          {loading ? "Processing..." : "Approve Purchase"}
        </button>
      </div>
    </div>
  );
}
