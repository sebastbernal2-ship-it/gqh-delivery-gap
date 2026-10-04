#!/usr/bin/env python3
"""Build the interconnection queue panel from the LBNL "Queued Up" workbook.

LBNL publishes the full project level U.S. transmission interconnection queue history as a public
workbook, no account needed. It is the dataset truth T11 called the highest value acquisition and
the ordering factor the delivery tail was missing.

  source: https://eta-publications.lbl.gov/sites/default/files/2025-08/lbnl_ix_queue_data_file_thru2024_v2.xlsx
  sheet:  "03. Complete Queue Data"
  note:   the host returns 403 to a bare client, so --fetch sends an ordinary browser user agent

Writes results/queue-panel.csv (one row per queue project, dates as ISO) and
results/queue-summary.json (counts, conversion times, rates).

    python3 scripts/build_queue_panel.py --fetch   # download once into data/queues/
    python3 scripts/build_queue_panel.py           # build from the local copy
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import statistics
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from eia.xlsx import read_sheet  # noqa: E402

SOURCE_URL = ("https://eta-publications.lbl.gov/sites/default/files/2025-08/"
              "lbnl_ix_queue_data_file_thru2024_v2.xlsx")
SHEET = "03. Complete Queue Data"
WORKBOOK = ROOT / "data" / "queues" / "lbnl_queue_thru2024.xlsx"
PANEL = ROOT / "results" / "queue-panel.csv"
SUMMARY = ROOT / "results" / "queue-summary.json"
USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/126 Safari/537.36")
DATE_FIELDS = ("q_date", "prop_date", "on_date", "wd_date", "ia_date")
EXCEL_EPOCH = dt.date(1899, 12, 30)


def fetch() -> None:
    WORKBOOK.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=300) as response:
        WORKBOOK.write_bytes(response.read())
    print(f"downloaded {WORKBOOK.relative_to(ROOT)} ({WORKBOOK.stat().st_size:,} bytes)")


def serial_to_iso(value: str) -> str:
    text = str(value).strip()
    if not text or text.upper() in {"NA", "N/A", "NONE"}:
        return ""
    try:
        number = float(text)
    except ValueError:
        return text
    if number < 1000:
        return text
    return (EXCEL_EPOCH + dt.timedelta(days=number)).isoformat()


def days_between(earlier: str, later: str) -> str:
    if not earlier or not later:
        return ""
    try:
        return str((dt.date.fromisoformat(later) - dt.date.fromisoformat(earlier)).days)
    except ValueError:
        return ""


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true", help="download the workbook first")
    args = parser.parse_args()
    if args.fetch or not WORKBOOK.exists():
        fetch()
    if not zipfile.is_zipfile(WORKBOOK):
        raise SystemExit(f"{WORKBOOK} is not a workbook; delete it and retry with --fetch")

    rows = read_sheet(WORKBOOK, SHEET)
    header_index = next((index for index, row in enumerate(rows) if row and row[0] == "q_id"), None)
    if header_index is None:
        raise SystemExit("could not find the q_id header row")
    header = rows[header_index]
    records = []
    for row in rows[header_index + 1:]:
        if not row or not row[0] or row[0] == "RETURN TO CONTENTS":
            continue
        record = {name: (row[index] if index < len(row) else "") for index, name in enumerate(header)}
        for field in DATE_FIELDS:
            record[field] = serial_to_iso(record.get(field, ""))
        record["days_ir_to_ia"] = days_between(record.get("q_date", ""), record.get("ia_date", ""))
        record["days_ir_to_cod"] = days_between(record.get("q_date", ""), record.get("on_date", ""))
        record["days_ir_to_wd"] = days_between(record.get("q_date", ""), record.get("wd_date", ""))
        record["mw"] = record.get("mw1", "")
        records.append(record)

    if not records:
        raise SystemExit("no queue records found")
    fields = header + ["days_ir_to_ia", "days_ir_to_cod", "days_ir_to_wd", "mw"]
    with PANEL.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)

    def status(name: str) -> list[dict]:
        return [record for record in records if record.get("q_status") == name]

    ia_days = [float(record["days_ir_to_ia"]) for record in records if record.get("days_ir_to_ia")]
    cod_days = [float(record["days_ir_to_cod"]) for record in records if record.get("days_ir_to_cod")]
    mw_by_status: dict[str, float] = {}
    for record in records:
        try:
            mw = float(record.get("mw") or 0)
        except ValueError:
            mw = 0.0
        mw_by_status[record.get("q_status", "?")] = mw_by_status.get(record.get("q_status", "?"), 0.0) + mw
    summary = {
        "source": SOURCE_URL,
        "sheet": SHEET,
        "projects": len(records),
        "date_range": {"first_request": min((r["q_date"] for r in records if r.get("q_date")), default=""),
                       "last_request": max((r["q_date"] for r in records if r.get("q_date")), default="")},
        "by_status": {name: len(status(name)) for name in sorted({r.get("q_status", "?") for r in records})},
        "mw_by_status": {name: round(value, 1) for name, value in sorted(mw_by_status.items())},
        "regions": len({record.get("region", "") for record in records if record.get("region")}),
        "developers": len({record.get("developer", "") for record in records if record.get("developer")}),
        "days_ir_to_ia": {"n": len(ia_days),
                          "median": percentile(ia_days, 0.5),
                          "p90": percentile(ia_days, 0.9)},
        "days_ir_to_cod": {"n": len(cod_days),
                           "median": percentile(cod_days, 0.5),
                           "p90": percentile(cod_days, 0.9)},
        "completion_share": round(len(status("operational")) / len(records), 4),
        "withdrawal_share": round(len(status("withdrawn")) / len(records), 4),
    }
    SUMMARY.write_text(json.dumps(summary, indent=1) + "\n")
    print(f"wrote {PANEL.relative_to(ROOT)} ({len(records):,} projects) and {SUMMARY.relative_to(ROOT)}")
    print(f"status counts: {summary['by_status']}")
    print(f"median days IR to IA: {summary['days_ir_to_ia']['median']}   "
          f"IR to COD: {summary['days_ir_to_cod']['median']}")
    print(f"completion share {summary['completion_share']:.1%}   "
          f"withdrawal share {summary['withdrawal_share']:.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
