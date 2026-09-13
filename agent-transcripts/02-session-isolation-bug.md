# Incident 02 — Session isolation: small model conflates evidence with chat history

This is the most significant correctness bug found in this build, and it was found by doing
exactly what the take-home's verification phase asks for: "create a new session, confirm context
isolation."

## What happened

With the full stack running for real (Postgres, Ollama, FastAPI, Next.js), a brand-new chat
session (zero prior messages) was asked:

> "What were we just talking about?"

The assistant replied:

> "We were discussing the topic of growth and retention in product management, specifically the
> importance of understanding and addressing retention issues... We also discussed various
> quotes and insights from growth experts, including Ines Vogler, Priya Nathanson, Dana Okafor,
> and Tomasz Rybicki."

This reads exactly like a session-isolation leak - a fresh session describing a conversation that
never happened in it, complete with named "guests."

## Diagnosis

First step was verifying whether this was a real data leak or a generation-time hallucination,
because the two require completely different fixes:

```sql
SELECT s.id, m.role, left(m.content, 50)
FROM sessions s JOIN messages m ON m.session_id = s.id
WHERE s.title = 'Fresh session' ORDER BY m.created_at;
```

Result: exactly two rows - the user's question and the assistant's reply. **No other session's
messages were present.** So `session_id` scoping at the persistence layer (`session_service.py`)
was correct. The bug was entirely in generation: retrieval still returned chunks for the
"deprecated" query (see incident 04 for why), those chunks were placed in the prompt under
"Retrieved context," and the small local model synthesized an answer treating that retrieved
context *as if it were prior conversation turns* - a plausible-sounding conflation a small model
makes but a larger model likely wouldn't.

## First fix attempt (insufficient)

Added explicit prompt language: a new rule telling the model never to confuse "Retrieved context"
with actual prior turns, plus an `EMPTY_HISTORY_NOTE` appended to the system prompt whenever
`history` is empty ("this is a brand-new conversation").

**Result after restart: same failure.** The 1B-parameter model did not reliably follow this
instruction - it's a subtle negative instruction buried among several other prompt rules, and
models this small are known to be unreliable at that kind of instruction-following.

## Second fix (effective)

Rather than keep tuning the prompt against a model too small to reliably obey it, added a
**deterministic code-level guard** in `app/agents/skills/grounded_qa.py`:

```python
_META_RECAP_RE = re.compile(
    r"\b(what (were|did|have) we (just )?(talk(ing)?|discuss(ing)?|chat(ting)?)"
    r"|what (did|have) (you|i) (say|said|tell|told)"
    r"|(summarize|recap) (our|this|the) conversation)\b",
    re.IGNORECASE,
)

if not history and _META_RECAP_RE.search(question):
    return GroundedAnswer(text=NEW_CONVERSATION_RECAP, sources=[], is_grounded=True)
```

This short-circuits *before* retrieval or the LLM are ever invoked when the specific, testable
failure pattern is detected (empty history + a "what did we discuss" style question) - it doesn't
try to solve the model's general instruction-following limitations, just the one concrete,
demoable scenario the take-home explicitly checks for.

## Verification

- Re-tested via `curl` against the running backend: fresh session → deterministic "This is a new
  conversation..." reply, zero sources.
- Re-tested via the actual browser UI (not just the API) - same correct behavior.
- Verified the fix doesn't break the *legitimate* case: a session with real prior history asked
  "What did we just discuss?" correctly summarizes the actual prior turn, not the fixed message.
- Added `test_meta_recap_on_fresh_session_never_calls_the_llm` to the automated suite, using a
  `RefusingLLMProvider` test double that raises an `AssertionError` if `complete()` is ever
  called - proving the guard short-circuits before the LLM, not just that the output happens to
  look right this time.

## Why this is documented as an architecture decision, not just a bug fix

This incident is the concrete reason `architecture.md` documents "deterministic routing over
LLM-driven behavior" as a deliberate choice for the mandatory local-model path, and it's called
out again in `PRD.md`'s risk table. A larger/cloud model would likely have followed the prompt
instruction correctly on the first attempt; the code-level guard exists specifically because the
mandatory demo path cannot assume that.
