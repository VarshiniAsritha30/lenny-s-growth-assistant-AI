# Manual test plan

Every case below was executed at least once against the real running stack during this build
(real Postgres+pgvector on port 5544, real Ollama with `llama3.2:1b` + `nomic-embed-text`, backend
on :8000, frontend on :3000) - not just written speculatively. Where a case surfaced a real bug,
the bug and fix are noted and cross-referenced in `agent-transcripts/`.

| # | Test case | Steps | Expected result | Result in this build |
|---|---|---|---|---|
| 1 | Health check | `curl /health` and `curl /health/ready` | `/health` → `{"status":"ok"}`; `/health/ready` → 200 with `database`, `llm_provider`, `embedding_provider` all reported | ✅ Pass |
| 2 | Ingestion | `python scripts/ingest_transcripts.py --source data/sample_transcripts` | 6 demo transcripts ingested, ~24 chunks created, re-running skips all as duplicates | ✅ Pass (24 chunks first run, 0 new on re-run) |
| 3 | Grounded question | Ask "How should I improve product activation?" | Answer cites ≥1 source from the activation demo episode with excerpt + relevance score | ✅ Pass |
| 4 | Follow-up context | After Q3, ask "What about retention specifically?" | Answer pulls retention-topic sources; no need to repeat "activation" context | ✅ Pass |
| 5 | Out-of-scope refusal | Ask about a topic absent from the corpus (e.g. "quantum chip fabrication") | Assistant states the transcript material doesn't support an answer; does not fabricate an episode/guest | ✅ Pass (model explicitly said no such content existed) |
| 6 | Session isolation - normal | Start a new chat, ask an unrelated question | No reference to any other session's content | ✅ Pass |
| 7 | Session isolation - meta-recap edge case | Start a brand-new chat, ask "What were we just talking about?" | Deterministic "this is a new conversation" reply; **zero** sources; LLM never invoked | ✅ Pass after fix - see `agent-transcripts/` (initially failed: small model fabricated a fake recap from retrieved excerpts) |
| 8 | Ship 30 essay | POST `/api/skills/ship30` with a covered topic | Markdown artifact returned, grounded, no fabricated quotes | ⚠️ Pass with caveat (660 words with `llama3.2:1b`, short of the 1250-word target; retested with `llama3.2:3b` — 612 words plus an unsourced fabricated company name in unquoted prose, not caught by the quote-validator. See `agent-transcripts/05-larger-local-model-does-not-help.md`) |
| 9 | Markdown artifact | Ask "Create a markdown one-pager summarizing activation best practices" | Artifact Viewer opens with rendered Markdown | ✅ Pass |
| 10 | HTML artifact | Ask "Create an HTML artifact one-pager on retention" | Artifact Viewer opens with rendered, styled HTML in Preview tab; raw HTML in Code tab | ✅ Pass |
| 11 | Artifact sandbox | Inspect the rendered HTML artifact's iframe | `sandbox="allow-same-origin"` only, no `allow-scripts` | ✅ Pass (verified via DOM query in-browser) |
| 12 | Artifact copy/download | Click Copy and Download on an artifact | Clipboard receives raw content; a `.html`/`.md` file downloads via the browser | ✅ Pass |
| 13 | Model switch | Open the model picker, view provider list | Ollama shown healthy; Anthropic/OpenAI shown unhealthy with "API key not set" detail | ✅ Pass |
| 14 | Model switch - failure handling | `POST /api/models/select {"provider":"anthropic"}` with no key configured | 503 `PROVIDER_CONFIG_ERROR`, not a crash; switching back to `ollama` still works afterward | ✅ Pass |
| 15 | Ollama down | Point `OLLAMA_BASE_URL` at an unused port, ask a question | 503 `MODEL_UNAVAILABLE` with a message naming the model to pull/start | ✅ Pass (automated in `tests/test_resilience.py`) |
| 16 | Invalid session | `GET /api/sessions/<random-uuid>` | 404 `NOT_FOUND` with `request_id` in the structured error body | ✅ Pass |
| 17 | Invalid message body | `POST /messages` with empty `content` | 422 `INVALID_REQUEST` with field-level detail | ✅ Pass |
| 18 | New chat / delete session | Create a session, send a message, delete it | Session and its messages disappear from the sidebar and DB (`ON DELETE CASCADE`) | ✅ Pass |
| 19 | Dark/light theme | Toggle theme in sidebar settings | Full palette swap, no flash-of-wrong-theme on reload (localStorage-seeded) | ✅ Pass |
| 20 | Mobile layout | Resize viewport to 375×812 | Sidebar collapses to a hamburger-triggered drawer; composer/empty-state remain usable | ✅ Pass |
| 21 | Artifact link persists across session reload | Generate an artifact, switch to another session, switch back | The "Open artifact" affordance reappears on the original message (via `GET /api/sessions/{id}/artifacts`) | ✅ Pass |

## Known gap in this pass

Live cloud-provider (Anthropic/OpenAI) end-to-end testing was not performed - no API key was
available in this environment. The provider classes are unit-tested with the HTTP layer mocked
(`test_anthropic_provider_without_api_key_raises_config_error_not_crash`) and the same
code path is exercised identically for Ollama, so the risk is limited to
provider-SDK-specific edge cases (e.g. Anthropic's exact `stop_reason` values), not the
surrounding architecture.
