# -*- coding: utf-8 -*-
"""Write to an Excel workbook without destroying what makes it a template.

The job this comes from: a project-reporting workbook maintained by several owners.
Each sheet is a template - conditional formatting that colours status cells, data
validation that restricts phase and priority to a fixed list, formulas that read
the cells you fill in. The task was to add two sheets and fill them from a script.

Two traps, both silent, both expensive.

**1. Writing with openpyxl removes conditional formatting and data validation.**
openpyxl reads the parts of the file it understands and writes back what it has.
Conditional formatting stored in the `x14` extension list, and data validations
written that way, are not among them. The file still opens, the values are all
correct, and the template is gone: status cells no longer colour, dropdowns no
longer restrict. On load openpyxl warns about an extension that "will be removed",
which is easy to read as cosmetic. It is not.

The route that preserves both is Excel itself, through COM: copy the template sheet
with `Worksheet.Copy` and fill the cells. :func:`health` is the canary either way -
count the conditional-formatting ranges and validations before and after, and let
the numbers tell you rather than the warning.

**2. pywin32 shifts a naive datetime by the local UTC offset.**
Writing `datetime(2026, 10, 13)` through COM can land as *12 October, 17:00* - the
value is treated as local time and converted. No error, no warning; a deadline moves
a day earlier and every formula that reads it is quietly off by one. In a workbook
of 74 dates, every one was wrong in the same direction, which is exactly the kind of
consistency that looks like correct behaviour.

The fix is to hand Excel the number it stores internally - the serial - and to verify
with `.Value2`, which returns the raw serial, rather than `.Value`, which hands back
a date object and hides the shift.

    python excel_safe.py health workbook.xlsx
"""
from __future__ import annotations

import datetime as dt
import sys
from dataclasses import dataclass

__all__ = ["SheetHealth", "health", "to_serial", "from_serial", "write_values",
           "copy_template_sheet", "EXCEL_EPOCH"]

#: Excel's day zero on Windows. Serial 1 is 1900-01-01; the 1900 leap-year bug means
#: serials at or above 60 are one day further on than a naive count suggests, which is
#: why the offset below is 693594 rather than 693595.
EXCEL_EPOCH = dt.date(1899, 12, 30)


@dataclass
class SheetHealth:
    """What a template sheet must still have after you have written to it."""

    sheet: str
    conditional_formats: int
    validations: int
    max_row: int
    max_column: int

    def __str__(self) -> str:
        return ("%-28s cf=%-3d dv=%-3d  %dx%d"
                % (self.sheet, self.conditional_formats, self.validations,
                   self.max_row, self.max_column))


def health(path: str) -> list[SheetHealth]:
    """Count conditional-formatting ranges and data validations per sheet.

    Read-only, and openpyxl is enough for counting: the point is to run this before
    and after a write and compare. A template sheet in the workbook this came from
    carries 7 conditional-formatting ranges and 5 validations; after a round trip
    through an openpyxl save, both read 0 while every value is still correct.

    Note `read_only=False` on purpose. In read-only mode openpyxl trusts the stored
    dimension record, which this workbook overstates - sheets came back far larger
    than they are, and a bounds check based on it looks past the real data.
    """
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=False, data_only=False)
    out = []
    for ws in wb.worksheets:
        cf = sum(1 for _ in ws.conditional_formatting)
        dv = len(getattr(ws.data_validations, "dataValidation", []) or [])
        out.append(SheetHealth(ws.title, cf, dv, ws.max_row, ws.max_column))
    wb.close()
    return out


def to_serial(value: dt.date | dt.datetime) -> float:
    """A date as the serial number Excel stores, so no timezone can touch it."""
    if isinstance(value, dt.datetime):
        days = (value.date() - EXCEL_EPOCH).days
        frac = (value.hour * 3600 + value.minute * 60 + value.second) / 86400.0
        return days + frac
    return float((value - EXCEL_EPOCH).days)


def from_serial(serial: float) -> dt.datetime:
    """Inverse of :func:`to_serial`, for checking what a cell actually holds."""
    days = int(serial)
    rest = serial - days
    return (dt.datetime.combine(EXCEL_EPOCH, dt.time()) + dt.timedelta(days=days)
            + dt.timedelta(seconds=round(rest * 86400)))


def _is_blank(com_cell) -> bool:
    v = com_cell.Value2
    return v is None or (isinstance(v, str) and not v.strip())


def write_values(worksheet, values: dict[str, object],
                 allow_overwrite: bool = False, verify: bool = True) -> int:
    """Write ``{"B5": value}`` into a COM worksheet. Returns how many cells changed.

    `worksheet` is a pywin32 COM object, not an openpyxl sheet - the whole point is
    to let Excel do the writing so the template survives.

    Dates and datetimes go in as serials through ``.Value2``; everything else is
    written as-is. With `verify`, each date is read back through ``.Value2`` and
    compared to the serial that was sent, because ``.Value`` would hand back a date
    object and hide a shift of exactly the local UTC offset.

    Refuses to write over a non-blank cell unless `allow_overwrite`. A template is
    somebody's working file; silently overwriting a filled cell is worse than failing.
    """
    changed = 0
    for ref, value in values.items():
        cell = worksheet.Range(ref)
        if not allow_overwrite and not _is_blank(cell):
            raise ValueError("%s is not empty (holds %r); pass allow_overwrite=True "
                             "if that is intended" % (ref, cell.Value2))
        if isinstance(value, (dt.date, dt.datetime)):
            serial = to_serial(value)
            cell.Value2 = serial
            if verify:
                got = cell.Value2
                if not isinstance(got, float) or abs(got - serial) > 1e-6:
                    raise RuntimeError(
                        "%s: wrote serial %r, read back %r. A difference of about "
                        "%.2f hours is the local UTC offset being applied."
                        % (ref, serial, got,
                           abs((got - serial) * 24) if isinstance(got, float) else 0))
        else:
            cell.Value = value
        changed += 1
    return changed


def copy_template_sheet(workbook, template: str, new_name: str, after: str | None = None):
    """Duplicate a template sheet with its formatting intact, and rename the copy.

    Uses Excel's own `Worksheet.Copy`, which carries conditional formatting, data
    validation, column widths and formulas across. Rebuilding a sheet cell by cell
    from a library instead is where the template gets lost.
    """
    src = workbook.Worksheets(template)
    anchor = workbook.Worksheets(after) if after else workbook.Worksheets(workbook.Worksheets.Count)
    src.Copy(None, anchor)
    made = workbook.Worksheets(anchor.Index + 1)
    made.Name = new_name
    return made


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] != "health":
        print("usage: python excel_safe.py health <workbook.xlsx>")
        return 2
    rows = health(argv[2])
    for r in rows:
        print(r)
    print("\n%d sheet(s). Run this before and after a write: cf and dv must not drop."
          % len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
