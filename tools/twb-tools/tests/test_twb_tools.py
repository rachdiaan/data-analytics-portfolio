# -*- coding: utf-8 -*-
"""Tests for twb_tools, run against fixtures/sample.twb.

    python -m pytest tools/twb-tools/tests -q
    python tools/twb-tools/tests/test_twb_tools.py     # works without pytest too
"""
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from twb_tools import (  # noqa: E402
    clone_worksheet, lint, quote_aliases, read_custom_sql, rewrite_custom_sql,
)

FIXTURE = os.path.join(os.path.dirname(HERE), "fixtures", "sample.twb")


def test_reads_both_storage_forms():
    """The whole point: a reader that misses one form misses half the estate."""
    qs = read_custom_sql(FIXTURE)
    forms = sorted(q.form for q in qs)
    assert forms == ["attribute", "element"], forms
    assert all("SELECT" in q.sql for q in qs)


def test_plain_table_is_not_custom_sql():
    assert not any(q.datasource == "Regions" for q in read_custom_sql(FIXTURE))


def test_rewrite_keeps_each_query_in_its_own_form():
    tree = ET.parse(FIXTURE)
    changed = rewrite_custom_sql(tree, lambda q: quote_aliases(q.sql))
    assert changed == 2, changed

    after = {q.datasource: q for q in read_custom_sql(tree)}
    el = after["Sales (element form)"]
    at = after["Targets (attribute form)"]
    # forms preserved
    assert el.form == "element" and at.form == "attribute"
    # aliases quoted in both
    assert 'AS "total_amount"' in el.sql and 'AS "n_orders"' in el.sql
    assert 'AS "target_amount"' in at.sql


def test_quote_aliases_is_idempotent():
    once = quote_aliases("SELECT a AS alpha, b AS beta FROM t")
    assert once == 'SELECT a AS "alpha", b AS "beta" FROM t', once
    assert quote_aliases(once) == once


def test_quote_aliases_never_touches_a_cast():
    """The regression that made the rule conservative: a type is not an alias."""
    out = quote_aliases("SELECT CAST(x AS INTEGER) AS x_int FROM t")
    assert "CAST(x AS INTEGER)" in out, out      # type left alone
    assert 'AS "x_int"' in out, out              # real alias still quoted


def test_quote_aliases_documented_false_negative():
    """An alias closed by `)` is skipped on purpose — see the note on _AS_ALIAS."""
    sql = "SELECT * FROM (SELECT SUM(a) AS total) s"
    assert quote_aliases(sql) == sql


def test_clone_remaps_column_references():
    """Renaming only name= is the trap; column= carries the name too."""
    tree = ET.parse(FIXTURE)
    clone = clone_worksheet(tree, "Revenue by region", "Revenue by region (copy)",
                            remap={"federated.sales1": "federated.sales2"})
    assert clone.get("name") == "Revenue by region (copy)"
    cols = [el.get("column") for el in clone.iter() if el.get("column")]
    assert cols and all("federated.sales2" in c for c in cols), cols
    # the source worksheet is untouched
    src = [w for w in tree.getroot().iter("worksheet")
           if w.get("name") == "Revenue by region"][0]
    src_cols = [el.get("column") for el in src.iter() if el.get("column")]
    assert all("federated.sales1" in c for c in src_cols), src_cols


def test_lint_catches_child_order_and_manifest():
    msgs = [str(f) for f in lint(FIXTURE)]
    joined = "\n".join(msgs)
    assert "children out of order" in joined, joined
    assert "WindowsPersistSimpleIdentifiers" in joined, joined
    assert "both storage forms" in joined, joined
    assert sum(1 for f in lint(FIXTURE) if f.level == "error") == 2


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok  %s" % fn.__name__)
    print("\n%d test(s) passed" % len(fns))
