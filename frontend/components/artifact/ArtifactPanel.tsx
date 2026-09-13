"use client";

import {
  AlertTriangle,
  Check,
  Code2,
  Copy,
  Download,
  Eye,
  Loader2,
  Maximize2,
  Minimize2,
  RefreshCw,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import { ArtifactOut } from "@/types";

interface Props {
  artifact: ArtifactOut | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onRegenerate?: () => void;
  fullscreen: boolean;
  onToggleFullscreen: () => void;
}

type Tab = "preview" | "code";

export function ArtifactPanel({
  artifact,
  loading,
  error,
  onClose,
  onRegenerate,
  fullscreen,
  onToggleFullscreen,
}: Props) {
  const [tab, setTab] = useState<Tab>("preview");
  const [copied, setCopied] = useState(false);

  const extension = artifact?.type === "html" ? "html" : "md";

  const srcDoc = useMemo(() => {
    if (!artifact || artifact.type !== "html") return "";
    return artifact.content;
  }, [artifact]);

  async function copy() {
    if (!artifact) return;
    await navigator.clipboard.writeText(artifact.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  function download() {
    if (!artifact) return;
    const blob = new Blob([artifact.content], {
      type: artifact.type === "html" ? "text/html" : "text/markdown",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${artifact.title.replace(/[^a-z0-9-_ ]/gi, "").trim() || "artifact"}.${extension}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <div
      className={cn(
        "flex h-full flex-col border-l border-border bg-surface",
        fullscreen ? "fixed inset-0 z-40 w-full border-l-0" : "w-full lg:w-[46%] xl:w-[42%]"
      )}
    >
      <div className="flex h-14 shrink-0 items-center justify-between border-b border-border px-3">
        <div className="min-w-0 flex items-center gap-2">
          <span className="rounded bg-accent/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-accent">
            {artifact?.type || "artifact"}
          </span>
          <h3 className="truncate text-sm font-medium text-ink">{artifact?.title || "Artifact"}</h3>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <Button variant="ghost" size="icon" onClick={onToggleFullscreen} title="Toggle fullscreen">
            {fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </Button>
          <Button variant="ghost" size="icon" onClick={onClose} title="Close panel" aria-label="Close artifact panel">
            <X size={16} />
          </Button>
        </div>
      </div>

      <div className="flex items-center justify-between border-b border-border px-3 py-2">
        <div className="inline-flex rounded-lg border border-border bg-canvas p-0.5">
          {(["preview", "code"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                tab === t ? "bg-surface shadow-sm text-ink" : "text-ink-faint hover:text-ink"
              )}
            >
              {t === "preview" ? <Eye size={12} /> : <Code2 size={12} />}
              {t === "preview" ? "Preview" : "Code"}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1">
          {onRegenerate && (
            <Button variant="ghost" size="icon" onClick={onRegenerate} title="Regenerate" disabled={loading}>
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            </Button>
          )}
          <Button variant="ghost" size="icon" onClick={copy} title="Copy" disabled={!artifact}>
            {copied ? <Check size={14} /> : <Copy size={14} />}
          </Button>
          <Button variant="ghost" size="icon" onClick={download} title="Download" disabled={!artifact}>
            <Download size={14} />
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        {loading && (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-ink-faint">
            <Loader2 size={20} className="animate-spin" />
            <p className="text-sm">Generating artifact...</p>
          </div>
        )}

        {!loading && error && (
          <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center">
            <AlertTriangle size={20} className="text-danger" />
            <p className="text-sm text-danger">{error}</p>
            {onRegenerate && (
              <Button variant="secondary" size="sm" onClick={onRegenerate}>
                Try again
              </Button>
            )}
          </div>
        )}

        {!loading && !error && !artifact && (
          <div className="flex h-full items-center justify-center px-6 text-center text-sm text-ink-faint">
            No artifact selected yet.
          </div>
        )}

        {!loading && !error && artifact && tab === "preview" && artifact.type === "markdown" && (
          <div className="markdown-body prose prose-sm max-w-none p-5 dark:prose-invert">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{artifact.content}</ReactMarkdown>
          </div>
        )}

        {!loading && !error && artifact && tab === "preview" && artifact.type === "html" && (
          <iframe
            title={artifact.title}
            srcDoc={srcDoc}
            sandbox="allow-same-origin"
            className="h-full w-full bg-white"
          />
        )}

        {!loading && !error && artifact && tab === "code" && (
          <pre className="h-full overflow-auto p-4 text-xs leading-relaxed text-ink">
            <code>{artifact.content}</code>
          </pre>
        )}
      </div>
    </div>
  );
}
