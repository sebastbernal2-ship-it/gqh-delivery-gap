#!/usr/bin/env python3
"""Attribute slipped generation capacity to firms that have a price, and show what stays unattributed.

Input: the delivery revisions, which carry the entity EIA names for each generator.
Join:  those entity names against SEC registrant names, with a score and an audit trail.
Output: a per-firm exposure panel stamped with the moment the revision became public, plus the
coverage report that says how much capacity could not be attributed to any registrant.

The coverage is the honest headline. Most slipping projects belong to project companies and private
developers, and an EIA entity is the developer or operator, never the contractor and never the equipment
vendor. So this panel measures owner and operator exposure only.

Usage:
    python scripts/build_exposure_panel.py --revisions results/delivery-revisions.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from edgar.filings import TICKERS_URL, get_json, session  # noqa: E402
from join.entities import coverage, match_entities  # noqa: E402

MATCH_FIELDS = ["entity_name", "status", "score", "runner_up", "title", "ticker", "cik",
                "segment", "direction", "weight", "economic_channel", "identity_vintage", "source_receipt"]
PANEL_FIELDS = ["ticker", "entity_name", "pair", "technology", "state", "slips", "slipped_mw",
                "median_slip_months", "available_from", "status", "segment", "direction", "weight",
                "economic_channel", "identity_vintage", "evidence", "source_receipt"]


def load_candidates(s) -> list[tuple[str, int, str]]:
    payload = get_json(s, TICKERS_URL, cache_name="company_tickers.json")
    return [(row.get("title", ""), int(row["cik_str"]), row.get("ticker", "")) for row in payload.values()]


def slips_only(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        try:
            months = int(row.get("revision_months") or 0)
        except ValueError:
            continue
        if months > 0:
            out.append({**row, "slip_months": months})
    return out


def summarise(rows: list[dict], match_rows: list[dict]) -> str:
    stats = coverage(rows)
    total = sum(mw for mw in stats["by_status"].values()) or 1.0
    lines = [f"slip rows: {len(rows)}   entities: {len(match_rows)}"]
    for status, mw in sorted(stats["by_status"].items(), key=lambda kv: -kv[1]):
        lines.append(f"  {status:10s} {mw:12,.0f} MW   {mw / total:5.1%} of slipped capacity")
    if stats["by_ticker"]:
        lines.append("")
        lines.append("slipped capacity attributed to a registrant, by ticker:")
        for ticker, mw in sorted(stats["by_ticker"].items(), key=lambda kv: -kv[1])[:12]:
            lines.append(f"  {ticker:6s} {mw:12,.0f} MW")
    unmatched = [r for r in match_rows if r["status"] == "unmatched"]
    if unmatched:
        lines.append("")
        lines.append(f"largest unattributed entities ({len(unmatched)} of {len(match_rows)}):")
        ranked = sorted(rows, key=lambda r: -float(r.get("capacity_mw") or 0))
        seen: set[str] = set()
        for row in ranked:
            name = row["entity_name"]
            if row.get("match_status") != "unmatched" or name in seen:
                continue
            seen.add(name)
            lines.append(f"  {row['capacity_mw']:>7s} MW  {name[:52]}")
            if len(seen) >= 6:
                break
    lines.append("")
    lines.append("Attribution is not automated here. An entity appears as verified only through")
    lines.append("docs/entity-crosswalk.csv, where every row needs evidence. The candidate matcher runs")
    lines.append("but proposes, because on this data it produced a preferred share series and a mortgage")
    lines.append("insurer as owners of power plants.")
    lines.append("An EIA entity is a developer or operator. The contractor and the equipment vendor are")
    lines.append("not in this data at all, so this panel is owner and operator exposure only.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revisions", default="results/delivery-revisions.csv")
    parser.add_argument("--match-out", default="results/entity-matching.csv")
    parser.add_argument("--panel-out", default="results/exposure-panel.csv")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)

    with (ROOT / args.revisions).open() as handle:
        revisions = slips_only(list(csv.DictReader(handle)))
    if not revisions:
        raise SystemExit(f"no slipped rows in {args.revisions}")

    s = session()
    candidates = load_candidates(s)
    entities = sorted({row["entity_name"].strip() for row in revisions if row["entity_name"].strip()})
    matched = match_entities(entities, candidates)

    # Attribution is not automated. The candidate matcher proposes, and only a verified crosswalk
    # attributes. Measured evidence for refusing automation: it picked a preferred share series for
    # Georgia Power and a mortgage insurer for a power developer.
    crosswalk = {}
    crosswalk_path = ROOT / "docs" / "entity-crosswalk.csv"
    if crosswalk_path.exists():
        with crosswalk_path.open() as handle:
            for entry in csv.DictReader(handle):
                if entry.get("entity_name") and entry.get("status", "").strip() == "verified":
                    crosswalk[entry["entity_name"].strip()] = entry

    for row in revisions:
        name = row["entity_name"].strip()
        verified = crosswalk.get(name)
        proposal = matched.get(name, {})
        row["match_status"] = "verified" if verified else "proposed" if proposal.get("status") == "matched" \
            else proposal.get("status", "unmatched")
        row["ticker"] = verified["ticker"] if verified else ""
        row["cik"] = verified["cik"] if verified else ""
        row["title"] = verified.get("evidence", "") if verified else proposal.get("title", "")
        for field in ("segment", "direction", "weight", "economic_channel", "identity_vintage",
                      "source_receipt"):
            row[field] = verified.get(field, "") if verified else ""

    grouped: dict[tuple, dict] = defaultdict(lambda: {"slips": 0, "slipped_mw": 0.0, "months": [],
                                                      "available_from": "", "state": "",
                                                      "status": "unmatched", "segment": "",
                                                      "direction": "", "weight": "",
                                                      "economic_channel": "",
                                                      "identity_vintage": "", "evidence": "",
                                                      "source_receipt": ""})
    for row in revisions:
        key = (row["ticker"] or "", row["entity_name"], row["pair"], row["technology"])
        bucket = grouped[key]
        bucket["slips"] += 1
        try:
            bucket["slipped_mw"] += float(row["capacity_mw"] or 0)
        except ValueError:
            pass
        bucket["months"].append(row["slip_months"])
        if not bucket["available_from"] or row["available_after"] > bucket["available_from"]:
            bucket["available_from"] = row["available_after"]
        bucket["state"] = row.get("state", "")
        if row.get("match_status") == "verified":
            bucket["status"] = "verified"
            for field in ("segment", "direction", "weight", "economic_channel",
                          "identity_vintage", "source_receipt"):
                bucket[field] = row.get(field, "")
            bucket["evidence"] = row.get("title", "")
        elif bucket["status"] != "verified":
            bucket["status"] = row.get("match_status", "unmatched")

    panel = []
    for (ticker, entity, pair, technology), bucket in grouped.items():
        months = sorted(bucket["months"])
        panel.append({
            "ticker": ticker, "entity_name": entity, "pair": pair, "technology": technology,
            "state": bucket["state"], "slips": bucket["slips"],
            "slipped_mw": round(bucket["slipped_mw"], 1),
            "median_slip_months": months[len(months) // 2],
            "available_from": bucket["available_from"],
            "status": bucket["status"], "segment": bucket["segment"],
            "direction": bucket["direction"], "weight": bucket["weight"],
            "economic_channel": bucket["economic_channel"],
            "identity_vintage": bucket["identity_vintage"],
            "evidence": bucket["evidence"],
            "source_receipt": bucket["source_receipt"] or "https://www.eia.gov/electricity/data/eia860m/",
        })
    panel.sort(key=lambda r: (-r["slipped_mw"], r["entity_name"]))

    if not args.summary:
        for name, fields, rows in ((args.match_out, MATCH_FIELDS,
                                    [{"entity_name": entity, **match} for entity, match in matched.items()]),
                                   (args.panel_out, PANEL_FIELDS, panel)):
            out = ROOT / name
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            print(f"wrote {name} ({len(rows)} rows)")
    print(summarise(revisions, [{"entity_name": e, **m} for e, m in matched.items()]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
