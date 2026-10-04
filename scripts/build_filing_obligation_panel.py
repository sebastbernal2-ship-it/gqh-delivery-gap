#!/usr/bin/env python3
"""Build the four-firm filing decisions labelled by the next point-in-time obligation surprise.

One row per filing that precedes a measured obligation vintage for the same issuer. The primary
metric uses the latest filing before each disclosure, because filings map many-to-one onto
disclosures; the all-filings version is a robustness row and reports its distinct-label count.

    python3 scripts/build_filing_obligation_panel.py
"""
from __future__ import annotations

import argparse
import bisect
import csv
import datetime
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.panel import parse_clock  # noqa: E402

BIN_EDGES = (-0.10, -0.02, 0.02, 0.10)
BIN_LABELS = ("surprise-down-large", "surprise-down-small", "flat",
              "surprise-up-small", "surprise-up-large")


def surprise_bin(value: float) -> int:
    return bisect.bisect_right(BIN_EDGES, value)


def obligations_from_vintages(path: Path) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for row in csv.DictReader(path.open()):
        if row["expectation_status"] != "measured" or not row["relative_surprise_pit"].strip():
            continue
        available, _ = parse_clock(row["availability"])
        if available is None:
            continue
        record = {"available": available, "relative": float(row["relative_surprise_pit"]),
                  "concept": row["concept"], "period_end": row["period_end"],
                  "change": row.get("change", ""), "previous_value": row.get("previous_value", ""),
                  "ticker": row["ticker"].strip().upper()}
        out.setdefault(record["ticker"], []).append(record)
    for items in out.values():
        items.sort(key=lambda item: item["available"])
    return out


def filings_from_register(path: Path) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for row in csv.DictReader(path.open()):
        ticker = (row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        available, _ = parse_clock(row.get("earliest_availability_utc")
                                   or row.get("acceptance_utc") or row.get("filed_date", ""))
        if available is None:
            continue
        out.setdefault(ticker, []).append({"available": available, "form": row.get("form", ""),
                                           "items": row.get("items", ""),
                                           "accession": row.get("accession", "")})
    for items in out.values():
        items.sort(key=lambda item: item["available"])
    return out


def prior_features(history: list[dict], decision: datetime.datetime) -> dict:
    changes = [item for item in history if item["available"] < decision]
    relatives = [float(item["change"]) / abs(float(item["previous_value"]))
                 for item in changes
                 if (item.get("change") or "").strip() and (item.get("previous_value") or "").strip()
                 and float(item["previous_value"]) != 0]
    return {
        "prior_count": float(len(changes)),
        "last_change_rel": relatives[-1] if relatives else None,
        "trailing_mean_change_rel": statistics.mean(relatives[-4:]) if relatives else None,
        "days_since_last_obligation": ((decision - changes[-1]["available"]).total_seconds() / 86400.0
                                       if changes else None),
        "missing_last_obligation": 0.0 if changes else 1.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vintages", type=Path, default=ROOT / "results" / "obligation-vintages.csv")
    parser.add_argument("--register", type=Path, default=ROOT / "results" / "filings-register.csv")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results" / "filing-obligation-decisions.csv")
    args = parser.parse_args()

    obligations = obligations_from_vintages(args.vintages)
    filings = filings_from_register(args.register)
    columns = ("ticker", "concept", "filing_accession", "filing_form", "filing_items",
               "decision_time", "label_available", "label_relative_surprise", "label_bin",
               "label_bin_label", "disclosure_id", "is_deciding", "prior_count",
               "last_change_rel", "trailing_mean_change_rel", "days_since_last_obligation",
               "missing_last_obligation")
    rows = []
    for ticker, disclosures in sorted(obligations.items()):
        items = filings.get(ticker, [])
        for index, disclosure in enumerate(disclosures):
            candidates = [item for item in items if item["available"] < disclosure["available"]]
            if not candidates:
                continue
            deciding = candidates[-1]
            history = disclosures[:index]
            for candidate in candidates:
                features = prior_features(history, candidate["available"])
                rows.append({
                    "ticker": ticker, "concept": disclosure["concept"],
                    "filing_accession": candidate["accession"], "filing_form": candidate["form"],
                    "filing_items": candidate["items"],
                    "decision_time": candidate["available"].isoformat(),
                    "label_available": disclosure["available"].isoformat(),
                    "label_relative_surprise": disclosure["relative"],
                    "label_bin": surprise_bin(disclosure["relative"]),
                    "label_bin_label": BIN_LABELS[surprise_bin(disclosure["relative"])],
                    "disclosure_id": f"{ticker}:{disclosure['concept']}:{disclosure['period_end']}",
                    "is_deciding": 1 if candidate is deciding else 0,
                    **features,
                })
    rows.sort(key=lambda row: (row["label_available"], row["ticker"]))
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    deciding = [row for row in rows if row["is_deciding"] == 1]
    by_bin: dict[str, int] = {}
    for row in deciding:
        by_bin[row["label_bin_label"]] = by_bin.get(row["label_bin_label"], 0) + 1
    summary = {
        "rows": len(rows),
        "deciding_rows": len(deciding),
        "distinct_disclosures": len({row["disclosure_id"] for row in rows}),
        "tickers": sorted({row["ticker"] for row in rows}),
        "bins_deciding": {label: by_bin.get(label, 0) for label in BIN_LABELS},
        "output": str(args.output),
    }
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
