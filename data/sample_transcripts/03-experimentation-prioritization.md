---
title: "[DEMO] How Great Growth Teams Decide What to Test Next"
guest: "Priya Nathanson (fictional demo guest)"
url: "https://example.com/demo-transcripts/experimentation-prioritization"
published_at: 2023-09-21
---

Host: Every growth team says they prioritize using something like ICE or PIE scores. Does
scoring frameworks actually change outcomes, in your experience?

Priya: The framework itself matters less than whether the team is honest when filling it in.
I've watched teams use ICE — impact, confidence, ease — and just reverse-engineer high scores for
the idea the loudest person in the room already wanted to ship. The framework becomes theater. The
version that actually works is when someone other than the idea's owner scores confidence, because
owners are structurally overconfident about their own ideas.

Host: How do you build that structure without slowing the team down with process?

Priya: We use a lightweight rule: any test that isn't a five-minute copy change needs a one-
paragraph hypothesis written before anyone opens a design tool. Not a doc, a paragraph: "We
believe [change] will cause [metric] to move because [reason], and we'll know we're right if we
see [specific threshold] within [time window]." Writing that sentence kills a surprising number
of ideas on the spot, because people realize they can't actually articulate why they expect it to
work.

Host: Let's talk about impact estimation specifically — that's usually the fuzziest part of these
scores. How do you make it less of a guess?

Priya: Use your funnel math, not your gut. If a test targets the signup-to-activation step and
that step currently converts at 30%, the realistic range of outcomes is bounded — you're not
going to double it with a button color change. Back-of-envelope math using your actual current
conversion rate, multiplied by your current traffic volume, gives you a defensible range instead
of a made-up "high/medium/low." Teams that skip this step consistently overrate cosmetic tests
and underrate structural ones, because structural tests are scarier to estimate so people avoid
doing the math on them.

Host: How many experiments should a team be running at once?

Priya: Fewer than people think, especially early on. Running eight small tests at once across a
funnel with modest traffic means each test is underpowered, so you get noisy, unreliable reads
and end up shipping decisions based on statistical accidents. I'd rather run two well-powered
tests sequentially than eight noisy ones in parallel, unless you genuinely have the traffic volume
to support parallel tests without interaction effects. Most seed and Series A companies don't.

Host: What's your take on "big swing" tests versus incremental ones?

Priya: You need both, but on a schedule, not a whim. I like a rough 70/30 split — 70% of testing
capacity on well-understood incremental improvements to a metric you already trust, 30% on bigger
bets that could be flat-out wrong but teach you something structural if they work. The mistake is
letting the ratio drift entirely toward incremental, because incremental tests compound slowly and
a team can spend a year optimizing button copy while missing that the entire funnel step is the
wrong shape.

Host: How do you handle a test that shows a statistically significant result that contradicts
everything the team believed?

Priya: Trust it, but verify the mechanism before you generalize it. If we expected a pricing page
simplification to increase conversion and it decreased it instead, the wrong move is to just
revert and move on. Dig into segment-level data — did it decrease across all traffic sources, or
just one? Surprising results are often the most valuable ones precisely because they mean your
mental model of the user was wrong somewhere, and that's usually worth more than the ten
experiments that confirmed what you already believed.

Host: Any advice for a team that's just starting to build an experimentation culture from
nothing?

Priya: Ship the first test badly rather than build the perfect experimentation platform first. I've
seen teams spend a full quarter building internal tooling for "proper" experimentation before
running a single real test. Start with the crudest version — a feature flag and a spreadsheet —
and let the pain points from real usage tell you what tooling you actually need. Most of what
teams think they need up front, they never end up using.
