#!/usr/bin/env python3
"""Fetch quarterly operating income, net income and gross profit for the complex.

Universe: every ticker in results/complex-capex-quarterly.csv, resolved through the SEC ticker file.
Raw responses are cached under results/sec-complex/.

    python3 scripts/fetch_complex_margins.py
"""
from __future__ import annotations

import csv
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "results" / "sec-complex"
UNIVERSE = ROOT / "results" / "complex-capex-quarterly.csv"
OUT = ROOT / "results" / "complex-margins-quarterly.csv"
AGENT = "VECTOR research gqh-delivery-gap contact: sebastian@example.com"
CONCEPTS = ["OperatingIncomeLoss", "NetIncomeLoss", "GrossProfit"]


def get(url: str, cache_name: str) -> dict | None:
    path = CACHE / cache_name
    if path.exists():
        return json.loads(path.read_text())
    request = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read())
    except Exception:
        return None
    path.write_text(json.dumps(payload))
    time.sleep(0.15)
    return payload


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    tickers = sorted({row["ticker"] for row in csv.DictReader(UNIVERSE.open())})
    tickers_file = get("https://www.sec.gov/files/company_tickers.json", "company_tickers.json")
    if not tickers_file:
        raise SystemExit("could not fetch the SEC ticker file")
    cik_by_ticker = {row["ticker"].upper(): str(row["cik_str"]).zfill(10) for row in tickers_file.values()}
    rows = []
    for ticker in tickers:
        cik = cik_by_ticker.get(ticker.upper())
        if not cik:
            continue
        for concept in CONCEPTS:
            payload = get(f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{concept}.json",
                          f"{ticker}-{concept}.json")
            if not payload:
                continue
            latest: dict[tuple[str, str], dict] = {}
            for fact in payload.get("units", {}).get("USD", []):
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
            for (start, end), fact in sorted(latest.items()):
                rows.append({"ticker": ticker, "concept": concept, "period_start": start, "period_end": end,
                             "value_usd": fact["val"], "form": fact.get("form", ""),
                             "filed": fact.get("filed", "")})
    rows.sort(key=lambda row: (row["ticker"], row["period_end"], row["concept"]))
    fields = ["ticker", "concept", "period_start", "period_end", "value_usd", "form", "filed"]
    with OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    names = len({row["ticker"] for row in rows})
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} facts on {names} names")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
