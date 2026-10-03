#!/usr/bin/env python3
"""Build the promised-work panel: reported balances, when they were reported, and how they changed.

This is the first real number in the study. It answers one question only: for each firm, what did the
disclosed obligations do over time, and how long after the period end did each number become public?

What it deliberately does not do:

- It does not label a delay. A fall in remaining performance obligations is a revision to contracted
  work, not proof of a slipped project, and it names no project.
- It does not pool fields. Remaining obligations and unapproved change orders are different objects
  from different sections, and the audit says never to merge them into one score.
- It does not report the sealed window, which is 120 filings and stays closed until the sealed test.

Usage:
    python scripts/build_obligation_panel.py --tickers PWR,ETN --out results/obligation-panel.csv
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

from edgar.filings import TICKERS_URL, get_json, session  # noqa: E402
from edgar.xbrl import attach_availability, days_to_public, extract, load_company_facts, revisions  # noqa: E402

FIELDS = ["ticker", "cik", "concept", "unit", "period_end", "value", "previous_value", "change",
          "days_to_public", "form", "filed", "accession", "acceptance_utc",
          "earliest_availability_utc", "availability_status", "in_sealed_window", "source_receipt"]


def as_bool(value) -> bool:
    """CSV gives strings, so "False" is truthy. That bug would have summarised the sealed window."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes")


def read_register(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"{path} is missing. Run scripts/build_filings_register.py first")
    with path.open() as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["in_sealed_window"] = as_bool(row.get("in_sealed_window"))
    return rows


def summarise(rows: list[dict]) -> str:
    sealed = [r for r in rows if as_bool(r.get("in_sealed_window"))]
    open_rows = [r for r in rows if not as_bool(r.get("in_sealed_window"))]
    # A lag can only be trusted where the filing that reported the number is in the register.
    dated = [r for r in open_rows if r.get("acceptance_utc")]
    undated = [r for r in open_rows if not r.get("acceptance_utc")]
    dev = dated
    lines = [f"facts: {len(rows)}   development: {len(open_rows)}   sealed and not summarised: {len(sealed)}",
             f"development facts with a matched acceptance timestamp: {len(dated)}/{len(open_rows)}",
             f"excluded from the summary for having no matched filing row: {len(undated)}"]
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in dev:
        groups[(row["ticker"], row["concept"])].append(row)
    lines.append("")
    lines.append(f"{'firm':5s} {'field':52s} {'n':>3s} {'range':>21s} {'changes':>9s} {'down':>5s} {'lag days':>9s}")
    for (ticker, concept), group in sorted(groups.items()):
        periods = sorted(r["period_end"] for r in group if r.get("period_end"))
        changes = [r for r in group
                   if isinstance(r.get("change"), (int, float)) and r["change"] != 0]
        downs = [r for r in changes if r["change"] < 0]
        lags = [d for d in (days_to_public(r) for r in group) if d is not None]
        median_lag = f"{statistics.median(lags):.0f}" if lags else "n/a"
        span = f"{periods[0]}..{periods[-1]}" if periods else "n/a"
        lines.append(f"{ticker:5s} {concept.split(':')[-1][:52]:52s} {len(group):3d} {span:>21s} "
                     f"{len(changes):9d} {len(downs):5d} {median_lag:>9s}")
    lines.append("")
    lines.append("A change is period over period. A fall means contracted work left the book, which is a")
    lines.append("revision to a promise, not proof of a delayed project. Fields are never pooled.")
    lines.append("lag days = period end to the filing that first made the number public.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", default="PWR,ETN")
    parser.add_argument("--register", default="results/filings-register.csv")
    parser.add_argument("--out", default="results/obligation-panel.csv")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    register = read_register(ROOT / args.register)
    s = session()
    lookup = get_json(s, TICKERS_URL, cache_name="company_tickers.json")

    rows: list[dict] = []
    for ticker in tickers:
        cik = next((int(r["cik_str"]) for r in lookup.values() if r["ticker"] == ticker), None)
        if cik is None:
            print(f"{ticker}: not in the SEC ticker map, skipped")
            continue
        payload = load_company_facts(cik, s)
        extracted = extract(payload, cik, ticker)
        joined = attach_availability(extracted, register)
        annotated = revisions(joined)
        for row in annotated:
            row["days_to_public"] = days_to_public(row)
        rows.extend(annotated)
        print(f"{ticker}: {len(extracted)} facts for the tracked fields")

    if not rows:
        print("no facts found. Check the ticker list and the register")
        return 1

    for row in rows:
        row.setdefault("previous_value", "")
        row.setdefault("change", "")
        row.setdefault("days_to_public", "")

    if not args.summary:
        out = ROOT / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {out.relative_to(ROOT)} ({len(rows)} rows)")
    print(summarise(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
