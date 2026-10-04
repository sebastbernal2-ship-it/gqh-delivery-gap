#!/usr/bin/env python3
"""Build the broad revenue and capex panels from whatever companyconcept cache exists.

The fetch runs in the background and only writes its panels at the end. This lets the analysis start
on the cached subset and re-run later, unchanged, when the cache is complete. Same earliest-filed
rule, same columns as the complex panels.

    python3 scripts/build_universe_driver_panels.py
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from fetch_universe_fundamentals import CONCEPTS, FIELDS, quarterly_earliest  # noqa: E402

CACHE = ROOT / "results" / "edgar-cache"
UNIVERSE = ROOT / "results" / "rpo-universe-vintages.csv"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    args = parser.parse_args()

    ticker_by_cik = {}
    for row in csv.DictReader(UNIVERSE.open()):
        ticker, cik = (row.get("ticker") or "").strip(), (row.get("cik") or "").strip()
        if ticker and not ticker.startswith("CIK") and cik:
            ticker_by_cik.setdefault(cik.zfill(10), ticker)

    by_concept: dict[str, list[dict]] = {name: [] for name in CONCEPTS}
    seen = 0
    for path in sorted(CACHE.glob("companyconcept_*.json")):
        for name, concept in CONCEPTS.items():
            if not path.name.endswith(f"_{concept}.json"):
                continue
            cik = path.name.split("companyconcept_")[1].split("_")[0]
            ticker = ticker_by_cik.get(cik.zfill(10))
            if not ticker:
                continue
            try:
                payload = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            by_concept[name].extend(quarterly_earliest(payload, ticker, concept))
            seen += 1
    for name, rows in by_concept.items():
        output = ROOT / "results" / f"universe-{name}-quarterly.csv"
        with output.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        lags = []
        for row in rows:
            try:
                lags.append((datetime.date.fromisoformat(row["filed"])
                             - datetime.date.fromisoformat(row["period_end"])).days)
            except ValueError:
                continue
        print(json.dumps({"panel": name, "cached_responses": seen, "rows": len(rows),
                          "tickers": len({row["ticker"] for row in rows}),
                          "median_lag_days": statistics.median(lags) if lags else None,
                          "share_over_300": round(sum(1 for lag in lags if lag > 300) / max(1, len(lags)), 3),
                          "output": str(output)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
