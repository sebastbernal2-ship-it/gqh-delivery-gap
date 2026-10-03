#!/usr/bin/env python3
"""Build a firm-level revision panel with breadth, using one mechanical rule.

The rule, declared once and applied uniformly: **every filer that reports remaining performance
obligations in any quarter of the development window is in the universe**, grouped by its own SIC code.
Nothing is hand-picked, and no company is dropped because it looked unhelpful.

Why remaining performance obligations: it is the one field that appears across industries, and it is the
firm-level trace of the same object the delivery panel measures at project level, which is work that is
promised but not yet done.

Sources, all joined on identifiers rather than names:
- XBRL frames give every filer's value for one field in one quarter, with the accession that reported it.
- Submissions give each filer's SIC code, name, ticker and the acceptance timestamp of each accession.

The rubric this answers to: a point-in-time availability for every event, no sealed data, and nothing
chosen by outcome.

Usage:
    python scripts/build_rpo_universe.py --start-quarter 2015Q1 --end-quarter 2024Q3
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from edgar.filings import OLD_SUBMISSIONS_URL, SUBMISSIONS_URL, sealed_start  # noqa: E402
from edgar.xbrl import facts_url  # noqa: E402

CONCEPT = "RevenueRemainingPerformanceObligation"
# A revision needs a history, so a filer must report the field at least this many times.
MIN_FACTS = 3
FRAMES = "https://data.sec.gov/api/xbrl/frames/us-gaap/{concept}/USD/{period}.json"
CACHE = ROOT / "results" / "edgar-cache"
USER_AGENT = "gqh-delivery-gap research research@example.com"

# Declared before any result was seen. A group is reported separately, never pooled into the best cell.
GROUPS = {
    "contractor": "electrical and mechanical contractors",
    "equipment": "electric equipment and components",
    "utility": "electric services and power producers",
    "datacenter": "real estate, including data centre owners",
    "other": "everything else that reports the field",
}
SIC_GROUP = {
    "1731": "contractor",   # electrical work
    "1799": "contractor",   # special trade contractors
    "1540": "contractor",   # general building contractors, nonresidential
    "1629": "contractor",   # heavy construction, not elsewhere classified
    "3612": "equipment",    # power and distribution transformers
    "3613": "equipment",    # switchgear and switchboard apparatus
    "3621": "equipment",    # motors and generators
    "3641": "equipment",    # lighting
    "3674": "equipment",    # semiconductors
    "3679": "equipment",    # electronic components
    "3600": "equipment",    # electronic and other electrical equipment
    "3510": "equipment",    # engines and turbines
    "3823": "equipment",    # industrial instruments
    "4911": "utility",      # electric services
    "4931": "utility",      # electric and other services combined
    "4991": "utility",      # cogeneration
    "4912": "utility",      # electric services, combined
    "6798": "datacenter",   # real estate investment trusts
    "7372": "datacenter",   # computer programming and data processing
    "7374": "datacenter",   # computer processing and data preparation
    "7370": "datacenter",   # computer services
    "7371": "datacenter",   # computer programming services
    "4813": "datacenter",   # telephone communications, the connectivity layer
}

EVENT_FIELDS = ["cik", "name", "ticker", "sic", "group", "period_end", "value", "previous_value",
                "change", "typical_change", "surprise", "form", "accession", "acceptance_utc",
                "earliest_availability_utc", "availability_resolution", "in_sealed_window",
                "source_receipt"]
UNIVERSE_FIELDS = ["cik", "name", "ticker", "sic", "sic_description", "group", "facts", "first_end",
                   "last_end"]


def quarters(start: str, end: str) -> list[str]:
    """Calendar quarters as the frames endpoint wants them, with the instant suffix."""
    first_year, first_quarter = int(start[:4]), int(start[-1])
    last_year, last_quarter = int(end[:4]), int(end[-1])
    out = []
    year, quarter = first_year, first_quarter
    while (year, quarter) <= (last_year, last_quarter):
        out.append(f"CY{year}Q{quarter}I")
        quarter += 1
        if quarter == 5:
            year, quarter = year + 1, 1
    return out


def fetch_json(url: str, cache: Path, tries: int = 4) -> dict:
    cache.mkdir(parents=True, exist_ok=True)
    key = cache / (url.replace("https://", "").replace("/", "_")[:180] + ".json")
    if key.exists():
        try:
            return json.loads(key.read_text())
        except (OSError, ValueError):
            pass
    delay = 15
    for attempt in range(tries):
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=90)
        if response.status_code == 200:
            payload = response.json()
            key.write_text(json.dumps(payload))
            time.sleep(0.4)
            return payload
        if response.status_code == 404:
            return {}
        if attempt < tries - 1:
            time.sleep(delay)
            delay *= 2
    return {}


def frame_rows(period: str, cache: Path) -> list[dict]:
    payload = fetch_json(FRAMES.format(concept=CONCEPT, period=period), cache)
    return payload.get("data", []) if payload else []


def acceptance_map(cik: int, cache: Path) -> dict[str, str]:
    """Accession to acceptance timestamp, for every filing of one company."""
    out: dict[str, str] = {}
    payload = fetch_json(SUBMISSIONS_URL.format(cik=cik), cache)
    if not payload:
        return out
    blocks = [payload.get("filings", {}).get("recent", {})]
    for extra in payload.get("filings", {}).get("files", [])[:6]:
        name = extra.get("name")
        if name:
            older = fetch_json(OLD_SUBMISSIONS_URL.format(name=name), cache)
            if older:
                blocks.append(older)
    for block in blocks:
        accessions = block.get("accessionNumber", [])
        stamps = block.get("acceptanceDateTime", [])
        for i, accession in enumerate(accessions):
            if i < len(stamps) and stamps[i]:
                out[accession] = stamps[i]
    return out


def filed_map(cik: int, cache: Path) -> dict[str, tuple[str, str]]:
    """Accession to (filing date, form), from one company facts request.

    Frames give the value and the accession, and company facts give that accession's filing date, so a
    revision can be stamped with when it became public without guessing.
    """
    payload = fetch_json(facts_url(cik), cache)
    out: dict[str, tuple[str, str]] = {}
    for namespace, entries in (payload.get("facts") or {}).items():
        for name, body in entries.items():
            if name != CONCEPT:
                continue
            for facts in (body.get("units") or {}).values():
                for fact in facts:
                    accession = fact.get("accn")
                    if accession and accession not in out:
                        out[accession] = (fact.get("filed", ""), fact.get("form", ""))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-quarter", default="2015Q1")
    parser.add_argument("--end-quarter", default="2024Q3")
    parser.add_argument("--history-start", default="2015-01-01")
    parser.add_argument("--history-end", default=dt.date.today().isoformat())
    parser.add_argument("--out", default="results/rpo-frames.csv")
    parser.add_argument("--universe-out", default="results/rpo-universe.csv")
    parser.add_argument("--max-filers", type=int, default=1200)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)

    boundary = sealed_start(dt.date.fromisoformat(args.history_start),
                            dt.date.fromisoformat(args.history_end))
    periods = quarters(args.start_quarter, args.end_quarter)

    facts: list[dict] = []
    for period in periods:
        rows = frame_rows(period, CACHE)
        facts.extend(rows)
        print(f"{period}: {len(rows)} filer values")
    if not facts:
        print("no frames returned")
        return 1

    # The universe rule, declared: every filer that reports the field at least MIN_FACTS times in the
    # window is in, grouped by its own SIC code. A company is never dropped for looking unhelpful, and
    # an industry group is never chosen by how it performed. A minimum history is needed only because a
    # revision requires something to compare against.
    per_cik: dict[int, list[dict]] = defaultdict(list)
    for row in facts:
        per_cik[int(row["cik"])].append(row)
    ranked = sorted(c for c in per_cik if len(per_cik[c]) >= MIN_FACTS)
    print(f"filers reporting the field: {len(per_cik)}   with at least {MIN_FACTS} facts: {len(ranked)}")

    universe: list[dict] = []
    for index, cik in enumerate(ranked, start=1):
        payload = fetch_json(SUBMISSIONS_URL.format(cik=cik), CACHE)
        if not payload:
            continue
        sic = str(payload.get("sic") or "")
        rows = per_cik[cik]
        tickers = payload.get("tickers") or []
        universe.append({"cik": cik, "name": payload.get("name", ""),
                         "ticker": tickers[0] if tickers else "", "sic": sic,
                         "sic_description": payload.get("sicDescription", ""),
                         "group": SIC_GROUP.get(sic, "other"), "facts": len(rows),
                         "first_end": min(r["end"] for r in rows),
                         "last_end": max(r["end"] for r in rows)})
        if index % 100 == 0:
            print(f"  classified {index}/{len(ranked)} companies")

    listed = [row for row in universe if row["group"] != "other"]
    print(f"\nin a declared industry group: {len(listed)} companies "
          f"({len(universe) - len(listed)} others form the placebo group)")

    if not args.summary:
        out = ROOT / args.universe_out
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=UNIVERSE_FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(universe)
        print(f"wrote {args.universe_out} ({len(universe)} rows)")

    by_group: dict[str, dict] = defaultdict(int)
    for row in universe:
        by_group[row["group"]] += 1
    print("")
    print(f"{'group':11s} {'companies':>9s}  what it is")
    for group, count in sorted(by_group.items(), key=lambda kv: -kv[1]):
        print(f"{group:11s} {count:>9d}  {GROUPS.get(group, '')}")
    print(f"\nsealed boundary: {boundary.isoformat()}")
    print("Pass two turns the selected companies into results/rpo-events.csv.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
