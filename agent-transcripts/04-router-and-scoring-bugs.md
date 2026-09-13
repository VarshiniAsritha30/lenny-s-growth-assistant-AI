# Incident 04 — Two correctness bugs found while writing tests

Both of these were caught by writing the automated test suite, not by manual exploration - a good
demonstration of why the tests were written *during* the build rather than bolted on afterward.

## Bug A — Groundedness threshold defeated by score normalization

**Original design:** `Retriever._reciprocal_rank_fusion` merged vector-search and full-text-search
results and returned a fused score normalized against the fused set's own maximum, then filtered
by `score >= retrieval_min_score`.

**The bug:** normalizing against the candidate set's own max score means the top result is
*always* ~1.0, regardless of whether anything in the set is actually relevant. Manually testing
an obviously off-topic query ("What does the podcast say about quantum computing chip design?")
against the demo corpus (which is entirely about product/growth topics) returned fused scores of
0.9+ for the top hits - the exact opposite of the intended refusal behavior.

**Fix:** separated *ranking order* (still reciprocal-rank fusion, fine for deciding which of
several relevant chunks to show first) from *groundedness* (now judged on the **raw**, un-normalized
pgvector cosine similarity, with a full-text match treated as independently sufficient evidence).
Calibrated the threshold empirically against the real embedding model and demo corpus: on-topic
queries scored ~0.58-0.65 raw cosine similarity; off-topic queries plateaued around ~0.42-0.53.
Set `retrieval_min_score = 0.55` accordingly (documented as corpus/model-specific in
`app/core/config.py`).

**Verification:** `tests/test_retrieval_live.py` (gated on a live Ollama daemon) asserts an
on-topic query returns chunks from the correct episode and an off-topic query returns none.

## Bug B — Intent router too strict on essay-request phrasing

**The bug:** `classify_intent`'s original essay-detection regex required a literal `turn (this|
that|it) into` phrase. A perfectly natural request from the take-home's own example prompt list -
"Turn the key lessons about retention into an essay" - has more text between "turn" and "into"
("the key lessons about retention"), so it silently fell through to the default `grounded_qa`
intent instead of routing to the Ship 30 skill.

**Fix:** replaced the single combined regex with two independent checks - one for an action verb
(write/draft/turn/generate/create/make) anywhere in the message, one for an essay-shaped target
noun (essay/ship30/blog post/article) anywhere in the message - and require both to be present,
rather than requiring a specific adjacency pattern between them.

**Verification:** `tests/test_router.py::test_essay_request_routes_to_ship30` asserts the exact
example prompt from the take-home brief routes correctly; this test failed against the original
regex and passes after the fix.
