# Security review — The Lenny Growth Assistant

This document covers what was checked, what protections exist, and what remains a known
limitation given this is a local-first take-home deliverable rather than a hosted multi-tenant
product.

## Secrets

- No secrets are committed. `.env` is gitignored; `.env.example` (root and `backend/`) contain
  only placeholder/blank values and a non-secret local dev Postgres password used purely for the
  disposable local database.
- API keys (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) are read once via `pydantic-settings` from the
  environment and never logged. `app/core/logging.py` documents this rule explicitly and no
  logging call anywhere in the codebase passes a key, token, or password value.
- Provider error messages are written to avoid echoing the key itself (e.g. "Anthropic API key
  was rejected", not the key or the raw HTTP body which could theoretically include it).

## CORS

`CORSMiddleware` is scoped to `CORS_ORIGINS` (default `http://localhost:3000`), not `*`. Update
this env var, not the code, when deploying the frontend to a different origin.

## SQL injection

All database access goes through SQLAlchemy's ORM or parameter-bound `text()` queries. The one
hand-written SQL (hybrid retrieval in `app/retrieval/retriever.py`) binds `:query_embedding`,
`:query`, and `:limit` as parameters - the query embedding vector is formatted into pgvector's
literal array syntax (`[0.123,...]`) as a bound *string parameter*, not interpolated into the SQL
text, so there is no injection surface even though the value is programmatically constructed.

## XSS / artifact rendering

This was the highest-risk surface in the spec and got two independent layers of defense:

1. **Server-side sanitization** (`app/agents/skills/artifact_generation.py`): any `<script>...
   </script>` block in a generated HTML artifact is stripped via regex before the artifact is
   persisted or returned. Markdown artifacts are never rendered as raw HTML - the frontend uses
   `react-markdown`, which does not execute embedded HTML/script by default and is used with no
   raw-HTML passthrough plugin enabled.
2. **Client-side sandboxing** (`components/artifact/ArtifactPanel.tsx`): HTML artifacts render
   inside `<iframe sandbox="allow-same-origin" srcDoc={content}>` - **no** `allow-scripts`, no
   `allow-top-navigation`, no `allow-popups`, no `allow-forms`. This was verified live: even if a
   `<script>` tag somehow survived server-side stripping, the sandbox attribute alone prevents it
   from executing, confirmed via a DOM check (`iframe.getAttribute('sandbox') ===
   "allow-same-origin"`) against the actual running app during this build.

Permitted: static rendering of HTML/CSS content, same-origin treatment for the iframe's own
internal resources (irrelevant here since content has no external references - artifacts are
instructed to be fully self-contained, no external stylesheets/fonts/images/scripts).
Blocked: script execution, top-level navigation, popups, form submission, and by extension any
attempt to read `document.cookie`, `localStorage`, or the parent page's DOM from inside the
artifact. Never allowed: application secrets or auth tokens are never passed into an artifact's
content or scope - there is no auth token in this build to begin with.

Remaining risk: a sufficiently creative HTML artifact could still misrepresent information
visually (e.g., fake UI chrome) - this is a content-trust problem inherent to LLM-generated
content, not something a sandbox can fully solve, and is mitigated by the artifact always
carrying visible `type`/title metadata identifying it as a generated artifact.

## Prompt injection

Retrieved transcript content is treated as *data* inside the system prompt (`Retrieved context:`
section), not as instructions - the system prompt is explicit that the model answers from the
excerpts but does not follow directives that might appear inside them. Since the shipped demo
dataset is original content authored for this project (not adversarial), this hasn't been
stress-tested against a deliberately injected transcript; the mitigation is architectural
(structural separation of "system instructions" vs "retrieved content" in the prompt) rather than
purely a matter of trusting the corpus.

## SSRF / arbitrary URL access

The application never fetches an arbitrary, user- or LLM-supplied URL server-side. The only
outbound HTTP calls are to the configured, operator-controlled `OLLAMA_BASE_URL` and the official
Anthropic/OpenAI SDKs' fixed endpoints. Source `url` fields stored on transcripts/chunks are
metadata only, rendered as a plain `<a>` link in the frontend (opened by the user's own click, in
a new tab, `rel="noreferrer"`) - the backend never dereferences them.

## Filesystem access

The ingestion script reads only files under an operator-specified directory
(`--source`, default `data/sample_transcripts`) - it is a deliberately offline, operator-run CLI
tool, not an API endpoint, so there is no remote path-traversal surface. The FastAPI app itself
performs no filesystem reads/writes outside of what SQLAlchemy/Alembic need.

## Dependency posture

`npm audit` on the frontend reports advisories in `postcss` (a build-time/dev dependency of the
Tailwind toolchain) that require upgrading to Next.js 16 to fully resolve - a breaking change out
of scope for this build. These advisories affect build-time source-map/CSS processing, not the
served runtime application, and are noted here rather than silently ignored. `pip-audit`-style
review of backend dependencies was not run as a separate step; versions in `requirements.txt` are
pinned and recent as of this build.

## Logs

Structured JSON logs include `request_id`, `session_id`, `operation`, `provider`, `model`,
`latency_ms`, `status` - never message content, API keys, or passwords. Verified by inspection of
every `logger.*` call site in `app/`.

## What this build does *not* implement (by design, given scope)

- No authentication/authorization layer - single-tenant local app. `users.external_id` exists in
  the schema for a future login integration but nothing currently populates or checks it.
- No rate limiting - appropriate for a local demo, not for a public deployment.
- No encryption at rest beyond whatever the host Postgres/filesystem provides - local dev
  database, not a hosted service.

If this were promoted beyond a local/demo deployment, the priority order would be: add auth,
add rate limiting on `/api/sessions/*/messages` (the only LLM-cost-incurring endpoint), and run a
dependency audit as part of CI.
