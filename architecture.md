# Architecture — The Lenny Growth Assistant

## System overview

```mermaid
flowchart TB
    UI["Next.js Frontend<br/>(chat, sidebar, artifact viewer)"]
    API["FastAPI<br/>(routes, error envelope, request logging)"]
    SVC["Session / Artifact Services<br/>(persistence, no business logic in routes)"]
    AGENT["Agent Orchestrator<br/>(router.py + orchestrator.py)"]
    SKILLS["Skills<br/>grounded_qa · ship30 · artifact_generation"]
    RET["Retriever<br/>hybrid vector + full-text search"]
    DB[("PostgreSQL + pgvector")]
    PROV["LLMProvider interface"]
    OLLAMA["Ollama (local, mandatory demo)"]
    ANTH["Anthropic (optional)"]
    OPENAI["OpenAI (optional)"]

    UI -->|REST, JSON| API
    API --> SVC
    API --> AGENT
    AGENT --> SKILLS
    SKILLS --> RET
    RET --> DB
    SVC --> DB
    SKILLS --> PROV
    PROV --> OLLAMA
    PROV --> ANTH
    PROV --> OPENAI
```

This matches the layering the take-home asked for: Frontend → FastAPI → Session Service → Agent
Orchestrator → Skills/Tools → Retriever → PostgreSQL/pgvector → LLM Provider. Retrieval is kept
strictly separate from generation (`app/retrieval/` never imports a provider; `app/providers/`
never imports the retriever), and skills are separate from the orchestrator (`app/agents/skills/`
contains no routing logic; `router.py` contains no prompt text).

## Why no LLM-driven tool calling

The take-home suggests the Anthropic Agent SDK or a tool-calling agent loop. This build uses a
**deterministic, code-based router** (`app/agents/router.py`) instead, for one concrete reason:
the mandatory local demo model is a small (~1B-parameter) Ollama model, which cannot be trusted
to reliably emit structured tool calls - in practice, small local models frequently either skip
tool calls, hallucinate arguments, or narrate the tool call in plain text instead of invoking it.
Making intent classification a deterministic, testable function (keyword/regex-based, unit
tested in `tests/test_router.py`) means routing behaves *identically* whether the active provider
is Ollama, Anthropic, or OpenAI - switching providers is purely a quality/latency change, not a
behavioral one. This is documented as a deliberate architecture decision, not an oversight.

## Database schema

```mermaid
erDiagram
    USERS ||--o{ SESSIONS : owns
    SESSIONS ||--o{ MESSAGES : contains
    SESSIONS ||--o{ ARTIFACTS : contains
    MESSAGES ||--o| ARTIFACTS : "may produce"
    TRANSCRIPTS ||--o{ TRANSCRIPT_CHUNKS : "split into"
    TRANSCRIPT_CHUNKS ||--|| EMBEDDINGS : has

    USERS {
        uuid id PK
        string external_id
        json user_metadata
        timestamp created_at
    }
    SESSIONS {
        uuid id PK
        uuid user_id FK
        string title
        timestamp created_at
        timestamp updated_at
    }
    MESSAGES {
        uuid id PK
        uuid session_id FK
        string role
        text content
        string model
        string provider
        json sources
        timestamp created_at
    }
    TRANSCRIPTS {
        uuid id PK
        string title
        string url
        string guest
        timestamp published_at
        text content
        string content_hash
        string source_type
    }
    TRANSCRIPT_CHUNKS {
        uuid id PK
        uuid transcript_id FK
        int chunk_index
        text content
        int token_count
        json chunk_metadata
    }
    EMBEDDINGS {
        uuid id PK
        uuid chunk_id FK
        vector embedding
        string model
    }
    ARTIFACTS {
        uuid id PK
        uuid session_id FK
        uuid message_id FK
        string type
        string title
        text content
        json sources
    }
```

`embeddings.embedding` is a pgvector `VECTOR(768)` column (matching `nomic-embed-text`'s output
size) with an HNSW cosine-distance index. Migrations live in `backend/alembic/`; the first
migration also runs `CREATE EXTENSION IF NOT EXISTS vector`, so a fresh Postgres needs no manual
setup beyond having the `pgvector` extension available (the `pgvector/pgvector:pg16` Docker image
ships it; the native-run README section covers installing it via Homebrew).

## RAG pipeline

```mermaid
flowchart LR
    Q[User question] --> QT["Conversation-aware query transform<br/>(fold in previous user turn)"]
    QT --> EMB[Embed via active EmbeddingProvider]
    EMB --> VEC["pgvector cosine search<br/>(top ~15 candidates)"]
    Q --> FTS["Postgres full-text search<br/>(plainto_tsquery, top ~15)"]
    VEC --> RRF["Reciprocal-rank fusion<br/>(ranking order only)"]
    FTS --> RRF
    RRF --> FLOOR{"Raw cosine score ≥ threshold<br/>OR matched lexically?"}
    FLOOR -->|no chunks pass| REFUSE["Fixed refusal message,<br/>no LLM call, zero sources"]
    FLOOR -->|chunks pass| CTX[Build context block with citations]
    CTX --> LLM[Active LLMProvider]
    LLM --> ANSWER[Grounded answer + source chips]
```

**Why RRF alone isn't the groundedness signal:** reciprocal-rank fusion normalizes to the
candidate set's own rank order, so it always produces a "top" result near 1.0 even when *every*
candidate is irrelevant - it would silently defeat the refusal requirement. Groundedness is
instead judged on the **raw pgvector cosine similarity** (calibrated per corpus/embedding model -
see the comment on `retrieval_min_score` in `app/core/config.py`), with a full-text match treated
as independently sufficient evidence regardless of vector score (catches exact terms/names a
small embedding model under-weights). This was caught and fixed during development - see
`agent-transcripts/`.

## Agent / skill routing

```mermaid
flowchart TD
    MSG[Incoming user message] --> ROUTE{classify_intent}
    ROUTE -->|essay/ship30 keywords| SHIP30[Ship 30 skill]
    ROUTE -->|html artifact keywords| HTMLART[Artifact skill: html]
    ROUTE -->|markdown/one-pager keywords| MDART[Artifact skill: markdown]
    ROUTE -->|default| QA[Grounded QA skill]

    QA --> GUARD{"Empty history AND<br/>'what did we discuss' pattern?"}
    GUARD -->|yes| FIXED["Deterministic reply:<br/>'this is a new conversation'<br/>(LLM never called)"]
    GUARD -->|no| RETRIEVE[Retrieve + answer]
```

The `GUARD` step is a deliberate, tested exception to "let the LLM handle it": a small local
model reliably conflates retrieved transcript excerpts with actual prior chat turns when asked to
recap a conversation that never happened, producing an answer that reads exactly like a
session-isolation leak even though the underlying data is correctly scoped per `session_id`. See
`app/agents/skills/grounded_qa.py` and `agent-transcripts/` for the incident.

## Model provider abstraction

```mermaid
classDiagram
    class LLMProvider {
        <<abstract>>
        +complete(messages) CompletionResult
        +stream(messages) AsyncIterator~str~
        +health_check() (bool, str)
    }
    class OllamaProvider
    class AnthropicProvider
    class OpenAIProvider
    LLMProvider <|-- OllamaProvider
    LLMProvider <|-- AnthropicProvider
    LLMProvider <|-- OpenAIProvider
```

`app/providers/factory.py` resolves the active provider from `LLM_PROVIDER` (env default) or a
runtime override set via `POST /api/models/select` (`app/core/runtime_state.py`) - no application
code imports a concrete provider class; routes and skills depend only on `LLMProvider` /
`EmbeddingProvider`, injected via FastAPI `Depends`. A missing cloud API key raises
`ProviderConfigError` (→ HTTP 503, `PROVIDER_CONFIG_ERROR`) at construction time, not a crash; an
unreachable Ollama raises `ModelUnavailableError` (→ HTTP 503, `MODEL_UNAVAILABLE`) with a message
telling the operator exactly what to run.

## Ingestion pipeline

```mermaid
flowchart LR
    SRC["Transcript files<br/>(.md/.txt, frontmatter: title/guest/url/published_at)"]
    LOAD[Parse frontmatter + body]
    HASH["SHA-256 content hash<br/>(dedup key)"]
    DUP{Hash already ingested?}
    CHUNK["Paragraph-aware sliding-window chunking<br/>(~350 tokens, 50-token overlap)"]
    EMBED[Embed each chunk]
    STORE[(Store transcript + chunks + embeddings)]

    SRC --> LOAD --> HASH --> DUP
    DUP -->|yes| SKIP[Skip - already ingested]
    DUP -->|no| CHUNK --> EMBED --> STORE
```

Every chunk carries provenance (`chunk_metadata`: episode title, guest, url) independent of the
parent transcript row, so retrieval results always resolve to a citable source. Re-running
`scripts/ingest_transcripts.py` is safe: unchanged files are skipped via content hash, not
re-embedded (see `IngestionService` and its tests).

## Artifact generation & sandboxing

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant SK as artifact_generation skill
    participant LLM as LLMProvider
    participant DB as Postgres
    participant FE as Frontend (iframe)

    U->>API: "Create an HTML one-pager on retention"
    API->>SK: generate_artifact(request, type="html")
    SK->>SK: retrieve() grounded context
    SK->>LLM: complete(system+context+request)
    LLM-->>SK: raw HTML
    SK->>SK: strip <script> tags server-side<br/>wrap in <html> if fragment
    SK->>DB: persist Artifact row
    API-->>FE: ArtifactOut {type, title, content}
    FE->>FE: render inside <iframe sandbox="allow-same-origin" srcDoc=...>
```

Two independent layers of defense, per `SECURITY.md`: the backend strips `<script>` tags before
persisting the artifact, and the frontend renders HTML artifacts in an iframe with
`sandbox="allow-same-origin"` and **no** `allow-scripts`, so even HTML the server-side stripper
missed cannot execute. Markdown artifacts are rendered via `react-markdown` (no `dangerouslySetInnerHTML`
anywhere in the codebase).

## Logging & observability

Structured JSON logs (via `structlog`) carry `request_id` (generated per HTTP request, echoed
back as an `x-request-id` response header), `session_id`, `operation`, `provider`, `model`,
`latency_ms`, `retrieval_count`, and `status`. Named events (`app/core/logging.py::Events`) match
the take-home's list: `REQUEST_STARTED`, `REQUEST_COMPLETED`, `RETRIEVAL_COMPLETED`,
`MODEL_STARTED`/`MODEL_COMPLETED`/`MODEL_FAILED`, `DATABASE_FAILED`, `ARTIFACT_CREATED`,
`ARTIFACT_RENDER_FAILED`, plus ingestion events. API keys, passwords, and message content are
never logged - only metadata about the request.

## Deployment topology

```mermaid
flowchart TB
    subgraph "docker-compose"
        FE[frontend :3000]
        BE[backend :8000]
        PG[(postgres+pgvector :5432)]
        OL[ollama :11434]
        OLI[ollama-init<br/>one-shot: pulls models]
        ING[ingest<br/>one-shot: loads demo transcripts]
    end
    FE -->|NEXT_PUBLIC_API_URL| BE
    BE --> PG
    BE --> OL
    OLI --> OL
    ING --> BE
```

`ollama-init` and `ingest` are one-shot services gated by `condition: service_healthy` /
`service_completed_successfully`, so `docker compose up` brings the whole stack to a usable state
without a manual post-start step (ingestion is also safely re-runnable manually at any time).

## Security boundaries

See `SECURITY.md` for the full review. Summary: CORS restricted to the configured frontend
origin; no secrets ever logged; SQL executed exclusively via SQLAlchemy parameter binding (the
one raw-SQL vector/FTS query in `retriever.py` uses bound parameters, never string
interpolation); generated HTML is sandboxed at render time in addition to being sanitized at
generation time; no filesystem or arbitrary-URL access is exposed to the LLM or to generated
artifacts.

## Failure handling

| Failure | Behavior |
|---|---|
| Postgres unreachable | `/health/ready` reports `degraded`; a request needing the DB gets a structured 503 rather than an unhandled exception |
| Ollama unreachable | `ModelUnavailableError` → 503 `MODEL_UNAVAILABLE` with a specific remediation message |
| Configured Ollama model not pulled | Same as above, message names the exact `ollama pull <model>` to run |
| Cloud API key missing | `ProviderConfigError` → 503 `PROVIDER_CONFIG_ERROR` at provider construction, before any network call |
| Retrieval returns zero results | Deterministic refusal message, zero sources, no LLM call for grounded QA / Ship30; artifact generation still proceeds but is instructed to rely only on conversation context, not invented facts |
| Invalid request body | Pydantic validation → 422 `INVALID_REQUEST` with per-field details |
| Unknown session/artifact id | 404 `NOT_FOUND` |
| Malformed/unsupported artifact type | 400-class `ARTIFACT_GENERATION_FAILED` before any LLM call |
