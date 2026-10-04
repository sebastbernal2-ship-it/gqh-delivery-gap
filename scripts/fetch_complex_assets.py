#!/usr/bin/env python3
"""Fetch total assets (instant facts) from SEC XBRL for every listed name in the complex.

Tickers come from results/market-panel.json groups, resolved through the SEC ticker file. Raw responses
are cached under results/sec-complex/.

    python3 scripts/fetch_complex_assets.py
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
OUT = ROOT / "results" / "complex-assets-quarterly.csv"
AGENT = "VECTOR research gqh-delivery-gap contact: sebastian@example.com"
CONCEPT = "Assets"


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
    tickers_file = get("https://www.sec.gov/files/company_tickers.json", "company_tickers.json")
    if not tickers_file:
        raise SystemExit("could not fetch the SEC ticker file")
    cik_by_ticker = {row["ticker"].upper(): str(row["cik_str"]).zfill(10) for row in tickers_file.values()}
    groups = json.loads(PANEL.read_text())["groups"]
    wanted = []
    for payload in groups.values():
        for series in payload["series"]:
            ticker = series["ticker"]
            if ticker.startswith("^") or "=" in ticker or ticker.upper() not in cik_by_ticker:
                continue
            if ticker not in wanted:
                wanted.append(ticker)
    rows = []
    for ticker in sorted(wanted):
        payload = get(f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik_by_ticker[ticker.upper()]}"
                      f"/us-gaap/{CONCEPT}.json", f"{ticker}-{CONCEPT}.json")
        if not payload:
            continue
        latest: dict[str, dict] = {}
        for fact in payload.get("units", {}).get("USD", []):
            end = fact.get("end")
            if not end or fact.get("start"):
                continue
            if end not in latest or fact.get("filed", "") > latest[end].get("filed", ""):
                latest[end] = fact
        for end, fact in sorted(latest.items()):
            rows.append({"ticker": ticker, "concept": CONCEPT, "period_end": end, "value_usd": fact["val"],
                         "form": fact.get("form", ""), "filed": fact.get("filed", ""),
                         "fy": fact.get("fy", ""), "fp": fact.get("fp", "")})
    rows.sort(key=lambda row: (row["ticker"], row["period_end"]))
    fields = ["ticker", "concept", "period_end", "value_usd", "form", "filed", "fy", "fp"]
    with OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    tickers = sorted({row["ticker"] for row in rows})
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} instant facts on {len(tickers)} tickers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
