# Inferring something the data does not contain

**Role** Senior Analyst, Data Analytics & AI · **Context** a per-measurement dataset where the
field we needed is entirely empty · **Method only** — no brands, no vendor, no geography beyond
"a city".

## The question

An analysis needed to split measurements by the access technology of the line — two physically
different last-mile technologies with different expected performance. The dataset has a field for
exactly that. The field is **100% empty** for this market, as are two related ones.

So: can the class be inferred from what *is* present, and — the part that matters — **how would
we know whether the inference is real or an artefact?**

## What I did

**Built a rule first, from two observable signals.** Not a model: a rule, from the two device and
network attributes that domain knowledge says should correlate with the technology. A rule can be
read, argued with and corrected by someone who knows the network. A model cannot be argued with,
which is a disadvantage early on.

**Found ground truth and joined on geography.** Infrastructure records from the network side gave
the actual technology present in each small geographic cell. Cells containing exactly one
technology became labels; mixed cells were excluded from training and scored separately later.
Without this step the whole exercise would be unfalsifiable, and a plausible rule with no ground
truth is just a strongly worded opinion.

**Scored the rule honestly.** Session-level AUC **0.93** against the single-technology cells. That
is a usable proxy, and it is a rule anyone can inspect.

**Then asked whether a model beats it — and set the bar before looking.** We agreed in advance
that replacing a readable rule with a model is only worth it for a material gain, and fixed that
bar at +0.05 AUC. The model landed about **+0.04 inside a city**. Below the bar, so the rule stays
in production and the model stays as evidence that the rule is close to the ceiling. Setting that
threshold beforehand is what stopped this from becoming a post-hoc argument about whether 0.04 is
impressive.

**Attacked my own result in the one way that mattered.** The obvious failure mode is that the
model learned *where* the technologies are rather than *what* they are. Two tests:

1. **Validate by geography, not at random.** Grouped folds by city, so the model is always scored
   on cities it never trained on. A random split gave a visibly better number — that gap *is* the
   leakage, and reporting the random-split figure would have been flattering and wrong.
2. **Refit inside single cities, and strip location-like inputs.** Here the useful finding
   appeared: one feature separated the classes well when pooled across the country but **reversed
   sign inside a single city**. Pooled, it was reading distance to the measurement server;
   locally, it was reading something else entirely. A feature that changes direction when you
   control for place was never measuring the thing — and this is the same feature a vendor metric
   uses as a quality threshold, which is how this analysis fed back into case study 02.

**Held back a time slice too.** Trained on the earlier months, tested on the newest one, on
held-out cities. A proxy that only works on the period it was fitted to is not a proxy.

## Outcome

A readable rule, in production, validated against operator ground truth, with a documented ceiling
and a documented failure mode. The learned model was not deployed, which I count as a successful
outcome rather than a negative one: we now know the rule is near the limit of what these inputs
can say, so effort moved to getting the real field populated at source.

## What I would do differently

**Ask for the source field earlier and louder.** Every hour spent on a proxy is an hour spent
reproducing a field that already exists upstream. The proxy was necessary, but the request to
enable the field should have been filed on day one, not after the proxy worked.

**Write the falsification test before the first result.** I ran the within-city refit because the
pooled number looked too good. That instinct is not a method. "What would make this finding
false?" belongs in the plan, next to the metric.

**Report the leaky number alongside the honest one.** Showing the random-split AUC next to the
grouped-fold AUC makes the leakage visible instead of hiding it, and it pre-empts the reviewer who
runs the random split themselves and wonders why your number is lower.
