"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FlaskConical, Loader2 } from "lucide-react";

interface DemoControlsProps {
  sessionId: string;
  onDone?: (result: Record<string, unknown>) => void;
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

const ACTIONS = [
  { key: "reset", label: "Reset demo", path: "/demo/reset", method: "POST" },
  { key: "success", label: "Run successful purchase", path: "/demo/run-successful-purchase", method: "POST" },
  { key: "failure", label: "Run payment failure", path: "/demo/run-payment-failure", method: "POST" },
  { key: "upsell", label: "Run upsell scenario", path: "/demo/run-upsell-scenario", method: "POST" },
];

export function DemoControls({ sessionId, onDone }: DemoControlsProps) {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/demo/status`)
      .then((res) => (res.ok ? res.json() : { demo_mode: false }))
      .then((data) => setEnabled(data.demo_mode === true))
      .catch(() => setEnabled(false));
  }, []);

  if (enabled !== true) return null;

  const run = async (action: (typeof ACTIONS)[number]) => {
    setBusy(action.key);
    setMessage(null);
    try {
      const res = await fetch(
        `${API_BASE}${action.path}?session_id=${encodeURIComponent(sessionId)}`,
        { method: action.method }
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `${action.label} failed`);
      const status = typeof data.status === "string" ? ` — ${data.status}` : "";
      setMessage(`${action.label} done${status}.`);
      onDone?.(data);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : `${action.label} failed.`);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="border-2 border-dashed border-amber-400 bg-amber-50 px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <FlaskConical className="h-4 w-4 text-amber-700" aria-hidden="true" />
        <span className="text-[13px] font-semibold text-amber-900">Demo Controls</span>
        <Badge variant="outline" className="border-amber-500 text-[10px] font-bold text-amber-800 bg-white">
          DEV
        </Badge>
        <span className="text-xs text-amber-700">
          Scripted, LLM-free triggers for stage reliability. Hidden when DEMO_MODE is off.
        </span>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          {ACTIONS.map((action) => (
            <Button
              key={action.key}
              size="sm"
              variant="outline"
              disabled={busy !== null}
              onClick={() => run(action)}
              className="border-amber-500 bg-white text-amber-900 hover:bg-amber-100 h-8 text-xs touch-manipulation"
            >
              {busy === action.key && <Loader2 className="mr-1.5 h-3 w-3 animate-spin" aria-hidden="true" />}
              {action.label}
            </Button>
          ))}
        </div>
      </div>
      {message && (
        <p className="mt-1.5 text-xs text-amber-800" aria-live="polite">
          {message}
        </p>
      )}
    </div>
  );
}
