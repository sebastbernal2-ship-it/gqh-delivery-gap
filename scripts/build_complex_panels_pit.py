#!/usr/bin/env python3
"""Rebuild the complex capex and revenue panels with the original disclosure clock.

The first build kept the latest filing that reported each quarter (a ten-K comparative), so the
median availability lag was 401 days and every signal was a year stale. This rebuild keeps the
earliest filing that reported the quarter, which is when the market first saw it. Reads the local
cache only; writes new files and never touches the originals.

    python3 scripts/build_complex_panels_pit.py
"""
from __future__ import annotations

import csv
import datetime
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "results" / "sec-complex"
CAPEX_CONCEPTS = ("PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets",
                  "PaymentsToAcquirePropertyPlantAndEquipmentExcludingInterestCapitalized")
REVENUE_CONCEPTS = ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues")
FIELDS = ["ticker", "concept", "period_start", "period_end", "value_usd", "form", "filed", "fy", "fp"]


def quarterly_earliest(payload: dict, ticker: str, concept: str) -> list[dict]:
    """One row per quarter, dated by the earliest filed occurrence of that exact period."""
    earliest: dict[tuple[str, str], dict] = {}
    for fact in payload.get("units", {}).get("USD", []):
        start, end = fact.get("start"), fact.get("end")
        if not start or not end:
            continue
        try:
            days = (datetime.date.fromisoformat(end) - datetime.date.fromisoformat(start)).days
        except ValueError:
            continue
        if not 80 <= days <= 100:
            continue
        key = (start, end)
        if key not in earliest or fact.get("filed", "9999") < earliest[key].get("filed", "9999"):
            earliest[key] = fact
    return [{"ticker": ticker, "concept": concept, "period_start": start, "period_end": end,
             "value_usd": fact["val"], "form": fact.get("form", ""), "filed": fact.get("filed", ""),
             "fy": fact.get("fy", ""), "fp": fact.get("fp", "")}
            for (start, end), fact in sorted(earliest.items())]


def build(concepts: tuple[str, ...]) -> list[dict]:
    rows = []
    for concept in concepts:
        for path in sorted(CACHE.glob(f"*-{concept}.json")):
            ticker = path.name.split("-")[0]
            rows.extend(quarterly_earliest(json.loads(path.read_text()), ticker, concept))
    return rows


def main() -> int:
    capex = build(CAPEX_CONCEPTS)
    revenue = build(REVENUE_CONCEPTS)
    for path, rows, label in ((ROOT / "results" / "complex-capex-quarterly-pit.csv", capex, "capex"),
                              (ROOT / "results" / "complex-revenue-quarterly-pit.csv", revenue, "revenue")):
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        lags = []
        for row in rows:
            try:
                lags.append((datetime.date.fromisoformat(row["filed"])
                             - datetime.date.fromisoformat(row["period_end"])).days)
            except ValueError:
                continue
        print(json.dumps({
            "panel": label, "rows": len(rows), "tickers": len({row["ticker"] for row in rows}),
            "median_filing_lag_days": statistics.median(lags) if lags else None,
            "share_lag_over_300_days": round(sum(1 for lag in lags if lag > 300) / max(1, len(lags)), 3),
            "output": str(path),
        }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
