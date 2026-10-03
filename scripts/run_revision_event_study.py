#!/usr/bin/env python3
"""Measure what a firm's own disclosed revision did to its own price, without tuning.

Why the firm-level channel and not the project-level one: an EIA entity is a developer or operator, and
93.8 percent of slipped capacity sits with project companies and private developers, so a project cannot
be attributed to a listed equity with evidence. A firm that discloses its own obligations can be, and its
disclosure carries its own acceptance timestamp.

The rubric this answers to: lag every signal by at least one session, report abnormal next to raw, report
the horizon plateau rather than its peak, keep the sealed window closed, and never elect a horizon from
the results.

Usage:
    python scripts/run_revision_event_study.py --horizons 1,2,5,10,20
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from edgar.filings import sealed_start  # noqa: E402
from event.study import abnormal, summarise, surprise, window_return  # noqa: E402

BENCHMARK = {"PWR": "XLI", "EME": "XLI", "ETN": "XLI", "DLR": "XLRE"}
MARKET = "SPY"


def bars(ticker: str, start: str, end: str) -> dict[str, float]:
    """Adjusted closes by session, which is what a multi-session return needs.

    The frame index format varies by provider version, so the session key is taken from the string form
    rather than assumed to be a timestamp object.
    """
    import yfinance as yf
    try:
        frame = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=True)
    except Exception as exc:  # a data outage must not look like a result
        print(f"{ticker}: bars unavailable ({type(exc).__name__})")
        return {}
    if frame is None or len(frame) == 0 or "Close" not in frame:
        return {}
    out: dict[str, float] = {}
    for stamp, value in frame["Close"].items():
        try:
            out[str(stamp)[:10]] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def revisions(panel_path: Path, horizons: list[int]) -> list[dict]:
    with panel_path.open() as handle:
        facts = list(csv.DictReader(handle))
    out: list[dict] = []
    for row in facts:
        if str(row.get("in_sealed_window", "")).lower() in ("true", "1"):
            continue
        if not row.get("earliest_availability_utc") or not row.get("change"):
            continue
        try:
            change = float(row["change"])
        except (TypeError, ValueError):
            continue
        out.append({"ticker": row["ticker"], "concept": row["concept"],
                    "period_end": row["period_end"], "change": change,
                    "available": row["earliest_availability_utc"],
                    "benchmark": BENCHMARK.get(row["ticker"], MARKET)})
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", default="results/obligation-panel.csv")
    parser.add_argument("--horizons", default="1,2,5,10,20")
    parser.add_argument("--history-end", default=dt.date.today().isoformat())
    parser.add_argument("--out", default="results/revision-events.csv")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)

    horizons = [int(h) for h in args.horizons.split(",")]
    events = revisions(ROOT / args.panel, horizons)
    if not events:
        print("no timestamped revisions in the panel")
        return 1

    tickers = sorted({e["ticker"] for e in events} | {e["benchmark"] for e in events} | {MARKET})
    start = min(e["period_end"] for e in events if e["period_end"])
    series = {ticker: bars(ticker, start, args.history_end) for ticker in tickers}
    for ticker, closes in series.items():
        if not closes:
            print(f"{ticker}: no daily bars returned")
    index = {ticker: sorted(series[ticker]) for ticker in tickers}

    history: dict[tuple, list[float]] = defaultdict(list)
    rows: list[dict] = []
    for event in sorted(events, key=lambda e: e["available"]):
        key = (event["ticker"], event["concept"])
        row = dict(event)
        for horizon in horizons:
            raw = window_return(series[event["ticker"]], index[event["ticker"]],
                                event["available"], horizon)
            bench = window_return(series[event["benchmark"]], index[event["benchmark"]],
                                  event["available"], horizon)
            market = window_return(series[MARKET], index[MARKET], event["available"], horizon)
            row[f"raw_{horizon}"] = raw
            row[f"abnormal_{horizon}"] = abnormal(raw, bench)
            row[f"abnormal_market_{horizon}"] = abnormal(raw, market)
        row["typical_change"] = statistics.median(history[key]) if history[key] else None
        row["surprise"] = surprise(event["change"], history[key]) if history[key] else None
        history[key].append(event["change"])
        rows.append(row)

    fields = (["ticker", "concept", "period_end", "change", "typical_change", "surprise",
               "available", "benchmark"]
              + [f"{kind}_{h}" for h in horizons for kind in ("raw", "abnormal", "abnormal_market")])
    if not args.summary:
        out = ROOT / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {out.relative_to(ROOT)} ({len(rows)} rows)")
    print(summarise(rows, horizons))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
