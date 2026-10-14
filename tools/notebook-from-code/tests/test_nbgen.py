# -*- coding: utf-8 -*-
"""Tests for nbgen. No dependencies beyond the standard library.

    python tools/notebook-from-code/tests/test_nbgen.py
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from nbgen import Notebook, Window, demo, lint_dates  # noqa: E402

W = Window(["2026-05", "2026-06", "2026-07", "2026-08", "2026-09"])


# ------------------------------------------------------------------------ window
def test_endpoints_and_labels_are_derived():
    assert (W.first, W.last) == ("2026-05", "2026-09")
    assert (W.first_label, W.last_label) == ("May", "Sep")
    assert W.last_sql == "2026-09-01"
    assert W.label == "May-Sep"
    assert W.delta_label == "May->Sep"


def test_adding_a_month_moves_every_label():
    """The property the whole design exists for: one edit, everything follows."""
    wider = Window(W.months + ("2026-10",))
    assert wider.last_label == "Oct"
    assert wider.last_sql == "2026-10-01"
    assert wider.label == "May-Oct"
    assert wider.delta_label == "May->Oct"
    assert wider.trailing(3).label == "Aug-Oct"
    # the old window is untouched - Window is frozen, so nothing shares state
    assert W.last_label == "Sep"


def test_trailing_window_moves_with_the_data():
    assert W.trailing(3).months == ("2026-07", "2026-08", "2026-09")
    assert W.trailing(3).label == "Jul-Sep"
    assert W.trailing(1).label == "Sep-Sep"


def test_trailing_rejects_an_impossible_window():
    for n in (0, 6, -1):
        try:
            W.trailing(n)
        except ValueError:
            pass
        else:
            raise AssertionError("trailing(%d) should not be allowed" % n)


def test_sql_between_covers_the_whole_window():
    sql = W.sql_between("partition_day")
    assert "partition_day BETWEEN DATE '2026-05-01'" in sql, sql
    assert "'2026-09-01'" in sql and "INTERVAL 1 MONTH" in sql, sql


def test_explicit_labels_are_kept():
    w = Window(["2026-01", "2026-02"], ["Jan '26", "Feb '26"])
    assert w.label == "Jan '26-Feb '26"


# --------------------------------------------------------------------- narrative
def test_marker_is_replaced_by_narrative():
    nb = Notebook(window=W, narrative={"FINDING": "the finding text"})
    nb.md("## Section\n\n<!-- FINDING -->")
    src = "".join(nb.build()["cells"][0]["source"])
    assert "the finding text" in src
    assert "<!-- FINDING -->" not in src


def test_missing_marker_is_reported_not_shipped_silently():
    nb = Notebook(window=W)
    nb.md("<!-- ABSENT -->")
    assert nb.missing_markers() == ["ABSENT"]
    # and it stays visible in the output rather than becoming an empty cell
    assert "<!-- ABSENT -->" in "".join(nb.build()["cells"][0]["source"])


def test_markers_are_only_substituted_in_markdown():
    nb = Notebook(window=W, narrative={"X": "prose"})
    nb.code("# <!-- X -->")
    assert "<!-- X -->" in "".join(nb.build()["cells"][0]["source"])


# -------------------------------------------------------------------------- lint
def test_lint_flags_a_hardcoded_date_in_a_code_cell():
    nb = Notebook(window=W)
    nb.preamble()
    nb.code("df = q(\"SELECT * FROM t WHERE day >= DATE '2026-08-01'\")")
    hits = lint_dates(nb)
    assert len(hits) == 1, hits
    assert "2026-08-01" in str(hits[0]), str(hits[0])


def test_lint_ignores_the_preamble_and_the_allow_list():
    nb = Notebook(window=W)
    nb.preamble()                                   # carries the window on purpose
    nb.code("OUTAGE_START = '2026-08-13'  # dated event, declared once")
    # flagged by default: a real fixed point still has to be declared deliberately
    assert len(lint_dates(nb)) == 1
    # and once it is on the allow list, it stops being noise
    assert lint_dates(nb, allow=("2026-08-13",)) == []


def test_lint_passes_a_notebook_built_from_the_window():
    nb = Notebook(window=W)
    nb.preamble()
    nb.code("sql = f\"SELECT 1 FROM t WHERE day >= DATE '{LAST}'\"")
    assert lint_dates(nb) == []


# -------------------------------------------------------------------------- demo
def test_demo_is_a_valid_notebook_and_lints_clean():
    path = os.path.join(tempfile.mkdtemp(prefix="nbgen_"), "demo.ipynb")
    demo(path)
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    assert doc["nbformat"] == 4
    assert len(doc["cells"]) == 6, len(doc["cells"])
    assert all(c["cell_type"] in ("markdown", "code") for c in doc["cells"])
    assert lint_dates(doc) == []
    # the narrative landed, the marker did not survive
    joined = "".join("".join(c["source"]) for c in doc["cells"])
    assert "[measured]" in joined and "<!-- FINDING -->" not in joined
    os.remove(path)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok  %s" % fn.__name__)
    print("\n%d test(s) passed" % len(fns))
