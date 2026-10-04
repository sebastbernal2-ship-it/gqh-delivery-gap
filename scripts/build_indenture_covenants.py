#!/usr/bin/env python3
"""Read the covenant families out of the deal documents, including the combined indenture.

Why: gate 1 asks for the constraint in writing and the earlier pass left the covenant blank because it read
series supplements, which are short instruments that define a series. The base and combined indentures are the
documents that hold the tests, the traps and the defaults, and one of them is over a million bytes.

What it extracts, with the sentence attached so a reader can check it: debt service coverage tests, cash trap
triggers, cash sweep, cross default, events of default, reserve and liquidity requirements, permitted debt and
liens, and any stated coverage ratio with its threshold.

Usage:
    python3 scripts/build_indenture_covenants.py [--workers 4]
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

OUT_CSV = ROOT / "results" / "indenture-covenants.csv"
OUT_JSON = ROOT / "results" / "indenture-covenants.json"
HOLDERS = {2069692: "Blue Owl Digital Infrastructure Trust"}
PATTERNS = {
    "dscr_test": r"[^.]{0,200}(?:debt service coverage ratio|DSCR)[^.]{0,240}\.",
    "cash_trap": r"[^.]{0,200}cash trap[^.]{0,240}\.",
    "cash_sweep": r"[^.]{0,200}(?:cash sweep|sweep period|excess cash flow)[^.]{0,240}\.",
    "cross_default": r"[^.]{0,200}cross[- ]default[^.]{0,240}\.",
    "event_of_default": r"[^.]{0,160}Events? of Default[^.]{0,240}\.",
    "reserve": r"[^.]{0,200}(?:liquidity reserve|reserve account|reserve requirement)[^.]{0,240}\.",
    "coverage_ratio_number": r"[^.]{0,160}(?:coverage ratio|no less than|at least)\s*(?:\d+\.\d+|\d+)\s?[x:][^.]{0,160}\.",
    "permitted_debt": r"[^.]{0,160}Permitted (?:Indebtedness|Debt)[^.]{0,200}\.",
    "lien": r"[^.]{0,160}(?:permitted lien|negative pledge)[^.]{0,200}\.",
}
FIELDS = ["holder", "form", "filed", "document", "document_bytes", "series_seen", "url", *PATTERNS.keys()]
THRESHOLD_RE = re.compile(r"[^.]{0,200}(?:not less than|at least|minimum|no less than|greater than|exceed)\s*"
                          r"([12]\.\d{2,3})\s*(?::\s*1\.00|x|to 1\.00)[^.]{0,160}\.", re.I)
OUT_THRESHOLDS = ROOT / "results" / "dscr-thresholds.csv"


def clean(body: str) -> str:
    body = re.sub(r"<(script|style).*?</\1>", " ", body, flags=re.S | re.I)
    body = body.replace("&nbsp;", " ").replace("&#160;", " ").replace("&amp;", "&").replace("&#8217;", "'")
    body = re.sub(r"&#\d+;|&[a-z]+;", " ", body)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--min-bytes", type=int, default=200000,
                        help="the base and combined indentures are the large documents")
    args = parser.parse_args(argv)

    s = session()
    targets: list[dict] = []
    for cik, holder in HOLDERS.items():
        submissions = get_json(s, f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
        rec = submissions["filings"]["recent"]
        for index, form in enumerate(rec["form"]):
            folder = rec["accessionNumber"][index].replace("-", "")
            try:
                idx = get_json(s, f"https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/index.json")
            except Exception:
                continue
            for item in idx.get("directory", {}).get("item", []):
                name, size = item["name"], int(item.get("size") or 0)
                if size < args.min_bytes or not name.lower().endswith((".htm", ".html", ".txt")):
                    continue
                targets.append({"holder": holder, "form": form, "filed": rec["filingDate"][index],
                                "document": name, "document_bytes": size,
                                "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{name}"})
    print(f"documents over {args.min_bytes} bytes: {len(targets)}")

    def work(target: dict) -> dict:
        try:
            body = urllib.request.urlopen(urllib.request.Request(target["url"],
                                                                 headers={"User-Agent": user_agent()}),
                                          timeout=180).read().decode("utf-8", "replace")
        except Exception as error:
            return dict(target, url=target["url"], series_seen="",
                        **{name: f"fetch failed: {str(error)[:50]}" for name in PATTERNS})
        text = clean(body)
        row = {"holder": target["holder"], "form": target["form"], "filed": target["filed"],
               "document": target["document"], "document_bytes": target["document_bytes"],
               "url": target["url"],
               "series_seen": ", ".join(sorted(set(re.findall(r"[Ss]eries\s(20\d\d-[A-Z]?\d+)", text)))[:8])}
        for name, pattern in PATTERNS.items():
            match = re.search(pattern, text, re.I)
            row[name] = re.sub(r"\s+", " ", match.group(0)).strip()[:700] if match else ""
        return row

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(work, targets))

    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    # The stated thresholds, pulled out of the same documents, because a covenant family is only useful once
    # it carries a number. Credit agreements are the documents that state them.
    threshold_rows: list[dict] = []
    for row in rows:
        if "exhibit10" not in row["document"]:
            continue
        try:
            body = urllib.request.urlopen(urllib.request.Request(row["url"],
                                                                 headers={"User-Agent": user_agent()}),
                                          timeout=180).read().decode("utf-8", "replace")
        except Exception:
            continue
        for match in THRESHOLD_RE.finditer(clean(body)):
            threshold_rows.append({
                "document": row["document"], "url": row["url"],
                "threshold_sentence": re.sub(r"\s+", " ", match.group(0)).strip()[:400],
                "value": match.group(1),
            })
    with OUT_THRESHOLDS.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["document", "url", "threshold_sentence", "value"])
        writer.writeheader()
        writer.writerows(threshold_rows)

    manifest = {
        "generated_by": "scripts/build_indenture_covenants.py",
        "threshold_sentences": len(threshold_rows),
        "threshold_values": sorted({row["value"] for row in threshold_rows}),
        "route": "the base and combined indentures filed by the holding trust as Exhibit 4",
        "documents_read": len(rows),
        "min_bytes": args.min_bytes,
        "documents_with_a_coverage_test": sum(1 for row in rows if row["dscr_test"]),
        "documents_with_a_cash_trap": sum(1 for row in rows if row["cash_trap"]),
        "documents_with_cross_default": sum(1 for row in rows if row["cross_default"]),
        "documents_with_a_reserve": sum(1 for row in rows if row["reserve"]),
        "documents_with_a_stated_ratio": sum(1 for row in rows if row["coverage_ratio_number"]),
        "boundary": "a sentence is stored with each family, not a parsed threshold. Turning these into structured "
                    "tests is a separate step and would need a reader per document",
    }
    OUT_JSON.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"documents: {len(rows)}")
    for key in ("documents_with_a_coverage_test", "documents_with_a_cash_trap", "documents_with_cross_default",
                "documents_with_a_reserve", "documents_with_a_stated_ratio"):
        print(f"  {key:34s} {manifest[key]}")
    for row in rows[:6]:
        print(f"\n  {row['document'][:50]} ({row['document_bytes']:,} bytes) series {row['series_seen'][:40]}")
        for family in ("dscr_test", "cash_trap", "cross_default"):
            if row[family]:
                print(f"    {family}: {row[family][:220]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
