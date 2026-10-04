#!/usr/bin/env python3
"""Build the named deal registry for data center securitizations from EDGAR, free, no entitlement.

Why this exists: the per site credit claim needs deal level data. FINRA reaches aggregates only, so the free
route with deal granularity is EDGAR, where Reg AB and Rule 15Ga-1 make a securitizer file even when the deal
itself is not registered.

Two sweeps, both recorded with their query so a reader can see how the set was found rather than only what
came out:

1. **Named securitizers.** A declared name list queried against the securitizer and trustee forms.
2. **A phrase sweep.** The phrase "data center" against the same forms, which finds deals whose filer name
   does not carry the phrase.

Nothing here parses a document or measures a relation. It builds the registry the parsing step will walk.

Usage:
    python3 scripts/build_credit_deal_registry.py [--pages 3]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from edgar.filings import get_json, session  # noqa: E402

OUT_CSV = ROOT / "results" / "credit-deal-registry.csv"
OUT_JSON = ROOT / "results" / "credit-deal-registry.json"

FTS = "https://efts.sec.gov/LATEST/search-index?q={query}&forms={forms}&from={offset}"
FORMS = "ABS-15G,10-D,424B2,424B3,424B5,S-3"
PHRASE = "data center"
# Only these two forms carry data about a specific deal rather than a fund's holdings of a name.
DEAL_LEVEL_FORMS = {"ABS-15G", "10-D"}
# A deal level filer counts as a data center program when its own name says so. A name query is a discovery
# route, not a classification: a Sunrun solar ABS filing is found by the query "Iron Mountain" because the
# document mentions the tenant, and it must not enter the data center set for that reason. It did, and this
# rule is why it no longer does.
CONFIRMED_OFF_TOPIC_TOKENS = ("sunrun", "vivint solar")
DATA_CENTER_TOKENS = ("data center", "datacenter", "colocation", "vantage", "cologix", "flexential",
                      "databank", "stack infra", "switch", "sabey", "compass datacenters", "cyrusone",
                      "aligned", "edgeconnex", "phoenix data center", "vault di", "mecp1", "urbacon",
                      "bryant park", "citigroup commercial mortgage", "bbcms")
# The forms that carry deal level credit disclosure, and what each one is for.
FORM_MEANING = {
    "ABS-15G": "securitizer asset level disclosure, filed even for unregistered 144A deals",
    "10-D": "monthly trustee distribution report: cash flows, delinquencies, current factors",
    "424B2": "prospectus supplement: tranche sizes, coupons, ratings, waterfall",
    "424B3": "prospectus: deal structure and asset pool",
    "424B5": "prospectus supplement: tranche sizes and pricing",
    "S-3": "registration statement, when the deal is registered",
}
# Declared securitizer and platform names, queried as phrases.
NAMES = ["Flexential", "Cologix", "Phoenix Data Center Acquisitions", "DataBank Holdings",
         "Vantage Data Centers", "Aligned Data Centers", "Switch ABS", "Sabey Data Center",
         "QTS Realty", "CyrusOne", "Iron Mountain", "Digital Realty", "Equinix",
         "Stack Infrastructure", "Crusoe Energy", "CoreWeave", "Applied Digital", "TeraWulf"]


def search(s, phrase: str, pages: int) -> tuple[list[dict], int]:
    """Page the full text search and return the hits with their filers, plus the reported total."""
    out: list[dict] = []
    total = 0
    for page in range(pages):
        url = FTS.format(query=phrase.replace(" ", "+"), forms=FORMS.replace(",", "%2C"),
                         offset=page * 10)
        try:
            payload = get_json(s, url)
        except Exception as error:  # the search host throttles; a failed page is not a failed sweep
            print(f"  page {page} for {phrase!r} failed: {str(error)[:80]}")
            break
        hits = payload.get("hits", {}).get("hits", [])
        total = payload.get("hits", {}).get("total", {}).get("value", total)
        if not hits:
            break
        for hit in hits:
            source = hit.get("_source", {})
            accession = hit.get("_id", "").split(":")[0]
            forms = source.get("root_forms") or [source.get("file_type", "")]
            for cik, name in zip(source.get("ciks", []), source.get("display_names", [])):
                out.append({
                    "query": phrase,
                    "form": (forms[0] or "").strip(),
                    "filer": name,
                    "cik": str(cik),
                    "filing_date": source.get("file_date", ""),
                    "accession": accession,
                })
    return out, total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=3, help="search pages per query, 10 hits each")
    args = parser.parse_args(argv)

    s = session()
    rows: list[dict] = []
    sweep: list[dict] = []

    print(f"named sweep: {len(NAMES)} names")
    for name in NAMES:
        hits, total = search(s, '"' + name + '"', args.pages)
        print(f"  {name:34s} hits={len(hits):3d} reported_total={total}")
        rows.extend(hits)

    hits, total = search(s, '"' + PHRASE + '"', args.pages)
    print(f"phrase sweep: {PHRASE!r} hits={len(hits)} reported_total={total}")
    sweep.extend(hits)

    # Deduplicate on the filing, keeping the queries that found it.
    merged: dict[tuple[str, str], dict] = {}
    for row in rows + sweep:
        key = (row["cik"], row["accession"])
        seen = merged.setdefault(key, dict(row, queries=[], from_phrase_sweep=False))
        if row["query"] == '"' + PHRASE + '"':
            seen["from_phrase_sweep"] = True
        elif row["query"] not in seen["queries"]:
            seen["queries"].append(row["query"])

    out_rows = []
    for row in merged.values():
        form = row["form"] or "form not reported"
        found_by = "; ".join(row["queries"]) or "phrase sweep"
        named = any(token in row["filer"].casefold() for token in DATA_CENTER_TOKENS)
        out_rows.append({
            "cik": row["cik"], "filer": row["filer"], "form": form,
            "filing_date": row["filing_date"], "accession": row["accession"],
            "found_by": found_by,
            "deal_level": form in DEAL_LEVEL_FORMS,
            "data_center_program": named,
            "carries": FORM_MEANING.get(form, "not one of the declared deal level forms"),
        })
    out_rows.sort(key=lambda item: (item["filer"], item["filing_date"]))

    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["cik", "filer", "form", "filing_date", "accession",
                                                    "found_by", "deal_level", "data_center_program", "carries"])
        writer.writeheader()
        writer.writerows(out_rows)

    by_form: dict[str, int] = {}
    for row in out_rows:
        by_form[row["form"]] = by_form.get(row["form"], 0) + 1
    core = [row for row in out_rows if row["deal_level"] and row["data_center_program"]]
    excluded = sorted({row["filer"] for row in out_rows
                       if row["deal_level"] and not row["data_center_program"]})
    confirmed_off_topic = [name for name in excluded
                           if any(token in name.casefold() for token in CONFIRMED_OFF_TOPIC_TOKENS)]
    unresolved = [name for name in excluded if name not in confirmed_off_topic]
    core_filers = sorted({row["filer"] for row in core}, key=lambda name: name.casefold())
    filers = sorted({row["filer"] for row in out_rows})
    manifest = {
        "generated_by": "scripts/build_credit_deal_registry.py",
        "route": "SEC EDGAR full text search, no key, no entitlement",
        "forms_queried": FORMS.split(","),
        "named_queries": NAMES,
        "phrase_query": PHRASE,
        "pages_per_query": args.pages,
        "filings": len(out_rows),
        "distinct_filers": len(filers),
        "by_form": by_form,
        "deal_level_filings": len(core),
        "deal_level_securitizers": core_filers,
        "deal_level_filers_excluded_by_name_rule": {
            "confirmed_off_topic": confirmed_off_topic,
            "unresolved": unresolved,
            "rule": "a deal level filer enters the set only when its own name carries a data center token. An "
                    "excluded filer is not evidence of anything until its document is read, which is why the "
                    "two lists are separate.",
        },
        "filers": filers,
        "form_meaning": FORM_MEANING,
        "boundary": "this is a registry of filings, not a measurement. A filing is a lead until the document "
                    "is parsed and its availability time is bound.",
    }
    OUT_JSON.write_text(json.dumps(manifest, indent=2) + "\n")
    print("")
    print(f"registry written: {len(out_rows)} filings from {len(filers)} filers")
    print(f"by form: {by_form}")
    print(f"deal level filings: {len(core)} from {len(core_filers)} securitizers")
    for name in core_filers:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
