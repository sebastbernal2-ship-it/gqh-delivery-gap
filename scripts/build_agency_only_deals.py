#!/usr/bin/env python3
"""Find the deals the agencies describe and the SEC register does not, with their blockers written in.

Why, in one line: the gate that decides a trade is concentration, and the one deal with a published
concentration number, the Vantage Jersey SPV, has no ABS-15G filing anywhere in the register. So the question
is how many such deals exist and what each one is missing.

Method: take every located agency page, fetch them concurrently, pull the issuer, the series, the concentration
numbers and the operating metrics, and split the result into deals the register already holds and deals it
does not. The second group is the actionable list, and each entry carries its blocker rather than a guess.

Usage:
    python3 scripts/build_agency_only_deals.py [--workers 10]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE = ROOT / "results" / "agency-universe.csv"
STRUCTURE = ROOT / "results" / "deal-structure.csv"
OUT_CSV = ROOT / "results" / "agency-only-deals.csv"
OUT_JSON = ROOT / "results" / "agency-only-deals.json"

AGENT = "Mozilla/5.0 (compatible; gqh research; research@example.com)"
FIELDS = ["source_page", "url", "issuer", "series", "in_register", "largest_tenant_pct", "top_tenants_pct",
          "walt_years", "data_centers", "critical_load_mw", "aanoi_musd", "annualized_revenue_musd",
          "classes_rated", "blocker"]
PROGRAMMES = ["databank", "flexential", "centersquare", "cologix", "tierpoint", "zayo", "firstlight", "qts",
              "lohrasp", "compass", "vantage", "sabey", "switch", "aligned", "cyrusone", "edgeconnex",
              "scalelogix", "amaps", "qts thunder"]
CONCENTRATION = {
    "largest_tenant_pct": r"(?:largest|top|anchor|single) tenant[^.%]{0,70}?([\d.]+)\s?%",
    "top_tenants_pct": r"(?:top|largest)\s+(?:ten|10|five|5)\s+tenants[^.%]{0,70}?([\d.]+)\s?%",
    "walt_years": r"(?:weighted average (?:remaining )?lease term|WALT)[^.]{0,40}?([\d.]+)\s?(?:years|yrs)",
}
OPERATING = {
    "data_centers": r"secured by\s+([\d,]+)\s+(?:multi[- ]?customer enterprise\s+)?data centers",
    "critical_load_mw": r"([\d.]+)\s+megawatts \(MW\) of critical load",
    "aanoi_musd": r"\$([\d.]+)\s+million of Annualized Adjusted Net Operating Income",
    "annualized_revenue_musd": r"approximately\s+\$([\d.]+)\s+million of Annualized Revenue",
}
RATING = r"['\u2018\u2019\"]?(AAA|AA|A|BBB|BB|B|CCC)(?:\+|-)?\s*(?:\(\s*(?:high|low|mid)\s*\))?\s*\(sf\)"


def fetch(url: str) -> str:
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": AGENT})
            body = urllib.request.urlopen(request, timeout=45).read().decode("utf-8", "replace")
            body = re.sub(r"<(script|style).*?</\1>", " ", body, flags=re.S | re.I)
            body = body.replace("&nbsp;", " ").replace("&#160;", " ").replace("&amp;", "&")
            body = re.sub(r"&#\d+;|&[a-z]+;", " ", body)
            return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))
        except Exception:
            continue
    return ""


def programme_of(text: str) -> str:
    folded = text.casefold()
    for token in sorted(PROGRAMMES, key=len, reverse=True):
        if token in folded:
            return token
    return ""


def work(row: dict, register: set[str]) -> tuple[dict, str]:
    text = fetch(row["url"])
    if not text:
        return {}, f"fetch refused: {row['url']}"
    out = {name: "" for name in FIELDS}
    out.update({"source_page": row["title"][:110], "url": row["url"],
                "issuer": row["issuer_guess"], "series": row["series_guess"]})
    for name, pattern in {**CONCENTRATION, **OPERATING}.items():
        match = re.search(pattern, text, re.I)
        if match:
            out[name] = next((group for group in match.groups() if group), "")
    out["classes_rated"] = str(len(set(re.findall(RATING, text))))
    programme = programme_of(row["issuer_guess"]) or programme_of(row["title"])
    out["in_register"] = bool(programme and programme in register)
    if out["in_register"]:
        out["blocker"] = "in the SEC register"
    elif programme:
        out["blocker"] = ("no ABS-15G in the register for this programme, so identity, covenants and the "
                          "lease schedule have no free filing, while the agency states the deal's terms")
    else:
        out["blocker"] = ("no SEC filing located and no register programme matched, so the deal is named by an "
                          "agency only and its identity needs one document read to resolve")
    return out, ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args(argv)

    register = {programme_of(row["issuing_entity"]) or programme_of(row["securitizer"])
                for row in csv.DictReader(STRUCTURE.open())
                if row.get("mentions_data_center") == "True" and row["issuing_entity"]}
    pages = [row for row in csv.DictReader(UNIVERSE.open()) if row.get("url")]
    print(f"pages: {len(pages)} | register programmes: {sorted(p for p in register if p)}")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda row: work(row, register), pages))

    rows = [item for item, _ in results if item]
    errors = [message for _, message in results if message]
    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    outside = [row for row in rows if row["in_register"] is False]
    with_concentration = [row for row in outside if row["largest_tenant_pct"] or row["top_tenants_pct"]]
    manifest = {
        "generated_by": "scripts/build_agency_only_deals.py",
        "pages_fetched": len(rows), "fetch_errors": errors,
        "deals_named_by_agencies": len(rows),
        "deals_in_the_register": sum(1 for row in rows if row["in_register"]),
        "deals_outside_the_register": len(outside),
        "outside_with_a_concentration_number": len(with_concentration),
        "outside_with_operating_metrics": sum(1 for row in outside
                                              if row["data_centers"] or row["critical_load_mw"]),
        "the_actionable_list": [
            {"issuer": row["issuer"][:80], "series": row["series"],
             "largest_tenant_pct": row["largest_tenant_pct"], "top_tenants_pct": row["top_tenants_pct"],
             "aanoi_musd": row["aanoi_musd"], "data_centers": row["data_centers"],
             "classes_rated": row["classes_rated"], "blocker": row["blocker"]}
            for row in sorted(with_concentration, key=lambda row: -(float(row["largest_tenant_pct"] or 0)))],
    }
    OUT_JSON.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"deals named by agencies: {len(rows)} | in register: {manifest['deals_in_the_register']} | "
          f"outside: {len(outside)} | outside with concentration: {len(with_concentration)}")
    for row in manifest["the_actionable_list"][:10]:
        print(f"  {row['issuer'][:44]:46s} S{row['series']:8s} largest={row['largest_tenant_pct']:6s} "
              f"top={row['top_tenants_pct']:6s} AANOI={row['aanoi_musd']:8s} dc={row['data_centers']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
