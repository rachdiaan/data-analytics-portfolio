# -*- coding: utf-8 -*-
"""Build an analysis notebook from a script, so it can be extended without editing cells.

The job this comes from: a monthly analysis of a large daily dataset. Nineteen
sections, a hundred-plus cells, a dozen charts, and every month a new month of data
to fold in. Maintained as a notebook, that work has two problems that have nothing
to do with analysis:

**Prose and code live in the same file.** Rewriting a finding means opening a
notebook and editing a markdown cell next to its chart. Reviewing a change means
diffing JSON. Here the narrative lives in its own module keyed by marker, and the
generator substitutes it - so the text can be rewritten and the notebook rebuilt
without touching a single code cell.

**A date written into a cell is a bug with a delay fuse.** `day >= '2026-08-01'`
means "the latest month" right up until a new month lands, at which point the same
line means two months pooled, under a caption that still says August. Nothing
errors. The table simply stops answering the question its title claims. So the
window lives in one list, and every endpoint, filter and label is derived from it:
extending the analysis is adding one entry.

:func:`lint_dates` is the check that keeps it that way - it flags a date literal in
any generated code cell, which is how the rule survives the next deadline.

    python nbgen.py demo out.ipynb
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from dataclasses import dataclass, field

__all__ = ["Window", "Notebook", "lint_dates", "DateLiteral"]

_DATE_LITERAL = re.compile(r"""['"](\d{4}-\d{2}-\d{2})['"]|\bDATE\s*['"](\d{4}-\d{2})""")
_MARKER = re.compile(r"<!--\s*([A-Z0-9_]+)\s*-->")


@dataclass(frozen=True)
class Window:
    """The analysis window, as the single source every date comes from.

    Give it the months it covers. Everything else - endpoints, labels, SQL dates,
    the trailing sub-window - is derived, so there is exactly one line to edit when
    the data grows and no caption can drift out of step with its filter.

    >>> w = Window(["2026-05", "2026-06", "2026-07", "2026-08", "2026-09"])
    >>> w.last, w.last_label, w.last_sql
    ('2026-09', 'Sep', '2026-09-01')
    >>> w.trailing(3).label
    'Jul-Sep'
    >>> w.delta_label
    'May->Sep'
    """

    months: tuple[str, ...]
    labels: tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "months", tuple(self.months))
        if not self.months:
            raise ValueError("a window needs at least one month")
        if not self.labels:
            object.__setattr__(self, "labels", tuple(
                dt.date.fromisoformat(m + "-01").strftime("%b") for m in self.months))
        if len(self.labels) != len(self.months):
            raise ValueError("labels and months must line up")

    # --- endpoints -------------------------------------------------------------
    @property
    def first(self) -> str:
        return self.months[0]

    @property
    def last(self) -> str:
        return self.months[-1]

    @property
    def first_label(self) -> str:
        return self.labels[0]

    @property
    def last_label(self) -> str:
        return self.labels[-1]

    @property
    def last_sql(self) -> str:
        """First day of the last month, for a `>= DATE '...'` filter."""
        return self.last + "-01"

    @property
    def label(self) -> str:
        return "%s-%s" % (self.first_label, self.last_label)

    @property
    def delta_label(self) -> str:
        """Caption for a change across the window, derived so it cannot lie."""
        return "%s->%s" % (self.first_label, self.last_label)

    def labelled(self) -> dict[str, str]:
        return dict(zip(self.months, self.labels))

    # --- sub-windows -----------------------------------------------------------
    def trailing(self, n: int) -> "Window":
        """The last `n` months, as a Window of its own.

        Pooled blocks that need volume use this instead of naming months. It moves
        with the data, which is the entire point: a window written by hand stays
        still while its caption keeps claiming otherwise.
        """
        if n < 1 or n > len(self.months):
            raise ValueError("cannot take %d of %d months" % (n, len(self.months)))
        return Window(self.months[-n:], self.labels[-n:])

    def sql_between(self, column: str = "day") -> str:
        return ("%s BETWEEN DATE '%s-01' AND (DATE '%s-01' + INTERVAL 1 MONTH "
                "- INTERVAL 1 DAY)" % (column, self.first, self.last))


@dataclass
class DateLiteral:
    cell: int
    line: int
    text: str

    def __str__(self) -> str:
        return "cell %d line %d: %s" % (self.cell, self.line, self.text.strip())


@dataclass
class Notebook:
    """Cells plus a narrative, assembled into a notebook.

    Markdown cells may carry `<!-- NAME -->` markers. On :meth:`build` each marker is
    replaced by `narrative["NAME"]`, so prose is edited in one module and the
    notebook is regenerated rather than hand-patched.
    """

    window: Window
    narrative: dict[str, str] = field(default_factory=dict)
    cells: list[tuple[str, str]] = field(default_factory=list)

    def md(self, text: str) -> "Notebook":
        self.cells.append(("markdown", text.strip("\n")))
        return self

    def code(self, text: str) -> "Notebook":
        self.cells.append(("code", text.strip("\n")))
        return self

    def preamble(self) -> "Notebook":
        """A code cell that puts the window in the notebook as constants.

        Everything downstream reads these names. No cell writes a date.
        """
        w = self.window
        return self.code(
            "MONTHS = %r\n"
            "LABEL = %r\n"
            "M0, M1 = MONTHS[0], MONTHS[-1]\n"
            "MLAB = dict(zip(MONTHS, LABEL))\n"
            "LAST, LAST_LABEL = M1 + '-01', MLAB[M1]\n"
            "P3 = MONTHS[-3:]\n"
            "P3_LABEL = '%s'\n"
            "DELTA_LABEL = '%s'"
            % (list(w.months), list(w.labels),
               w.trailing(min(3, len(w.months))).label, w.delta_label))

    def _render(self, kind: str, text: str) -> str:
        if kind != "markdown":
            return text
        return _MARKER.sub(
            lambda m: self.narrative.get(m.group(1), m.group(0)), text)

    def missing_markers(self) -> list[str]:
        """Markers with no narrative. Better to list them than to ship `<!-- X -->`."""
        out = []
        for kind, text in self.cells:
            if kind == "markdown":
                out += [m for m in _MARKER.findall(text) if m not in self.narrative]
        return out

    def build(self) -> dict:
        cells = []
        for kind, text in self.cells:
            cell = {"cell_type": kind, "metadata": {},
                    "source": self._render(kind, text).splitlines(keepends=True)}
            if kind == "code":
                cell["outputs"] = []
                cell["execution_count"] = None
            cells.append(cell)
        return {"cells": cells, "nbformat": 4, "nbformat_minor": 5,
                "metadata": {"kernelspec": {"name": "python3",
                                            "display_name": "Python 3",
                                            "language": "python"},
                             "language_info": {"name": "python"}}}

    def write(self, path: str) -> str:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.build(), fh, indent=1, ensure_ascii=False)
        return path


def lint_dates(nb: dict | Notebook, allow: tuple[str, ...] = ()) -> list[DateLiteral]:
    """Flag date literals in code cells.

    The preamble is allowed to carry the window; nothing else is. `allow` lists
    literals that are genuinely fixed points - the start of an outage, a regulatory
    cut-off - and those belong in one declared place with a comment, not scattered
    through filters.
    """
    doc = nb.build() if isinstance(nb, Notebook) else nb
    out: list[DateLiteral] = []
    for i, cell in enumerate(doc["cells"]):
        if cell["cell_type"] != "code":
            continue
        src = "".join(cell["source"])
        if "MONTHS = " in src:                 # the preamble: the one declared place
            continue
        for j, line in enumerate(src.splitlines(), start=1):
            for m in _DATE_LITERAL.finditer(line):
                hit = m.group(1) or m.group(2)
                if hit not in allow:
                    out.append(DateLiteral(i, j, line))
    return out


# ------------------------------------------------------------------------- demo
NARRATIVE = {
    "FINDING": "**[measured]** Volume fell in the last month of the window, and the "
               "fall is larger than the month-to-month spread of the four before it.\n\n"
               "**[inferred]** A change in collection rather than in the market. What "
               "would disprove it: an unaffected control series falling by as much.",
}


def demo(path: str) -> str:
    w = Window(["2026-05", "2026-06", "2026-07", "2026-08", "2026-09"])
    nb = Notebook(window=w, narrative=NARRATIVE)
    nb.md("# Monthly analysis - %s\n\nWindow: **%s**, five complete months."
          % (w.label, w.label))
    nb.preamble()
    nb.md("## 1. Coverage\n\nEvery month, with its row count, before anything else.")
    nb.code("import pandas as pd\n"
            "cov = pd.DataFrame({'month': MONTHS, 'label': LABEL})\n"
            "cov")
    nb.md("## 2. The last month against the window\n\n<!-- FINDING -->")
    nb.code("# the filter and its caption come from the same place\n"
            "sql = f\"SELECT COUNT(*) FROM t WHERE day >= DATE '{LAST}'\"\n"
            "title = f'Volume, {LAST_LABEL} ({DELTA_LABEL} on the window)'\n"
            "print(sql)\nprint(title)")
    return nb.write(path)


def main(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[1] == "demo":
        out = demo(argv[2])
        with open(out, encoding="utf-8") as fh:
            doc = json.load(fh)
        print("written %s: %d cells" % (out, len(doc["cells"])))
        bad = lint_dates(doc)
        print("date literals outside the preamble: %d" % len(bad))
        for b in bad:
            print("  " + str(b))
        return 0
    print("usage: python nbgen.py demo out.ipynb")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
