"use client";

import { Loader2 } from "lucide-react";

interface AgentActivityProps {
  message: string;
}

export function AgentActivity({ message }: AgentActivityProps) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-indigo-50 rounded-xl border border-indigo-100" aria-live="polite">
      <Loader2 className="h-4 w-4 text-indigo-600 animate-spin" aria-hidden="true" />
      <span className="text-sm text-indigo-900">{message}</span>
    </div>
  );
}
