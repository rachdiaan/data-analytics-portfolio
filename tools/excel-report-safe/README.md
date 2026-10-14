# excel-report-safe

Write to an Excel workbook without destroying what makes it a template.

```bash
python excel_safe.py health workbook.xlsx       # count CF ranges and validations per sheet
python tests/test_excel_safe.py                 # 10 tests, no Excel required
```

`health()` needs openpyxl. Writing needs Excel itself through pywin32 (`write_values`,
`copy_template_sheet`) — which is the entire point of the module.

## The two traps

**1. Writing with openpyxl removes conditional formatting and data validation.**

openpyxl reads the parts of the file it understands and writes back what it has.
Conditional formatting stored in the `x14` extension list, and data validations written that
way, are not among them. On load it warns that an extension "will be removed", which reads like
a cosmetic note. It is not: after the save, every value in the file is correct and the template
is gone. Status cells no longer colour; dropdowns no longer restrict what can be typed.

The workbook this comes from had **7 conditional-formatting ranges and 5 data validations per
template sheet**. After a round trip through an openpyxl save, both counts read 0.

The route that preserves them is Excel: copy the template sheet with `Worksheet.Copy` through
COM and fill the cells. `health()` is the canary either way — run it before and after a write,
and compare the numbers instead of trusting the absence of an error.

```python
from excel_safe import health
before = {h.sheet: (h.conditional_formats, h.validations) for h in health("wb.xlsx")}
# ... write ...
after = {h.sheet: (h.conditional_formats, h.validations) for h in health("wb.xlsx")}
assert after == before, "the write cost the template its formatting"
```

**2. pywin32 shifts a naive datetime by the local UTC offset.**

Writing `datetime(2026, 10, 13)` through COM can land as **12 October, 17:00**: the value is
treated as local time and converted to UTC. No error, no warning. A deadline moves a day
earlier and every formula reading it is off by one — and in the workbook this came from, **all
74 dates were wrong in the same direction**, which is exactly the kind of consistency that looks
like correct behaviour.

Two rules follow:

- **Write the serial, not the datetime.** `to_serial(date(2026, 10, 13))` is `46308.0`, and a
  number has no timezone to apply.
- **Verify with `.Value2`, not `.Value`.** `.Value` hands back a date object and hides the
  shift; `.Value2` returns the raw serial, so a difference of exactly 7/24 is visible.
  `write_values(..., verify=True)` does this and raises with the offset in the message.

## The overwrite guard

`write_values` refuses to write over a non-blank cell unless `allow_overwrite=True`. A template
is somebody's working file: failing is better than silently replacing a filled cell. In the
original job this guard fired on a sheet that looked empty but held a single leftover character
— which is the case it exists for.

## Tests

Ten tests, none of which need Excel installed:

- the serial arithmetic against anchors you can check by hand in a spreadsheet;
- a round trip across 60 years of dates;
- the −7 hour failure reproduced as arithmetic, showing why it lands on the previous day at 17:00;
- a fake COM sheet that applies the shift, to prove `verify` catches it;
- the overwrite guard, including whitespace-only cells counting as empty;
- `health()` against a workbook generated with two conditional formats and one validation.
