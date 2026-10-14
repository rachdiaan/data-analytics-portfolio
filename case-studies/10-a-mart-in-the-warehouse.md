# A mart in the warehouse, and the procedure that was already wrong

**Role** Senior Analyst, Data Analytics & AI · **Context** turning a local analysis into a
scheduled mart in the warehouse · **Method only** — no schema, table or procedure names, no data.

## The question

An analysis had settled: the aggregations were agreed, the definitions were stable, and people
wanted the numbers without asking me. That is the moment to move it from a laptop into the
warehouse — a set of tables, the procedures that build them, and views for the people consuming
them.

The interesting part is not the DDL. It is **how a mart goes wrong after it works**, because that
is the failure mode nobody plans for.

## What I did

**Split it into tables, builders and a consumption layer.** Aggregate tables at agreed grains;
one stored procedure per table, each idempotent for a given day so a re-run repairs rather than
duplicates; and views as the only thing anyone else reads, so a table can be reshaped without
breaking a dashboard. Roughly a dozen tables, a procedure each, and a view layer on top.

**Made every build step idempotent, and gave it a verification gate.** Each procedure deletes and
rebuilds the day it is loading, then checks the result: the row count for that day must equal the
count taken from the source, and the aggregates must sum back to it. A mismatch stops the build
rather than publishing a plausible number. This is the same discipline as
[mirror-verify](../tools/mirror-verify/): the analyst will be tired eventually, the gate will not.

**Set guard thresholds from the distribution, not from intuition.** The first version of the
data-quality guards fired constantly — they were comparing a day against the previous one and
flagging any movement past a round-number tolerance I had picked. On low-volume slices that is
noise, and a guard that cries wolf is worse than no guard because people learn to clear it
without reading. I replaced the thresholds with values taken from the observed spread, and
recorded them where they can be re-derived when volumes change.

A related mistake worth confessing: I once wrote the intended threshold into a comment before
running the measurement. The comment then stated a number the code did not use and nobody had
verified. Comments describing behaviour must be written after the thing behaves.

**Found the real failure: a deployed procedure carrying an old rule.** The business rule for
grouping brands changed. Scripts and notebooks were updated, results were re-checked, everything
agreed — and the mart kept producing the old grouping, because the *procedure already deployed in
the warehouse* still contained the previous rule. A scheduled load ran, and the corrected
grouping was overwritten by the stale one. From the outside this looks exactly like a mistake in
the new rule.

Two things came out of that. First, a deployed procedure is a build artefact and goes stale like
any other, so a rule change has to update the thing that runs on a schedule, not only the thing
in the repository. Second, the rule itself now lives in one place that both the local analysis and
the deployed procedure derive from, instead of being written twice and trusted to stay identical.

**Kept scheduling as the last step, deliberately.** The mart ran on demand, with green guards,
before anything was scheduled. A schedule turns a correct build into a recurring one and an
incorrect build into a recurring one as well.

## Outcome

A mart in the warehouse with per-day idempotent builders, verification gates that stop the build
on a mismatch, guard thresholds derived from the data, and a single definition of the business
rule shared by the local analysis and the deployed procedures.

## What I would do differently

**Treat deployed procedures as versioned artefacts from day one.** Something that records which
version of the rule is live, and compares it to the repository, would have cost an afternoon and
saved the whole stale-grouping incident.

**Derive guard thresholds in the same script that uses them.** Hardcoding a measured value is the
same bug as hardcoding a date (case study 06) — correct at the moment it is written, silently
wrong once volumes move.

**Write down who the views are for.** A consumption layer with no stated audience accumulates
columns for everyone and serves nobody, and it is much harder to remove a view than to add one.
