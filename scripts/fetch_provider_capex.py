#!/usr/bin/env python3
"""Fetch quarterly provider capex from SEC XBRL company facts.

Resolves tickers through the SEC ticker file, pulls the capex concepts per issuer, keeps the quarterly
durations, prefers the latest filed fact per period, and writes results/provider-capex-quarterly.csv.
Raw responses are cached under results/sec-capex/ so the study is reproducible without refetching.

    python3 scripts/fetch_provider_capex.py
"""
from __future__ import annotations

import csv
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "results" / "sec-capex"
OUT = ROOT / "results" / "provider-capex-quarterly.csv"
AGENT = "VECTOR research gqh-delivery-gap contact: sebastian@example.com"
TICKERS = ["MSFT", "AMZN", "GOOGL", "META", "ORCL", "CRWV", "IREN", "HUT", "CORZ", "APLD", "EQIX", "DLR"]
CONCEPTS = ["PaymentsToAcquirePropertyPlantAndEquipment",
            "PaymentsToAcquirePropertyPlantAndEquipmentExcludingInterestCapitalized",
            "PaymentsToAcquireProductiveAssets"]


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
    tickers = get("https://www.sec.gov/files/company_tickers.json", "company_tickers.json")
    if not tickers:
        raise SystemExit("could not fetch the SEC ticker file")
    by_ticker = {row["ticker"]: row for row in tickers.values()}
    rows = []
    for ticker in TICKERS:
        entry = by_ticker.get(ticker)
        if not entry:
            print(f"skip {ticker}: not in the SEC ticker file")
            continue
        cik = str(entry["cik_str"]).zfill(10)
        best = None
        for concept in CONCEPTS:
            url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{concept}.json"
            payload = get(url, f"{ticker}-{concept}.json")
            if not payload:
                continue
            facts = payload.get("units", {}).get("USD", [])
            quarterly = [fact for fact in facts
                         if fact.get("start") and fact.get("end")
                         and 75 <= (__import__("datetime").date.fromisoformat(fact["end"])
                                    - __import__("datetime").date.fromisoformat(fact["start"])).days <= 100]
            if quarterly and (best is None or len(quarterly) > len(best[1])):
                best = (concept, quarterly)
        if not best:
            print(f"skip {ticker}: no quarterly capex facts")
            continue
        concept, quarterly = best
        latest: dict[str, dict] = {}
        for fact in quarterly:
            key = fact["end"]
            if key not in latest or fact.get("filed", "") > latest[key].get("filed", ""):
                latest[key] = fact
        for fact in sorted(latest.values(), key=lambda item: item["end"]):
            rows.append({"ticker": ticker, "cik": cik, "concept": concept, "period_end": fact["end"],
                         "value_usd": fact["val"], "form": fact.get("form", ""),
                         "filed": fact.get("filed", ""), "fy": fact.get("fy", ""),
                         "fp": fact.get("fp", "")})
        print(f"{ticker}: {len(latest)} quarterly capex observations ({concept})")
    with OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ticker", "cik", "concept", "period_end",
                                                    "value_usd", "form", "filed", "fy", "fp"],
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
