#!/usr/bin/env python3
"""Repair split artifacts in the bar cache by refetching adjusted closes.

A raw-close download shows a ten-for-one split as a ninety percent daily drop. Any cached series with
an unexplained drop below the declared bound is refetched with adjustment on. Volume is kept.

    python3 scripts/repair_unadjusted_bars.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLOSE_CACHE = ROOT / "results" / "bar-cache"
BOUND = -0.35


def suspicious(series: dict[str, float]) -> bool:
    days = sorted(series)
    for index in range(1, len(days)):
        previous, current = series[days[index - 1]], series[days[index]]
        if previous > 0 and current / previous - 1 < BOUND:
            return True
    return False


def main() -> int:
    import yfinance as yf

    argparse.ArgumentParser(description=__doc__).parse_args()
    flagged = []
    for path in sorted(CLOSE_CACHE.glob("*.json")):
        try:
            series = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(series, dict) and suspicious({str(k): float(v) for k, v in series.items()}):
            flagged.append(path.stem)
    print(f"flagged {len(flagged)} series", flush=True)
    fixed = failed = 0
    for position, ticker in enumerate(flagged, start=1):
        try:
            frame = yf.download(ticker, start="2017-01-01", progress=False, auto_adjust=True,
                                threads=False)
        except Exception:
            failed += 1
            continue
        if frame is None or frame.empty:
            failed += 1
            continue
        if hasattr(frame.columns, "nlevels") and frame.columns.nlevels > 1:
            frame = frame.droplevel(1, axis=1)
        closes = {}
        for index, row in frame.iterrows():
            try:
                close_value = float(row["Close"])
            except (TypeError, ValueError, KeyError):
                continue
            if close_value > 0:
                closes[str(index)[:10]] = close_value
        if closes:
            (CLOSE_CACHE / f"{ticker}.json").write_text(json.dumps(closes))
            fixed += 1
        if position % 50 == 0:
            print(f"  {position}/{len(flagged)} fixed {fixed} failed {failed}", flush=True)
    print(f"done: fixed {fixed}, failed {failed}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
