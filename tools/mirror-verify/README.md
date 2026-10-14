# mirror-verify

Verify a local Parquet mirror against a reference row count per day.

Needs DuckDB (`pip install duckdb`). Counts come from Parquet metadata, so a five-month,
hundred-gigabyte mirror is checked in seconds rather than read end to end.

```bash
python mirror_verify.py make-fixture ./demo          # synthetic mirror with planted faults
python mirror_verify.py verify ./demo/mirror ./demo/reference.json
python tests/test_mirror_verify.py                   # 4 tests
```

## Why not just compare file sizes

Three failure modes walk straight past a size check, and all three happened:

| Failure | What it looks like on disk | What it does to the analysis |
|---|---|---|
| **A doubled day** | the day is *bigger* | an export interrupted and re-run appends instead of replacing. Every ratio for that day is diluted by rows counted twice. |
| **A half day** | a valid Parquet file that opens fine | the export stopped mid-write; the day holds 40% of its rows and still answers queries. |
| **An orphan file** | a readable file in a directory nobody asked for | left behind by an earlier partition layout. A glob counts it; it belongs to no day. |

A size check sees a big file, a valid file and a readable file, and reports success. Row counts
per day, compared against a reference taken from the source, see all three.

Worth knowing about interrupted exports: on some warehouses the server-side unload keeps running
after the client is killed, so "I cancelled it" and "it did not finish" are different statements.
That is how a day ends up doubled rather than missing.

## Why the reference must be rebuilt, not reused

A stale reference makes the check pass by construction. Days added since the reference was taken
are simply absent from it, so they are never row-count tested — and the verifier reports a clean
mirror for data it has not looked at. That is not hypothetical: it is how three days in a row
were reported as matching when nothing had compared them.

So `verify` treats a day on disk with no reference count as an **issue**, not as a pass:

```
mirror: 6 day(s), 5,401 row(s) | reference: 4 day(s), 4,000 row(s)

unreferenced (no partition_day in path) 1 row(s) on disk but no reference count - rebuild the reference
unreferenced 2026-01-05 1,000 row(s) on disk but no reference count - rebuild the reference
mismatch     2026-01-02 2,000 vs 1,000 expected - looks doubled
mismatch     2026-01-03 400 vs 1,000 expected - looks partial (40% of expected)

FAIL - 4 issue(s)
```

That output is `make-fixture` followed by `verify`: the fixture plants a doubled day, a half day,
a day missing from the reference and an orphan directory, and the run above finds each one. The
exit code is 1 when anything fails, so this drops into a build step.

## Layout it expects

```
<root>/<anything>/partition_day=YYYY-MM-DD/*.parquet
```

The day is read from the directory name rather than from a column, on purpose: a half-written
file still carries correct values in the rows it does have, and an orphan directory carries none
of the day it claims. Reading the layout and the counts from different places is what lets the
two disagree where you can see it.
