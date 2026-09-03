"use client";

import { useState, useEffect, useCallback } from "react";

interface SessionUsage {
  session_id: string;
  spending_limit_paise: number;
  session_spent_paise: number;
  cart_total_paise: number;
  used_paise: number;
  remaining_paise: number;
}

interface SessionLimitBarProps {
  sessionId: string;
  refreshKey?: string | number;
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

function formatPaise(paise: number): string {
  return `₹${(paise / 100).toLocaleString("en-IN")}`;
}

export function SessionLimitBar({ sessionId, refreshKey }: SessionLimitBarProps) {
  const [usage, setUsage] = useState<SessionUsage | null>(null);

  const fetchUsage = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/policy/session-usage?session_id=${sessionId}`);
      if (!res.ok) return;
      setUsage(await res.json());
    } catch {
      /* limit bar is advisory — never break the page */
    }
  }, [sessionId, refreshKey]);

  useEffect(() => {
    fetchUsage();
    const timer = setInterval(fetchUsage, 5000);
    return () => clearInterval(timer);
  }, [fetchUsage]);

  if (!usage || usage.spending_limit_paise <= 0) return null;

  const pct = Math.min(100, (usage.used_paise / usage.spending_limit_paise) * 100);
  const barColor =
    pct >= 90 ? "bg-red-500" : pct >= 70 ? "bg-amber-500" : "bg-emerald-500";

  return (
    <div
      className="flex items-center gap-3"
      title={`Spent ${formatPaise(usage.session_spent_paise)} · in cart ${formatPaise(usage.cart_total_paise)}`}
      aria-live="polite"
    >
      <span className="text-xs tabular-nums text-slate-600 whitespace-nowrap">
        {formatPaise(usage.used_paise)} of {formatPaise(usage.spending_limit_paise)} limit
        <span className="text-slate-400"> · {formatPaise(usage.remaining_paise)} left</span>
      </span>
      <div
        className="h-1.5 w-28 overflow-hidden rounded-full bg-slate-200"
        role="progressbar"
        aria-valuenow={Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Session spending limit used"
      >
        <div className={`h-full rounded-full transition-[width] duration-500 ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
