# Tiered leaderboards, and the threshold that decides the winner

**Role** Senior Analyst, Data Analytics & AI · **Context** quality leaderboards by geography for
a competitive benchmark · **Method only** — no brands, no results, no vendor named.

## The question

Publish leaderboards at four levels of geography — national, region, province, kabupaten/kota —
on half a dozen metrics, with a defensible winner at each level. Easy to state, and the first
honest attempt produced a national latency board won by operators nobody has heard of, with the
largest provider in the market ranked 143rd.

Nothing was broken. That is the problem worth writing about: **a leaderboard is mostly a set of
eligibility decisions, and if you do not make them deliberately they get made for you.**

## What I did

**Found the inclusion threshold in the data instead of choosing a round number.** A small
operator serving one affluent district can post an excellent median, on a sample far too thin to
mean anything. Any cut-off excludes someone, so the cut-off has to be defensible.

I looked at the distribution of session share across all brands and found a natural break: a
cluster above 1% of sessions, then a gap, then everyone else at 0.9% and below. That break became
the rule — "major brands" are those at or above 1% of sessions in the window — and the rule is
published next to the board. A threshold taken from a gap in the data can be argued with on its
merits; a threshold of "top 10" cannot be argued with at all, which sounds like a strength and is
the opposite.

**Made "winner" a statistical statement, not a sort order.** Ranking by point estimate declares a
winner when two brands differ by 0.1 of a point on overlapping intervals. Each metric therefore
carries an interval — the delta method for a product of two ratios, an order-statistic interval
for a median read off a histogram — and a brand is a **joint winner** when its interval overlaps
the leader's. Boards then say "winner" or "joint winner", and the honest result of a close race
is a tie rather than a false precision.

**Picked the aggregation level per metric, from how deep the data actually goes.** Not every
metric survives to kabupaten level. Session counts do; medians on a sub-sampled test type do not.
Rather than publishing a board with convincing-looking numbers on twelve tests, each metric
declares the deepest level at which it still has an adequate sample, and the board stops there.
Of 514 kabupaten, 425 supported a quality board at all — stating that is part of the deliverable.

**Separated the statistic from the metric.** A median and a mean rank brands differently on a
heavy-tailed distribution, so a leaderboard has to say which one it uses and why. We ran both,
reported the one that matched the external benchmark's method, and kept the other beside it for
the few places they disagree.

**Used the absence of a class as information.** One metric turned out to be unreportable: nearly
90% of brand-months had a zero, because only a handful of operators had the feature at all. The
first draft framed this as "brand X lags on this metric". The correct framing is "only a dozen
brands have it, and here they are" — the metric was measuring availability, not performance, and
a ranking would have been a ranking of a category error.

## Outcome

Leaderboards at four grains with a published eligibility rule, intervals on every metric, joint
winners where the data says tie, and an explicit statement of where each metric stops. The rules
are in code, so a new month rebuilds the boards without anyone re-deciding who qualifies.

## What I would do differently

**Write the eligibility rules before computing anything.** I discovered the 1% break while
debugging an absurd result. Finding it that way is lucky; the threshold is a design decision and
belongs in the plan, where it can be reviewed before it is load-bearing.

**Treat "rank 143" as a signal about the method, not about the brand.** The first instinct was to
check the brand's data. The answer was in the eligibility rule the whole time, and I would now
reach for "who is in this population and why" before "is this number wrong".

**Put the sample size on the board.** Every version where the test count is visible gets fewer
questions, and the questions it gets are better.
