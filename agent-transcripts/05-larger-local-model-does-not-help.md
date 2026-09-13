# Incident 05 — "Just use a bigger local model" doesn't hold up under test

## Context

Ship 30 essay generation with the default `llama3.2:1b` produced ~660 words against the
~1250-word target (see `docs/MANUAL_TEST_PLAN.md` test case 8). The obvious next thing to try:
pull a larger model in the same family and see if it closes the gap, since the machine (8GB RAM,
no GPU) had headroom for a ~2GB model.

## What was tested

```bash
ollama pull llama3.2:3b
```

Then the exact same `generate_ship30_essay()` call, same topic ("lessons on growth experimentation
prioritization"), same retrieved context, swapping only the model.

## Result

`llama3.2:3b` produced **612 words** — shorter than the 1B model's 660, not longer. It also
included this in the draft:

> "...We see companies like Facebook and Airbnb, with seemingly magical growth trajectories..."

Neither Facebook nor Airbnb appear anywhere in the retrieved transcript excerpts for this topic.
This is exactly the kind of fabrication the take-home brief explicitly prohibits ("Do not
fabricate statistics, company names, or outcomes not present in the excerpts") and the Ship 30
system prompt explicitly forbids too — the 3B model violated an instruction the 1B model didn't
even attempt to violate in the same test.

The pipeline's existing safety net, `validate_and_repair_quotes()`, did correctly catch and strip
one fabricated **quoted** claim from the same draft ("Unverified quotation removed: 'What will
happen if we change this one thing?...'"). But it only inspects text inside quotation marks - the
"Facebook and Airbnb" fabrication was unquoted prose, which the current validator has no coverage
for.

## Why this was worth stopping to document rather than just moving on

The instinct after finding the 1B model's essay was too short was to write "swap in a bigger
local model" as the fix in the README and move on. Actually testing that claim instead of
asserting it surfaced two things that would have been wrong to leave undocumented:

1. Model size within the same family doesn't reliably fix length - this specific 3B checkpoint
   was *shorter*, not longer, on this exact task.
2. It introduced a new grounding failure mode (unquoted fabricated entities) that the existing
   validation doesn't cover, which is arguably worse than the original length shortfall.

## Resulting documentation change

`README.md`'s "Ollama setup" and "Known limitations" sections were corrected to stop suggesting a
larger local model as *the* fix, and instead point at a cloud provider (Anthropic/OpenAI) as the
more reliable lever for both length and grounding quality - based on this test, not assumption.

## Follow-up not done in this build (scope call)

Extending `validate_and_repair_quotes()` (or a sibling check) to flag named entities in unquoted
prose that don't appear in the retrieved context would close this specific gap, but risks false
positives on legitimate content (e.g. a company name that genuinely appears in a transcript but
gets paraphrased slightly). Left as a documented future improvement rather than shipped
half-tested under time pressure - see README "Future improvements."
