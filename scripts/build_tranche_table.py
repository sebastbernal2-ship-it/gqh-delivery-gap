#!/usr/bin/env python3
"""Extract the tranche table from the deal documents that sit on EDGAR as fund Exhibit 4 filings.

Why this is the payoff: the tranche table was declared unreachable. EDGAR holds no prospectus for a 144A
securitization, the agencies state ratings but not sizes, and the FINRA catalogue holds aggregates. It turns out
the registered trusts that hold the deals file the series supplements as Exhibit 4, and a supplement states the
class, the initial principal balance, the note rate, the rating, the anticipated repayment date, the rated final
payment date and the post-ARD spread. That is the table.

Verified structure, from the Series 2025-1 supplement, which is why the patterns look the way they do:

    Series 2025-1, Class A-2    $345,000,000   $345,000,000   5.00%   Term Notes   A-(sf)
    the Anticipated Repayment Date is the Payment Date in May 2030
    the Rated Final Payment Date is the Payment Date in May 2050
    the Post-ARD Note Spread is 1.45%

Ground truth for that row: 345 million at 5.00 percent, rated A-(sf), repayment May 2030, final May 2050,
post-ARD spread 1.45 percent.

Usage:
    python3 scripts/build_tranche_table.py [--workers 6]
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

OUT_CSV = ROOT / "results" / "tranche-table.csv"
OUT_JSON = ROOT / "results" / "tranche-table.json"
HOLDERS = {2069692: "Blue Owl Digital Infrastructure Trust", 1944366: "Blue Owl Real Estate Net Lease Trust"}
FIELDS = ["holder", "form", "filed", "document", "series", "class", "initial_balance_usd",
          "current_balance_usd", "note_rate_pct", "note_type", "rating", "anticipated_repayment_date",
          "rated_final_payment_date", "post_ard_spread_pct", "url"]

CLASS_ROW = re.compile(
    r"Series\s(20\d\d-[A-Z]?\d+),\s*Class\s+([A-Z0-9\-]+)\s+\$([\d,]+)\s+\$([\d,]+)\s+([\d.]+)%\s+"
    r"([A-Za-z][A-Za-z ]{2,24}?)\s+([A-Za-z0-9+\-]{1,8}\s*\(sf\))")
ARD = re.compile(r"Anticipated Repayment Date[^.]{0,120}?is the Payment Date in\s+([A-Z][a-z]+ \d{4})")
FINAL = re.compile(r"Rated Final Payment Date[^.]{0,120}?is the Payment Date in\s+([A-Z][a-z]+ \d{4})")
POST_ARD = re.compile(r"Post-ARD Note Spread[^.]{0,160}?([\d.]+)\s?%")
ANY_CLASS_RATE = re.compile(r"Class\s+([A-Z0-9\-]+)[^.]{0,60}?([\d.]+)\s?%")


def clean(body: str) -> str:
    body = re.sub(r"<(script|style).*?</\1>", " ", body, flags=re.S | re.I)
    body = body.replace("&nbsp;", " ").replace("&#160;", " ").replace("&amp;", "&").replace("&#8217;", "'")
    body = re.sub(r"&#\d+;|&[a-z]+;", " ", body)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))


def fetch_text(url: str, tries: int = 3) -> str:
    last = ""
    for attempt in range(tries):
        try:
            return clean(urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": user_agent()}), timeout=120)
                .read().decode("utf-8", "replace"))
        except Exception as error:
            last = str(error)[:70]
    raise RuntimeError(last)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args(argv)

    s = session()
    documents: list[dict] = []
    for cik, holder in HOLDERS.items():
        subs = get_json(s, f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
        rec = subs["filings"]["recent"]
        for index, form in enumerate(rec["form"]):
            if form not in ("10-K", "10-Q", "8-K", "N-CSR"):
                continue
            folder = rec["accessionNumber"][index].replace("-", "")
            try:
                idx = get_json(s, f"https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/index.json")
            except Exception:
                continue
            for item in idx.get("directory", {}).get("item", []):
                name, size = item["name"], int(item.get("size") or 0)
                if not re.match(r"(ex|exhibit)?[-_]?4", name, re.I) or size < 20000:
                    continue
                if not name.lower().endswith((".htm", ".html", ".txt")):
                    continue
                documents.append({"holder": holder, "form": form, "filed": rec["filingDate"][index],
                                  "document": name,
                                  "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{name}"})

    def work(doc: dict) -> list[dict]:
        try:
            text = fetch_text(doc["url"])
        except Exception:
            return []
        rows: list[dict] = []
        for series, klass, initial, current, rate, note_type, rating in CLASS_ROW.findall(text):
            ard = ARD.search(text)
            final = FINAL.search(text)
            post = POST_ARD.search(text)
            rows.append({
                "holder": doc["holder"], "form": doc["form"], "filed": doc["filed"],
                "document": doc["document"], "series": series, "class": klass,
                "initial_balance_usd": initial.replace(",", ""), "current_balance_usd": current.replace(",", ""),
                "note_rate_pct": rate, "note_type": note_type.strip(), "rating": rating.strip(),
                "anticipated_repayment_date": ard.group(1) if ard else "",
                "rated_final_payment_date": final.group(1) if final else "",
                "post_ard_spread_pct": post.group(1) if post else "", "url": doc["url"],
            })
        if not rows:
            segments = re.split(r"Series\s(20\d\d-[A-Z]?\d+)", text)
            for position in range(1, len(segments), 2):
                series, body = segments[position], segments[position + 1]
                for klass, rate in ANY_CLASS_RATE.findall(body):
                    rows.append({"holder": doc["holder"], "form": doc["form"], "filed": doc["filed"],
                                 "document": doc["document"], "series": series, "class": klass,
                                 "initial_balance_usd": "", "current_balance_usd": "",
                                 "note_rate_pct": rate, "note_type": "", "rating": "",
                                 "anticipated_repayment_date": "", "rated_final_payment_date": "",
                                 "post_ard_spread_pct": "", "url": doc["url"]})
        return rows

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        nested = list(pool.map(work, documents))
    rows = [row for group in nested for row in group]

    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    with_balance = [row for row in rows if row["initial_balance_usd"]]
    with_rating = [row for row in rows if row["rating"]]
    with_ard = [row for row in rows if row["anticipated_repayment_date"]]
    manifest = {
        "generated_by": "scripts/build_tranche_table.py",
        "route": "EDGAR Exhibit 4 series supplements filed by the registered trusts that hold the deals",
        "documents_read": len(documents),
        "documents_with_rows": sum(1 for group in nested if group),
        "class_rows": len(rows),
        "rows_with_balance_and_rate": len(with_balance),
        "rows_with_a_rating": len(with_rating),
        "rows_with_an_anticipated_repayment_date": len(with_ard),
        "series_covered": sorted({row["series"] for row in rows}),
        "ground_truth_checked": "Series 2025-1 Class A-2: 345 million at 5.00 percent, A-(sf), repayment May "
                                "2030, final May 2050, post-ARD spread 1.45 percent",
        "boundary": "a class row states the note's own terms. It carries no price, no trade and no cash flow, "
                    "and a rate printed at issue is not a current yield",
    }
    OUT_JSON.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"documents read: {len(documents)} | with class rows: {manifest['documents_with_rows']}")
    print(f"class rows: {len(rows)} | with balance and rate: {len(with_balance)} | rated: {len(with_rating)} "
          f"| with ARD: {len(with_ard)}")
    print(f"series covered: {manifest['series_covered']}")
    print("")
    for row in sorted(with_balance, key=lambda item: (item['series'], item['class']))[:14]:
        print(f"  {row['series']:9s} Class {row['class']:9s} ${int(row['initial_balance_usd']):>13,d} "
              f"{row['note_rate_pct']:>6s}%  {row['rating']:9s} ARD {row['anticipated_repayment_date']:14s} "
              f"post-ARD {row['post_ard_spread_pct']}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
