"use client";

import { ArrowUp } from "lucide-react";
import { KeyboardEvent, useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
  initialValue?: string;
}

export function Composer({ onSend, disabled }: Props) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (ref.current) {
      ref.current.style.height = "auto";
      ref.current.style.height = Math.min(ref.current.scrollHeight, 200) + "px";
    }
  }, [value]);

  function submit() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className="border-t border-border bg-surface px-4 py-3">
      <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-border bg-canvas px-3 py-2 focus-within:ring-2 focus-within:ring-accent/40">
        <textarea
          ref={ref}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          rows={1}
          placeholder="Ask about product strategy, growth, retention... (Shift+Enter for a new line)"
          disabled={disabled}
          className="max-h-[200px] flex-1 resize-none bg-transparent py-1.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none disabled:opacity-60"
        />
        <button
          onClick={submit}
          disabled={disabled || !value.trim()}
          aria-label="Send message"
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-full transition-colors",
            disabled || !value.trim()
              ? "bg-ink-faint/20 text-ink-faint cursor-not-allowed"
              : "bg-accent text-accent-ink hover:opacity-90"
          )}
        >
          <ArrowUp size={16} />
        </button>
      </div>
      <p className="mx-auto mt-1.5 max-w-3xl text-center text-[11px] text-ink-faint">
        Grounded in the ingested transcript knowledge base — the assistant will say so when it
        can&apos;t find supporting evidence.
      </p>
    </div>
  );
}
