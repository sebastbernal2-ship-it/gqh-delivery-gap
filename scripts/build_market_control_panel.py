#!/usr/bin/env python3
"""Build a lagged PWR market-control panel from existing daily bar caches."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from event.study import abnormal, window_return  # noqa: E402

FIELDS = ["event_id", "ticker", "available", "horizon", "firm_return", "market_return",
          "sector_return", "market_abnormal", "sector_abnormal", "source_receipt"]


def load_bars(ticker: str, cache: Path) -> dict[str, float]:
    path = cache / f"{ticker}.json"
    if not path.exists():
        return {}
    return {stamp: float(value) for stamp, value in json.loads(path.read_text()).items()}


def build_rows(events: list[dict], series: dict[str, dict[str, float]], horizon: int = 5) -> list[dict]:
    indexes = {ticker: sorted(values) for ticker, values in series.items()}
    output = []
    for event in events:
        ticker = event.get("ticker", "")
        available = event.get("earliest_availability_utc", "")
        if ticker != "PWR" or not available or not event.get("change"):
            continue
        firm = window_return(series.get(ticker, {}), indexes.get(ticker, []), available, horizon)
        market = window_return(series.get("SPY", {}), indexes.get("SPY", []), available, horizon)
        sector = window_return(series.get("XLI", {}), indexes.get("XLI", []), available, horizon)
        if firm is None or market is None or sector is None:
            continue
        output.append({"event_id": f"market:{event['accession']}:{event['concept']}:{event['period_end']}",
                       "ticker": ticker, "available": available, "horizon": horizon,
                       "firm_return": firm, "market_return": market, "sector_return": sector,
                       "market_abnormal": abnormal(firm, market),
                       "sector_abnormal": abnormal(firm, sector),
                       "source_receipt": "market:yfinance:results/bar-cache"})
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", default="results/obligation-panel.csv")
    parser.add_argument("--cache", default="results/bar-cache")
    parser.add_argument("--out", default="results/market-control-panel.csv")
    args = parser.parse_args(argv)
    with (ROOT / args.events).open(newline="") as handle:
        events = list(csv.DictReader(handle))
    tickers = {"PWR", "SPY", "XLI"}
    series = {ticker: load_bars(ticker, ROOT / args.cache) for ticker in tickers}
    rows = build_rows(events, series)
    out = ROOT / args.out
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    print(f"wrote {args.out} ({len(rows)} control rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
