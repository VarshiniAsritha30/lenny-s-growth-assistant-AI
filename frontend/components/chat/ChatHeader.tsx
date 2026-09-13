"use client";

import { PanelRight, Menu } from "lucide-react";
import { ModelPicker } from "@/components/ModelPicker";
import { Button } from "@/components/ui/Button";

interface Props {
  title: string;
  onOpenSidebar: () => void;
  onToggleArtifactPanel: () => void;
  artifactPanelAvailable: boolean;
}

export function ChatHeader({ title, onOpenSidebar, onToggleArtifactPanel, artifactPanelAvailable }: Props) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface px-4">
      <div className="flex min-w-0 items-center gap-2">
        <button onClick={onOpenSidebar} className="lg:hidden p-1.5 text-ink-muted" aria-label="Open sidebar">
          <Menu size={18} />
        </button>
        <h2 className="truncate text-sm font-medium text-ink">{title}</h2>
      </div>
      <div className="flex items-center gap-2">
        <div className="hidden sm:block">
          <ModelPicker compact />
        </div>
        {artifactPanelAvailable && (
          <Button variant="secondary" size="icon" onClick={onToggleArtifactPanel} title="Toggle artifact panel">
            <PanelRight size={16} />
          </Button>
        )}
      </div>
    </header>
  );
}
