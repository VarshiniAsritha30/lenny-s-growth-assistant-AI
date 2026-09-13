"use client";

import { ExternalLink, FileText } from "lucide-react";
import { useState } from "react";
import { SourceOut } from "@/types";

export function SourceChips({ sources }: { sources: SourceOut[] }) {
  const [openId, setOpenId] = useState<string | null>(null);
  if (sources.length === 0) return null;

  return (
    <div className="mt-2.5">
      <p className="mb-1.5 text-xs font-medium text-ink-faint">Sources</p>
      <div className="flex flex-wrap gap-1.5">
        {sources.map((s) => (
          <div key={s.chunk_id} className="relative">
            <button
              onClick={() => setOpenId(openId === s.chunk_id ? null : s.chunk_id)}
              className="inline-flex max-w-[220px] items-center gap-1.5 rounded-full border border-border bg-surface-raised px-2.5 py-1 text-xs text-ink-muted hover:border-accent/40 hover:text-ink transition-colors"
              title={s.episode_title}
            >
              <FileText size={11} className="shrink-0" />
              <span className="truncate">{s.episode_title}</span>
            </button>
            {openId === s.chunk_id && (
              <div className="absolute z-20 mt-1.5 w-72 rounded-lg border border-border bg-surface p-3 shadow-lg animate-fade-in">
                <p className="text-xs font-semibold text-ink">{s.episode_title}</p>
                {s.guest && <p className="text-xs text-ink-faint">{s.guest}</p>}
                <p className="mt-2 text-xs leading-relaxed text-ink-muted line-clamp-6">
                  &ldquo;{s.excerpt}&rdquo;
                </p>
                <div className="mt-2 flex items-center justify-between">
                  <span className="text-[10px] text-ink-faint">relevance {(s.score * 100).toFixed(0)}%</span>
                  {s.url && (
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-[10px] text-accent hover:underline"
                    >
                      Source <ExternalLink size={10} />
                    </a>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
