#!/usr/bin/env python3
"""Fetch quarterly capex and revenue from SEC XBRL for every listed name in the complex.

Tickers come from results/market-panel.json groups. Funds, indices and futures are skipped. Raw
responses are cached under results/sec-complex/.

    python3 scripts/fetch_complex_fundamentals.py
"""
from __future__ import annotations

import csv
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "results" / "sec-complex"
PANEL = ROOT / "results" / "market-panel.json"
OUT_CAPEX = ROOT / "results" / "complex-capex-quarterly.csv"
OUT_REVENUE = ROOT / "results" / "complex-revenue-quarterly.csv"
AGENT = "VECTOR research gqh-delivery-gap contact: sebastian@example.com"
CAPEX_CONCEPTS = ["PaymentsToAcquirePropertyPlantAndEquipment",
                  "PaymentsToAcquireProductiveAssets",
                  "PaymentsToAcquirePropertyPlantAndEquipmentExcludingInterestCapitalized"]
REVENUE_CONCEPTS = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"]


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


def quarterly(payload: dict, ticker: str, concept: str) -> list[dict]:
    rows = []
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
                     "value_usd": fact["val"], "form": fact.get("form", ""), "filed": fact.get("filed", ""),
                     "fy": fact.get("fy", ""), "fp": fact.get("fp", "")})
    return rows


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    tickers_file = get("https://www.sec.gov/files/company_tickers.json", "company_tickers.json")
    if not tickers_file:
        raise SystemExit("could not fetch the SEC ticker file")
    cik_by_ticker = {row["ticker"].upper(): str(row["cik_str"]).zfill(10) for row in tickers_file.values()}
    groups = json.loads(PANEL.read_text())["groups"]
    wanted = []
    for group, payload in groups.items():
        for series in payload["series"]:
            ticker = series["ticker"]
            if ticker.startswith("^") or "=" in ticker or ticker.upper() not in cik_by_ticker:
                continue
            if ticker not in wanted:
                wanted.append(ticker)
    capex_rows, revenue_rows = [], []
    for ticker in sorted(wanted):
        cik = cik_by_ticker[ticker.upper()]
        for concept in CAPEX_CONCEPTS:
            payload = get(f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{concept}.json",
                          f"{ticker}-{concept}.json")
            if payload:
                capex_rows.extend(quarterly(payload, ticker, concept))
        for concept in REVENUE_CONCEPTS:
            payload = get(f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{concept}.json",
                          f"{ticker}-{concept}.json")
            if payload:
                revenue_rows.extend(quarterly(payload, ticker, concept))
    fields = ["ticker", "concept", "period_start", "period_end", "value_usd", "form", "filed", "fy", "fp"]
    for path, rows in ((OUT_CAPEX, capex_rows), (OUT_REVENUE, revenue_rows)):
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    capex_tickers = sorted({row["ticker"] for row in capex_rows})
    revenue_tickers = sorted({row["ticker"] for row in revenue_rows})
    both = sorted(set(capex_tickers) & set(revenue_tickers))
    print(f"requested {len(wanted)} tickers; capex {len(capex_rows)} facts on {len(capex_tickers)} tickers; "
          f"revenue {len(revenue_rows)} facts on {len(revenue_tickers)} tickers; both {len(both)}")
    print("names with both:", ", ".join(both))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
