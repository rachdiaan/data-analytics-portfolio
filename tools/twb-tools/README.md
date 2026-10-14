# twb-tools

Read, lint and rewrite Tableau workbook XML (`.twb`) without silently breaking it.

A `.twb` is XML, so editing one looks like a solved problem. The failures are what make it
interesting: the file still opens, and the damage surfaces somewhere else — a sheet that turns
red, a calculation that divides by zero, a save that fails hours later. Each function here
exists because of one of those.

No dependencies beyond the standard library. Reading and linting never modify the file.

```bash
python twb_tools.py lint path/to/workbook.twb      # exits 1 if the workbook will not open
python tests/test_twb_tools.py                     # 8 tests, no pytest required
```

```python
from twb_tools import read_custom_sql, rewrite_custom_sql, quote_aliases

for q in read_custom_sql("workbook.twb"):
    print(q.datasource, q.name, q.form)            # 'element' or 'attribute'

import xml.etree.ElementTree as ET
tree = ET.parse("workbook.twb")
n = rewrite_custom_sql(tree, lambda q: quote_aliases(q.sql))
tree.write("workbook_fixed.twb", encoding="utf-8", xml_declaration=True)
```

## The four traps

**1. Custom SQL is stored in two different forms.** Tableau writes a Custom SQL relation
either as element text or as an escaped `text=` attribute on a self-closing element:

```xml
<relation name='Custom SQL Query' type='text'>SELECT a, b FROM t</relation>
<relation name='Custom SQL Query' type='text' text='SELECT a, b FROM t' />
```

Both forms turn up in the same estate, occasionally in the same workbook. Code that handles
only the first reports "no Custom SQL" for the others and leaves their queries untouched. That
is how a script written to repair a division across an estate ships the unrepaired half, and
the error you get back names a GUID rather than a workbook. `read_custom_sql` returns both and
records which form each came from; `rewrite_custom_sql` puts each one back the way it was found,
so the diff stays limited to the SQL.

**2. Renaming a worksheet instance is not renaming a worksheet.** The name also appears in
`column=` references. Rename only the `name=` attributes and *every* sheet in the workbook turns
red — not just the one you touched, and with no message pointing at the cause.
`clone_worksheet` remaps both, including bracketed references like `[Orders].[Sales]`.

**3. The schema fixes the order of a worksheet's children.** `<worksheet>` expects `<view>`,
then `<style>`, then `<panes>`. Hand-built XML in another order is rejected on open.

**4. `<simple-id>` needs a manifest flag.** If any element carries `<simple-id>`, the workbook
must declare `WindowsPersistSimpleIdentifiers` inside
`<document-format-change-manifest>` — an empty child element, not an attribute on `<workbook>`,
which is why searching the header for it finds nothing. Without it the workbook opens and then
fails on save.

## On `quote_aliases`

Some warehouses fold unquoted identifiers to lower case. A workbook built against a
case-preserving source keeps asking for `Revenue_Actual` while the new source returns
`revenue_actual`; the field goes missing, and a calculation dividing by it fails rather than
reporting zero rows. Quoting the aliases in the Custom SQL is the smallest change that survives
the move, and it is idempotent.

The rule is deliberately conservative, and the tests pin both halves of that choice:

- `CAST(x AS INTEGER)` looks exactly like an alias to a regex. An earlier version accepted a
  closing parenthesis as a terminator, quoted the type name, and broke the query. Now a `)` is
  not a terminator and a type-name list guards the same trap from the other side.
- The cost is a missed alias in `(SELECT SUM(a) AS total)`. That leaves correct SQL alone, which
  is the right direction to be wrong in: miss one rather than corrupt one.
- Implicit aliases (`SELECT a total`) are not touched at all. Finding those needs a real parser,
  and a half-right regex on a production query is worse than no change.

## Fixture

`fixtures/sample.twb` is hand-written and carries all four failures and nothing else — no real
data source, no connection details. `lint` on it reports 2 errors, 2 warnings and 1 note.
