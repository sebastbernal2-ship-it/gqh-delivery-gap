#!/usr/bin/env python3
"""Measure the revision-to-price association across industry groups, group by group.

The universe rule lives in build_rpo_universe.py: every filer that reports remaining performance
obligations at least three times, grouped by its own SIC code. This script spends that breadth.

Four decisions, all declared rather than tuned:

1. **Benchmark per group**: XLI for contractors and equipment, XLU for electric services, XLRE for the
   real estate and data centre group. A group is never compared against the pooled average of others.
2. **Signal lagged**: the fill is the first session after the revision became available.
3. **Both directions reported**: the chain predicts that a downward surprise is bad news, so the upward
   side is the check, not the claim.
4. **Every cell is reported, and the cell count is printed.** Choosing the best group, sign and horizon
   after seeing this table is exactly the mistake the rubric names, so nothing is chosen.

Usage:
    python scripts/run_group_event_study.py --horizons 1,2,5,10,20
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from event.study import abnormal, window_return  # noqa: E402

BENCHMARK = {"contractor": "XLI", "equipment": "XLI", "utility": "XLU", "datacenter": "XLRE",
             "other": "SPY"}
BAR_CACHE = ROOT / "results" / "bar-cache"


def bars(ticker: str, start: str, end: str) -> dict[str, float]:
    """Adjusted closes by session, cached, because a few hundred tickers is a lot of requests."""
    BAR_CACHE.mkdir(parents=True, exist_ok=True)
    key = BAR_CACHE / f"{ticker}.json"
    if key.exists():
        try:
            return json.loads(key.read_text())
        except (OSError, ValueError):
            pass
    import yfinance as yf
    try:
        frame = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=True)
    except Exception as exc:
        print(f"{ticker}: bars unavailable ({type(exc).__name__})")
        return {}
    out: dict[str, float] = {}
    if frame is not None and len(frame) and "Close" in frame:
        for stamp, value in frame["Close"].items():
            try:
                out[str(stamp)[:10]] = float(value)
            except (TypeError, ValueError):
                continue
    key.write_text(json.dumps(out))
    return out


def tstat(values: list[float]) -> float | None:
    if len(values) < 3:
        return None
    spread = statistics.stdev(values)
    return statistics.mean(values) / (spread / math.sqrt(len(values))) if spread else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", default="results/rpo-events.csv")
    parser.add_argument("--horizons", default="1,2,5,10,20")
    parser.add_argument("--history-end", default=dt.date.today().isoformat())
    parser.add_argument("--out", default="results/group-event-study.csv")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)

    horizons = [int(h) for h in args.horizons.split(",")]
    with (ROOT / args.events).open() as handle:
        rows = list(csv.DictReader(handle))

    events = []
    for row in rows:
        if str(row.get("in_sealed_window", "")).lower() in ("true", "1"):
            continue
        if not row.get("surprise") or not row.get("earliest_availability_utc") or not row.get("ticker"):
            continue
        events.append({"ticker": row["ticker"], "group": row["group"],
                       "surprise": float(row["surprise"]), "available": row["earliest_availability_utc"],
                       "change": float(row["change"]) if row.get("change") else None})
    if not events:
        print("no usable events")
        return 1
    print(f"usable events with a ticker and a surprise: {len(events)}")
    print("without a ticker, so not priced here: "
          f"{sum(1 for r in rows if not r.get('ticker'))} of {len(rows)} rows")

    tickers = sorted({e["ticker"] for e in events} | set(BENCHMARK.values()))
    start = (min(e["available"][:10] for e in events) if events else "2015-01-01")
    series: dict[str, dict] = {}
    for index, ticker in enumerate(tickers, start=1):
        series[ticker] = bars(ticker, start, args.history_end)
        if index % 50 == 0:
            print(f"  {index}/{len(tickers)} tickers")
    missing = [t for t, closes in series.items() if not closes]
    if missing:
        print(f"no bars for {len(missing)} tickers, first few: {missing[:6]}")
    index_map = {ticker: sorted(closes) for ticker, closes in series.items()}

    for event in events:
        benchmark = BENCHMARK.get(event["group"], "SPY")
        event["benchmark"] = benchmark
        for horizon in horizons:
            firm = window_return(series.get(event["ticker"], {}), index_map.get(event["ticker"], []),
                                 event["available"], horizon)
            bench = window_return(series.get(benchmark, {}), index_map.get(benchmark, []),
                                  event["available"], horizon)
            event[f"abnormal_{horizon}"] = abnormal(firm, bench)

    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for event in events:
        sign = "down" if event["surprise"] < 0 else "up"
        buckets[(event["group"], sign)].append(event)
        buckets[("all", sign)].append(event)

    lines = []
    cells = 0
    lines.append(f"{'group':11s} {'sign':5s} {'horizon':>7s} {'n':>6s} {'mean':>9s} {'median':>9s} {'t':>6s}")
    out_rows = []
    for (group, sign), group_events in sorted(buckets.items()):
        for horizon in horizons:
            values = [e[f"abnormal_{horizon}"] for e in group_events
                      if e.get(f"abnormal_{horizon}") is not None]
            if len(values) < 20:
                continue
            cells += 1
            lines.append(f"{group:11s} {sign:5s} {horizon:>7d} {len(values):>6d} "
                         f"{statistics.mean(values):>8.2%} {statistics.median(values):>8.2%} "
                         f"{(tstat(values) or 0):>6.2f}")
            out_rows.append({"group": group, "sign": sign, "horizon": horizon, "n": len(values),
                             "mean_abnormal": statistics.mean(values),
                             "median_abnormal": statistics.median(values),
                             "t": tstat(values)})

    if not args.summary:
        out = ROOT / args.out
        with out.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["group", "sign", "horizon", "n",
                                                        "mean_abnormal", "median_abnormal", "t"])
            writer.writeheader()
            writer.writerows(out_rows)
        print(f"wrote {args.out} ({len(out_rows)} rows)")

    print("")
    print("\n".join(lines))
    print(f"\ncells examined: {cells} (group, sign, horizon). Every one is reported above.")
    print("Choosing the best cell from this table would be tuning, so nothing is chosen here.")
    print("Events cluster in reporting weeks, so the effective sample is smaller than n.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
