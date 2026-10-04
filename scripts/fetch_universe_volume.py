#!/usr/bin/env python3
"""Fetch daily volume and close for the strategy universe, then write monthly dollar volume.

Universe: every ticker with both capex and revenue in the complex panel. Daily bars are cached under
results/bar-volume/ (ignored by git). The committed output is the monthly median dollar volume per name,
which is what the strategy needs for the capacity curve and the cost buckets.

    python3 scripts/fetch_universe_volume.py
"""
from __future__ import annotations

import collections
import csv
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE = ROOT / "results" / "complex-capex-quarterly.csv"
REVENUE = ROOT / "results" / "complex-revenue-quarterly.csv"
CACHE = ROOT / "results" / "bar-volume"
OUT = ROOT / "results" / "universe-adv-monthly.csv"
START = "2017-06-01"


def main() -> int:
    import yfinance as yf

    capex_tickers = {row["ticker"] for row in csv.DictReader(UNIVERSE.open())}
    revenue_tickers = {row["ticker"] for row in csv.DictReader(REVENUE.open())}
    tickers = sorted(capex_tickers & revenue_tickers)
    CACHE.mkdir(parents=True, exist_ok=True)

    monthly: dict[tuple[str, str], list[float]] = collections.defaultdict(list)
    for ticker in tickers:
        path = CACHE / f"{ticker}.json"
        if path.exists():
            rows = json.loads(path.read_text())
        else:
            try:
                frame = yf.download(ticker, start=START, progress=False, auto_adjust=False, threads=False)
            except Exception as error:
                print(f"  {ticker}: download failed ({error})")
                continue
            if frame is None or frame.empty:
                print(f"  {ticker}: empty frame")
                continue
            if hasattr(frame.columns, "nlevels") and frame.columns.nlevels > 1:
                frame = frame.droplevel(1, axis=1)
            rows = []
            for index, row in frame.iterrows():
                try:
                    close_value = float(row["Close"])
                    volume_value = float(row["Volume"])
                except (TypeError, ValueError, KeyError):
                    continue
                if close_value <= 0 or volume_value <= 0:
                    continue
                rows.append({"date": str(index)[:10], "close": close_value, "volume": volume_value})
            if rows:
                path.write_text(json.dumps(rows))
            print(f"  {ticker}: {len(rows)} bars")
        for row in rows:
            monthly[(ticker, row["date"][:7])].append(row["close"] * row["volume"])

    with OUT.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ticker", "month", "adv_usd", "bars"])
        for (ticker, month), values in sorted(monthly.items()):
            writer.writerow([ticker, month, round(statistics.median(values)), len(values)])
    names = len({ticker for ticker, _ in monthly})
    months = sorted({month for _, month in monthly})
    print(f"wrote {OUT.relative_to(ROOT)}: {len(monthly)} name-months across {names} names, "
          f"{months[0] if months else 'n/a'} to {months[-1] if months else 'n/a'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
