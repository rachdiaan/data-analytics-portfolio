# Revenue reconciliation across three systems

**Role** Senior Analyst, Data Analytics & AI · **Context** enterprise revenue operations at a
telecommunications operator · **Method only** — no customer data, table names or system
internals appear here.

## The question

Enterprise revenue passes through three systems: the CRM where a deal is agreed, the billing
platform that issues invoices, and the ledger that books the revenue. A monthly reconciliation
between them did not close, and had not closed for months, by an amount large enough that nobody
could sign off on the numbers downstream of it.

The standing explanation was "timing differences". That explanation has the shape of an answer
without being one: it predicts nothing. If it were timing, the gap would close when the next
period opened. It did not.

## What I did

**Stopped comparing totals.** Two totals that differ tell you only that they differ. I rebuilt
the comparison at row level — one row per agreement, per period, with the identifier that each
system uses for it — so that every unit of the gap had a name attached. A gap you can list is a
gap you can explain; a gap expressed as one number invites a story.

**Separated "unmatched" from "mismatched".** Those are different defects with different fixes.
Rows present on one side only point at a join or a filter; rows present on both sides with
different amounts point at a transformation. Mixing them in a single "variance" figure is how a
reconciliation stays open for months.

**Found two causes, not one.** This is the part worth generalising:

1. **A deduplication rule that destroyed the join key.** Upstream, a "keep the latest record per
   customer" step ranked rows and kept the first. Where the ranking tied, the surviving row was
   sometimes the one whose customer identifier was empty — so the record survived and its key did
   not. Those rows then matched nothing downstream and dropped out of the comparison entirely.
   They were not missing from the data; they were missing from the join, which looks the same in
   a total and nothing like it in a row list.

2. **Two columns that mean different things and are named almost the same.** One side of the
   comparison was summing an *actual* measure, the other an *all-inclusive* measure that also
   carried items not yet recognised. Both are legitimate columns. Comparing one to the other
   produces a difference that is perfectly stable, perfectly explainable, and entirely artificial.

**Proved it rather than asserted it.** The test was not "the gap got smaller". It was: correct
the two defects and the remaining difference should be the amount the finance team could already
account for, to the rupiah. It was. That is the difference between a hypothesis and a finding.

## Outcome

Restored integrity on **IDR 873 billion** of revenue data across **105,000+ production records**,
validated against executive P&L reporting; identified **IDR 11.3 billion** of concealed
corruption traced to a FIFO matching defect in the ETL within 30 days of joining; and closed an
**IDR 2.09 billion** monthly-recurring-charge gap across **13,000+ active accounts** by building
a bulk update pipeline rather than correcting rows by hand.

The automation around it — Python ETL plus the CRM platform's bulk API — reduced the manual part
of the monthly reconciliation by more than 90% and, more usefully, let non-technical owners run
their own corrections instead of queuing behind an analyst.

## What I would do differently

**Instrument the dedup step, don't just fix it.** The ranking defect was invisible because
nothing counted how many rows lost their key. A single assertion — "no surviving row may have an
empty join key" — would have caught it years earlier, and costs one line.

**Write the tie-break down.** Every "latest record per entity" rule has a tie somewhere. The
rule is only complete when it says what happens then, and the person who writes the rule is
rarely the person who discovers it was undefined.

**Name columns for what they contain, not for how they are used.** Two measures a letter apart
in name and a concept apart in meaning will eventually be compared to each other. The fix was
arithmetic; the cause was vocabulary.
