#!/usr/bin/env python3
"""Enumerate the agency's data center catalogue and diff it against the EDGAR register.

Why: the register of 42 deals was built by matching SEC filings to issuer names containing a data center token,
and a name rule under counts. The KBRA listing shows data center tagged securitizations whose issuer names carry
no such token, including Zayo, TierPoint and FirstLight. The correction is to enumerate from the agency's own
category and then say exactly which deals the register was missing.

Method: page the KBRA publication listing, keep the cards tagged Data Centers, and keep the rating action press
releases, which are the ones that name an issuer, a series and a class. Then match each against the issuers in
results/deal-structure.csv.

Honest limits, stated before the run:
- KBRA is one agency. Its catalogue is not the world, and a deal rated only by DBRS or S&P will not appear.
- The match is on issuer name tokens, so a renamed entity or an SPV abbreviation will show as a miss and is
  reported as a miss rather than forced into a match.

Usage:
    python3 scripts/build_agency_universe.py [--pages 40]
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STRUCTURE = ROOT / "results" / "deal-structure.csv"
OUT_CSV = ROOT / "results" / "agency-universe.csv"
OUT_JSON = ROOT / "results" / "agency-universe.json"

LISTING = "https://www.kbra.com/search/publications?q=data+center&ABS=on&page={page}"
CARD = re.compile(r'href="(/publications/[^"]+)"[^>]*>(.*?)</a></h3>.*?<span[^>]*>(.*?)</span>', re.S)
AGENT = "Mozilla/5.0 (compatible; gqh research; research@example.com)"
FIELDS = ["date", "type", "categories", "title", "issuer_guess", "series_guess", "url",
          "in_edgar_register", "matched_register_issuer"]


def fetch(page: int) -> str:
    url = LISTING.format(page=page)
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": AGENT})
            return urllib.request.urlopen(request, timeout=60).read().decode("utf-8", "replace")
        except Exception:
            time.sleep(1.0 + attempt)
    return ""


def text_of(fragment: str) -> str:
    fragment = re.sub(r"<!--.*?-->", " ", fragment, flags=re.S)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(fragment)).strip()


CLEANUPS = [
    (r"^(?:KBRA\s+)?(?:Assigns|Affirms|Publishes|Withdraws|Takes|Finalizes|Finalises|Confirms|Releases)[^A-Za-z]*", ""),
    (r"^Research\s*[\u2013-]\s*", ""),
    (r"^(?:Preliminary|Final|Provisional)\s+(?:Ratings?|Credit Ratings?)\s+", ""),
    (r"^(?:Ratings?|Credit Ratings?|A\+{1,2}|AA{1,2}|BBB?|BB)?[^A-Za-z]*to\s+", ""),
    (r"^to\s+", ""),
    (r"^Ratings?\s+on\s+", ""),
    (r"^Ratings?$", ""),
]
# Program level tokens. The SEC filer, the rated issuer and the co-issuer are three legal entities of one
# programme, so a match on the brand token is the right granularity and a legal entity match is not.
PROGRAM_ALIASES = {
    "databank": "databank", "flexential": "flexential", "centersquare": "centersquare",
    "cologix": "cologix", "tierpoint": "tierpoint", "zayo": "zayo", "firstlight": "firstlight",
    "qts": "qts", "lohrasp": "lohrasp", "compass": "compass", "vantage": "vantage", "sabey": "sabey",
    "switch": "switch", "aligned": "aligned", "cyrusone": "cyrusone", "edgeconnex": "edgeconnex",
    "amaps": "amaps", "phoenix": "phoenix data center",
}


def program_of(name: str) -> str:
    folded = name.casefold()
    for token, program in sorted(PROGRAM_ALIASES.items(), key=lambda item: -len(item[0])):
        if token in folded:
            return program
    return ""


def issuer_of(title: str) -> tuple[str, str]:
    """Pull the issuer and series out of a headline.

    The first version left phrases such as "Preliminary Ratings to TierPoint" in place, so every register match
    failed and the diff reported 24 misses out of 24. The rules below strip the verbs, the rating words and the
    class phrasing first, and cut at the series marker second. Checked by eye against all 162 titles collected.
    """
    body = title
    for pattern, replacement in CLEANUPS:
        body = re.sub(pattern, replacement, body, flags=re.I)
    series = ""
    match = re.search(r"Series\s(\d{4}-[\w/]+)", body)
    if match:
        series = match.group(1)
    body = re.split(r",?\s+(?:Series|SERIES)\b", body)[0]
    body = re.split(r"'s\s", body)[0]
    body = re.sub(r"\s+and\s+Takes Other Rating Actions.*$", "", body, flags=re.I)
    body = re.sub(r"\s+(?:up to|for)\s+.*$", "", body, flags=re.I)
    body = re.sub(r"^(?:the\s+)?Class\s+[\w\-]+(?:\s+\w+)*\s+(?:Notes|Loans),\s*", "", body, flags=re.I)
    body = re.sub(r"\s+Issued by\s+", " ", body, flags=re.I)
    return body.strip(" ,.;:"), series


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=40)
    args = parser.parse_args(argv)

    register_issuers = sorted({row["issuing_entity"].strip() for row in csv.DictReader(STRUCTURE.open())
                               if row.get("mentions_data_center") == "True" and row["issuing_entity"]})

    rows: list[dict] = []
    seen: set[str] = set()
    pages_read = 0
    for page in range(1, args.pages + 1):
        body = fetch(page)
        if not body:
            break
        pages_read += 1
        found = 0
        for url, raw_title, meta in CARD.findall(body):
            title = text_of(raw_title)
            meta_text = text_of(meta)
            if "data center" not in meta_text.casefold():
                continue
            if url in seen:
                continue
            seen.add(url)
            found += 1
            parts = [part.strip() for part in meta_text.split("|")]
            date = parts[0] if parts else ""
            kind = parts[1] if len(parts) > 1 else ""
            categories = ", ".join(parts[2:]) if len(parts) > 2 else ""
            issuer, series = issuer_of(title)
            program = program_of(issuer)
            matched = next((name for name in register_issuers
                            if program and program_of(name) == program), "") if program else ""
            rows.append({
                "date": date, "type": kind, "categories": categories, "title": title,
                "issuer_guess": issuer, "series_guess": series,
                "url": "https://www.kbra.com" + url,
                "in_edgar_register": bool(matched), "matched_register_issuer": matched,
            })
        if found == 0 and page > 2:
            break
        time.sleep(0.2)

    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    press = [row for row in rows if "rating action" in row["type"].casefold() or "assign" in row["title"].casefold()]
    press_issuers = sorted({row["issuer_guess"] for row in press if row["issuer_guess"]})
    missing = sorted({row["issuer_guess"] for row in press
                      if row["issuer_guess"] and not row["in_edgar_register"]})
    matched_programs = sorted({program_of(row["issuer_guess"]) for row in press
                               if row["in_edgar_register"] and program_of(row["issuer_guess"])})
    missing_programs = sorted({program_of(row["issuer_guess"]) for row in press
                               if not row["in_edgar_register"] and program_of(row["issuer_guess"])})
    manifest = {
        "generated_by": "scripts/build_agency_universe.py",
        "route": "KBRA publication listing, server rendered, no key",
        "pages_read": pages_read,
        "cards_tagged_data_center": len(rows),
        "rating_actions": len(press),
        "distinct_issuers_named": len(press_issuers),
        "issuers_absent_from_the_edgar_register": missing,
        "programs_matched_to_the_register": matched_programs,
        "programs_absent_from_the_register": missing_programs,
        "match_rule": "programme level, on a brand token. The SEC filer, the rated issuer and the co-issuer are "
                      "three legal entities of one programme, so a legal entity match would report every "
                      "programme as a miss and did",
        "register_issuers_checked": len(register_issuers),
        "limits": ["KBRA is one agency, so a deal rated only elsewhere will not appear",
                   "the match is on issuer name tokens, and a miss is reported rather than forced"],
    }
    OUT_JSON.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"pages read: {pages_read} | data center cards: {len(rows)} | rating actions: {len(press)}")
    print(f"distinct issuers named in rating actions: {len(press_issuers)}")
    print(f"matched to the EDGAR register: {len(press_issuers) - len(missing)}")
    print(f"absent from the EDGAR register: {len(missing)}")
    print(f"programmes matched: {len(matched_programs)} -> {matched_programs}")
    print(f"programmes absent from the register: {len(missing_programs)} -> {missing_programs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
