"""How much capacity each vintage promises, by the year it is promised for.

The project-level panel asks what happened to one generator. This asks something the whole market can
read: in a given month, how much capacity does the inventory promise for each future year? Comparing the
same promise across twelve months gives the aggregate revision, which is the tradable-looking object.

Definitions kept explicit:

- **Promise** means the value in the planned sheet, whatever status it carries (planned, under
  construction, regulatory approvals pending). Nothing is filtered by status, because filtering is a
  choice that would have to be justified later.
- **Capacity** is MW summed by promised operation year, ignoring generators with no year. The field is
  **net summer capacity**, because the earliest vintages carry no nameplate column at all. Using one field
  across the whole series matters: a revision spanning a change of field would be a measurement artefact
  rather than a change in the promise, so nameplate is kept only as a cross-check.
- **Availability** is the last day of the vintage month.
"""
from __future__ import annotations

import calendar
import datetime as dt
from pathlib import Path

from eia.vintages import cell, read_vintage
from eia.xlsx import find_header, read_sheet


# Column names drift between vintages, and the earliest files carry only the first of these.
CAPACITY_COLUMNS = ("Net Summer Capacity (MW)", "Nameplate Capacity (MW)")
YEAR_COLUMN = "Planned Operation Year"


def column_named(header: list[str], wanted: str) -> str:
    """The real header text for a wanted column, tolerating the line breaks early files carry."""
    for name in header:
        if not name:
            continue
        flat = " ".join(str(name).split())
        if flat.lower().startswith(wanted.lower()):
            return name
    return ""


def promised_capacity_by_year(path, year: int, month: int) -> dict[int, float]:
    """MW promised, keyed by promised operation year, from one vintage's planned sheet."""
    sheet = read_sheet(path, "Planned")
    header = sheet[find_header(sheet)]
    year_column = column_named(header, YEAR_COLUMN)
    capacity_column = next((column_named(header, candidate) for candidate in CAPACITY_COLUMNS
                            if column_named(header, candidate)), "")
    if not year_column or not capacity_column:
        return {}
    totals: dict[int, float] = {}
    for row in sheet[find_header(sheet) + 1:]:
        promised_year = cell(row, header, year_column) if year_column in header else ""
        if not promised_year:
            continue
        try:
            key = int(float(promised_year))
        except ValueError:
            continue
        if key < 1990 or key > 2100:
            continue
        try:
            megawatts = float(cell(row, header, capacity_column))
        except ValueError:
            continue
        totals[key] = totals.get(key, 0.0) + megawatts
    return totals


def availability(year: int, month: int) -> str:
    last = calendar.monthrange(year, month)[1]
    return dt.date(year, month, last).isoformat()


def months(start_year: int, start_month: int, end_year: int, end_month: int):
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        yield year, month
        month += 1
        if month == 13:
            year, month = year + 1, 1
