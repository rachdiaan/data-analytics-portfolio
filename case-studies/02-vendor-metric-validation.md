# Validating a vendor's published metric

**Role** Senior Analyst, Data Analytics & AI · **Context** a commercial benchmark product from a
global network-measurement vendor, alongside the raw per-test delivery it is built from ·
**Method only** — the vendor is not named, no brand results, no figures from the dataset.

## The question

A vendor sells monthly benchmark reports that compare operators on quality metrics. Those
numbers get quoted internally and externally, so the first question is not "what do they say"
but **"can we reproduce them from the raw data we already receive?"** If we can, every slide
becomes auditable. If we cannot, we need to know which gap is specification and which is
disagreement.

## What I did

**Rebuilt the formula from the raw delivery.** Their headline metric is a product of two ratios:
a quality ratio (share of measurements passing several conditions at once) and a reliability
ratio (share of measurements that completed at all). I implemented it per measurement, then
aggregated, and compared cell by cell against the published charts — same months, same brands,
same tiers.

**Validated at the cell level, not the headline level.** Agreement on a headline is weak
evidence: two different methods can land on the same average. I compared **156 transcribed
cells** of a published distribution chart and the mean absolute difference was **0.05
percentage points**, with 99% of cells inside ±0.2. On the per-measurement level, my
reconstruction of their quality ratio agreed with theirs on **99.5%** of the measurements both
formulas judged. At that point the method is not similar to theirs, it *is* theirs.

**Treated the leftover 0.5% as the actual finding.** Reaching agreement only mattered because it
isolated the disagreements. Each one turned out to be a specification detail that changes
published numbers:

- **The denominators differ between the two ratios.** The product is therefore an exact
  decomposition, not an independence assumption — but the headline alone cannot tell you which
  half moved. We measured a case where quality rose to its best level of the period while the
  headline fell, because reliability collapsed. Published without its two parts, that metric
  tells the opposite of what happened.
- **A conjunctive rule is dominated by its strictest condition.** The quality ratio requires six
  conditions to pass simultaneously. Measured per condition, one of them fails several times more
  often than the rest for every brand, while two others almost never bind. So a metric presented
  as a balanced composite is in practice a ranking on one condition. That is defensible — it just
  needs saying.
- **One threshold uses a *minimum*, not an average.** Minimum latency is a best-case path
  measurement, so it largely encodes distance to the test server rather than experienced latency.
  A footprint far from the server is penalised for geography. (Case study 05 shows the measurement
  that demonstrates this: the same feature reverses sign once you look inside a single city.)
- **A missing measurement is counted as a pass.** Where one field is empty, the condition is
  treated as satisfied. It is a small share of tests and a one-directional bias, which is the
  worst combination: too small to notice, never self-cancelling.
- **A vendor-supplied flag covers only part of the data, and not randomly.** Roughly half of the
  eligible measurements carry no value for it, and the ones that do pass the equivalent rule
  6–12 points more often than the ones that do not. Any level computed from that flag is a level
  on a *selected subpopulation*. Two brands compared on it are two different selections, not two
  networks.
- **"Average" was not a plain mean.** Their speed figures are described as averages. Tested
  against a published deck, a plain mean ran 31% above their values and got the ranking wrong; a
  median reproduced the ranking exactly; a 10% trimmed mean reproduced the level. On a
  heavy-tailed distribution a plain mean measures the top of the plan mix more than the network,
  so this distinction decides whether our numbers can sit beside theirs.

## Outcome

Our reporting now reproduces the vendor's published metric from raw data rather than transcribing
it, with a cell-level validation that is re-run whenever a new month arrives. Where our numbers
differ from a slide, we can say which specification choice causes it.

The second deliverable was a list of precise questions for the vendor — each one attached to a
measurement rather than an impression. A validation's useful output is not a verdict on whether
the vendor is right; it is the shortlist of things only they can answer.

## What I would do differently

**Transcribe the published charts into the repository on day one.** The cell-by-cell comparison
was what made every later claim defensible, and it was cheap. I built it late, after arguing
about headlines for longer than necessary.

**Keep the vendor's months and our months separate in code.** Their chart covers fewer months
than our data. Extending our window silently extended the comparison and briefly scored a month
the vendor never published. The fix is in case study 06: a window belongs in a constant, with
its label derived from the same constant.

**Never report the composite alone.** Every table that shows the headline metric now shows both
components next to it. That one layout decision prevents the most expensive misreading available.
