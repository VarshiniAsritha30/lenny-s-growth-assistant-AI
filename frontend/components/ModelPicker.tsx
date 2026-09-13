"use client";

import { Check, ChevronDown, CircleAlert, Cpu, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { ModelInfo } from "@/types";

const PROVIDER_LABEL: Record<string, string> = {
  ollama: "Ollama (local)",
  anthropic: "Anthropic",
  openai: "OpenAI",
};

export function ModelPicker({ compact = false }: { compact?: boolean }) {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [open, setOpen] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  async function refresh() {
    try {
      const data = await api.listModels();
      setModels(data);
    } catch {
      setError("Could not reach the backend to list models.");
    }
  }

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 15000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const active = models.find((m) => m.is_active);

  async function selectProvider(provider: string) {
    setSwitching(true);
    setError(null);
    try {
      await api.selectModel(provider);
      await refresh();
      setOpen(false);
    } catch (e: any) {
      setError(e?.message || "Could not switch provider.");
    } finally {
      setSwitching(false);
    }
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "inline-flex items-center gap-2 rounded-lg border border-border bg-surface-raised text-sm hover:bg-canvas transition-colors",
          compact ? "h-8 px-2.5" : "h-9 px-3 w-full justify-between"
        )}
      >
        <span className="inline-flex items-center gap-1.5 min-w-0">
          <Cpu size={14} className={active?.is_healthy ? "text-accent" : "text-danger"} />
          <span className="truncate">
            {active ? `${PROVIDER_LABEL[active.provider]} · ${active.model}` : "Loading model..."}
          </span>
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full shrink-0",
              active?.is_healthy ? "bg-emerald-500" : "bg-danger"
            )}
            title={active?.detail}
          />
        </span>
        <ChevronDown size={14} className="text-ink-faint shrink-0" />
      </button>

      {open && (
        <div className="absolute z-30 mt-1.5 w-80 rounded-lg border border-border bg-surface shadow-lg animate-fade-in right-0">
          <div className="px-3 py-2 border-b border-border">
            <p className="text-xs font-medium text-ink-muted">Model provider</p>
          </div>
          <div className="p-1.5">
            {models.map((m) => (
              <button
                key={m.provider}
                onClick={() => selectProvider(m.provider)}
                disabled={switching}
                className="w-full flex items-start gap-2.5 rounded-md px-2.5 py-2 text-left hover:bg-canvas transition-colors disabled:opacity-60"
              >
                <span className="mt-0.5">
                  {m.is_active ? (
                    <Check size={15} className="text-accent" />
                  ) : (
                    <span className="inline-block w-[15px]" />
                  )}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-1.5 text-sm font-medium text-ink">
                    {PROVIDER_LABEL[m.provider] || m.provider}
                    {!m.is_healthy && <CircleAlert size={13} className="text-danger" />}
                  </span>
                  <span className="block text-xs text-ink-faint truncate">{m.model}</span>
                  <span className="block text-xs text-ink-faint truncate mt-0.5">{m.detail}</span>
                </span>
              </button>
            ))}
            {models.length === 0 && !error && (
              <div className="px-2.5 py-3 text-xs text-ink-faint flex items-center gap-2">
                <Loader2 size={13} className="animate-spin" /> Loading providers...
              </div>
            )}
            {error && <p className="px-2.5 py-2 text-xs text-danger">{error}</p>}
          </div>
        </div>
      )}
    </div>
  );
}
