#!/usr/bin/env python3
"""Stage 2b: daily close and volume for the broad RPO universe, cached and ignored by git.

The edge test at breadth was blocked by price coverage: only 298 liquid names had bars. This fetches
the rest of the universe so the measurement can cover it. Existing cache entries are never refetched.

    python3 scripts/fetch_universe_bars.py            # fills the gaps
    python3 scripts/fetch_universe_bars.py --limit 25 # bounded probe
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLOSE_CACHE = ROOT / "results" / "bar-cache"
VOLUME_CACHE = ROOT / "results" / "bar-volume"
UNIVERSE = ROOT / "results" / "rpo-universe-vintages.csv"
COMPLEX = ROOT / "results" / "market-panel.json"
START = "2017-01-01"


def universe() -> list[str]:
    tickers = set()
    for row in csv.DictReader(UNIVERSE.open()):
        ticker = (row.get("ticker") or "").strip()
        if ticker and not ticker.startswith("CIK"):
            tickers.add(ticker)
    panel = json.loads(COMPLEX.read_text())
    for group, payload in panel.get("groups", {}).items():
        for series in payload.get("series", []):
            tickers.add(series["ticker"])
    return sorted(tickers)


def main() -> int:
    import yfinance as yf

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    CLOSE_CACHE.mkdir(parents=True, exist_ok=True)
    VOLUME_CACHE.mkdir(parents=True, exist_ok=True)

    tickers = universe()
    missing = [t for t in tickers if not (CLOSE_CACHE / f"{t}.json").exists()]
    if args.limit:
        missing = missing[:args.limit]
    print(f"universe {len(tickers)} | cached {len(tickers) - len(missing)} | fetching {len(missing)}",
          flush=True)

    fetched = empty = failed = 0
    for position, ticker in enumerate(missing, start=1):
        try:
            frame = yf.download(ticker, start=START, progress=False, auto_adjust=False, threads=False)
        except Exception as error:
            failed += 1
            print(f"  {ticker}: download failed ({error})", flush=True)
            continue
        if frame is None or frame.empty:
            empty += 1
            continue
        if hasattr(frame.columns, "nlevels") and frame.columns.nlevels > 1:
            frame = frame.droplevel(1, axis=1)
        closes, bars = {}, []
        for index, row in frame.iterrows():
            try:
                close_value = float(row["Close"])
                volume_value = float(row["Volume"])
            except (TypeError, ValueError, KeyError):
                continue
            if close_value <= 0:
                continue
            day = str(index)[:10]
            closes[day] = close_value
            bars.append({"date": day, "close": close_value,
                         "volume": volume_value if volume_value > 0 else 0.0})
        if not closes:
            empty += 1
            continue
        (CLOSE_CACHE / f"{ticker}.json").write_text(json.dumps(closes))
        (VOLUME_CACHE / f"{ticker}.json").write_text(json.dumps(bars))
        fetched += 1
        if position % 50 == 0:
            print(f"  {position}/{len(missing)} fetched {fetched} empty {empty} failed {failed}",
                  flush=True)
        time.sleep(0.05)
    print(f"done: fetched {fetched}, empty {empty}, failed {failed} of {len(missing)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
