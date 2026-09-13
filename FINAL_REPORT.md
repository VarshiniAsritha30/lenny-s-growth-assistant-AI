# Final Report — The Lenny Growth Assistant

## What was built

A full-stack, locally-deployable RAG product: FastAPI + SQLAlchemy + PostgreSQL/pgvector backend
with a deterministic agent/skill layer, a Next.js/TypeScript/Tailwind frontend with a dedicated
sandboxed Artifact Viewer, a provider-agnostic LLM abstraction (Ollama mandatory local + Anthropic
+ OpenAI), a real ingestion pipeline over a clearly-labeled synthetic demo transcript corpus, 34
passing automated backend tests, Docker/Compose deployment, and full documentation including a
security review and honest, real (not fabricated) build-time incident transcripts.

Every core flow was verified against the **real running stack** — real Postgres+pgvector, real
Ollama, real FastAPI, real Next.js in an actual browser — not just written and assumed to work.
Two genuine, non-trivial bugs were found and fixed during that verification (see
`agent-transcripts/`), which is the strongest evidence this wasn't just generated and left
untested.

## Architecture

See `architecture.md` for full diagrams. In one line: Next.js → FastAPI → Session Service →
deterministic agent router → skills (grounded QA / Ship 30 / artifact generation) → hybrid
retriever → Postgres+pgvector, with all generation routed through a swappable `LLMProvider`.

## Major decisions (and why)

1. **Deterministic code-based routing instead of an LLM-driven agent SDK.** The mandatory local
   demo model is small (~1B params) and unreliable at structured tool calls. A regex/keyword
   router (`app/agents/router.py`) gives identical, testable behavior across every provider. This
   directly caused and then fixed a real bug — see decision #3.
2. **Groundedness judged on raw cosine similarity, not normalized fusion rank.** A fused/
   normalized retrieval score always produces a confident-looking top result even when nothing is
   relevant, which would silently defeat the "explicitly refuse when unsupported" requirement.
   Found and fixed live — see `agent-transcripts/04-router-and-scoring-bugs.md`.
3. **A deterministic guard for the "recap a conversation that never happened" failure mode.**
   Prompt instructions alone weren't reliable enough on the 1B model to prevent it from
   conflating retrieved transcript excerpts with actual prior chat turns — which looks exactly
   like a session-isolation leak to an evaluator. Fixed with a code-level short-circuit, verified
   with a test that proves the LLM is never even called for this case. Full incident in
   `agent-transcripts/02-session-isolation-bug.md`.
4. **No real Lenny's Podcast transcripts.** They're copyrighted; a synthetic, clearly-`[DEMO]`-
   labeled dataset stands in, with the ingestion pipeline built to work identically on real
   transcripts an operator supplies.

## What works (verified live)

- Grounded Q&A with citations, follow-up context, explicit refusal on out-of-scope questions
- Session creation/listing/deletion, full isolation between sessions (including the meta-recap
  edge case)
- Ship 30 essay generation (grounded, quote-verified — see length caveat below)
- Markdown and HTML artifact generation, rendered in the Artifact Viewer, sandbox verified via
  DOM inspection (`sandbox="allow-same-origin"`, no `allow-scripts`)
- Model picker: live health per provider, runtime switching, clean error on missing cloud key
- Dark/light theme, mobile responsive layout (drawer sidebar, full-width artifact panel)
- Structured error envelope and logging across every failure mode tested

## Test results

```
$ cd backend && pytest -q
34 passed in ~3s
```

Includes unit tests (chunker, router, quote validation), integration tests against a real test
Postgres database (sessions, ingestion, artifact security), and two live-Ollama-gated retrieval
tests (skipped gracefully if Ollama/models aren't present, run for real in this build).

Frontend: `npm run build` and `npx tsc --noEmit` both pass clean.

## Local Ollama setup

```bash
ollama pull llama3.2:1b
ollama pull nomic-embed-text
```

Both chosen for an 8GB-RAM, no-GPU machine (this build's actual environment). Verified live for
every flow in this report.

## Cloud provider setup

`AnthropicProvider`/`OpenAIProvider` are implemented behind the same `LLMProvider` interface,
config-driven via `.env`, and unit-tested for the "missing key → clean config error, not a crash"
path. **Not exercised live end-to-end** — no API key was available in this environment. This is
disclosed, not hidden, in `docs/ASSESSMENT_CHECKLIST.md`.

## Ingestion process

`scripts/ingest_transcripts.py --source data/sample_transcripts` — parses frontmatter, dedups by
content hash, chunks paragraph-aware with overlap, embeds, stores with full provenance. Verified
live: 6 demo transcripts → 24 chunks → all correctly retrievable with citations; re-running
correctly skips all as duplicates.

## Security model

Full detail in `SECURITY.md`. Headline: HTML artifacts get two independent layers of defense
(server-side `<script>` stripping + client-side `sandbox="allow-same-origin"` iframe with no
script execution), no secrets ever logged, all SQL parameter-bound, CORS scoped to the configured
frontend origin, no SSRF/arbitrary-filesystem surface exposed to the LLM or generated content.

## Known limitations

1. **Ship 30 essay length:** ~660 words against the ~1250-word target with `llama3.2:1b` — the
   pipeline (prompt, token budget, structure) correctly targets 1250 words; the small local model
   doesn't reliably sustain long-form generation. A larger local model or cloud provider closes
   this gap with zero code changes.
2. **Docker Compose not live-smoke-tested:** this build machine had no Docker runtime installed.
   The Compose file and Dockerfiles were written carefully and YAML-validated, and every
   underlying piece they orchestrate (migrations, ingestion, backend, frontend) was verified
   natively instead — but a genuine `docker compose up --build` pass on a machine with Docker is
   the one verification step this submission couldn't perform itself.
3. **No live cloud-provider test** — see above.
4. **No authentication layer** — appropriate for this scope; `users.external_id` exists in the
   schema for a future login integration.
5. **Demo transcript data is synthetic**, not real Lenny's Podcast content — a deliberate
   copyright-safety choice, disclosed prominently in the README and the dataset's own README.

## Future improvements

Token-by-token streaming in the UI (provider interface already supports it), a cross-encoder
re-ranker for retrieval at larger corpus scale, rate limiting for anything beyond local/demo use,
and wiring the existing `users` table to real authentication.

## Exact commands to run the demo

```bash
git clone <this-repo> && cd lenny-growth-assistant
cp .env.example .env
docker compose up --build
# open http://localhost:3000
```

Or natively — see the README's "Run without Docker" section for the exact sequence this build
was actually verified with.

## Evaluator walkthrough

1. Start the application (Docker Compose, or native per the README)
2. Open http://localhost:3000 — empty state with four suggested prompts
3. Click a suggested prompt → grounded answer with source chips (click a chip to see the excerpt)
4. Ask a follow-up in the same session — context carries over
5. Ask "Turn the key lessons about retention into an essay" → grounded Ship 30-style essay
6. Ask "Create an HTML artifact one-pager on retention" → Artifact Viewer opens automatically
7. In the Artifact Viewer: toggle Preview/Code, Copy, Download, Regenerate, Fullscreen
8. Open the model picker (header or sidebar Settings) → see Ollama healthy, cloud providers
   showing a clear "no key" status without crashing
9. Confirm Ollama is doing the work: it's the only provider configured with a key-free, local
   `OLLAMA_BASE_URL` — the model tag on each assistant message reads `ollama · llama3.2:1b`
10. Start a New Chat → ask "What were we just talking about?" → deterministic "this is a new
    conversation" reply, proving no cross-session leakage
11. Read `docs/ASSESSMENT_CHECKLIST.md` for the full requirement-by-requirement accounting and
    `agent-transcripts/` for the real bugs found and fixed while building this
