#!/usr/bin/env python3
"""Fetch quarterly provider revenue from SEC XBRL company concept files.

Uses the CIKs already recorded in results/provider-capex-quarterly.csv, pulls revenue concepts, keeps
quarterly durations, prefers the latest filed fact per period, and writes
results/provider-revenue-quarterly.csv. Raw responses are cached under results/sec-revenue/.

    python3 scripts/fetch_provider_revenue.py
"""
from __future__ import annotations

import csv
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "results" / "sec-revenue"
CAPEX = ROOT / "results" / "provider-capex-quarterly.csv"
OUT = ROOT / "results" / "provider-revenue-quarterly.csv"
AGENT = "VECTOR research gqh-delivery-gap contact: sebastian@example.com"
CONCEPTS = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"]


def get(url: str, cache_name: str) -> dict | None:
    path = CACHE / cache_name
    if path.exists():
        return json.loads(path.read_text())
    request = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read())
    except Exception as error:
        print(f"  fetch failed: {url} ({error})")
        return None
    path.write_text(json.dumps(payload))
    time.sleep(0.2)
    return payload


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    cik_by_ticker: dict[str, str] = {}
    for row in csv.DictReader(CAPEX.open()):
        cik_by_ticker.setdefault(row["ticker"], row["cik"])
    rows = []
    for ticker, cik in sorted(cik_by_ticker.items()):
        for concept in CONCEPTS:
            payload = get(f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{concept}.json",
                          f"{ticker}-{concept}.json")
            if not payload:
                continue
            units = payload.get("units", {}).get("USD", [])
            latest: dict[tuple[str, str], dict] = {}
            for fact in units:
                start, end = fact.get("start"), fact.get("end")
                if not start or not end:
                    continue
                try:
                    days = (int(end[:4]) * 372 + int(end[5:7]) * 31 + int(end[8:10])) - \
                           (int(start[:4]) * 372 + int(start[5:7]) * 31 + int(start[8:10]))
                except ValueError:
                    continue
                if not 80 <= days <= 100:
                    continue
                key = (start, end)
                if key not in latest or fact.get("filed", "") > latest[key].get("filed", ""):
                    latest[key] = fact
            for (start, end), fact in latest.items():
                rows.append({"ticker": ticker, "cik": cik, "concept": concept, "period_start": start,
                             "period_end": end, "value_usd": fact["val"], "form": fact.get("form", ""),
                             "filed": fact.get("filed", ""), "fy": fact.get("fy", ""), "fp": fact.get("fp", "")})
    rows.sort(key=lambda row: (row["ticker"], row["period_end"]))
    with OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ticker", "cik", "concept", "period_start",
                                                    "period_end", "value_usd", "form", "filed", "fy", "fp"])
        writer.writeheader()
        writer.writerows(rows)
    by_ticker = {}
    for row in rows:
        by_ticker.setdefault(row["ticker"], set()).add(row["period_end"])
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} quarterly facts")
    for ticker, periods in sorted(by_ticker.items()):
        print(f"  {ticker}: {len(periods)} quarters, {min(periods)} to {max(periods)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
