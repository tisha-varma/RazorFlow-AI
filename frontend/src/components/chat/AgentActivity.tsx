"use client";

import { Loader2 } from "lucide-react";

interface AgentActivityProps {
  message: string;
}

export function AgentActivity({ message }: AgentActivityProps) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-slate-800/50 rounded-lg border border-slate-700/50">
      <Loader2 className="h-4 w-4 text-blue-400 animate-spin" />
      <span className="text-sm text-slate-300">{message}</span>
    </div>
  );
}
