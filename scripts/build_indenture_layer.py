#!/usr/bin/env python3
"""Pull the indenture and series supplement documents that sit on EDGAR inside fund Exhibit 4 filings.

The discovery: a 144A securitization files no prospectus, so the covenant text is normally out of reach. But
the trusts that hold these deals are registered funds, and a registered fund files the instruments that define
its security holders' rights as Exhibit 4. In this case Blue Owl Digital Infrastructure Trust files series
supplements and indentures for data center securitizations, including a STACK indenture of over a million bytes.

So the free route to gates 1, 2, 3 and 5 runs through the holder, not the issuer. This script enumerates those
filings, fetches every Exhibit 4 sized document concurrently, and extracts a declared term list with the
sentence each term came from, so a reader can check the extraction rather than trust it.

Terms are searched, not interpreted. A term that is absent is written empty and counted as absent.

Usage:
    python3 scripts/build_indenture_layer.py [--workers 6]
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
sys.path.insert(0, str(ROOT / "src"))
from edgar.filings import get_json, session, user_agent  # noqa: E402

OUT_CSV = ROOT / "results" / "indenture-layer.csv"
OUT_JSON = ROOT / "results" / "indenture-layer.json"

# The holders that file deal documents. Found by EDGAR full text search for the phrase that appears in the
# notes' own names, "Secured Data Center Revenue Term Notes".
HOLDERS = {
    2069692: "Blue Owl Digital Infrastructure Trust",
    1944366: "Blue Owl Real Estate Net Lease Trust",
}
SERIES_RE = re.compile(r"[Ss]eries\s(20\d\d-[A-Z]?\d+)")
DSCR_RE = re.compile(r"[^.]{0,140}(?:debt service coverage ratio|DSCR)[^.]{0,140}\.", re.I)
TRAP_RE = re.compile(r"[^.]{0,140}cash trap[^.]{0,160}\.", re.I)
CROSS_RE = re.compile(r"[^.]{0,120}cross[- ]default[^.]{0,160}\.", re.I)
CONC_RE = re.compile(r"[^.]{0,140}(?:largest|top)\s+(?:tenant|three tenants|five tenants)[^.]{0,160}\.", re.I)
COUPON_RE = re.compile(r"[^.]{0,100}(?:interest rate|coupon)[^.]{0,40}?([\d.]{1,6})\s?%[^.]{0,120}", re.I)
MATURITY_RE = re.compile(r"[^.]{0,80}(?:stated maturity|anticipated repayment date|maturity date)[^.]{0,60}?"
                         r"([A-Z][a-z]+ \d{1,2}, \d{4})", re.I)
RESERVE_RE = re.compile(r"[^.]{0,120}(?:liquidity reserve|reserve account)[^.]{0,140}\.", re.I)
FIELDS = ["holder", "cik", "form", "filed", "document", "document_bytes", "series",
          "dscr_clause", "cash_trap_clause", "cross_default_clause", "concentration_clause",
          "coupon_clause", "maturity_clause", "reserve_clause", "url"]


def clean(body: str) -> str:
    body = re.sub(r"<(script|style).*?</\1>", " ", body, flags=re.S | re.I)
    body = body.replace("&nbsp;", " ").replace("&#160;", " ").replace("&amp;", "&").replace("&#8217;", "'")
    body = re.sub(r"&#\d+;|&[a-z]+;", " ", body)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))


def fetch_text(url: str, tries: int = 3) -> str:
    last = ""
    for attempt in range(tries):
        try:
            body = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": user_agent()}),
                                          timeout=120).read().decode("utf-8", "replace")
            return clean(body)
        except Exception as error:
            last = str(error)[:80]
    raise RuntimeError(last)


def first(pattern: re.Pattern, text: str) -> str:
    match = pattern.search(text)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(0)).strip()[:600]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args(argv)

    s = session()
    targets: list[dict] = []
    for cik, holder in HOLDERS.items():
        submissions = get_json(s, f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
        rec = submissions["filings"]["recent"]
        for index, form in enumerate(rec["form"]):
            if form not in ("10-K", "10-Q", "8-K", "N-CSR", "S-11", "10-12G", "10-12G/A"):
                continue
            accession = rec["accessionNumber"][index]
            folder = accession.replace("-", "")
            try:
                idx = get_json(s, f"https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/index.json")
            except Exception:
                continue
            for item in idx.get("directory", {}).get("item", []):
                name = item["name"]
                size = int(item.get("size") or 0)
                if not re.match(r"(ex|exhibit)?[-_]?4", name, re.I):
                    continue
                if size < 20000 or not name.lower().endswith((".htm", ".html", ".txt")):
                    continue
                targets.append({
                    "holder": holder, "cik": cik, "form": form, "filed": rec["filingDate"][index],
                    "document": name, "document_bytes": size,
                    "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{name}",
                })
    print(f"exhibit 4 documents over 20 KB: {len(targets)}")

    def work(target: dict) -> dict:
        try:
            text = fetch_text(target["url"])
        except Exception as error:
            return dict(target, series="", dscr_clause=f"fetch failed: {str(error)[:60]}", cash_trap_clause="",
                        cross_default_clause="", concentration_clause="", coupon_clause="", maturity_clause="",
                        reserve_clause="")
        series = ", ".join(sorted(set(SERIES_RE.findall(text)))[:6])
        return dict(
            target, series=series,
            dscr_clause=first(DSCR_RE, text), cash_trap_clause=first(TRAP_RE, text),
            cross_default_clause=first(CROSS_RE, text), concentration_clause=first(CONC_RE, text),
            coupon_clause=first(COUPON_RE, text), maturity_clause=first(MATURITY_RE, text),
            reserve_clause=first(RESERVE_RE, text),
        )

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(work, targets))

    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    def with_term(field: str) -> int:
        return sum(1 for row in rows if row.get(field) and not row[field].startswith("fetch failed"))

    manifest = {
        "generated_by": "scripts/build_indenture_layer.py",
        "route": "EDGAR Exhibit 4 filings by the registered trusts that hold the deals. Free, no entitlement",
        "why": "a 144A securitization files no prospectus, but a registered fund files the instruments that "
               "define its security holders' rights as Exhibit 4, and those instruments are the deal documents",
        "documents": len(rows),
        "documents_fetched": sum(1 for row in rows if not str(row.get("dscr_clause", "")).startswith("fetch")),
        "with_dscr_clause": with_term("dscr_clause"),
        "with_cash_trap_clause": with_term("cash_trap_clause"),
        "with_cross_default_clause": with_term("cross_default_clause"),
        "with_concentration_clause": with_term("concentration_clause"),
        "with_coupon_clause": with_term("coupon_clause"),
        "with_maturity_clause": with_term("maturity_clause"),
        "with_reserve_clause": with_term("reserve_clause"),
        "series_seen": sorted({series for row in rows for series in row["series"].split(", ") if series}),
        "boundary": "terms are searched and the sentence is stored with each one. A term that is absent is "
                    "written empty and counted, never inferred from a sibling document",
    }
    OUT_JSON.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"documents: {manifest['documents']} | fetched: {manifest['documents_fetched']}")
    for key in ("with_dscr_clause", "with_cash_trap_clause", "with_cross_default_clause",
                "with_concentration_clause", "with_coupon_clause", "with_maturity_clause",
                "with_reserve_clause"):
        print(f"  {key:30s} {manifest[key]}")
    print(f"  series seen: {manifest['series_seen']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
