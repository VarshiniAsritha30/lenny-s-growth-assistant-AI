import { Sparkles } from "lucide-react";

const SUGGESTIONS = [
  "How should I improve product activation?",
  "What does Lenny's Podcast say about product-market fit?",
  "How do great growth teams prioritize experiments?",
  "Turn the key lessons about retention into an essay",
];

export function EmptyState({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center px-6 text-center">
      <div className="h-11 w-11 rounded-xl bg-accent/10 flex items-center justify-center mb-4">
        <Sparkles size={20} className="text-accent" />
      </div>
      <h1 className="text-lg font-semibold text-ink">Lenny Growth Assistant</h1>
      <p className="mt-1.5 max-w-md text-sm text-ink-muted">
        Ask about product strategy, growth, retention, hiring, experimentation, or startup
        lessons — grounded in the ingested transcript knowledge base, with sources cited.
      </p>
      <div className="mt-6 grid w-full max-w-lg grid-cols-1 gap-2 sm:grid-cols-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            className="rounded-lg border border-border bg-surface px-3.5 py-2.5 text-left text-sm text-ink-muted hover:border-accent/40 hover:text-ink hover:bg-surface-raised transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
