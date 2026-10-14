# A monitoring dashboard from scratch

**Role** Senior Analyst, Data Analytics & AI · **Context** a finance operations process tracked in
spreadsheets, rebuilt as a modelled dashboard · **Method only** — no agreement data, counterparty
names or amounts.

## The question

A recurring compliance-and-monitoring process lived in spreadsheets maintained by hand: one file
per period, columns added as needs appeared, formulas pointing at other files. It worked, in the
sense that someone could always answer a question about it given an afternoon. The ask was a
dashboard — but the real ask, as usual, was **a single source that does not need an afternoon**.

Two weeks to go-live, with the business owner available for a few hours a week.

## What I did

**Spent the first days on the grain, not on charts.** Every argument in a project like this is
downstream of one decision: what does a row represent? Candidates were one row per agreement, one
row per agreement per reporting period, and one row per obligation per period. They are not
interchangeable — the second lets you show history and double-counts if someone filters wrongly;
the first cannot show history at all.

We settled on one row per agreement per reporting snapshot, with the snapshot date part of the
key. Writing that sentence down, and getting the owner to agree to it out loud, was the single
highest-value hour of the project. Everything after it is mechanics.

**Modelled it as a star schema.** Facts at the agreed grain; conformed dimensions for the
entities, the calendar and the status vocabulary. Not because star schemas are fashionable, but
because the questions were known to be sliced-and-diced ("by entity, by period, by status") and
that is exactly the shape a star answers without a join written fresh each time.

**Made the status vocabulary explicit.** The spreadsheets carried statuses as free text, so the
same state appeared in four spellings. A dimension with a fixed set of values, and a rule for
mapping legacy text onto it, turns a filter from an archaeology exercise into a click. This is
dull work that decides whether anyone trusts the numbers.

**Handled late-arriving data on purpose.** Source records get corrected after the fact. A model
that assumes append-only produces a dashboard that disagrees with itself across refreshes. The
snapshot-keyed grain absorbs corrections because a restated period is a new snapshot, not an
overwrite — and the previous reading stays visible, which is what an auditor asks for.

**Built the reminder layer last and small.** A derived flag for approaching deadlines, with the
thresholds taken from the owner's own working rules rather than invented. One flag the owner
recognises beats five the owner has to learn.

**Designed for the handover, not the demo.** The dashboard went out with a usage guide written for
the person who will open it on a Monday without me, including what each metric counts and what it
deliberately does not. No step in the refresh requires my laptop. Publishing stays a human action.

## Outcome

Live on schedule, replacing the spreadsheet as the reference for the process, with history
preserved rather than overwritten each period. The owner runs it; I am not in the loop.

## What I would do differently

**Get the grain agreed in writing on day one, with an example row.** We agreed it verbally and I
wrote it down later. In between, two charts were built on an assumption that quietly contradicted
it, and rebuilding them cost more than the conversation would have.

**Ship the data-quality page with version one, not after.** Row counts per period, records failing
each validation rule, and the freshness of the last load. Users forgive a gap they can see; they
do not forgive finding one themselves.

**Say no to one more column, earlier.** Every spreadsheet-to-dashboard migration arrives with
requests to carry over fields nobody has read in a year. Each one costs model complexity forever.
Asking "when did you last use this to make a decision?" removed a third of them, and should have
removed them before modelling rather than after.
