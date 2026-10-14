# -*- coding: utf-8 -*-
"""Verify a local Parquet mirror against a reference row count per day.

The job this comes from: a daily partitioned table was copied from a warehouse to
local disk so that analysis could run without hammering the source. The question
"is the copy complete?" has an obvious wrong answer and a boring right one.

**The wrong answer: compare file sizes.** Three real failure modes walk straight
past a size check:

* **a doubled day** - an export that was interrupted and re-run appends a second
  copy instead of replacing the first. The day gets bigger, not smaller. Nothing
  about a larger file looks like an error, and every ratio computed from that day
  is quietly diluted.
* **a half day** - the export stopped mid-write. The file is valid Parquet and
  opens fine; it simply holds 40% of the rows.
* **an orphan file** - a partition directory left behind by an earlier run with a
  different partition layout. It is readable, it is counted by a glob, and it
  belongs to no day you asked for.

**The right answer: count rows per day and compare to a reference**, then also
check that the set of days matches. That is all this module does, through DuckDB so
the counts come from Parquet metadata rather than from reading the data.

One more thing worth knowing, and the reason the reference must be rebuilt rather
than reused: a stale reference makes the check pass by construction. New days are
absent from it, so they are never row-count tested, and the verifier reports a clean
mirror for data it has not looked at. :func:`verify` treats a day that is missing
from the reference as a finding, not as a pass.

    python mirror_verify.py make-fixture ./demo          # synthetic mirror + faults
    python mirror_verify.py verify ./demo/mirror ./demo/reference.json
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from dataclasses import dataclass, field

try:
    import duckdb
except ImportError:                                      # pragma: no cover
    duckdb = None

__all__ = ["Issue", "Report", "count_by_day", "verify", "write_reference"]

#: Layout this module expects: <root>/<anything>/partition_day=YYYY-MM-DD/*.parquet
DAY_DIR = re.compile(r"partition_day=(\d{4}-\d{2}-\d{2})")


@dataclass
class Issue:
    kind: str          # missing | extra | mismatch | unreferenced | empty
    day: str
    detail: str

    def __str__(self) -> str:
        return "%-12s %-10s %s" % (self.kind, self.day, self.detail)


@dataclass
class Report:
    days_found: int = 0
    rows_found: int = 0
    days_expected: int = 0
    rows_expected: int = 0
    issues: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def __str__(self) -> str:
        head = ("mirror: %d day(s), %s row(s) | reference: %d day(s), %s row(s)"
                % (self.days_found, "{:,}".format(self.rows_found),
                   self.days_expected, "{:,}".format(self.rows_expected)))
        if self.ok:
            return head + "\nPASS - every day present and every row count equal"
        lines = [head, ""] + [str(i) for i in self.issues]
        lines.append("")
        lines.append("FAIL - %d issue(s)" % len(self.issues))
        return "\n".join(lines)


def _connect():
    if duckdb is None:
        raise RuntimeError("DuckDB is required: pip install duckdb")
    return duckdb.connect()


def count_by_day(root: str) -> dict[str, int]:
    """Rows per day in the mirror, read from Parquet metadata.

    The day comes from the directory name, not from a column: a half-written file
    can still carry the right value in its rows while the file itself is short, and
    an orphan directory carries no rows of the day it claims at all. Reading the
    layout and the counts separately is what lets the two disagree visibly.
    """
    files = glob.glob(os.path.join(root, "**", "*.parquet"), recursive=True)
    if not files:
        return {}
    con = _connect()
    out: dict[str, int] = {}
    for path in files:
        m = DAY_DIR.search(path.replace("\\", "/"))
        day = m.group(1) if m else "(no partition_day in path)"
        n = con.execute("SELECT COUNT(*) FROM read_parquet(?)", [path]).fetchone()[0]
        out[day] = out.get(day, 0) + n
    con.close()
    return out


def write_reference(counts: dict[str, int], path: str) -> None:
    """Store a reference manifest. Rebuild it from the source, never from the mirror."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"days": counts,
                   "total_rows": sum(counts.values()),
                   "note": "row counts taken from the SOURCE; rebuilding this from "
                           "the mirror would make any verification circular"},
                  fh, indent=2, sort_keys=True)


def verify(root: str, reference: str | dict) -> Report:
    """Compare the mirror with the reference and report every disagreement."""
    ref = reference if isinstance(reference, dict) else json.load(
        open(reference, encoding="utf-8"))
    expected: dict[str, int] = ref["days"] if "days" in ref else ref
    found = count_by_day(root)

    rep = Report(days_found=len(found), rows_found=sum(found.values()),
                 days_expected=len(expected), rows_expected=sum(expected.values()))

    for day in sorted(set(expected) - set(found)):
        rep.issues.append(Issue("missing", day, "in the reference, absent from the mirror"))

    for day in sorted(set(found) - set(expected)):
        # Not a pass. A day the reference does not know about has never been
        # row-count tested, which is exactly how a stale reference hides a bad day.
        rep.issues.append(Issue("unreferenced", day,
                                "%s row(s) on disk but no reference count - rebuild "
                                "the reference" % "{:,}".format(found[day])))

    for day in sorted(set(found) & set(expected)):
        got, want = found[day], expected[day]
        if got == want:
            continue
        if got == 0:
            rep.issues.append(Issue("empty", day, "file(s) present, zero rows"))
        else:
            ratio = got / want if want else float("inf")
            hint = ("looks doubled" if abs(ratio - 2) < .05 else
                    "looks partial (%.0f%% of expected)" % (100 * ratio) if ratio < .95 else
                    "off by %+d" % (got - want))
            rep.issues.append(Issue("mismatch", day, "%s vs %s expected - %s"
                                    % ("{:,}".format(got), "{:,}".format(want), hint)))
    return rep


# ---------------------------------------------------------------- demo fixture
def make_fixture(dest: str, days: int = 5, rows: int = 1000) -> str:
    """Build a small synthetic mirror that contains each failure mode on purpose.

    Day 1 is correct. Day 2 is doubled (a second file with the same rows). Day 3 is
    half written. Day 4 is fine. Day 5 exists on disk but not in the reference. One
    orphan directory is added with a layout nobody asked for.
    """
    import datetime as dt

    con = _connect()
    mirror = os.path.join(dest, "mirror", "table")
    os.makedirs(mirror, exist_ok=True)
    base = dt.date(2026, 1, 1)
    reference: dict[str, int] = {}

    def write(day: str, n: int, part: str = "part-0") -> None:
        d = os.path.join(mirror, "partition_day=%s" % day)
        os.makedirs(d, exist_ok=True)
        con.execute(
            "COPY (SELECT i AS id, 'row ' || i AS label FROM range(%d) t(i)) TO '%s' "
            "(FORMAT parquet)" % (n, os.path.join(d, part + ".parquet").replace("\\", "/")))

    for k in range(days):
        day = (base + dt.timedelta(days=k)).isoformat()
        write(day, rows)
        reference[day] = rows

    doubled = (base + dt.timedelta(days=1)).isoformat()
    write(doubled, rows, part="part-1")                       # interrupted re-run

    half = (base + dt.timedelta(days=2)).isoformat()
    os.remove(os.path.join(mirror, "partition_day=%s" % half, "part-0.parquet"))
    write(half, int(rows * 0.4))                              # stopped mid-write

    unreferenced = (base + dt.timedelta(days=days - 1)).isoformat()
    reference.pop(unreferenced)                               # stale reference

    orphan = os.path.join(mirror, "dt=2025-12-31")             # old partition layout
    os.makedirs(orphan, exist_ok=True)
    con.execute("COPY (SELECT 1 AS id, 'orphan' AS label) TO '%s' (FORMAT parquet)"
                % os.path.join(orphan, "part-0.parquet").replace("\\", "/"))

    con.close()
    ref_path = os.path.join(dest, "reference.json")
    write_reference(reference, ref_path)
    return ref_path


def main(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[1] == "make-fixture":
        ref = make_fixture(argv[2])
        print("fixture written; reference at", ref)
        return 0
    if len(argv) >= 4 and argv[1] == "verify":
        rep = verify(argv[2], argv[3])
        print(rep)
        return 0 if rep.ok else 1
    print(__doc__.strip().splitlines()[-2].strip())
    print(__doc__.strip().splitlines()[-1].strip())
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
