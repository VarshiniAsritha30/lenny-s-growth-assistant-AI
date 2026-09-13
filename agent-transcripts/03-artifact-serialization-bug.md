# Incident 03 — Artifact serialization crash (MissingGreenlet)

## How it was found

Not by the automated test suite - by manually driving the actual frontend in the browser against
the real backend. Asking "Create an HTML artifact one-pager summarizing retention best practices"
produced a visible error banner in the UI: "Something went wrong sending your message." The
network panel showed the `POST /messages` request failing at the network level
(`net::ERR_FAILED`), and the backend log had the real error:

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for ArtifactOut
updated_at
  Error extracting attribute: MissingGreenlet: greenlet_spawn has not been called;
  can't call await_only() here. Was IO attempted in an unexpected place?
```

## Root cause

In `app/agents/orchestrator.py`, after generating an artifact and creating the assistant message,
the artifact is linked back to that message:

```python
if artifact is not None:
    artifact.message_id = assistant_message.id
    await db.commit()
```

`Artifact.updated_at` has `onupdate=func.now()` - a **server-generated** value on UPDATE. Even
though the session factory uses `expire_on_commit=False` (so most attributes survive a commit
without needing a re-fetch), SQLAlchemy still needs an actual round-trip to learn the new
server-generated value for a column changed via `onupdate`. Without an explicit `refresh()`, that
attribute is left in a state that requires a lazy load on next access - and Pydantic's
`ArtifactOut.model_validate(result.artifact)` accesses `.updated_at` *synchronously*, outside of
any `await`, which is exactly the situation `MissingGreenlet` is designed to catch (async SQLAlchemy
can't silently do blocking IO to satisfy a sync attribute access).

## Fix

```python
if artifact is not None:
    artifact.message_id = assistant_message.id
    await db.commit()
    await db.refresh(artifact)
```

One line, but it only surfaces when: (a) an artifact is generated *through the chat message
endpoint* specifically (the standalone `/api/artifacts` and `/api/skills/ship30` endpoints don't
hit this path, since they don't do the message-linking commit-then-serialize sequence), and (b)
something downstream actually reads the lazily-invalidated attribute. This combination wasn't
covered by the artifact-generation unit tests (`test_artifact_security.py`), which call
`generate_artifact()` directly and never touch the message-linking code path in the orchestrator.

## Verification and regression coverage

- Restarted the backend, repeated the exact browser action that failed - artifact generated and
  rendered correctly, no error banner.
- Added `test_html_artifact_request_via_message_endpoint_serializes_cleanly` in
  `tests/test_message_artifact_flow.py`, which exercises the *message endpoint* specifically
  (not just the skill function directly) and asserts the response serializes with a populated
  `updated_at` - this is the test that would have caught the bug had it existed first, and now
  prevents a regression.

## Takeaway

This is a good example of why "type-checks and unit tests pass" is not the same claim as "the
feature works" - the bug lived at the intersection of an async ORM refresh-timing detail and a
synchronous serialization boundary, a combination that unit tests exercising each piece in
isolation didn't reach. It was only found by actually using the product end-to-end through the
real UI, which is why that step is treated as mandatory in this build rather than optional
polish.
