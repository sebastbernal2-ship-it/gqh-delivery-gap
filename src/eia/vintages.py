"""Promised against realized generator delivery, from monthly inventory vintages.

Each monthly file is a vintage: what the inventory said at that date. Reading two vintages together
gives the two objects this study needs.

- **A revision**: the promised operation month for the same generator moved between two vintages.
- **A realization**: the generator appears in the operating sheet in a later vintage, carrying the month
  it actually ran, which can be compared with the last promise.

Availability is the conservative rule we can defend: a file named `<month>_generator<year>.xlsx` is
treated as public at the **end** of that month. The exact publication day is not claimed, so nobody can
say this study used a number before it existed.

Two honesty rules carried from the filings audit:

1. **A moved promise is not an economic event.** It is a change in a published schedule. Whether it moves
   cash is a separate, later question, and the field is reported per generator, never pooled.
2. **Months stay months.** A promised month is stored as year and month, never as a fabricated day.
"""
from __future__ import annotations

import calendar
import datetime as dt
import re
from dataclasses import dataclass, asdict
from pathlib import Path

import requests

from eia.xlsx import find_header, read_sheets

BASE = "https://www.eia.gov/electricity/data/eia860m"
CACHE = Path(__file__).resolve().parents[2] / "results" / "eia-cache"
SHEETS = ("Planned", "Operating", "Canceled or Postponed")
USER_AGENT = "gqh-delivery-gap research research@example.com"

# Column names, by the header the files actually carry.
COLUMNS = {
    "entity_id": "Entity ID",
    "entity_name": "Entity Name",
    "plant_id": "Plant ID",
    "plant_name": "Plant Name",
    "state": "Plant State",
    "sector": "Sector",
    "generator_id": "Generator ID",
    "technology": "Technology",
    "capacity_mw": "Nameplate Capacity (MW)",
    "status": "Status",
}


def availability(date: dt.date) -> dt.date:
    """The last day of the vintage month: the earliest moment the whole file could have been public."""
    return dt.date(date.year, date.month, calendar.monthrange(date.year, date.month)[1])


def vintage_name(year: int, month: int) -> str:
    return f"{calendar.month_name[month].lower()}_generator{year}.xlsx"


def vintage_url(year: int, month: int) -> str:
    """Current files live at the root, older ones in the archive. Both are candidates."""
    return f"{BASE}/archive/xls/{vintage_name(year, month)}"


def fetch_vintage(year: int, month: int, session=None, cache: Path | None = None) -> Path:
    """Download a vintage once. The cache is the whole rate-limit story: these files are not small."""
    cache = cache if cache is not None else CACHE
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / vintage_name(year, month)
    if target.exists() and target.stat().st_size > 1_000_000:
        return target
    session = session or requests.Session()
    headers = {"User-Agent": USER_AGENT}
    for url in (f"{BASE}/xls/{vintage_name(year, month)}",
                vintage_url(year, month)):
        response = session.get(url, headers=headers, timeout=180)
        if response.status_code == 200 and response.content[:2] == b"PK":
            target.write_bytes(response.content)
            return target
    raise RuntimeError(f"no vintage file served for {year}-{month:02d}")


def _month(value) -> int | None:
    text = str(value or "").strip()
    if text.isdigit() and 1 <= int(text) <= 12:
        return int(text)
    for index, name in enumerate(calendar.month_name):
        if index and text.lower().startswith(name[:3].lower()):
            return index
    return None


def _year(value) -> int | None:
    text = str(value or "").strip()
    return int(float(text)) if re.fullmatch(r"\d{4}(\.0)?", text) else None


def _statement(month, year) -> str:
    """A promised month as a sortable key, never as a fabricated day."""
    month_i, year_i = _month(month), _year(year)
    if month_i is None or year_i is None:
        return ""
    return f"{year_i:04d}-{month_i:02d}"


@dataclass(frozen=True)
class Generator:
    """One generator as one vintage describes it."""

    vintage: str
    available_from: str
    sheet: str
    plant_id: str
    generator_id: str
    entity_name: str
    plant_name: str
    state: str
    sector: str
    technology: str
    capacity_mw: str
    statement: str          # the promised month, for a planned generator
    realized: str           # the month it actually ran, for an operating generator
    status: str

    @property
    def key(self) -> tuple[str, str]:
        return (self.plant_id, self.generator_id)

    def as_dict(self) -> dict:
        return asdict(self)


def cell(row: list[str], header: list[str], column: str) -> str:
    """A named cell, or empty. Column positions move between vintages, so never index by number."""
    try:
        position = header.index(column)
    except ValueError:
        return ""
    return row[position] if position < len(row) else ""


def _values(row: list[str], header: list[str]) -> dict[str, str]:
    index = {name: i for i, name in enumerate(header)}
    return {field: (row[index[column]] if column in index and index[column] < len(row) else "")
            for field, column in COLUMNS.items()}


def read_vintage(path, year: int, month: int) -> dict[str, list[Generator]]:
    """Every generator in one vintage, grouped by sheet."""
    stamp = f"{year:04d}-{month:02d}"
    available = availability(dt.date(year, month, 1)).isoformat()
    sheets = read_sheets(path, SHEETS)
    out: dict[str, list[Generator]] = {}
    for sheet_name, sheet in sheets.items():
        header = sheet[find_header(sheet)]
        rows = sheet[find_header(sheet) + 1:]
        planned = sheet_name == "Planned"
        generators: list[Generator] = []
        for row in rows:
            values = _values(row, header)
            plant_id = values["plant_id"].strip()
            generator_id = values["generator_id"].strip()
            if not plant_id or not generator_id:
                continue
            if planned:
                statement = _statement(cell(row, header, "Planned Operation Month"),
                                       cell(row, header, "Planned Operation Year"))
                realized = ""
            else:
                statement = ""
                realized = _statement(cell(row, header, "Operating Month"),
                                      cell(row, header, "Operating Year"))
            generators.append(Generator(
                vintage=stamp, available_from=available, sheet=sheet_name,
                plant_id=plant_id, generator_id=generator_id,
                entity_name=values["entity_name"].strip(), plant_name=values["plant_name"].strip(),
                state=values["state"].strip(), sector=values["sector"].strip(),
                technology=values["technology"].strip(), capacity_mw=values["capacity_mw"].strip(),
                statement=statement, realized=realized, status=values["status"].strip()))
        out[sheet_name] = generators
    return out


def promised(vintages: dict[str, list[Generator]]) -> dict[tuple[str, str], Generator]:
    return {g.key: g for g in vintages.get("Planned", [])}


def operating(vintages: dict[str, list[Generator]]) -> dict[tuple[str, str], Generator]:
    return {g.key: g for g in vintages.get("Operating", [])}


def cancelled(vintages: dict[str, list[Generator]]) -> set[tuple[str, str]]:
    return {g.key for g in vintages.get("Canceled or Postponed", [])}


def months_between(earlier: str, later: str) -> int | None:
    """Whole months from one year-month to another. Positive means later."""
    if not earlier or not later:
        return None
    try:
        y1, m1 = (int(part) for part in earlier.split("-"))
        y2, m2 = (int(part) for part in later.split("-"))
    except ValueError:
        return None
    return (y2 * 12 + m2) - (y1 * 12 + m1)


def revisions(before: dict[str, list[Generator]],
              after: dict[str, list[Generator]]) -> list[dict]:
    """Promises that moved between two vintages, or that left the planned sheet entirely."""
    old, new = promised(before), promised(after)
    gone = cancelled(after)
    out: list[dict] = []
    for key, earlier in old.items():
        later = new.get(key)
        if later is None:
            out.append({
                "plant_id": key[0], "generator_id": key[1],
                "entity_name": earlier.entity_name, "plant_name": earlier.plant_name,
                "state": earlier.state, "technology": earlier.technology,
                "capacity_mw": earlier.capacity_mw,
                "promised_before": earlier.statement, "promised_after": "",
                "revision_months": None,
                "change": "cancelled or postponed" if key in gone else "left the planned sheet",
                "available_before": earlier.available_from,
                "available_after": after["Planned"][0].available_from if after.get("Planned") else "",
            })
            continue
        shift = months_between(earlier.statement, later.statement)
        if shift is None or shift == 0:
            continue
        out.append({
            "plant_id": key[0], "generator_id": key[1],
            "entity_name": later.entity_name, "plant_name": later.plant_name,
            "state": later.state, "technology": later.technology,
            "capacity_mw": later.capacity_mw,
            "promised_before": earlier.statement, "promised_after": later.statement,
            "revision_months": shift,
            "change": "slipped" if shift > 0 else "pulled forward",
            "available_before": earlier.available_from,
            "available_after": later.available_from,
        })
    return out


def realizations(promised_last: dict[tuple[str, str], Generator],
                 running: dict[tuple[str, str], Generator]) -> list[dict]:
    """Generators that started running, against the promise recorded in the earlier vintage."""
    out: list[dict] = []
    for key, earlier in promised_last.items():
        promise = earlier.statement
        actual = running.get(key)
        if actual is None or not actual.realized:
            continue
        out.append({
            "plant_id": key[0], "generator_id": key[1],
            "entity_name": actual.entity_name, "plant_name": actual.plant_name,
            "state": actual.state, "technology": actual.technology,
            "capacity_mw": actual.capacity_mw,
            "promised_first": promise, "realized": actual.realized,
            "late_months": months_between(promise, actual.realized),
            "available_from": actual.available_from,
        })
    return out
