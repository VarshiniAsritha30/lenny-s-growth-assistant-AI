"use client";

import { MessageSquarePlus, Search, Trash2, X } from "lucide-react";
import { useMemo, useState } from "react";
import { ModelPicker } from "@/components/ModelPicker";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button } from "@/components/ui/Button";
import { cn, formatRelativeTime } from "@/lib/utils";
import { SessionOut } from "@/types";

interface Props {
  sessions: SessionOut[];
  activeSessionId: string | null;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  onDelete: (id: string) => void;
  onCloseMobile?: () => void;
}

export function Sidebar({ sessions, activeSessionId, onSelect, onNewChat, onDelete, onCloseMobile }: Props) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    if (!query.trim()) return sessions;
    const q = query.toLowerCase();
    return sessions.filter((s) => s.title.toLowerCase().includes(q));
  }, [sessions, query]);

  return (
    <div className="flex h-full w-72 flex-col border-r border-border bg-surface">
      <div className="flex items-center justify-between px-3 pt-3 pb-2">
        <div className="flex items-center gap-2 px-1">
          <div className="h-6 w-6 rounded-md bg-accent flex items-center justify-center text-accent-ink text-xs font-bold">
            L
          </div>
          <span className="text-sm font-semibold text-ink">Lenny Growth Assistant</span>
        </div>
        {onCloseMobile && (
          <button onClick={onCloseMobile} className="lg:hidden p-1 text-ink-muted" aria-label="Close sidebar">
            <X size={18} />
          </button>
        )}
      </div>

      <div className="px-3 pb-2">
        <Button variant="primary" className="w-full" onClick={onNewChat}>
          <MessageSquarePlus size={16} /> New chat
        </Button>
      </div>

      <div className="px-3 pb-2">
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-faint" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search conversations"
            className="w-full h-8 rounded-md border border-border bg-canvas pl-8 pr-2.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-accent/40"
          />
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 space-y-0.5" aria-label="Recent conversations">
        {filtered.length === 0 && (
          <p className="px-3 py-6 text-center text-xs text-ink-faint">
            {sessions.length === 0 ? "No conversations yet" : "No matches"}
          </p>
        )}
        {filtered.map((s) => (
          <div
            key={s.id}
            className={cn(
              "group flex items-center gap-2 rounded-md px-2.5 py-2 cursor-pointer transition-colors",
              s.id === activeSessionId ? "bg-accent/10 text-ink" : "text-ink-muted hover:bg-canvas hover:text-ink"
            )}
            onClick={() => onSelect(s.id)}
          >
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm">{s.title}</p>
              <p className="text-xs text-ink-faint">{formatRelativeTime(s.updated_at)}</p>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(s.id);
              }}
              className="opacity-0 group-hover:opacity-100 p-1 rounded text-ink-faint hover:text-danger transition-opacity"
              aria-label={`Delete ${s.title}`}
              title="Delete conversation"
            >
              <Trash2 size={13} />
            </button>
          </div>
        ))}
      </nav>

      <div className="border-t border-border p-3 space-y-2">
        <p className="text-xs font-medium text-ink-faint px-1">Settings</p>
        <ModelPicker />
        <div className="flex items-center justify-between px-1">
          <span className="text-xs text-ink-faint">Appearance</span>
          <ThemeToggle />
        </div>
      </div>
    </div>
  );
}
