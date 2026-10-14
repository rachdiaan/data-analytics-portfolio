# Migrating a BI estate between warehouses

**Role** Senior Analyst, Data Analytics & AI · **Context** moving a Tableau estate from one cloud
warehouse to another · **Method only** — no server names, connection details or workbook contents.

## The question

A set of production dashboards read from one cloud warehouse; the organisation moved the data to
another. Every workbook had to point at the new source and keep showing the same numbers. The
interesting part is not the repointing, which is mechanical. It is: **how do you know a migrated
dashboard is still correct?**

"It opens and the charts render" is not an answer. A dashboard can render beautifully with a
field silently missing.

## What I did

**Inventoried before touching anything.** Which workbooks are actually used, which data sources
they share, which carry Custom SQL versus plain table relations, and which have extracts rather
than live connections. The inventory is also the test plan: you cannot validate what you have not
listed, and in an estate assembled over years the list is never the one people remember.

**Validated per view, not per workbook.** A workbook is a container; correctness lives in the
views. For each view I compared row counts and the key measures before and after. A workbook-level
check passes when one of its eight sheets is wrong.

**Hit the identifier-folding rule, and generalised the fix.** The new warehouse folds unquoted
identifiers to lower case. Workbooks built against a case-preserving source keep asking for
`Revenue_Actual` while the new source returns `revenue_actual`. The field does not error — it goes
*missing*, and any calculation dividing by it fails rather than reporting zero rows. The fix is to
quote the aliases inside the Custom SQL, which is small, idempotent, and survives the move. It is
packaged as `quote_aliases` in [twb-tools](../tools/twb-tools/).

**Hit the two storage forms, which is the one I would have missed.** Tableau stores a Custom SQL
query either as element text or as an escaped attribute on a self-closing element. My first pass
handled the element form, reported "no Custom SQL" for a large share of the estate, and left those
queries untouched — so the repair shipped for half the workbooks and the other half failed later,
with an error naming a GUID rather than a workbook. Handling both forms is a four-line change that
took a day to find. It is now the first thing `read_custom_sql` does, and the lint note exists
purely so nobody repeats it.

**Kept credentials and publishing out of the automation.** The scripts transform files on disk.
They do not embed credentials in workbooks or data sources, and they do not publish: pushing a
workbook to a server is a human action with a human's judgement about timing and audience. A
migration script that publishes on its own is a migration script that overwrites something during
a month-end close.

## Outcome

The estate migrated with per-view validation, and the two pitfalls above were turned into reusable
checks rather than tribal knowledge. The alias-quoting and dual-form handling are in
[twb-tools](../tools/twb-tools/) with tests, including a test that pins the deliberately
conservative behaviour of the alias rule.

## What I would do differently

**Write the validation harness before the first repoint.** I built comparisons as I went, which
meant the early workbooks got a weaker check than the late ones. The harness is the deliverable;
the repointing is a loop around it.

**Treat "field not found" as a build failure, not a warning.** The most dangerous migration
outcome is not an error — it is a dashboard that renders with one measure quietly absent. Any
check that can distinguish "zero rows" from "no such field" is worth more than ten eyeballed
screenshots.

**Record the schema contract, not just the fix.** The real lesson is not "quote aliases". It is
that the two warehouses disagree about identifier case, which will bite again in a different
place — a view name, a cast, a connector option. Writing down the rule beats writing down the
patch.
