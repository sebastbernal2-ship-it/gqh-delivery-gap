#!/usr/bin/env python3
"""Stage 2b: revenue and capex for the broad universe, from companyconcept with earliest-filed clocks.

Duration frames pick whichever filing the SEC indexed, which is often a later comparative, so they
cannot carry a point-in-time clock. Companyconcept lists every occurrence of a tag with its own filing
date, so the earliest occurrence is the original disclosure. Cached under the ignored cache and safe
to rerun: a cached response is never refetched.

    python3 scripts/fetch_universe_fundamentals.py
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "results" / "edgar-cache"
UNIVERSE = ROOT / "results" / "rpo-universe-vintages.csv"
AGENT = "VECTOR research gqh-delivery-gap contact: sebastian@example.com"
CONCEPTS = {"revenue": "RevenueFromContractWithCustomerExcludingAssessedTax",
            "capex": "PaymentsToAcquirePropertyPlantAndEquipment"}
FIELDS = ["ticker", "concept", "period_start", "period_end", "value_usd", "form", "filed", "fy", "fp"]


def get(url: str, key: Path) -> dict | None:
    if key.exists():
        try:
            return json.loads(key.read_text())
        except (OSError, ValueError):
            pass
    request = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read())
    except Exception:
        return None
    key.write_text(json.dumps(payload))
    time.sleep(0.12)
    return payload


def quarterly_earliest(payload: dict, ticker: str, concept: str) -> list[dict]:
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)

    pairs: dict[str, str] = {}
    for row in csv.DictReader(UNIVERSE.open()):
        ticker, cik = (row.get("ticker") or "").strip(), (row.get("cik") or "").strip()
        if ticker and not ticker.startswith("CIK") and cik:
            pairs.setdefault(ticker, cik.zfill(10))
    tickers = sorted(pairs)
    if args.limit:
        tickers = tickers[:args.limit]
    print(f"tickers with a CIK: {len(tickers)}", flush=True)

    rows_by_concept: dict[str, list[dict]] = {name: [] for name in CONCEPTS}
    done = missing = 0
    for position, ticker in enumerate(tickers, start=1):
        cik = pairs[ticker]
        for name, concept in CONCEPTS.items():
            key = CACHE / f"companyconcept_{cik[:10]}_{concept}.json"
            payload = get(f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{concept}.json",
                          key)
            if not payload:
                missing += 1
                continue
            rows_by_concept[name].extend(quarterly_earliest(payload, ticker, concept))
            done += 1
        if position % 100 == 0:
            print(f"  {position}/{len(tickers)} responses {done} missing {missing}", flush=True)
    for name, rows in rows_by_concept.items():
        output = ROOT / "results" / f"universe-{name}-quarterly.csv"
        with output.open("w", newline="") as handle:
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
        lags.sort()
        print(json.dumps({"panel": name, "rows": len(rows),
                          "tickers": len({row["ticker"] for row in rows}),
                          "median_lag_days": lags[len(lags) // 2] if lags else None,
                          "share_over_300": round(sum(1 for l in lags if l > 300) / max(1, len(lags)), 3),
                          "output": str(output)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
