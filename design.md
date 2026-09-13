# Design — The Lenny Growth Assistant

## Principles

Clean, modern, minimal, information-dense without clutter, responsive, accessible,
keyboard-friendly, fast, with clear loading/error states and obvious provenance for every
grounded claim. Explicitly avoided: generic AI-chatbot tropes (giant gradients, excessive rounded
cards/animations, neon accents), and rendering untrusted content unsandboxed.

## Layout

```
┌─────────────┬──────────────────────────────┬─────────────────────┐
│  SIDEBAR    │  CHAT                        │  ARTIFACT PANEL     │
│  New chat   │  Header: title · model · ⛶   │  (opens on demand)  │
│  Search     │  ─────────────────────────   │  Preview | Code     │
│  Recent...  │  Messages (markdown, source  │  Copy / Download /  │
│  ─────────  │  chips, copy/feedback)       │  Regenerate / ⛶     │
│  Settings   │  Composer                    │                     │
│  (model,    │                              │                     │
│   theme)    │                              │                     │
└─────────────┴──────────────────────────────┴─────────────────────┘
```

On narrow viewports (< lg breakpoint), the sidebar collapses into a hamburger-triggered drawer and
the artifact panel becomes full-width when opened, verified at 375×812 in-browser during this
build.

## Component inventory (as built)

- `components/sidebar/Sidebar.tsx` - new chat, live search-filtered conversation list with
  relative timestamps, hover-to-delete, and a Settings section housing the model picker + theme
  toggle.
- `components/ModelPicker.tsx` - compact (header) and full (sidebar) variants of one component;
  polls `GET /api/models` every 15s, shows a health dot per provider, switches via
  `POST /api/models/select`.
- `components/chat/EmptyState.tsx` - the four suggested prompts specified in the brief.
- `components/chat/MessageBubble.tsx` - Markdown rendering (`react-markdown` + `remark-gfm`),
  inline "Open artifact" affordance when a message produced one, per-message copy/thumbs-up/down,
  provider/model tag revealed on hover.
- `components/chat/SourceChips.tsx` - click-to-expand source cards showing episode, guest,
  excerpt, relevance %, and an external link when a real URL exists.
- `components/chat/Composer.tsx` - auto-growing textarea, Enter to send / Shift+Enter for a
  newline, disabled state while a response is in flight.
- `components/artifact/ArtifactPanel.tsx` - Preview/Code tabs, copy, download (Blob-based, real
  file save - this is a standalone web app the user runs locally, not a sandboxed artifact host),
  regenerate, fullscreen toggle, and distinct loading/error/empty states.

## Visual system

- Tokens are CSS custom properties (`--canvas`, `--surface`, `--surface-raised`, `--border`,
  `--ink`, `--ink-muted`, `--ink-faint`, `--accent`, `--accent-ink`, `--danger`) defined once for
  light and once under `.dark`, consumed via Tailwind's `rgb(var(--x) / <alpha-value>)` pattern so
  every utility (`bg-surface`, `text-ink-muted`, `border-border`, opacity modifiers) stays
  themeable from one source of truth.
- Dark mode is a manual `.dark` class toggle (persisted to `localStorage`) seeded by
  `prefers-color-scheme` on first load via a blocking inline script in `app/layout.tsx`, avoiding
  a flash of the wrong theme.
- Typography: system font stack (no webfont fetch - keeps the app fully functional offline once
  loaded, matching the "local-first" spirit of the mandatory Ollama path).
- Motion is deliberately small: a 150-200ms fade/slide on new messages and panel open, a
  three-dot pulse for the typing indicator - no page-level transitions, no skeleton
  over-animation.

## Empty & loading states

- Chat empty state: icon, one-sentence description, four suggested prompts (as specified).
- Artifact panel: distinct `loading` (spinner + "Generating artifact..."), `error` (with a
  "Try again" retry action wired to the same generation call), and `no artifact selected` states.
- Sidebar empty state distinguishes "no conversations yet" from "no search matches".

## Accessibility

- All icon-only buttons carry `aria-label`/`title`.
- Focus rings via `focus-visible:ring-2 ring-accent/50` on interactive elements.
- Color contrast: ink/canvas pairs verified visually in both themes during in-browser testing
  (screenshots in `agent-transcripts/`); accent color chosen for sufficient contrast against both
  `--accent-ink` values.
- Keyboard: Enter sends, Shift+Enter inserts a newline, Escape-equivalent close (×) buttons on
  every panel/drawer.

## What was verified in-browser (not just designed on paper)

Using the in-app browser against the real running stack (real Postgres+pgvector, real Ollama,
real FastAPI): empty state → suggested prompt → grounded answer with citations, HTML artifact
generation → Artifact Viewer auto-open → Preview tab (styled render) → Code tab (raw HTML) →
sandbox attribute confirmed as exactly `allow-same-origin` via a DOM check, dark/light theme
toggle, new-chat session isolation (including the meta-recap edge case), and the mobile drawer at
a 375px viewport. Two real bugs were found and fixed during this pass - see
`agent-transcripts/`.
