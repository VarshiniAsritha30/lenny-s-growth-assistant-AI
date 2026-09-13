# The Lenny Growth Assistant

A grounded, cited, conversational assistant over a Lenny's Podcast-style transcript knowledge
base — with essay generation, Markdown/HTML artifacts, a sandboxed Artifact Viewer, and a
provider-agnostic LLM layer that runs entirely locally (Ollama) or against a cloud model
(Anthropic/OpenAI), switchable at runtime with no code change.

## Overview

Ask a product/growth question → get an answer grounded in retrieved transcript excerpts, with
sources cited. Ask a follow-up → context carries over within the session. Ask for an essay →
get a grounded, Ship 30-style Markdown essay. Ask for an artifact → get a Markdown or HTML
document rendered live in a dedicated, sandboxed viewer. If the knowledge base doesn't support a
question, the assistant says so explicitly instead of guessing.

**This build ships with a synthetic demo transcript dataset** (`data/sample_transcripts/`), not
real Lenny's Podcast transcripts — see that directory's README for why and how to point the
pipeline at real transcripts you have legitimate access to.

## Product demo

The full flow below was executed against the real running stack during development — see
`docs/MANUAL_TEST_PLAN.md` for the complete pass/fail table and `agent-transcripts/` for the real
bugs found and fixed along the way.

1. Empty state with suggested prompts → click one → grounded answer with source chips
2. Follow-up question → context carries over
3. "Create an HTML artifact one-pager on retention" → Artifact Viewer opens automatically,
   rendered inside a sandboxed iframe
4. "Turn the key lessons about retention into an essay" → grounded Ship 30-style essay
5. Model picker → shows Ollama healthy, Anthropic/OpenAI unhealthy (no key) → switch providers
   live
6. New chat → previous session's content never leaks in

## Architecture

See [`architecture.md`](architecture.md) for the full system diagram, database schema, RAG
pipeline, agent routing, provider abstraction, artifact sandboxing, and failure-handling table.
See [`PRD.md`](PRD.md) for product scope/success metrics and [`design.md`](design.md) for the
UI/UX system.

```
Frontend (Next.js) → FastAPI → Session Service → Agent Orchestrator → Skills → Retriever
                                                                              ↓
                                                            PostgreSQL + pgvector ← LLM Provider
```

## Features

- Grounded Q&A with per-answer source citations (episode, guest, excerpt, relevance score)
- Explicit refusal when the knowledge base doesn't support a question — never a fabricated answer
- Persistent, isolated chat sessions (PostgreSQL-backed)
- Follow-up-aware retrieval (folds prior turn into the retrieval query)
- Ship 30-style essay generation with a post-hoc quote-verification pass
- Markdown + HTML artifact generation, rendered in a dedicated Artifact Viewer
  (Preview/Code tabs, copy, download, regenerate, fullscreen)
- HTML artifacts sandboxed via `<iframe sandbox="allow-same-origin">` — no script execution
- Provider-agnostic LLM layer: Ollama (mandatory local), Anthropic, OpenAI — runtime-switchable
- Structured error envelope, structured JSON logging, health/readiness endpoints
- Dark/light theme, responsive down to mobile, keyboard-friendly composer

## Tech stack

**Backend:** Python, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic, PostgreSQL + pgvector,
structlog, pytest. **Frontend:** Next.js 15 (App Router), TypeScript, Tailwind CSS,
react-markdown. **Infra:** Docker, Docker Compose.

## Prerequisites

- Docker + Docker Compose (recommended path), **or** Node 20+, Python 3.12+, and a local
  PostgreSQL with the `pgvector` extension available (native path — see below)
- [Ollama](https://ollama.com) installed if you want the local model running outside Docker too
  (Docker Compose pulls its own Ollama container and models automatically)
- ~4GB free disk for the default Ollama models (`llama3.2:1b` + `nomic-embed-text`)

## Quick start (Docker — recommended)

```bash
git clone <this-repo>
cd lenny-growth-assistant
cp .env.example .env
docker compose up --build
```

This starts Postgres+pgvector, Ollama (auto-pulling `llama3.2:1b` and `nomic-embed-text` via the
one-shot `ollama-init` service), the FastAPI backend (running migrations on startup), an
`ingest` one-shot service that loads the demo transcripts, and the Next.js frontend. Open
**http://localhost:3000**.

> **Note on this repository's own verification:** this specific build machine did not have
> Docker installed, so the Compose file was written carefully and validated for YAML/structural
> correctness, but a live `docker compose up` was not smoke-tested end-to-end here. Every other
> piece (schema, ingestion, retrieval, agent, API, frontend) was verified against a real,
> natively-run Postgres+pgvector and Ollama instead — see `docs/IMPLEMENTATION_PLAN.md` and
> `FINAL_REPORT.md` for the honest accounting of what was and wasn't verified where.

To re-run ingestion later (e.g. after adding real transcripts to `data/`):

```bash
docker compose run --rm ingest
```

## Run without Docker (native — how this build was actually verified)

```bash
# 1. Postgres + pgvector (Homebrew example; use your own Postgres + pgvector install otherwise)
brew install postgresql@17 pgvector
# create/start a Postgres 17 instance, then:
createdb lenny_growth_assistant
psql -d lenny_growth_assistant -c "CREATE EXTENSION vector;"

# 2. Backend
cd backend
cp .env.example .env   # adjust DATABASE_URL if your Postgres isn't on 127.0.0.1:5544
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3. Ollama (separate terminal)
ollama pull llama3.2:1b
ollama pull nomic-embed-text
# ollama serve runs automatically as a background daemon on most installs

# 4. Ingest the demo dataset (separate terminal, from repo root)
python3 scripts/ingest_transcripts.py --source data/sample_transcripts

# 5. Frontend (separate terminal)
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open **http://localhost:3000**.

### macOS Postgres troubleshooting

If `pg_ctl start` fails with `postmaster became multithreaded during startup`, set
`LC_ALL=en_US.UTF-8` before starting Postgres — a known interaction on recent macOS builds. See
`agent-transcripts/01-environment-setup.md` for the full story.

## Environment variables

See [`.env.example`](.env.example) (Docker) and [`backend/.env.example`](backend/.env.example)
(native) for the complete, commented list. Key ones:

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | `ollama` (default) \| `anthropic` \| `openai` — also switchable at runtime via the UI |
| `EMBEDDING_PROVIDER` | `ollama` (default) \| `openai` |
| `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_EMBEDDING_MODEL` | Local model config — no key required |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | Optional cloud provider |
| `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_EMBEDDING_MODEL` | Optional cloud provider |
| `RETRIEVAL_MIN_SCORE` | Groundedness threshold — calibrated for `nomic-embed-text` against the demo corpus; re-calibrate if you change either |
| `NEXT_PUBLIC_API_URL` | Frontend → backend base URL |

**No cloud API key is required to run the app.** Leaving both cloud keys blank and
`LLM_PROVIDER=ollama` is the fully-functional default.

## Ollama setup

```bash
ollama pull llama3.2:1b        # chat model, ~1.3GB
ollama pull nomic-embed-text   # embedding model, ~274MB
```

Both were chosen to run comfortably on an 8GB-RAM machine with no discrete GPU — the machine this
was built and verified on. A larger local model is a zero-code-change swap (`OLLAMA_MODEL`), but
don't assume "bigger automatically means better grounded" — see the Known Limitations note below,
which documents a real, tested case where `llama3.2:3b` performed *worse* on grounding for this
task. A cloud provider (Anthropic/OpenAI) is the more reliable way to improve quality.

## Cloud LLM setup

Set `LLM_PROVIDER=anthropic` (or `openai`) and the matching `*_API_KEY` in `.env`, or leave
`LLM_PROVIDER=ollama` and switch live from the UI's model picker once a key is present. A missing
key surfaces as a clear `PROVIDER_CONFIG_ERROR`, not a crash.

## Database

Schema is managed entirely by Alembic — never create tables by hand. See `architecture.md` for
the ER diagram. To reset:

```bash
cd backend && alembic downgrade base && alembic upgrade head
```

## Transcript ingestion

```bash
python3 scripts/ingest_transcripts.py --source data/sample_transcripts
```

Idempotent — re-running skips files whose content hash is already ingested. See
`data/sample_transcripts/README.md` for the demo-data disclosure and instructions for pointing
this at real transcripts you have legitimate access to.

## Running tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```

34 tests, all passing in this build. Most are fully offline (fake LLM/embedding providers via
dependency injection); a handful of retrieval-quality and resilience tests use a live Postgres
and are gated (`@requires_ollama`) to skip cleanly if Ollama isn't running with the expected
models pulled — they run for real, against real embeddings, in this build's own verification.

Frontend:

```bash
cd frontend
npm run build   # production build + type check
npx tsc --noEmit
```

## API

See `architecture.md` for the full contract table. Summary:

`GET /health`, `GET /health/ready`, `POST|GET /api/sessions`, `GET /api/sessions/{id}`,
`DELETE /api/sessions/{id}`, `GET|POST /api/sessions/{id}/messages`,
`GET /api/sessions/{id}/artifacts`, `POST /api/skills/ship30`, `POST /api/artifacts`,
`GET /api/artifacts/{id}`, `GET /api/models`, `POST /api/models/select`, `POST /api/feedback`.

Errors follow one envelope everywhere:

```json
{"error": {"code": "MODEL_UNAVAILABLE", "message": "...", "request_id": "...", "details": {}}}
```

## Artifact security

Generated HTML is sanitized server-side (`<script>` tags stripped) and rendered client-side
inside `<iframe sandbox="allow-same-origin">` with **no** `allow-scripts` — verified live during
this build via a DOM check on the running app. Full writeup in [`SECURITY.md`](SECURITY.md).

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| "Local model unavailable" error | Ollama isn't running, or the configured model isn't pulled — the error message names the exact `ollama pull <model>` to run |
| "ANTHROPIC_API_KEY is not set" when selecting Anthropic | Expected — add the key to `.env` or stay on `ollama` |
| Assistant always refuses / no sources found | Run the ingestion script; check `RETRIEVAL_MIN_SCORE` isn't set too high for your embedding model |
| Postgres won't start on macOS (`postmaster became multithreaded`) | `export LC_ALL=en_US.UTF-8` before starting it — see `agent-transcripts/01-environment-setup.md` |
| `pgvector` extension missing | Ensure `pgvector` was installed against the *same* Postgres major version you're running — see the same transcript for the exact failure mode this build hit |

## Observability

Structured JSON logs with `request_id`, `session_id`, `operation`, `provider`, `model`,
`latency_ms`, `status`. Named events documented in `architecture.md`. Every response carries an
`x-request-id` header, echoed into any error body for support/debugging correlation.

## Project structure

```
backend/app/{api,agents,db,models,providers,retrieval,services,schemas,core}
frontend/{app,components,lib,types}
scripts/ingest_transcripts.py
data/sample_transcripts/          (synthetic demo dataset — see its own README)
docs/{IMPLEMENTATION_PLAN,MANUAL_TEST_PLAN,ASSESSMENT_CHECKLIST}.md
agent-transcripts/                (real build-time failures & fixes)
PRD.md · architecture.md · design.md · SECURITY.md · FINAL_REPORT.md
```

## Design decisions

The most consequential ones, with the reasoning, live in `architecture.md`:
deterministic code-based intent routing instead of LLM-driven tool calling (small local models
aren't reliable at structured tool calls), pgvector instead of a separate vector database
(avoids a second moving part), and groundedness judged on raw cosine similarity rather than a
normalized fused rank (a normalized score always looks "confident" even when nothing is relevant
— this was a real bug found and fixed during this build, see `agent-transcripts/`).

## Known limitations

- **Ship 30 essay length with the default local model:** `llama3.2:1b` produced a ~660-word essay
  against the ~1250-word target in this build's testing — small local models don't reliably
  sustain long-form coherent generation. The prompt, token budget, and pipeline all correctly
  target 1250 words. **Tested and confirmed the fix isn't "just use a bigger local model":**
  `llama3.2:3b` was pulled and tested on the same prompt and produced an even shorter essay (612
  words) *and* hallucinated unsourced company names ("Facebook and Airbnb") in unquoted prose —
  the post-hoc quote-verification pass only checks quoted spans, so it didn't catch this. A cloud
  provider (Anthropic/OpenAI) is the more reliable path to both length and grounding quality
  here, not a larger local model of the same family. See `docs/MANUAL_TEST_PLAN.md` test case 8
  and `agent-transcripts/05-larger-local-model-does-not-help.md`.
- **Docker Compose was not live-smoke-tested** on the build machine (no Docker runtime available)
  — written carefully and YAML-validated, but flagged here rather than claimed as verified.
- **No live cloud-provider test** — no Anthropic/OpenAI API key was available in this
  environment; those providers are unit-tested with the HTTP layer mocked, not exercised live.
- **No authentication** — single-tenant local app by design at this scope; see `SECURITY.md`.
- **Real transcripts not included** — the shipped dataset is original synthetic content, clearly
  labeled `[DEMO]`, standing in for real Lenny's Podcast transcripts (copyright — see
  `SECURITY.md` and `data/sample_transcripts/README.md`).

## Future improvements

Token-by-token streaming in the chat UI (the provider interface already supports it via
`LLMProvider.stream`, just not wired into the frontend yet), a cross-encoder re-ranker for
retrieval at larger corpus scale, rate limiting if deployed beyond local/demo use, and an auth
layer using the `users` table that already exists in the schema but isn't wired to a login flow.
