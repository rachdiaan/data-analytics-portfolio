# A template people actually maintain

**Role** Senior Analyst, Data Analytics & AI · **Context** a shared project-reporting workbook
with several owners · **Method only** — no project data, owners or dates.

## The question

Analytics teams report progress in a shared workbook: one sheet per initiative, a header with
dates and status, a task tracker, and a small Gantt. It is a template — conditional formatting
colours status cells, data validation restricts phase and priority to fixed lists, and a column
of formulas derives flags from what the owner types.

My part was to add two sheets for my initiatives and fill them from a script. Which sounds like
a formatting job, and turned out to be three lessons about writing into somebody else's file.

## What I did

**Studied the whole workbook before touching my two sheets.** Fifteen sheets with different
owners, and a template whose rules are not written down anywhere — which columns are inputs and
which are derived, which cells carry validation, how the Gantt's twelve-week span is computed
from the start date. I mapped that first, because a script that fills a derived column
overwrites a formula and nobody notices until the next refresh.

Two things fell out of the mapping. Only nine columns are inputs; the rest are formulas that must
be left alone. And the Gantt covers exactly twelve weeks from the Monday of the start date — so
an initiative longer than twelve weeks renders off the end of its own chart, which is a
constraint on how I phase the plan, not a bug to fix.

**Did not use the obvious library.** Writing with openpyxl removes conditional formatting and
data validation stored as extensions: the values land correctly and the template is gone. The
route that preserves them is Excel itself, copying the template sheet and filling cells through
COM. I verified it by counting, before and after — 7 conditional-formatting ranges and 5
validations per sheet, unchanged. That count is now the health check in
[excel-report-safe](../tools/excel-report-safe/).

**Found the dates were all wrong, in the same direction.** Writing a plain datetime through COM
shifted every value by the local UTC offset: a date landed on the previous day at 17:00. No
error. Seventy-four dates, every one a day early, which is the kind of consistency that reads as
correct. A target date was off by one and a derived "days remaining" came back negative, which is
what made me look.

The fix is to write the serial number Excel stores and to read it back with `.Value2` rather than
`.Value`, because `.Value` returns a date object and hides the shift. Both are in the tool, with
the arithmetic of the failure pinned by a test.

**Guarded against writing over someone's work.** The script refuses to fill a sheet that is not
empty. It fired immediately — the target sheet held a single leftover character — and that is
exactly the case it exists for: a template in a shared workbook is somebody's working file, and
failing is cheaper than overwriting.

**Reported other owners' defects instead of fixing them.** Mapping the workbook surfaced problems
on sheets that were not mine: an index entry pointing at a renamed sheet, a sheet missing from the
index, broken references, a status column disagreeing with its own completion flag. I listed them
for their owners and changed nothing. On a shared file, an unannounced helpful edit is
indistinguishable from an accident, and the owner is the one who gets asked about it.

**Found a gap in the shared template and did not patch it globally.** When every task is complete,
one derived cell renders a "next deadline" line with no date, because the formula has no guard for
an empty set. I handled it on my own sheet and reported it rather than editing the template other
owners depend on.

**Closed what was finished, honestly.** My first draft showed one initiative as in progress with
open items. Reviewed against what had actually been committed for the phase, the phase was
complete and the open items were follow-ups outside its scope. I moved them to an explicit
out-of-scope list with the reason each one sits there, rather than leaving a completed phase
looking unfinished — or, worse, calling it complete with no account of what was left.

## Outcome

Two sheets added with formatting and validation intact, dates verified cell by cell, the index
updated, and a defect list handed to the other owners. The reusable parts became a tool with ten
tests.

## What I would do differently

**Verify dates by reading back the raw value from the first write, not the hundredth.** I checked
a derived field, noticed it was negative, and then found seventy-four wrong dates. Reading one
cell back immediately would have caught it on the first one.

**Write the template's rules down and hand them to the owners.** I reverse-engineered which
columns are inputs; the next person will do it again. Half a page would end that permanently.

**Ask before assuming an initiative is still open.** The correction from "in progress" to
"complete" came from someone who knew the commitment, not from the data. A status column records
what someone typed, which is not the same as the state of the work.
