# PRD — The Lenny Growth Assistant

## User

**Primary user:** product managers, growth managers, founders, product leaders, and internal
strategy teams who want fast, evidence-backed answers to product/growth questions, plus
reusable written artifacts (essays, one-pagers) built from that evidence.

## Problem

Lenny's Podcast is a deep, high-quality source of product/growth knowledge, but it's locked in
hours of audio/transcript across hundreds of episodes. Extracting a specific, actionable answer
today means remembering which episode covered it, searching manually, and re-reading around the
relevant section. The assistant should collapse that into a single question, answered with
evidence attached.

It should reduce: research time, context switching between episodes, repetitive transcript
searching, prompt engineering to get useful output from a raw LLM, and manual drafting of
follow-up content (essays, one-pagers).

## Jobs to be done

- "When I face a product/growth problem, I want to ask a natural-language question and get a
  grounded answer with evidence, so I don't have to guess whether the advice is real."
- "When I get a useful answer, I want to ask a follow-up without repeating context."
- "When I find useful advice, I want to turn it into a reusable essay or one-pager without
  starting a blank document."
- "When I request an artifact, I want to see the rendered result immediately, not raw
  Markdown/HTML I have to mentally render."
- "When the knowledge base doesn't cover something, I want to be told plainly, not given a
  confident-sounding guess."

## Success metrics

| Metric | Target | Notes |
|---|---|---|
| Grounded-answer citation coverage | ≥ 95% of non-refused answers carry ≥1 source | Enforced structurally: `grounded_qa` only calls the LLM when retrieval returns ≥1 supported chunk |
| Successful response rate (excl. model unavailable) | ≥ 99% | Verified via error-envelope tests; genuine dependency outages surface as `MODEL_UNAVAILABLE`/`DATABASE_UNAVAILABLE`, not crashes |
| Artifact rendering success rate | ≥ 99% | HTML sanitized + doctype-wrapped server-side; Markdown fenced-code stripped |
| Fresh evaluator setup success rate | 100% via `docker compose up --build` | Verified natively on this dev machine (no Docker runtime available here - see Known Limitations) |
| Median local (Ollama) response latency | Best-effort, model-dependent | `llama3.2:1b` observed 1-5s per grounded answer on an 8GB M-series-class machine in this build |
| Retrieval relevance | On-topic queries score ≥0.55 raw cosine similarity; off-topic queries return 0 supported chunks | Calibrated and verified against `nomic-embed-text` + the demo corpus - see `retrieval_min_score` comment in `backend/app/core/config.py` |

## Assumptions

- Real Lenny's Podcast transcripts are not available/licensed for redistribution in this
  environment, so a clearly-labeled synthetic demo dataset stands in for them (see
  `data/sample_transcripts/README.md`). The ingestion pipeline is fully generic and works
  identically against real transcripts supplied locally.
- The mandatory local demo runs on modest hardware (this build: 8GB RAM, no discrete GPU), so a
  small (~1B-parameter) local model is the realistic default; answer quality scales up
  meaningfully with a larger local model or a cloud provider.
- One user per session/browser for this build - no authentication layer. `users.external_id`
  exists in the schema for a future auth integration but isn't wired to a login flow.

## Scope

**MVP / Required** (all implemented in this build):
- Grounded Q&A over ingested transcripts with citations and explicit refusal when unsupported.
- Independent, persisted chat sessions with follow-up context.
- Ollama (mandatory) + Anthropic + OpenAI providers behind one interface, runtime-switchable.
- Ship 30-style essay generation, grounded, ~1250-word target.
- Markdown and HTML artifact generation with a dedicated, sandboxed Artifact Viewer.
- Structured errors, logging, and graceful degradation when a dependency is down.
- Automated backend test suite; Docker Compose deployment.

**Nice-to-have** (partially or lightly implemented):
- Streaming responses - the provider interface supports streaming (`LLMProvider.stream`), but
  the chat UI currently renders complete responses rather than token-by-token, to keep the
  request/response/error-envelope model simple for this scope.
- Hybrid hybrid retrieval re-ranking beyond RRF + a cosine floor - would benefit from a
  cross-encoder re-ranker at larger corpus scale.

**Explicitly excluded:**
- Multi-tenant auth/accounts, billing, or team permissions.
- Automated transcript scraping from lennyspodcast.com (copyright - see `SECURITY.md`).
- A vector database beyond pgvector (Postgres already needed for relational data; a second
  system would add operational surface without a concrete benefit at this scale).

## Risks

| Risk | Mitigation |
|---|---|
| Hallucination / fabricated quotes | System prompts forbid it; Ship 30 skill runs a post-hoc quote-verification pass that de-quotes any unverified quotation (`validate_and_repair_quotes`). **Known gap, found by testing:** this check only covers quoted spans — a live test with `llama3.2:3b` produced an unsourced fabricated company name in *unquoted* prose that the current validator doesn't catch. See `agent-transcripts/05-larger-local-model-does-not-help.md` |
| Retrieval failure / irrelevant retrieval | Hybrid (vector + full-text) retrieval with an absolute cosine-similarity floor, not just relative ranking - see `retriever.py` |
| Small local model unreliable at subtle instructions | A specific, demoable failure (conflating retrieved excerpts with "prior conversation" on a fresh session) is guarded deterministically in code rather than left to prompting alone - see `grounded_qa.py`'s meta-recap guard |
| Local model quality / latency | Documented known limitation; architecture is provider-agnostic so a larger model is a config change |
| API cost (cloud providers) | Cloud providers are opt-in via `LLM_PROVIDER`; never called unless explicitly selected and keyed |
| Database / Ollama unavailable | Structured `DATABASE_UNAVAILABLE` / `MODEL_UNAVAILABLE` errors, never a raw 500 or crash |
| Prompt injection via retrieved transcript content | Transcript content is treated as data inside the prompt, never as instructions; the system prompt explicitly scopes the model to answering from it, not obeying it |
| HTML/JS artifact security | Server strips `<script>` tags; client renders HTML artifacts in a `sandbox="allow-same-origin"` iframe with no `allow-scripts` - see `SECURITY.md` |
| Transcript copyright | No real transcripts bundled or scraped; demo dataset is original synthetic content, clearly labeled |
| Data leakage across sessions | Sessions are isolated by `session_id` at the query layer; verified by an automated regression test (`test_new_session_never_sees_another_sessions_messages`) |

## User flows

1. **New conversation** - sidebar "New chat" clears the active view; a session row is created
   lazily on the first message (no empty sessions clutter the list).
2. **Ask question** - composer → optimistic user bubble → `POST /messages` → grounded answer with
   source chips.
3. **Follow-up question** - prior turns in the same session are included in the LLM context;
   retrieval folds in the previous user turn so pronoun-heavy follow-ups ("what about X?") still
   retrieve well.
4. **Source inspection** - clicking a source chip expands the exact excerpt, episode, guest, and
   relevance score inline.
5. **Generate essay** - "turn this into an essay" (or `/api/skills/ship30`) routes to the Ship 30
   skill, producing a grounded Markdown artifact.
6. **Generate artifact** - "create a markdown/HTML one-pager..." routes to artifact generation;
   the Artifact Viewer opens automatically.
7. **View artifact** - Preview/Code tabs, copy, download, regenerate, fullscreen.
8. **Switch model** - the model picker (header + sidebar settings) lists every configured
   provider's live health and lets the user switch with no restart.
9. **Error/recovery** - a missing model, unreachable Ollama, or missing cloud API key surfaces a
   specific, actionable message instead of a stack trace or silent failure.

## Acceptance criteria (selected)

- A question with no supporting transcript content returns the fixed refusal message and zero
  fabricated sources, verified by `test_off_topic_query_returns_no_supported_chunks` and manual
  testing.
- A new session's first message never references content from any other session, verified by
  `test_new_session_never_sees_another_sessions_messages` and the meta-recap guard test.
- Generated HTML artifacts never execute script content when rendered, verified by
  `test_html_artifact_strips_script_tags` and the iframe `sandbox="allow-same-origin"` attribute
  (no `allow-scripts`).
- Switching `LLM_PROVIDER` to `anthropic`/`openai` without an API key returns a structured
  `PROVIDER_CONFIG_ERROR`, not a crash, verified by `test_anthropic_provider_without_api_key_raises_config_error_not_crash`.
- `docker compose up --build` (with `.env` copied from `.env.example`) brings up Postgres+pgvector,
  Ollama (with models pre-pulled by `ollama-init`), the backend, and the frontend, with health
  checks gating startup order.

## Implementation plan

See `docs/IMPLEMENTATION_PLAN.md` for the phase-by-phase build log, environment constraints
encountered, and verification performed at each stage.
