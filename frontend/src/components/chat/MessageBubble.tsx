"use client";

import React from "react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface MessageBubbleProps {
  message: Message;
}

/** Inline markdown: **bold**, *italic*, `code`. */
function renderInline(text: string, keyPrefix: string, isUserBubble = false): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*\n]+\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    const key = `${keyPrefix}-i${i}`;
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return (
        <strong key={key} className={`font-semibold ${isUserBubble ? "text-white" : "text-slate-900"}`}>
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("*") && part.endsWith("*") && part.length > 2 && !part.startsWith("**")) {
      return (
        <em key={key} className={isUserBubble ? "text-indigo-100" : "text-slate-700"}>
          {part.slice(1, -1)}
        </em>
      );
    }
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      return (
        <code
          key={key}
          className="rounded bg-slate-100 border border-slate-200 px-1.5 py-0.5 font-mono text-xs text-slate-700"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return <React.Fragment key={key}>{part}</React.Fragment>;
  });
}

/** Block markdown: headings, bullets, numbered lists, paragraphs. */
function renderMarkdown(content: string, isUserBubble = false): React.ReactNode[] {
  const lines = content.split("\n");
  const blocks: React.ReactNode[] = [];
  let listItems: string[] = [];
  let listOrdered = false;
  let key = 0;

  const flushList = () => {
    if (listItems.length === 0) return;
    const items = listItems;
    const ordered = listOrdered;
    const listKey = key++;
    blocks.push(
      ordered ? (
        <ol key={listKey} className="ml-5 list-decimal space-y-1.5">
          {items.map((item, i) => (
            <li key={i} className="pl-1">
              {renderInline(item, `b${listKey}-${i}`, isUserBubble)}
            </li>
          ))}
        </ol>
      ) : (
        <ul key={listKey} className="ml-1 space-y-1.5">
          {items.map((item, i) => (
            <li key={i} className="flex gap-2">
              <span className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${isUserBubble ? "bg-indigo-200" : "bg-indigo-500"}`} aria-hidden="true" />
              <span>{renderInline(item, `b${listKey}-${i}`, isUserBubble)}</span>
            </li>
          ))}
        </ul>
      )
    );
    listItems = [];
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (line === "") {
      flushList();
      continue;
    }
    const bullet = line.match(/^[*•\-]\s+(.*)$/);
    const numbered = line.match(/^\d+[.)]\s+(.*)$/);
    const heading = line.match(/^#{1,3}\s+(.*)$/);
    if (bullet) {
      if (listItems.length > 0 && listOrdered) flushList();
      listOrdered = false;
      listItems.push(bullet[1]);
    } else if (numbered) {
      if (listItems.length > 0 && !listOrdered) flushList();
      listOrdered = true;
      listItems.push(numbered[1]);
    } else if (heading) {
      flushList();
      const hKey = key++;
      blocks.push(
        <p key={hKey} className={`text-[15px] font-semibold ${isUserBubble ? "text-white" : "text-slate-900"}`}>
          {renderInline(heading[1], `h${hKey}`, isUserBubble)}
        </p>
      );
    } else {
      flushList();
      const pKey = key++;
      blocks.push(<p key={pKey}>{renderInline(line, `p${pKey}`, isUserBubble)}</p>);
    }
  }
  flushList();
  return blocks;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex items-end gap-2 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-900 text-[11px] font-bold text-white" aria-hidden="true">
          AI
        </span>
      )}
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-[14px] leading-relaxed ${
          isUser
            ? "rounded-br-md bg-blue-700 text-white"
            : "rounded-bl-md border border-slate-200/80 bg-white text-slate-800 shadow-[0_1px_2px_rgba(15,23,42,0.06)]"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        ) : (
          <div className="space-y-2 break-words">{renderMarkdown(message.content, false)}</div>
        )}
        <p className={`text-[11px] mt-1.5 tabular-nums ${isUser ? "text-indigo-200" : "text-slate-400"}`}>
          {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </p>
      </div>
    </div>
  );
}
