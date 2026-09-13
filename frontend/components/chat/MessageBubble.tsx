"use client";

import { Check, Copy, FileCode2, ThumbsDown, ThumbsUp } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { SourceChips } from "@/components/chat/SourceChips";
import { api } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { ArtifactOut, MessageOut } from "@/types";

interface Props {
  message: MessageOut;
  artifact?: ArtifactOut;
  onOpenArtifact?: (artifact: ArtifactOut) => void;
}

export function MessageBubble({ message, artifact, onOpenArtifact }: Props) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);
  const isUser = message.role === "user";

  async function copy() {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  async function sendFeedback(rating: "up" | "down") {
    setFeedback(rating);
    try {
      await api.sendFeedback(message.id, rating);
    } catch {
      // Feedback is best-effort - failing silently here beats interrupting the reading flow.
    }
  }

  if (isUser) {
    return (
      <div className="flex justify-end animate-slide-in">
        <div className="max-w-[75%] rounded-2xl rounded-tr-sm bg-accent px-4 py-2.5 text-sm text-accent-ink whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start animate-slide-in group">
      <div className="max-w-[85%] min-w-0">
        <div className="rounded-2xl rounded-tl-sm border border-border bg-surface px-4 py-3">
          <div className="markdown-body prose prose-sm max-w-none prose-p:leading-relaxed prose-pre:text-xs dark:prose-invert prose-headings:mt-3 prose-headings:mb-1.5">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>

          {artifact && (
            <button
              onClick={() => onOpenArtifact?.(artifact)}
              className="mt-2.5 inline-flex items-center gap-2 rounded-lg border border-accent/30 bg-accent/5 px-3 py-2 text-xs font-medium text-accent hover:bg-accent/10 transition-colors"
            >
              <FileCode2 size={14} />
              Open {artifact.type === "html" ? "HTML" : "Markdown"} artifact — {artifact.title}
            </button>
          )}

          <SourceChips sources={message.sources} />
        </div>

        <div className="mt-1 flex items-center gap-0.5 px-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {message.provider && (
            <span className="mr-1.5 text-[10px] text-ink-faint">
              {message.provider} · {message.model}
            </span>
          )}
          <button
            onClick={copy}
            className="rounded p-1 text-ink-faint hover:text-ink hover:bg-surface-raised"
            aria-label="Copy message"
          >
            {copied ? <Check size={12} /> : <Copy size={12} />}
          </button>
          <button
            onClick={() => sendFeedback("up")}
            className={cn(
              "rounded p-1 hover:bg-surface-raised",
              feedback === "up" ? "text-emerald-500" : "text-ink-faint hover:text-ink"
            )}
            aria-label="Good response"
          >
            <ThumbsUp size={12} />
          </button>
          <button
            onClick={() => sendFeedback("down")}
            className={cn(
              "rounded p-1 hover:bg-surface-raised",
              feedback === "down" ? "text-danger" : "text-ink-faint hover:text-ink"
            )}
            aria-label="Bad response"
          >
            <ThumbsDown size={12} />
          </button>
        </div>
      </div>
    </div>
  );
}
