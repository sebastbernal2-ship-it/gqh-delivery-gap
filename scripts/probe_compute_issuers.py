#!/usr/bin/env python3
"""Ask whether any listed issuer carries one compute rental family in its reported revenue.

The compute relative value candidate failed the instrument gate because the only expression looked like
diversified provider equity. That judgement was an assumption. This decides it from the issuers' own XBRL
filings: for each declared issuer, take the latest annual report, read its revenue facts together with their
dimensional members, and report how concentrated reported revenue is.

An issuer whose whole business is compute rental is concentrated by construction, and its segment note adds
nothing. An issuer with several reported segments tells us exactly how much of its revenue the rental business
carries, which is the dilution we need to measure.

Usage:
    python scripts/probe_compute_issuers.py [--out results/compute-issuer-segments.csv]
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from edgar.filings import get_json, session  # noqa: E402

CACHE = ROOT / "data" / "sec-instances"

# Declared issuers, with the reason each is here. Renters are the direct exposure. Suppliers are the dilution
# test. Data centre and power names are the second order exposure.
ISSUERS = {
    "CRWV": "AI cloud rental, whole business",
    "NBIS": "AI cloud and infrastructure, whole business",
    "APLD": "data centre and compute hosting",
    "IREN": "bitcoin mining to AI cloud pivot",
    "WULF": "bitcoin mining to compute hosting",
    "CORZ": "bitcoin mining to compute hosting",
    "CIFR": "bitcoin mining with compute hosting",
    "HUT": "mining and compute hosting",
    "GLXY": "digital asset and compute infrastructure",
    "SMCI": "GPU server supplier",
    "DELL": "server and storage supplier, diversified",
    "HPE": "server supplier, diversified",
    "VRT": "data centre power and cooling",
    "DLR": "data centre REIT, diversified",
    "EQIX": "data centre REIT, diversified",
    "ETN": "electrical equipment, diversified",
    "PWR": "electrical construction, diversified",
}
KEYWORDS = ("comput", "gpu", "cloud", "rental", "hosting", "data cent", "colocation", "ai ", "ai,")

REVENUE = re.compile(r"^(us-gaap:)?(Revenue|Revenues|RevenueFromContractWithCustomer"
                     r"(ExcludingAssessedTax|IncludingAssessedTax))$")


def local(tag: str) -> str:
    return tag.split("}")[-1]


def parse_instant(payload: str) -> str:
    return payload.strip()


def latest_annual(session_obj, cik: int) -> tuple[str, str, str]:
    sub = get_json(session_obj, f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
    recent = sub["filings"]["recent"]
    for form, accession, report, filed in zip(recent["form"], recent["accessionNumber"],
                                              recent["reportDate"], recent["filingDate"]):
        if form == "10-K":
            return accession, report, filed
    raise SystemExit("no annual report found")


def instance_path(session_obj, cik: int, accession: str) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    acc = accession.replace("-", "")
    target = CACHE / f"{cik}-{acc}.xml"
    if target.exists() and target.stat().st_size > 1000:
        return target
    index = get_json(session_obj, f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/index.json")
    names = [item["name"] for item in index["directory"]["item"]]
    instance = next((n for n in names if n.endswith("_htm.xml")), None)
    if instance is None:
        raise SystemExit(f"no instance document in {accession}")
    body = get_json(session_obj, f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{instance}",
                    raw=True) if hasattr(get_json, "raw") else None
    if body is None:
        import requests  # local import: only used when the instance is not cached
        response = session_obj.get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{instance}")
        response.raise_for_status()
        body = response.text
    target.write_text(body)
    return target


def revenue_by_member(path: Path) -> dict:
    """One axis, chosen as the one that best covers reported revenue, then shares within it.

    Facts carrying several axes at once are combinations, so they are kept separately from single axis facts.
    The default member that means the total across all segments is dropped, because it restates the total.
    """
    root = ET.parse(path).getroot()
    contexts: dict[str, dict] = {}
    for element in root:
        if local(element.tag) != "context":
            continue
        identifier = element.get("id")
        start = end = None
        members = []
        for child in element.iter():
            name = local(child.tag)
            if name == "startDate":
                start = parse_instant(child.text or "")
            elif name == "endDate":
                end = parse_instant(child.text or "")
            elif name == "explicitMember":
                dimension = local(child.get("dimension", ""))
                member = local((child.text or "").strip())
                if member in ("OperatingSegmentsMember", "AllOtherSegmentsMember", "ConsolidationItemsMember"):
                    continue
                members.append((dimension, member))
        contexts[identifier] = {"start": start, "end": end, "members": members}

    facts = []
    for element in root:
        if not REVENUE.match(local(element.tag)):
            continue
        context = contexts.get(element.get("contextRef"))
        if not context or not context["start"] or not context["end"]:
            continue
        try:
            value = float(element.text or "nan")
        except ValueError:
            continue
        facts.append((context, value))
    if not facts:
        return {"period": None, "total": None, "breakdown": {}, "axis": "", "durations": 0}

    longest = max(facts, key=lambda item: _days(item[0]["start"], item[0]["end"]))
    start, end = longest[0]["start"], longest[0]["end"]
    same = [item for item in facts if item[0]["start"] == start and item[0]["end"] == end]

    total = None
    groups: dict[tuple, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for context, value in same:
        axes = tuple(sorted({dimension for dimension, _ in context["members"]}))
        if not axes:
            total = max(total or 0.0, value)
            continue
        label = " | ".join(member for _, member in context["members"])
        groups[axes][label] += value

    # choose the axis whose facts come closest to the reported total without overshooting it badly
    def fits(group):
        summed = sum(group.values())
        if total:
            return abs(summed - total) / total
        return abs(summed)

    axis, breakdown = ((), {})
    for axes, group in groups.items():
        if not breakdown or fits(group) < fits(breakdown):
            axis, breakdown = axes, group
    return {"period": f"{start} to {end}", "total": total, "breakdown": dict(breakdown),
            "axis": ", ".join(axis), "durations": len({(item[0]["start"], item[0]["end"]) for item in facts})}


def _days(start: str, end: str) -> int:
    from datetime import date
    a = date.fromisoformat(start)
    b = date.fromisoformat(end)
    return (b - a).days


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="results/compute-issuer-segments.csv")
    parser.add_argument("--tickers", default=",".join(ISSUERS))
    args = parser.parse_args(argv)
    wanted = [t.strip() for t in args.tickers.split(",") if t.strip()]

    s = session()
    from edgar.filings import ticker_map
    mapping = ticker_map(s)
    rows = []
    for ticker in wanted:
        cik = mapping.get(ticker)
        if not cik:
            print(f"{ticker:6s} no CIK")
            continue
        try:
            accession, report, filed = latest_annual(s, cik)
            path = instance_path(s, cik, accession)
            result = revenue_by_member(path)
        except SystemExit as exc:
            print(f"{ticker:6s} {exc}")
            continue
        total = result["total"]
        members = result["breakdown"]
        named = {k: v for k, v in members.items() if any(word in k.lower() for word in KEYWORDS)}
        share = (sum(named.values()) / sum(members.values())) if members else None
        rows.append({
            "ticker": ticker, "cik": cik, "why": ISSUERS.get(ticker, ""),
            "fiscal_year_end": report, "filed": filed, "period": result["period"],
            "total_revenue": round(total, 1) if total else "",
            "segment_axis": result["axis"],
            "segments_reported": len(members),
            "rental_like_segments": len(named),
            "rental_like_share": round(share, 4) if share is not None else "",
            "largest_segment": max(members, key=members.get) if members else "",
            "largest_segment_share": round(max(members.values()) / sum(members.values()), 4) if members else "",
        })
        largest = max(members, key=members.get) if members else ""
        largest_share = (max(members.values()) / sum(members.values())) if members else 0.0
        print(f"{ticker:6s} FY{report} total {('' if total is None else f'{total/1e6:,.0f}M'):>10s} "
              f"members {len(members):>2d} rental-like {len(named):>2d} "
              f"share {('' if share is None else f'{share:.0%}'):>5s} "
              f"largest {('' if not members else f'{largest_share:.0%}'):>5s} {largest[:44]}")

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else
                                ["ticker", "cik", "why", "fiscal_year_end", "filed", "period",
                                 "total_revenue", "segment_axis", "segments_reported",
                                 "rental_like_segments", "rental_like_share", "largest_segment",
                                 "largest_segment_share"],
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.out} ({len(rows)} issuers)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
