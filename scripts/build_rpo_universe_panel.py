#!/usr/bin/env python3
"""Stage 2: the broad RPO panel from cached XBRL frames and cached submissions.

One request per quarter is enough because an XBRL frame carries every filer's value for one field in
one quarter, with the accession that reported it. The acceptance timestamp of that accession comes
from the filer's submissions file. Both are already cached, so this build makes no network calls.

The clock is the accession's acceptance timestamp, the exact instant the fact became public, and the
build reports the declared clock rule beside the panel.

    python3 scripts/build_rpo_universe_panel.py
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.vintages import COLUMNS, build_vintages  # noqa: E402

CACHE = ROOT / "results" / "edgar-cache"
CONCEPT = "RevenueRemainingPerformanceObligation"
MAX_GAP_DAYS = 120


def load_frames() -> dict[tuple[int, str], dict]:
    """(cik, period end) to the frame row that reported it."""
    rows = {}
    for path in sorted(CACHE.glob(f"*frames_us-gaap_{CONCEPT}_USD_CY*.json*")):
        payload = json.loads(path.read_text())
        for row in payload.get("data", []):
            cik = row.get("cik")
            end = row.get("end")
            if cik is None or not end:
                continue
            key = (int(cik), end)
            current = rows.get(key)
            if current is None or str(row.get("accn", "")) < str(current.get("accn", "")):
                rows[key] = row
    return rows


def load_filers() -> dict[int, dict]:
    """Accession to acceptance timestamp, plus identity, from the cached submissions files."""
    filers = {}
    for path in sorted(CACHE.glob("*submissions_CIK*.json*")):
        match = re.search(r"CIK(\d+)", path.name)
        if not match:
            continue
        try:
            payload = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        stamps: dict[str, str] = {}
        blocks = [payload.get("filings", {}).get("recent", {})]
        for block in blocks:
            accessions = block.get("accessionNumber", [])
            accepted = block.get("acceptanceDateTime", [])
            for index, accession in enumerate(accessions):
                if index < len(accepted) and accepted[index]:
                    stamps[accession] = accepted[index]
        filers[int(match.group(1))] = {
            "ticker": (payload.get("tickers") or [""])[0],
            "name": payload.get("name", ""),
            "sic": str(payload.get("sic", "")),
            "stamps": stamps,
        }
    return filers


def prepared_rows(frames: dict, filers: dict) -> tuple[list[dict], dict]:
    drops: Counter = Counter()
    by_filer: dict[int, list[dict]] = defaultdict(list)
    for (cik, end), row in frames.items():
        filer = filers.get(cik)
        if filer is None:
            drops["no_submissions"] += 1
            continue
        stamp = filer["stamps"].get(str(row.get("accn", "")))
        if not stamp:
            drops["no_acceptance_stamp"] += 1
            continue
        value = row.get("val")
        if not isinstance(value, (int, float)) or value <= 0:
            drops["no_positive_value"] += 1
            continue
        by_filer[cik].append({"period_end": end, "value": float(value),
                              "acceptance": stamp, "accession": row.get("accn", "")})

    out = []
    for cik, rows in by_filer.items():
        rows.sort(key=lambda item: item["period_end"])
        for position, row in enumerate(rows):
            if position == 0:
                drops["no_previous_value"] += 1
                continue
            previous = rows[position - 1]
            gap = (datetime.date.fromisoformat(row["period_end"])
                   - datetime.date.fromisoformat(previous["period_end"])).days
            if not 80 <= gap <= MAX_GAP_DAYS:
                drops["gap_not_quarterly"] += 1
                continue
            filer = filers[cik]
            out.append({
                "ticker": filer["ticker"] or f"CIK{cik}",
                "cik": str(cik),
                "name": filer["name"],
                "concept": CONCEPT,
                "sic": filer["sic"],
                "group": "",
                "period_end": row["period_end"],
                "earliest_availability_utc": row["acceptance"],
                "value": row["value"],
                "previous_value": previous["value"],
                "change": row["value"] - previous["value"],
                "availability_resolution": "accession acceptance timestamp",
                "accession": row["accession"],
                "source_receipt": f"frames/{CONCEPT}",
            })
    return out, dict(drops)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results" / "rpo-universe-vintages.csv")
    args = parser.parse_args()

    frames = load_frames()
    filers = load_filers()
    prepared, drops = prepared_rows(frames, filers)
    records, vintage_drops = build_vintages(prepared)

    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COLUMNS), extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(record)

    measured = [row for row in records if str(row.get("relative_surprise_pit") or "").strip()]
    lags = []
    for row in prepared:
        availability = row["earliest_availability_utc"][:10]
        lags.append((datetime.date.fromisoformat(availability)
                     - datetime.date.fromisoformat(row["period_end"])).days)
    per_quarter = Counter(row["period_end"][:7] for row in prepared)
    print(json.dumps({
        "frames": len(frames), "filers_cached": len(filers), "prepared_rows": len(prepared),
        "drops": drops, "vintage_drops": vintage_drops, "vintages": len(records),
        "measured_events": len(measured),
        "issuers": len({row["ticker"] for row in records}),
        "issuers_measured": len({row["ticker"] for row in measured}),
        "median_filing_lag_days": statistics.median(lags) if lags else None,
        "share_lag_over_300_days": round(sum(1 for lag in lags if lag > 300) / max(1, len(lags)), 4),
        "first_period": min(row["period_end"] for row in prepared) if prepared else None,
        "last_period": max(row["period_end"] for row in prepared) if prepared else None,
        "quarter_sizes": dict(sorted(per_quarter.items())[-8:]),
        "output": str(args.output),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
