#!/usr/bin/env python3
"""Build the timestamped filings register for a predeclared universe.

Why: the audit of 2026-10-03 found fifteen annual-filing observations and no resolved first-public
timestamp, so nothing was eligible for a timed test. This writes the register that fixes it, and it
refuses to summarise the sealed window without an explicit flag.

Usage:
    python scripts/build_filings_register.py --tickers PWR,ETN,EME,DLR --out results/filings-register.csv
    python scripts/build_filings_register.py --tickers PWR --summary
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from edgar.filings import build_rows, sealed_start  # noqa: E402

FIELDS = ["ticker", "cik", "form", "filed_date", "acceptance_utc", "acceptance_et",
          "earliest_availability_utc", "processing_lag_minutes", "timestamp_status", "period",
          "items", "candidate_surface", "surface_reason", "in_sealed_window",
          "press_release_unchecked", "document_url", "source_receipt"]


def summarise(rows: list[dict], sealed_from: dt.date, include_sealed: bool) -> str:
    dev = [r for r in rows if not r.get("in_sealed_window")]
    sealed = [r for r in rows if r.get("in_sealed_window")]
    lines = []
    lines.append(f"rows: {len(rows)}   development window: {len(dev)}   sealed window: {len(sealed)}")
    lines.append(f"sealed window starts: {sealed_from.isoformat()} "
                 f"(shorter of the last fifth of history or two years)")
    named = [r for r in dev if r.get("acceptance_utc")]
    lines.append(f"development rows with a real acceptance timestamp: {len(named)}/{len(dev)}")
    surfaces = [r for r in dev if r.get("candidate_surface")]
    lines.append(f"development candidate surfaces: {len(surfaces)}")
    by_form = Counter(r["form"] for r in surfaces)
    if by_form:
        lines.append("  by form: " + ", ".join(f"{k} {v}" for k, v in sorted(by_form.items())))
    by_reason = Counter(r["surface_reason"] for r in surfaces)
    for reason, count in sorted(by_reason.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {count:5d}  {reason}")
    dated = sorted(r["filed_date"] for r in dev if r.get("filed_date"))
    if dated:
        lines.append(f"development range: {dated[0]} to {dated[-1]}")
    lines.append(f"press release precedence unresolved on every row: "
                 f"{sum(1 for r in dev if r.get('press_release_unchecked'))}/{len(dev)}")
    if include_sealed:
        lines.append("")
        lines.append(f"SEALED WINDOW SUMMARISED BY EXPLICIT REQUEST: {len(sealed)} rows, "
                     f"{sum(1 for r in sealed if r.get('candidate_surface'))} candidate surfaces. "
                     f"Nothing here may inform design.")
    else:
        lines.append("sealed window left unsummarised. Pass --include-sealed only at the sealed test.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", default="PWR,ETN,EME,DLR")
    parser.add_argument("--history-start", default="2015-01-01")
    parser.add_argument("--history-end", default=dt.date.today().isoformat())
    parser.add_argument("--lag-minutes", type=int, default=15)
    parser.add_argument("--out", default="results/filings-register.csv")
    parser.add_argument("--summary", action="store_true", help="print the summary only")
    parser.add_argument("--include-sealed", action="store_true",
                        help="summarise the sealed window. Only at the sealed test")
    args = parser.parse_args(argv)

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    start = dt.date.fromisoformat(args.history_start)
    end = dt.date.fromisoformat(args.history_end)
    sealed_from = sealed_start(start, end)

    rows = build_rows(tickers, start, end, lag_minutes=args.lag_minutes)
    for row in rows:
        for field in FIELDS:
            row.setdefault(field, "")

    if not args.summary:
        out = ROOT / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {out.relative_to(ROOT)} ({len(rows)} rows)")
    print(summarise(rows, sealed_from, args.include_sealed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
