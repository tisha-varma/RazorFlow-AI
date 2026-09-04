"use client";

import { Loader2 } from "lucide-react";

interface AgentActivityProps {
  message: string;
}

export function AgentActivity({ message }: AgentActivityProps) {
  return (
    <div className="flex items-center gap-3 rounded-2xl rounded-bl-md border border-blue-100 bg-blue-50 px-4 py-3" aria-live="polite">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-700" aria-hidden="true">
        <Loader2 className="h-3.5 w-3.5 animate-spin text-white" />
      </span>
      <span className="text-sm text-indigo-900">{message}</span>
      <span className="ml-1 flex items-center gap-1" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-400"
            style={{ animationDelay: `${i * 180}ms` }}
          />
        ))}
      </span>
    </div>
  );
}
