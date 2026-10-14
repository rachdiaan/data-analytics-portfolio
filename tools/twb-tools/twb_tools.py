# -*- coding: utf-8 -*-
"""Read, lint and rewrite Tableau workbook XML (`.twb`) without breaking it.

A `.twb` is XML, so editing one looks easy. It is not, and the failures are quiet:
the file still opens, and the damage shows up as a red sheet or a divide-by-zero
somewhere else. The four traps below cost me days each; every function here exists
because of one of them.

**1. Custom SQL is stored in two different forms.**
Tableau writes a Custom SQL relation either as element text::

    <relation name='Custom SQL Query' type='text'>SELECT a, b FROM t</relation>

or as an escaped attribute on a self-closing element::

    <relation name='Custom SQL Query' type='text' text='SELECT a, b FROM t' />

Both appear in the same estate, sometimes in the same workbook. Code that handles
only the first form sees "no Custom SQL" in half the workbooks and leaves their
queries untouched — which is how a sanitiser that was supposed to fix a division
ends up shipping the unfixed one.

**2. Renaming a worksheet instance is not renaming a worksheet.**
A cloned worksheet carries the source name in `column=` references as well as in
the obvious `name=` attributes. Rename only the instance and every sheet in the
workbook turns red, with no error message to explain why. :func:`clone_worksheet`
remaps both.

**3. The schema fixes the order of a worksheet's children.**
`<worksheet>` expects `<view>`, then `<style>`, then `<panes>`. Hand-built XML with
`<style>` before `<view>` is rejected on open, and the message names a GUID rather
than the element.

**4. `<simple-id>` requires a manifest flag.**
If any element carries `<simple-id>`, the workbook element must declare
`WindowsPersistSimpleIdentifiers`. Without it the workbook opens and then fails on
save, far away from the cause.

Reading and linting never modify the file. Rewriting goes through
:func:`rewrite_custom_sql`, which puts each query back in the form it was found in.

    python twb_tools.py lint path/to/workbook.twb
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Callable, Iterable

__all__ = [
    "CustomSQL", "Finding", "read_custom_sql", "rewrite_custom_sql",
    "quote_aliases", "clone_worksheet", "lint",
]

#: Tableau marks a Custom SQL relation with this `type`.
TEXT_RELATION = "text"

#: Order the schema expects for the children of <worksheet>. Extra children are
#: allowed; these three must appear in this relative order.
WORKSHEET_ORDER = ("view", "style", "panes")

#: Any element carrying <simple-id> obliges the workbook to declare this.
SIMPLE_ID_FLAG = "WindowsPersistSimpleIdentifiers"


@dataclass
class CustomSQL:
    """One Custom SQL relation, with the form it was stored in.

    `form` is ``"element"`` when the query sits in the element's text and
    ``"attribute"`` when it sits in ``@text``. Keep it: writing a query back in the
    other form changes the file more than intended and is a needless diff.
    """

    datasource: str
    name: str
    sql: str
    form: str
    element: ET.Element

    @property
    def is_attribute_form(self) -> bool:
        return self.form == "attribute"


@dataclass
class Finding:
    """A lint result. `level` is ``"error"`` when the workbook will not open."""

    level: str
    where: str
    message: str

    def __str__(self) -> str:
        return "%-5s %-34s %s" % (self.level.upper(), self.where, self.message)


def _datasource_name(ds: ET.Element) -> str:
    return ds.get("caption") or ds.get("name") or "(unnamed datasource)"


def read_custom_sql(source: str | ET.ElementTree) -> list[CustomSQL]:
    """Every Custom SQL relation in the workbook, in both storage forms.

    `source` is a path or an already-parsed tree. Nothing is modified.
    """
    tree = source if isinstance(source, ET.ElementTree) else ET.parse(source)
    out: list[CustomSQL] = []
    for ds in tree.getroot().iter("datasource"):
        dsn = _datasource_name(ds)
        for rel in ds.iter("relation"):
            if rel.get("type") != TEXT_RELATION:
                continue
            name = rel.get("name") or "(unnamed relation)"
            attr = rel.get("text")
            if attr is not None and attr.strip():
                out.append(CustomSQL(dsn, name, attr, "attribute", rel))
            elif rel.text and rel.text.strip():
                out.append(CustomSQL(dsn, name, rel.text, "element", rel))
    return out


def rewrite_custom_sql(tree: ET.ElementTree,
                       transform: Callable[[CustomSQL], str]) -> int:
    """Apply `transform` to every Custom SQL query, in place. Returns how many changed.

    Each query is written back in the form it was read in, so a workbook that mixes
    both forms keeps mixing them and the diff stays limited to the SQL itself.
    """
    changed = 0
    for q in read_custom_sql(tree):
        new = transform(q)
        if new is None or new == q.sql:
            continue
        if q.is_attribute_form:
            q.element.set("text", new)
        else:
            q.element.text = new
        changed += 1
    return changed


# Only the explicit `AS alias` form is matched, and only where the alias is followed
# by a comma, by FROM, or by the end of the query. Two deliberate limits:
#
#   * a closing parenthesis is NOT a terminator here, because `CAST(x AS INTEGER)`
#     looks exactly like an alias to a regex. Accepting `)` quoted the type name and
#     broke the query; refusing it only costs a missed alias in `(SELECT ... AS t)`,
#     which leaves correct SQL alone. Miss one rather than corrupt one.
#   * implicit aliases (`SELECT a total`) are left alone: finding those needs a real
#     parser, and a half-right regex on a production query is worse than no change.
_AS_ALIAS = re.compile(r"(?i)\bAS\s+([A-Za-z_][A-Za-z0-9_]*)(?=\s*(?:,|\bFROM\b|$))")

#: Belt and braces for the same trap: a type name is never an alias.
_SQL_TYPES = frozenset("""
    int integer bigint smallint tinyint decimal numeric float real double precision
    char varchar text string date time timestamp timestamptz datetime boolean bool
    json jsonb uuid bytea blob variant array struct
""".split())


def quote_aliases(sql: str) -> str:
    """Double-quote unquoted ``AS`` aliases.

    Why: some warehouses fold unquoted identifiers to lower case. A workbook built
    against a case-preserving source keeps referring to ``Revenue_Actual`` while the
    new source returns ``revenue_actual``; the field goes missing and any calculation
    dividing by it fails rather than reporting zero rows. Quoting the aliases in the
    Custom SQL is the smallest fix that survives the move.

    Already-quoted aliases are left alone, so this is safe to run twice.
    """
    def repl(m):
        name = m.group(1)
        if name.lower() in _SQL_TYPES:          # CAST(x AS INTEGER) — a type, not an alias
            return m.group(0)
        return 'AS "%s"' % name

    return _AS_ALIAS.sub(repl, sql)


def clone_worksheet(tree: ET.ElementTree, src_name: str, new_name: str,
                    remap: dict[str, str] | None = None) -> ET.Element:
    """Copy a worksheet and rename it everywhere the name appears.

    `remap` optionally renames datasource instances inside the clone. The point of
    this function is the part that is easy to forget: a worksheet's name also appears
    in `column=` references, and renaming only `name=` leaves the clone pointing at
    fields it no longer owns — which Tableau shows as every sheet in red, not as an
    error on the sheet you touched.
    """
    import copy

    root = tree.getroot()
    sheets = root.find("worksheets")
    if sheets is None:
        raise ValueError("workbook has no <worksheets> element")
    src = next((w for w in sheets.findall("worksheet") if w.get("name") == src_name), None)
    if src is None:
        raise ValueError("no worksheet named %r" % src_name)

    clone = copy.deepcopy(src)
    clone.set("name", new_name)
    pairs = {src_name: new_name, **(remap or {})}
    for el in clone.iter():
        for attr in ("name", "datasource", "column", "caption", "field"):
            val = el.get(attr)
            if val is None:
                continue
            for old, new in pairs.items():
                if val == old:
                    el.set(attr, new)
                elif ("[%s]" % old) in val:          # e.g. [Orders].[Sales]
                    el.set(attr, val.replace("[%s]" % old, "[%s]" % new))
    sheets.append(clone)
    return clone


def _child_order_findings(ws: ET.Element) -> Iterable[Finding]:
    seen = [c.tag for c in ws if c.tag in WORKSHEET_ORDER]
    expected = [t for t in WORKSHEET_ORDER if t in seen]
    if seen != expected:
        yield Finding("error", "worksheet %r" % (ws.get("name") or "?"),
                      "children out of order: %s, expected %s"
                      % (" > ".join(seen), " > ".join(expected)))


def lint(source: str | ET.ElementTree) -> list[Finding]:
    """Check a workbook for the four failures this module exists for."""
    tree = source if isinstance(source, ET.ElementTree) else ET.parse(source)
    root = tree.getroot()
    found: list[Finding] = []

    for ws in root.iter("worksheet"):
        found.extend(_child_order_findings(ws))

    # The flag is declared as an empty element inside the format-change manifest,
    # not as an attribute on <workbook> — which is why grepping the header for it
    # finds nothing and the check looks like it passed.
    manifest = root.find("document-format-change-manifest")
    declared = manifest is not None and manifest.find(SIMPLE_ID_FLAG) is not None
    if any(True for _ in root.iter("simple-id")) and not declared:
        found.append(Finding("error", "<document-format-change-manifest>",
                             "a <simple-id> is present but %s is not declared; the "
                             "workbook opens and then fails on save" % SIMPLE_ID_FLAG))

    queries = read_custom_sql(tree)
    by_form = {"element": 0, "attribute": 0}
    for q in queries:
        by_form[q.form] += 1
        if quote_aliases(q.sql) != q.sql:
            found.append(Finding("warn", "%s / %s" % (q.datasource, q.name),
                                 "unquoted AS alias - folds to lower case on some "
                                 "warehouses; see quote_aliases()"))
    if by_form["element"] and by_form["attribute"]:
        found.append(Finding("info", "<datasource>",
                             "Custom SQL appears in both storage forms (%d element, "
                             "%d attribute) - handle both, or half of them go unedited"
                             % (by_form["element"], by_form["attribute"])))
    return found


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] != "lint":
        print(__doc__.strip().splitlines()[-1].strip())
        return 2
    results = lint(argv[2])
    for f in results:
        print(f)
    errors = sum(1 for f in results if f.level == "error")
    print("\n%d finding(s), %d error(s)" % (len(results), errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
