#!/usr/bin/env python3
"""Offline tests for the vintage reader and the delivery panel. No network, no real spreadsheet."""
from __future__ import annotations

import datetime as dt
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_delivery_panel import months_in_range, summarise  # noqa: E402
from eia.vintages import (  # noqa: E402
    availability, cell, months_between, read_vintage, realizations, revisions,
    vintage_name, vintage_url,
)
from eia.xlsx import find_header, read_sheet, read_sheets  # noqa: E402

failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


def column_name(index: int) -> str:
    letters, index = "", index + 1
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'


def write_xlsx(path: Path, sheets: dict[str, list[list[str]]], use_shared: set[str]) -> None:
    """A minimal workbook: shared strings for one sheet, inline strings for another.

    The parts carry the real spreadsheet namespace, because that is what the reader matches on and a
    fixture without it would test the wrong thing.
    """
    shared: list[str] = []
    for name, rows in sheets.items():
        if name in use_shared:
            for row in rows:
                for value in row:
                    if isinstance(value, str) and value not in shared:
                        shared.append(value)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/workbook.xml", "<workbook><sheets>" + "".join(
            f'<sheet name="{name}" sheetId="{i+1}" r:id="rId{i+1}"/>'
            for i, name in enumerate(sheets)) + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels", "<Relationships>" + "".join(
            f'<Relationship Id="rId{i+1}" Target="worksheets/sheet{i+1}.xml"/>'
            for i, _ in enumerate(sheets)) + "</Relationships>")
        z.writestr("xl/sharedStrings.xml", f"<sst {NS}>" + "".join(
            f"<si><t>{value}</t></si>" for value in shared) + "</sst>")
        for i, (name, rows) in enumerate(sheets.items()):
            body = []
            for r, row in enumerate(rows, start=1):
                cells = ""
                for c, value in enumerate(row):
                    ref = f"{column_name(c)}{r}"
                    if isinstance(value, str) and name in use_shared:
                        cells += f'<c r="{ref}" t="s"><v>{shared.index(value)}</v></c>'
                    elif isinstance(value, str):
                        cells += f'<c r="{ref}" t="inlineStr"><is><t>{value}</t></is></c>'
                    elif value == "":
                        cells += f'<c r="{ref}"/>'
                    else:
                        cells += f'<c r="{ref}"><v>{value}</v></c>'
                body.append(f'<row r="{r}">{cells}</row>')
            z.writestr(f"xl/worksheets/sheet{i+1}.xml",
                       f"<worksheet {NS}><sheetData>" + "".join(body) + "</sheetData></worksheet>")


TITLE = ["Inventory of Planned Generators, November 2024"]
BLANK = [""]
# The date columns sit at positions other than the real files use, on purpose.
PLANNED_HEADER = ["Entity ID", "Entity Name", "Plant ID", "Plant Name", "Plant State", "Sector",
                  "Generator ID", "Technology", "Nameplate Capacity (MW)",
                  "Planned Operation Month", "Planned Operation Year", "Status"]
PLANNED_ROWS = [
    ["1", "Sun Corp", "60104", "Sun Site", "TX", "IPP", "G1", "Solar Photovoltaic", "100",
     "June", "2024", "Planned"],
    ["1", "Sun Corp", "60104", "Sun Site", "TX", "IPP", "G2", "Solar Photovoltaic", "50",
     "12", "2024", "Planned"],
    ["2", "Wind Co", "60105", "Wind Site", "IA", "IPP", "W1", "Onshore Wind Turbine", "200",
     "January", "2023", "Planned"],
]
OPERATING_HEADER = ["Entity ID", "Entity Name", "Plant ID", "Plant Name", "Plant State", "Sector",
                    "Generator ID", "Technology", "Nameplate Capacity (MW)",
                    "Operating Month", "Operating Year", "Status"]
OPERATING_ROWS = [
    ["2", "Wind Co", "60105", "Wind Site", "IA", "IPP", "W1", "Onshore Wind Turbine", "200",
     "March", "2023", "Operating"],
]
CANCELED_HEADER = ["Entity ID", "Entity Name", "Plant ID", "Plant Name", "Plant State", "Generator ID"]
CANCELED_ROWS = [["1", "Sun Corp", "60104", "Sun Site", "TX", "G2"]]

tmp = Path(tempfile.mkdtemp(prefix="eia-"))
book = tmp / "november_generator2024.xlsx"
write_xlsx(book, {
    "Planned": [TITLE, BLANK, PLANNED_HEADER] + PLANNED_ROWS,
    "Operating": [TITLE, BLANK, OPERATING_HEADER] + OPERATING_ROWS,
    "Canceled or Postponed": [TITLE, BLANK, CANCELED_HEADER] + CANCELED_ROWS,
}, use_shared={"Planned"})

sheets = read_sheets(book, ("Planned", "Operating", "Canceled or Postponed"))
check("every requested sheet is read", sorted(sheets), ["Canceled or Postponed", "Operating", "Planned"])
check("the header row is found three rows down (shared strings)",
      find_header(sheets["Planned"]), 2)
check("the header row is found in an inline-string sheet too",
      find_header(sheets["Operating"]), 2)
check("a named cell is read", cell(sheets["Planned"][3], sheets["Planned"][2], "Plant ID"), "60104")
check("a missing column gives empty rather than raising",
      cell(["a"], ["Only"], "Nothing"), "")
check("a short row gives empty rather than raising",
      cell(["a"], ["A", "B"], "B"), "")

check("availability is the last day of the vintage month",
      availability(dt.date(2024, 11, 1)), dt.date(2024, 11, 30))
check("availability handles a short February",
      availability(dt.date(2024, 2, 10)), dt.date(2024, 2, 29))
check("the file name is the month then the year",
      vintage_name(2024, 11), "november_generator2024.xlsx")
check("older vintages live in the archive",
      vintage_url(2024, 11).endswith("/archive/xls/november_generator2024.xlsx"), True)

vintage = read_vintage(book, 2024, 11)
planned = {g.key: g for g in vintage["Planned"]}
check("planned rows are read with their promised month",
      planned[("60104", "G1")].statement, "2024-06")
check("a numeric month is read as a month", planned[("60104", "G2")].statement, "2024-12")
check("a month name is read as a month", planned[("60105", "W1")].statement, "2023-01")
check("the vintage stamp and availability ride along",
      (planned[("60104", "G1")].vintage, planned[("60104", "G1")].available_from),
      ("2024-11", "2024-11-30"))
check("operating rows are read with their realized month",
      {g.key: g for g in vintage["Operating"]}[("60105", "W1")].realized, "2023-03")
check("a planned row carries no realized month", planned[("60104", "G1")].realized, "")

check("months between two statements", months_between("2023-01", "2024-06"), 17)
check("the same month is zero", months_between("2024-06", "2024-06"), 0)
check("an empty statement gives no answer", months_between("", "2024-06"), None)

# A second vintage: the promise moves, one generator vanishes, one is cancelled.
book2 = tmp / "december_generator2024.xlsx"
write_xlsx(book2, {
    "Planned": [TITLE, BLANK, PLANNED_HEADER,
                ["1", "Sun Corp", "60104", "Sun Site", "TX", "IPP", "G1", "Solar Photovoltaic",
                 "100", "June", "2025", "Planned"]],
    "Operating": [TITLE, BLANK, OPERATING_HEADER,
                  ["1", "Sun Corp", "60104", "Sun Site", "TX", "IPP", "G1", "Solar Photovoltaic",
                   "100", "October", "2025", "Operating"]],
    "Canceled or Postponed": [TITLE, BLANK, CANCELED_HEADER,
                              ["1", "Sun Corp", "60104", "Sun Site", "TX", "G2"]],
}, use_shared=set())
later = read_vintage(book2, 2024, 12)

moved = {r["generator_id"]: r for r in revisions(vintage, later)}
check("a moved promise is reported", moved["G1"]["revision_months"], 12)
check("a later promise is called a slip", moved["G1"]["change"], "slipped")
check("the pair keeps both statements",
      (moved["G1"]["promised_before"], moved["G1"]["promised_after"]), ("2024-06", "2025-06"))
check("a cancelled generator is named as such", moved["G2"]["change"], "cancelled or postponed")
check("a cancelled row has no revision size", moved["G2"]["revision_months"], None)
departed = {(r["plant_id"], r["generator_id"]): r for r in revisions(vintage, later)}
check("a generator that left without being cancelled is named as such",
      departed[("60105", "W1")]["change"], "left the planned sheet")

backwards = revisions(later, vintage)
check("a promise brought forward is called a pull forward",
      {r["generator_id"]: r for r in backwards}["G1"]["change"], "pulled forward")

realized = realizations({g.key: g for g in vintage["Planned"]},
                        {g.key: g for g in read_vintage(book2, 2024, 12)["Operating"]})
# Promised 2024-06 in the November vintage, actually running 2025-10 in the December one: 16 months.
check("a realization compares the earlier promise with the actual month",
      realized[0]["late_months"], 16)
check("a realization carries the generator identity", realized[0]["generator_id"], "G1")

check("a year range becomes one November per year", months_in_range("2022-2023"), [(2022, 11), (2023, 11)])
check("a single year is allowed", months_in_range("2023"), [(2023, 11)])

# The summary must not divide by zero when no realization is comparable (it did once).
empty_text = summarise([{"revision_months": None, "change": "left the planned sheet",
                         "technology": "Solar Photovoltaic"}], [{"late_months": None}], [])
check("the summary survives a realisation with no comparable promise",
      "no comparable promise" in empty_text, True)

if failures:
    print("\n".join(f"  FAIL {f}" for f in failures))
    print(f"\n{36 - len(failures)}/36 passed")
    raise SystemExit(1)
print("\n36/36 passed")
