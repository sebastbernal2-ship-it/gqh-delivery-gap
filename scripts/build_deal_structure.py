#!/usr/bin/env python3
"""Parse the ABS-15G cover pages into a deal register with the issuing entity's own CIK.

Why this and not a prospectus: reconnaissance on 2026-10-03 checked all 28 data center securitizer CIKs and
found **no 424B, no S-3, no prospectus anywhere in the set**. These are 144A securitizations, so there is no
registered offering and no prospectus to parse. The tranche table is not on EDGAR at any price. What is on
EDGAR, reliably, is the ABS-15G cover page, and it carries the identity of the deal.

Fields taken from each cover page, with a found and missing count printed so the parse rate is stated and not
assumed:

- the rule the filing answers, 15Ga-1 or 15Ga-2
- the depositor's CIK
- the exact name of the issuing entity, and its own CIK, which is a different registration from the
  securitizer's and is the entity a future filing would come from
- the underwriter's CIK where one is named
- the report date and the signing entity
- the independent accountant's report: its date and the firm

Nothing is inferred. A field that is not found is written empty and counted as missing.

Usage:
    python3 scripts/build_deal_structure.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from edgar.filings import get_json, session, user_agent  # noqa: E402

REGISTRY = ROOT / "results" / "credit-deal-registry.json"
OUT_CSV = ROOT / "results" / "deal-structure.csv"
OUT_JSON = ROOT / "results" / "deal-structure.json"

FIELDS = ["securitizer", "securitizer_cik", "issuing_entity", "issuing_entity_cik", "depositor_cik",
          "underwriter", "rule", "report_date", "accountant", "accountant_report_date",
          "deal_series", "deal_class", "mentions_data_center", "pool_type", "accession",
          "primary_document",
          "exhibit_document"]
# Fields with a measured parse rate below one half are cut rather than shipped fragile. The signature block
# was one: its layout varies by filer and the field adds nothing the securitizer CIK does not already say.
CUT_FIELDS = ["signed_by: signature block layout varies by filer, cut in favour of the securitizer CIK"]
# Two different objects share the words data center and must not be blended. A pure play issuer's collateral is
# data center rent only, so the site's constraint is the whole instrument. A conduit trust holds a data center
# loan inside a diversified pool, so the same constraint is diluted before it reaches the note. The second kind
# is labelled, not dropped, because that dilution is what the instrument gate exists to catch.
CONDUIT_TOKENS = ("mortgage trust", "commercial mortgage securities", "benchmark 20", "bbcms",
                  "liberty street")


def fetch_text(url: str, tries: int = 4) -> str:
    """Fetch a filing document with retries. A register must not change size because one request timed out.

    Measured 2026-10-03: a single unretried run lost an EdgeConneX filing to an SSL handshake timeout, which
    moved the reported deal count. Three runs later the count only agreed once the fetch retried.
    """
    last = ""
    for attempt in range(tries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": user_agent()})
            return urllib.request.urlopen(request, timeout=90).read().decode("utf-8", "replace")
        except Exception as error:
            last = str(error)[:90]
            time.sleep(1.0 + attempt)
    raise RuntimeError(last)


def clean(body: str) -> str:
    body = re.sub(r"<(script|style).*?</\1>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<[^>]+>", " ", body)
    body = body.replace("&nbsp;", " ").replace("&#8217;", "'").replace("&amp;", "&")
    body = re.sub(r"&#\d+;|&[a-z]+;", " ", body)  # tabs and other numeric entities leaked into names
    return re.sub(r"\s+", " ", body)


def field(text: str, pattern: str, group: int = 1) -> str:
    match = re.search(pattern, text, re.I)
    return match.group(group).strip() if match else ""


def parse_cover(text: str, cik: str, accession: str, doc: str) -> dict:
    # The template lists both rule headings and ticks one with a checked box, &#9745;. Detecting a mention
    # instead of the tick labelled all 324 filings as answering both rules, which was wrong.
    rules = []
    for match in re.finditer(r"\u2611|\u2612|&#9745;|&#9746;", text):
        tail = text[match.end():match.end() + 160]
        found = re.search(r"Rule 15Ga-(1|2)", tail)
        if found:
            rules.append("Rule 15Ga-" + found.group(1))
    if not rules:
        rules = [name for name in ("Rule 15Ga-1", "Rule 15Ga-2") if name.lower() in text.lower()]
        rules = [name + " (unconfirmed tick)" for name in rules]
    return {
        "securitizer": "",
        "securitizer_cik": cik,
        "issuing_entity": field(text,
                                r"Central Index Key Number of depositor:\s*\d{10}\s*(.{3,120}?)\s*\(Exact name of"),
        "issuing_entity_cik": field(text, r"Central Index Key Number of issuing entity \(if applicable\):\s*(\d{10})"),
        "depositor_cik": field(text, r"Central Index Key Number of depositor:\s*(\d{10})"),
        "underwriter": field(text, r"Central Index Key Number of underwriter \(if applicable\):\s*(\[Not applicable\]|\d{10})"),
        "rule": "+".join(rules),
        "report_date": field(text, r"Date:\s*([A-Z][a-z]+ \d{1,2}, \d{4})"),
        "accountant": field(text, r"of\s+((?:[A-Z&][\w&.,'\-]*\s+){1,5}?(?:LLP|LLC|PLLC|Inc\.?|Corporation|Company|Co\.))"),
        "accountant_report_date": field(text, r"Agreed.Upon Procedures,?\s*dated\s*([A-Z][a-z]+ \d{1,2}, \d{4})"),
        "deal_series": "",
        "deal_class": "",
        "accession": accession,
        "primary_document": doc,
        "exhibit_document": "",
    }


def exhibit_of(s, cik: str, accession: str) -> tuple[str, str, bool]:
    """The exhibit file and its text, which is where the series and class are named."""
    folder = accession.replace("-", "")
    index = get_json(s, f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{folder}/index.json")
    names = [item["name"] for item in index.get("directory", {}).get("item", [])]
    candidates = [name for name in names
                  if name.lower().endswith((".htm", ".html", ".txt")) and "index" not in name.lower()]
    for name in candidates:
        try:
            body = fetch_text(f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{folder}/{name}")
        except Exception:
            continue
        text = clean(body)
        # The series pattern has to allow a letter after the dash: conduit deals are named 2019-C5, and a
        # digits-only pattern silently skipped every one of them.
        if re.search(r"Series\s?20\d\d-[A-Z]?\d+", text):
            class_match = re.search(r"Series\s?(20\d\d-[A-Z]?\d+)[^.]{0,80}?Class\s([A-Z0-9\-]+)", text)
            series_match = re.search(r"Series\s?(20\d\d-[A-Z]?\d+)", text)
            series = class_match.group(1) if class_match else (series_match.group(1) if series_match else "")
            klass = class_match.group(2) if class_match else ""
            mentions = bool(re.search(r"data cent(?:er|re)|datacent(?:er|re)|colocation", text, re.I))
            return name, series, klass, mentions
    return (candidates[0] if candidates else ""), "", "", False


def main() -> int:
    registry = json.loads(REGISTRY.read_text())
    securitizers: dict[str, str] = {}
    for row in registry["deal_level_securitizers"]:
        match = re.search(r"CIK (\d+)", row)
        if match:
            securitizers[match.group(1)] = row.split("  (CIK")[0]

    s = session()
    rows: list[dict] = []
    missing_counts: dict[str, int] = {name: 0 for name in FIELDS}
    errors: list[str] = []

    for cik, name in sorted(securitizers.items(), key=lambda item: item[1].casefold()):
        try:
            submissions = get_json(s, f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json")
        except Exception as error:
            errors.append(f"{name}: submissions failed: {str(error)[:80]}")
            continue
        rec = submissions["filings"]["recent"]
        for index, form in enumerate(rec["form"]):
            if not form.startswith("ABS-15G"):
                continue
            accession = rec["accessionNumber"][index]
            doc = rec["primaryDocument"][index]
            url = (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                   f"{accession.replace('-', '')}/{doc}")
            try:
                body = fetch_text(url)
            except Exception as error:
                errors.append(f"{name} {accession}: fetch failed after retries: {str(error)[:60]}")
                continue
            cover_text = clean(body)
            row = parse_cover(cover_text, cik, accession, doc)
            row["securitizer"] = name
            exhibit, series, klass, exhibit_mentions = exhibit_of(s, cik, accession)
            row["exhibit_document"], row["deal_series"], row["deal_class"] = exhibit, series, klass
            # The flag tests the cover and the exhibit. Testing the cover alone dropped DataBank and Flexential
            # entirely: 22 filings whose cover names an issuer and an amount, with the data center asset named
            # only in the exhibit. That was a false negative of the same kind as the earlier false positive
            # that admitted Sunrun.
            cover_mentions = bool(re.search(r"data cent(?:er|re)|datacent(?:er|re)|colocation|critical IT",
                                            cover_text, re.I))
            row["mentions_data_center"] = cover_mentions or exhibit_mentions
            row["pool_type"] = ("mixed_pool_conduit"
                                if any(token in name.casefold() for token in CONDUIT_TOKENS) else "pure_play")
            rows.append(row)
            for key in FIELDS:
                if not str(row.get(key, "")).strip():
                    missing_counts[key] += 1
            time.sleep(0.12)

    rows.sort(key=lambda item: (item["securitizer"].casefold(), item["accession"]))
    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    entities = sorted({row["issuing_entity"] for row in rows if row["issuing_entity"]})
    entity_ciks = sorted({row["issuing_entity_cik"] for row in rows if row["issuing_entity_cik"]})
    series = sorted({row["deal_series"] for row in rows if row["deal_series"]})
    total = len(rows)
    manifest = {
        "generated_by": "scripts/build_deal_structure.py",
        "route": "SEC EDGAR ABS-15G cover pages, no key, no entitlement",
        "prospectus_reconnaissance": "all 28 securitizer CIKs checked: no 424B, no S-3, no prospectus in the "
                                     "set. These are 144A securitizations, so the tranche table does not exist "
                                     "on EDGAR and cannot be parsed from it",
        "filings_parsed": total,
        "securitizers": len({row["securitizer_cik"] for row in rows}),
        "distinct_issuing_entities": len(entities),
        "distinct_issuing_entity_ciks": len(entity_ciks),
        "series_named_in_text": series,
        "data_center_filings": sum(1 for row in rows if row.get("mentions_data_center")),
        "data_center_filings_pure_play": sum(1 for row in rows if row.get("mentions_data_center")
                                             and row.get("pool_type") == "pure_play"),
        "data_center_filings_mixed_pool": sum(1 for row in rows if row.get("mentions_data_center")
                                              and row.get("pool_type") == "mixed_pool_conduit"),
        "pool_type_note": "a pure play issuer's collateral is data center rent only; a mixed pool conduit holds "
                          "a data center loan inside a diversified pool, so the constraint is diluted before it "
                          "reaches the note",
        "data_center_deals": sorted({f"{row['issuing_entity']} Series {row['deal_series']}"
                                     for row in rows
                                     if row.get("mentions_data_center") and row["deal_series"]
                                     and row["issuing_entity"]}),
        "parse_rate": {name: (total - count, count) for name, count in missing_counts.items()},
        "parse_rate_note": "the tuple is (found, missing) over all parsed filings",
        "errors": errors,
        "cut_fields": CUT_FIELDS,
        "boundary": "identity only. A cover page names the deal and its parties; it carries no cash flow, no "
                    "coupon and no price.",
    }
    OUT_JSON.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"parsed {total} ABS-15G cover pages from {manifest['securitizers']} securitizers")
    print(f"distinct issuing entities: {len(entities)} | with their own CIK: {len(entity_ciks)}")
    print("parse rate (found, missing):")
    for name, (found, missing) in manifest["parse_rate"].items():
        if name in ("securitizer", "securitizer_cik", "accession", "primary_document", "exhibit_document"):
            continue
        print(f"  {name:24s} {found:4d} found  {missing:4d} missing")
    if errors:
        print(f"errors: {len(errors)}")
        for line in errors[:5]:
            print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
