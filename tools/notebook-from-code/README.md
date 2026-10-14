# notebook-from-code

Build an analysis notebook from a script, so it can be extended without editing cells.

No dependencies beyond the standard library.

```bash
python nbgen.py demo out.ipynb                  # builds a 6-cell notebook, then lints it
python tests/test_nbgen.py                      # 13 tests
```

## Why not just maintain the notebook

The analysis this comes from runs monthly over a large daily dataset: nineteen sections, a
hundred-plus cells, twenty charts, and a new month of data every month. Kept as a notebook, that
work has two problems that have nothing to do with analysis.

**Prose and code share a file.** Rewriting a finding means editing a markdown cell wedged between
a chart and the code that made it, and reviewing the change means reading a JSON diff. Here the
narrative lives in its own module keyed by marker:

```python
nb.md("## 11. Regions\n\n<!-- REGION -->")       # the cell says where prose goes
NARRATIVE = {"REGION": "**[measured]** ..."}     # the prose lives on its own
```

Text gets rewritten, the notebook gets regenerated, and no code cell is touched. `missing_markers()`
lists markers with no narrative, so an unfilled section is reported rather than shipped as a
literal `<!-- REGION -->`.

**A date written into a cell is a bug with a delay fuse.** This is the expensive one.

```sql
WHERE day >= DATE '2026-08-01'      -- "the latest month"
```

While the data ended in August that clause meant *August*, and the caption above it said August.
Both were true. When a new month landed, the identical line came to mean *August and September
pooled* — under a caption that still said August. Nothing errored. The table simply stopped
answering the question its title claimed, and the only way to notice was to re-read every caption.

So the window lives in one place and everything is derived from it:

```python
w = Window(["2026-05", "2026-06", "2026-07", "2026-08", "2026-09"])
w.last, w.last_label, w.last_sql      # '2026-09', 'Sep', '2026-09-01'
w.trailing(3).label                   # 'Jul-Sep'   - pooled blocks, moves with the data
w.delta_label                         # 'May->Sep'  - captions cannot drift from filters
```

Extending the analysis is adding `"2026-10"` to that list. The test that matters is
`test_adding_a_month_moves_every_label`: one edit, and endpoints, labels, SQL dates and the
trailing sub-window all follow.

## The lint

`lint_dates()` flags a date literal in any generated code cell. The preamble — the one declared
place the window lives — is exempt, and `allow` covers genuine fixed points:

```python
lint_dates(nb)                          # flags "2026-08-13"
lint_dates(nb, allow=("2026-08-13",))   # the start of a known outage, declared on purpose
```

A fixed date is allowed to exist. It is not allowed to be scattered, undeclared and uncommented
through filters, because that is the state the whole module exists to prevent.

Point it at a notebook you did not generate and it works the same way — it reads a notebook
document, so it drops into a build step over an existing `.ipynb`.

## Tests

Thirteen tests, covering the window arithmetic (including that a `Window` is frozen, so widening
one cannot mutate another), label derivation, marker substitution in markdown but not in code,
missing markers being reported, the lint's exemptions, and the demo notebook being valid
nbformat that lints clean.
