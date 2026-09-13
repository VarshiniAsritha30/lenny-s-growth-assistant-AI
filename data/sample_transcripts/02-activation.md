---
title: "[DEMO] Fixing Activation Without Redesigning the Whole Product"
guest: "Marcus Feld (fictional demo guest)"
url: "https://example.com/demo-transcripts/activation"
published_at: 2023-06-02
---

Host: When a team comes to you saying "our activation rate is bad," what's the first thing you
ask them?

Marcus: I ask them to define activation in one sentence, tied to a specific action, not a vibe.
Half the time there isn't a shared definition — marketing thinks activation is signup, product
thinks it's "used the core feature once," and the exec team thinks it's "became a paying
customer." You can't fix a metric three teams define differently. Once we agree on a single
event — say, "created and shared their first report within 7 days" — the real work can start.

Host: Once you have that definition, how do you find where people are dropping off?

Marcus: Build the funnel at the event level, not the page level. Page views lie to you, because
someone can sit on a page confused for ten minutes and it looks identical in your analytics to
someone who read it in five seconds and moved on happily. I want to see: signup, first
meaningful action attempted, first meaningful action completed, and then the habit-forming
repeat action. Nine times out of ten, the biggest drop is between "attempted" and "completed" —
people try the thing and something breaks their momentum.

Host: What tends to break momentum at that step?

Marcus: Almost always one of three things: the action requires data or setup the user doesn't
have yet, the action requires a decision the user isn't equipped to make on their own, or the UI
requires more steps than the user expected. A good diagnostic is to watch five session recordings
of people who attempted and failed. You'll usually see the same stall point across all five —
that's your fix.

Host: A lot of teams reach for an onboarding checklist or tooltip tour as the default fix. Does
that actually work?

Marcus: Tooltip tours fix "I didn't know this button existed." They do nothing for "I know the
button exists but I don't have the confidence or the data to click it." Most activation problems
are the second kind, and no amount of UI hand-holding fixes a missing precondition. If someone
needs to connect a data source before your product is useful, and connecting it takes real
effort, your activation problem isn't the tour — it's that the value doesn't show up until step
four of a five-step setup. The fix is usually to compress time-to-value, often by pre-filling
with sample data so users experience the "aha" before they've done any setup work at all.

Host: How do you think about templates and sample data as an activation lever?

Marcus: Underrated and cheap to build relative to the lift. If your product needs a user's real
data to be useful, ship a pre-populated demo workspace that shows the finished state on day one.
People decide whether to invest effort based on whether they believe the payoff is real. Showing
them the payoff before asking for the effort is one of the highest-leverage activation changes
we've shipped — in one case it moved a 7-day activation metric from the low twenties to the high
thirties, just by making the empty state not empty.

Host: What about activation for products that are inherently collaborative — where the value
only shows up once a second person joins?

Marcus: That's the hardest category, because your new user's activation depends on someone
else's behavior. The lever there is reducing the ask for that second person to almost nothing —
a viewer link that requires no signup, for instance — so the first user can get a taste of the
network effect without needing to convince a teammate to create a full account. Once they've
seen it work with a lightweight invite, asking for the "real" invite gets much easier, because
they've already seen the payoff once.

Host: Any activation mistakes you see repeatedly, even at experienced companies?

Marcus: Measuring activation weekly or monthly and then wondering why nothing improves. Activation
is one of the few metrics you can and should watch daily, because you can usually get a read on
an experiment within days, not weeks, since new users hit the funnel constantly. Teams that treat
it like a lagging, monthly board metric instead of a live daily dashboard end up shipping five
fixes at once and never learning which one mattered.
