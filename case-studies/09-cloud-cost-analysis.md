# Cloud cost analysis, from the billing data rather than the console

**Role** Senior Analyst, Data Analytics & AI · **Context** analysing cloud spend from the
detailed billing export · **Method only** — no account identifiers, no amounts, no service mix.

## The question

The cloud console gives a monthly total and a chart. That answers "how much", and nothing anyone
actually asks: **which workload, whose, why it moved, and what would happen if we changed it.**
Those need the detailed billing export — one row per resource per hour, with the usage type,
the account, and whatever tags were applied.

## What I did

**Queried the export directly instead of through a dashboard.** The detailed export is large,
wide and column-oriented, which makes it a straightforward analytics problem: read it where it
sits, aggregate before pulling anything local, and keep the heavy group-by in the engine. Cost
analysis is unusual in that the dataset describing the spend is itself a thing you can spend
money querying, so "aggregate first, download second" is both good practice and the point.

**Learned the grain before trusting a single number.** The billing export is not a ledger of
charges; it is a record of usage lines that *become* a charge after discounts, commitments,
credits and amortisation are applied. Several cost columns exist and they mean different things —
unblended, amortised, net of credits. Summing the wrong one produces a number that is internally
consistent, reproducible, and not the number finance uses. This is the same defect as case study
01 in a different costume: two columns a letter apart in name and a concept apart in meaning.

**Made allocation explicit, including what cannot be allocated.** Tag coverage is never complete.
The honest output is three buckets — attributable to a workload, attributable to shared
infrastructure, and unattributable — with the third one reported rather than quietly spread
across the first two. A pro-rata allocation of untagged spend looks tidier and tells people a
number they will make decisions with that nobody measured.

**Separated price from usage.** A cost going up is two different stories: more of something, or
the same amount at a different rate. Decomposing the change into a usage component and a rate
component is what turns "spend rose" into an action, because only one of those two is something
an engineering team can do anything about this quarter.

**Asked what decision each view supports.** A cost dashboard attracts requests for every cut the
data permits. The ones that survived were the cuts tied to a decision somebody actually makes:
which workloads to review this month, which resources have no owner, and where usage is growing
faster than the thing it supports.

## Outcome

Spend analysable by workload and account from the billing export, with the unattributable share
stated instead of hidden, and movements separable into usage and rate.

## What I would do differently

**Fix tagging at the source before building the analysis.** Every hour spent allocating untagged
spend is an hour spent working around a one-line policy. The analysis makes the gap visible,
which is useful exactly once — after that it is a recurring tax.

**Agree the cost column with finance in writing, on day one.** Picking it myself and reconciling
later was the wrong order, and it is the single fastest way for a cost analysis to lose
credibility it will not get back.

**Keep a monthly snapshot of the aggregate.** The detailed export is restated as credits and
discounts land, so a figure quoted in a deck last month may not reproduce today. A small stored
aggregate per month, with the date it was taken, prevents an argument that has no winner.
