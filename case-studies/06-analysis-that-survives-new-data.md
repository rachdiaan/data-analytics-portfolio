# Analysis that survives new data

**Role** Senior Analyst, Data Analytics & AI · **Context** extending a multi-month analysis by one
month · **Method only** — the dataset, brands and findings are not described here.

## The question

An analysis covering four months of daily data had to be extended to five. The data was already
there and the pipeline already worked, so this looked like a configuration change.

It was not, and the reason is worth writing down, because the bug class is everywhere and silent:
**an analysis full of hardcoded dates does not break when the window moves. It changes meaning.**

## The bug class

Scattered through the code were filters like:

```sql
WHERE day >= DATE '2026-08-01'      -- "the latest month"
```

While the data ended in August, that clause meant *August*. The table beneath it was captioned
"August", and both were true. When a new month landed, the identical clause came to mean *August
and September pooled* — two months of data under a caption that still said August. Nothing raised
an error. Nothing looked wrong. The table simply answered a different question from the one its
title claimed.

The same thing happened one level up, with a three-month pooled window written as
`day >= '2026-06-01'` and labelled "Jun–Aug". After the new month it silently pooled four.

And once in the other direction: a brand's label was renamed upstream across the whole history,
so a filter listing the old name returned an **empty** month rather than a wrong one — which is
the lucky case, because empty is visible.

## What I did

**Bound every window to constants derived from one list.** A single list of months is the only
place a date appears. Everything else — the latest month, the trailing three months, the first and
last month, the SQL date literals — is derived from it:

```python
MONTHS = ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09"]
MLAB   = dict(zip(MONTHS, ["May", "Jun", "Jul", "Aug", "Sep"]))
M0, M1 = MONTHS[0], MONTHS[-1]          # window endpoints
LAST   = M1 + "-01"                     # blocks that want the latest month only
P3     = MONTHS[-3:]                    # the trailing three-month window
```

Extending the analysis is now adding one entry to `MONTHS`.

**Derived the labels from the same constants as the filters.** This is the half that actually
prevents the bug. A caption written by hand can disagree with the filter above it; a caption built
from `MLAB[M1]` cannot. Where a table shows a month in a column header, a sort key or a chart
title, it reads from the same source as the `WHERE` clause.

**Made the window a guard, not a convention.** The data layer refuses to return rows outside the
declared window, so free-form SQL written later cannot accidentally pick up a partial day at the
edge or a start-up day at the beginning. A convention is something everyone follows until a
deadline; a guard is checked by the machine.

**Kept the already-quoted window instead of sliding it.** A three-month pooled window had been
published externally as "Jun–Aug". Sliding it forward silently would have made a quoted figure
unreproducible, so the new window was added *beside* the old one with both labelled explicitly. A
rolling window that means different months each time it runs is not comparable to itself.

**Separated the vendor's months from ours.** An external comparison covered fewer months than our
data. Extending our window silently extended the comparison and briefly scored a month the vendor
had never published. Now the comparison iterates over the vendor's months, our series runs to the
end of ours, and the gap is shown as an empty cell rather than filled in.

**Rebuilt the reference manifest first.** The verifier that checks the local data copy compares
row counts against a reference. A stale reference has no entry for the new days, so they are never
tested, and the verifier reports a clean copy for data it has not looked at. Rebuilding the
reference is step one of the refresh, and a day on disk with no reference entry is now reported as
an issue rather than passing. That check is packaged as
[mirror-verify](../tools/mirror-verify/).

## Outcome

The analysis extended cleanly, and more usefully, the next extension is one line. Several numbers
changed when the hardcoded anchors were replaced — which is the point: those tables had been
answering a question slightly different from their captions, and nobody could have seen it by
reading the output.

## What I would do differently

**Treat a date literal in analysis code as a lint error.** Not a style preference — a defect with
a delay fuse. If a date must appear, it belongs in one declared place with a comment saying what
it means.

**Re-read every caption after the window moves.** The tables were checked; the labels were not.
Half the problems above were labels telling the truth about a window that no longer existed.

**Write down which windows have been quoted outside.** A figure that has left the building cannot
be silently redefined, and three months later nobody remembers which ones those were.
