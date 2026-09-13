# Agent transcripts

This directory documents what actually happened while building this project with an AI coding
agent (Claude Code) in a single session - genuine failures, debugging, and corrections, not a
sanitized retelling. Nothing here is fabricated; every incident below was hit for real against
the running stack during this build and is cross-referenced from `docs/MANUAL_TEST_PLAN.md`,
`architecture.md`, and `PRD.md` where relevant.

## Files

- `01-environment-setup.md` - Postgres/pgvector version mismatch and a macOS-specific Postgres
  startup bug hit while setting up the local dev database (no Docker available on this machine).
- `02-session-isolation-bug.md` - the most significant correctness bug found: a small local model
  conflating retrieved transcript excerpts with actual prior conversation turns, discovered via
  the exact "confirm context isolation" check the take-home's verification phase calls for.
- `03-artifact-serialization-bug.md` - an async ORM/Pydantic interaction bug found while manually
  exercising the HTML-artifact flow through the real browser UI, not caught by the unit test
  suite until a regression test was added afterward.
- `04-router-and-scoring-bugs.md` - two smaller correctness bugs (an intent-routing regex that
  was too strict, and a groundedness-threshold bug in the retrieval fusion math) found while
  writing the automated test suite.
- `05-larger-local-model-does-not-help.md` - a documentation correction: pulling a larger local
  model to fix the Ship 30 essay-length shortfall was tested, not assumed, and found to make
  things worse (shorter output, plus a new unsourced-fabrication failure mode the existing
  quote-validator doesn't catch).

## What's redacted

Nothing sensitive appeared in this build - no real API keys were ever entered (Anthropic/OpenAI
were tested only for their "missing key" failure path), so there is no redaction to perform. If a
future run of this project does exercise a live cloud key, transcripts added here should have the
key value replaced with `[REDACTED]` before committing, never the surrounding request/response
context.
