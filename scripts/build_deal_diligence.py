#!/usr/bin/env python3
"""Extract the due diligence record behind each data center securitization's rent stream.

Why: the ABS-15G exhibit is the independent accountant's agreed upon procedures report on the tenant lease
portfolio. It is the audit trail behind the deal's cash flow, and it names the systems queried, the tolerances
applied, the characteristics tested and the individual facility codes. The facility codes are the closest thing
to a site level identifier that exists in a free filing.

What it does not give: the rents, the lease expiries or the tenant names. Those sit in the Statistical Data File
which is referenced but not filed. That gap is recorded rather than papered over.

Reads results/deal-structure.csv, keeps the filings whose text mentions data center terms, and writes one row
per filing. Fetches run concurrently, with a bounded worker count to stay polite to the SEC.

Usage:
    python3 scripts/build_deal_diligence.py [--workers 4]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from edgar.filings import get_json, session, user_agent  # noqa: E402

STRUCTURE = ROOT / "results" / "deal-structure.csv"
OUT_CSV = ROOT / "results" / "deal-diligence.csv"
OUT_JSON = ROOT / "results" / "deal-diligence.json"

FIELDS = ["securitizer", "issuing_entity", "deal_series", "report_date", "accountant", "exhibit_document",
          "characteristics_referenced", "characteristic_numbers", "systems_named", "tolerance_clauses",
          "lease_terms_mentioned", "exhibit_chars", "accession"]
# Cut fields, with the evidence, because a shipped field that is mostly wrong is worse than a stated gap.
CUT_FIELDS = {
    "facility_codes": "attempted twice. A pattern rule over the whole exhibit returned boilerplate such as "
                      "BZ7 and JTU31 ten times per report. Restricting the rule to codes within 80 characters "
                      "of facility, location, property or site language left two filings out of 68. Real site "
                      "codes do appear, verified on Switch as AUS.02 and TX1, so the route exists, but it is "
                      "the Statistical Data File referenced by the report and not filed, not a better regex",
}


def fetch_text(url: str, tries: int = 4) -> str:
    last = ""
    for attempt in range(tries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": user_agent()})
            return urllib.request.urlopen(request, timeout=90).read().decode("utf-8", "replace")
        except Exception as error:
            last = str(error)[:80]
            time.sleep(1.0 + attempt)
    raise RuntimeError(last)


def clean(body: str) -> str:
    body = re.sub(r"<(script|style).*?</\1>", " ", body, flags=re.S | re.I)
    body = body.replace("&nbsp;", " ").replace("&#160;", " ").replace("&#8217;", "'").replace("&amp;", "&")
    body = re.sub(r"&#\d+;|&[a-z]+;", " ", body)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))


def parse_diligence(text: str) -> dict:
    numbers = sorted({int(value) for value in re.findall(r"Characteristic[s]?\s+(\d{1,2})", text)})
    systems = sorted({name for name in ("Asset Management System", "Statistical Data File", "Service Order",
                                        "Lease Agreement", "Invoice", "Colocation Facilities Agreement",
                                        "Rent Roll", "General Ledger")
                      if name.casefold() in text.casefold()})
    tolerances = [match.group(0)[:220] for match in
                  re.finditer(r"[^.]{0,160}deemed to be in agreement[^.]{0,120}\.", text)][:6]
    # Facility codes: two to five capitals, optionally a dot, then digits, as used in the Switch report
    # (AUS.02, TX1). Restricted to codes that appear more than once so prose capitals do not flood the list.
    return {
        "characteristics_referenced": len(numbers),
        "characteristic_numbers": " ".join(str(value) for value in numbers),
        "systems_named": "; ".join(systems),
        "tolerance_clauses": " | ".join(tolerances),
        "lease_terms_mentioned": len(re.findall(r"lease term|expiration|expiry|renewal option", text, re.I)),
    }


def work(s, row: dict) -> dict:
    out = {name: "" for name in FIELDS}
    for key in ("securitizer", "issuing_entity", "deal_series", "report_date", "accountant", "accession"):
        out[key] = row.get(key, "")
    cik = int(row["securitizer_cik"])
    accession = row["accession"]
    folder = accession.replace("-", "")
    try:
        index = get_json(s, f"https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/index.json")
    except Exception as error:
        out["exhibit_document"] = f"index failed: {str(error)[:60]}"
        return out
    for name in [item["name"] for item in index.get("directory", {}).get("item", [])]:
        if not name.lower().endswith((".htm", ".html", ".txt")) or "index" in name.lower():
            continue
        try:
            text = clean(fetch_text(f"https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{name}"))
        except Exception:
            continue
        if len(text) < 4000:
            continue
        if "agreed" not in text.casefold() and "procedure" not in text.casefold():
            continue
        out.update(parse_diligence(text))
        out["exhibit_document"] = name
        out["exhibit_chars"] = len(text)
        return out
    out["exhibit_document"] = "no agreed upon procedures exhibit found"
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)

    rows = [row for row in csv.DictReader(STRUCTURE.open())
            if row.get("mentions_data_center") == "True"]
    print(f"data center filings to read: {len(rows)}")
    s = session()
    started = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda row: work(s, row), rows))
    print(f"fetched in {time.time() - started:.1f}s with {args.workers} workers")

    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)

    found_exhibit = [row for row in results if row["exhibit_document"].endswith((".htm", ".html", ".txt"))]

    with_characteristics = [row for row in results if row["characteristics_referenced"]]
    manifest = {
        "generated_by": "scripts/build_deal_diligence.py",
        "route": "SEC EDGAR ABS-15G exhibits, no key, no entitlement",
        "filings_read": len(results),
        "exhibits_found": len(found_exhibit),
        "filings_with_characteristics": len(with_characteristics),
        "cut_fields": CUT_FIELDS,
        "securitizers": sorted({row["securitizer"].split("  (CIK")[0] for row in results}),
        "what_this_is": "the independent accountant's agreed upon procedures report behind each deal's tenant "
                        "lease portfolio",
        "known_gap": "the rents, lease expiries and tenant names sit in the Statistical Data File the report "
                     "references, and that file is not filed with the SEC",
        "workers": args.workers,
    }
    OUT_JSON.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"exhibits found: {len(found_exhibit)} of {len(results)}")
    print(f"filings naming characteristics: {len(with_characteristics)}")

    for row in results[:6]:
        print(f"  {row['issuing_entity'][:40]:42s} chars={row['exhibit_chars']:>7} "
              f"characteristics={row['characteristics_referenced']:>2} systems={row['systems_named'][:40]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
