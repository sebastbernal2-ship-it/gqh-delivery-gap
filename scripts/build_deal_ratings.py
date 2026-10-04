#!/usr/bin/env python3
"""Extract the rated class ladder per deal from agency publications, which is where the tranche table lives.

Why: EDGAR holds no prospectus for these 144A securitizations, so the class ladder comes from the rating
agencies. Their press releases are free and fetchable, and they carry more than ratings: the verified DBRS
pages give the rating per class, whether it is provisional or final, the original balance in currency, the
indicative coupon where one is stated, and the collateral description in words.

Boundaries, stated because both are real:

1. **The seed list is declared, not crawled.** This pass reads a fixed list of pages located by search. It is
   a proof of extractability with a measured coverage, not a census.
2. **Agencies rate deals that are not in the EDGAR register and the reverse.** The Vantage Jersey SPV is rated
   and is not in the 42, so the match is reported and left visible rather than forced.

Usage:
    python3 scripts/build_deal_ratings.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STRUCTURE = ROOT / "results" / "deal-structure.csv"
OUT_CSV = ROOT / "results" / "deal-ratings.csv"
OUT_JSON = ROOT / "results" / "deal-ratings.json"

AGENT = "Mozilla/5.0 (compatible; gqh-delivery-gap research; research@example.com)"
# Declared seed pages, all located by search on 2026-10-03 and none guessed.
SEEDS = [
    ("Morningstar DBRS", "Switch ABS Issuer, LLC Series 2025-2",
     "https://dbrs.morningstar.com/research/463873/morningstar-dbrs-assigns-provisional-credit-ratings-to-switch-abs-issuer-llc-series-2025-2"),
    ("Morningstar DBRS", "Compass Datacenters Issuer II, LLC Series 2025-2",
     "https://dbrs.morningstar.com/research/466648/morningstar-dbrs-finalizes-provisional-credit-rating-on-compass-datacenters-issuer-ii-llc-series-2025-2-and-confirms-credit-ratings-on-compass-datacenters-issuer-ii-llc-series-2025-1-series-2024-2-and-series-2024-1"),
    ("Morningstar DBRS", "Eight data center transactions",
     "https://dbrs.morningstar.com/research/449784/morningstar-dbrs-takes-credit-rating-actions-on-eight-data-center-transactions"),
    ("Morningstar DBRS", "EdgeConneX Data Centers Issuer, LLC credit rating report",
     "https://dbrs.morningstar.com/research/465304/edgeconnex-data-centers-issuer-llc-credit-rating-report"),
    ("Morningstar DBRS", "EdgeConneX Data Centers Issuer, LLC rating report",
     "https://dbrs.morningstar.com/research/404351/edgeconnex-data-centers-issuer-llc-rating-report"),
    ("Morningstar DBRS", "Vantage Data Centers Jersey Borrower SPV Limited",
     "https://dbrs.morningstar.com/research/454685/morningstar-dbrs-confirms-credit-ratings-on-vantage-data-centers-jersey-borrower-spv-limited"),
    ("Morningstar DBRS", "Vantage Data Centers Jersey Borrower SPV Limited Class B",
     "https://dbrs.morningstar.com/research/466962/morningstar-dbrs-assigns-provisional-credit-rating-to-class-b-notes-issued-by-vantage-data-centers-jersey-borrower-spv-limited-and-confirms-credit-rating-on-class-a-2-notes-stable-trends"),
    ("Morningstar DBRS", "Vantage Data Centers Jersey Borrower SPV Limited Class B final",
     "https://dbrs.morningstar.com/research/468688/morningstar-dbrs-finalises-provisional-credit-rating-on-class-b-notes-issued-by-vantage-data-centers-jersey-borrower-spv-limited-and-confirms-credit-rating-on-class-a-2-notes-stable-trends"),
    ("KBRA", "DataBank Issuer, LLC Series 2026-1",
     "https://www.kbra.com/publications/tGrWrdbr/kbra-assigns-preliminary-ratings-to-databank-series-2026-1"),
    ("KBRA", "Flexential Issuer, LLC Series 2026-1/2",
     "https://www.kbra.com/publications/PtCMQJLf/kbra-assigns-preliminary-ratings-to-flexential-issuer-llc-and-flexential-co-issuer-llc-series-2026-1-2"),
    ("KBRA", "Centersquare series",
     "https://www.kbra.com/publications/VnNyrVVh"),
    ("KBRA", "TierPoint Issuer LLC Series 2025-3/4",
     "https://www.kbra.com/publications/NWSCDPYs"),
    ("KBRA", "FirstLight Issuer, LLC",
     "https://www.kbra.com/publications/PDCvRdky"),
    ("Morningstar DBRS", "Vantage Data Centers Jersey Borrower SPV Limited provisional",
     "https://dbrs.morningstar.com/research/432090/morningstar-dbrs-assigns-a-provisional-credit-rating-to-vantage-data-centers-jersey-borrower-spv-limited"),
    ("Morningstar DBRS", "Vantage Data Centers Jersey Borrower SPV Limited finalised",
     "https://dbrs.morningstar.com/research/433235/morningstar-dbrs-finalizes-its-provisional-credit-rating-on-vantage-data-centers-jersey-borrower-spv-limited"),
    ("KBRA", "Cologix Canadian Issuer LP Series 2026-1/2",
     "https://apnews.com/press-release/business-wire/press-release-cd173833bd44460f8928ff73aa03f35d"),
    ("S&P Global Ratings", "Vantage Data Centers Issuer LLC Series 2025-2",
     "https://www.spglobal.com/ratings/en/regulatory/article/-/view/type/HTML/id/3480932"),
]

RATING = r"['\u2018\u2019\"]?(AAA|AA|A|BBB|BB|B|CCC|CC|C|D)(\+|-)?\s*(?:\(\s*(high|low|mid)\s*\))?\s*\(sf\)"
FIELDS = ["agency", "seed", "url", "class", "rating", "provisional", "amount_text", "coupon_text",
          "matched_register_issuer", "page_chars"]


def fetch(url: str, tries: int = 3) -> str:
    last = ""
    for attempt in range(tries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "text/html"})
            return urllib.request.urlopen(request, timeout=60).read().decode("utf-8", "replace")
        except Exception as error:
            last = str(error)[:80]
    return f"__FETCH_FAILED__ {last}"


def clean(body: str) -> str:
    body = re.sub(r"<(script|style).*?</\1>", " ", body, flags=re.S | re.I)
    body = body.replace("&nbsp;", " ").replace("&#160;", " ").replace("&amp;", "&").replace("&#8212;", "-")
    body = re.sub(r"&#\d+;|&[a-z]+;", " ", body)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))


def extract(text: str) -> list[dict]:
    """One row per class, paired by position and merged by name.

    Three versions were needed and the first two were wrong, both caught against ground truth. The first read
    200 characters after each class mention, which split a class's facts apart and lost the coupon on the
    Vantage Jersey release. The second concatenated every window for a class, which shared the first rating on
    the page across every class and turned the Switch ladder into AAA four times. This version keeps the chunk
    rule, meaning a rating belongs to the class printed before it, and then merges the facts of repeated
    mentions of the same class, so a coupon stated in a sentence without a rating still attaches. Verified
    against the Switch Series 2025-2 release, whose ladder is AAA, AA (low), A (low), BBB (low).
    """
    anchors = [(match.start(), match.group(1))
               for match in re.finditer(r"Class\s+([A-Z0-9][A-Z0-9\-]{0,10})", text)]
    order: list[str] = []
    merged: dict[str, dict] = {}
    for index, (position, name) in enumerate(anchors):
        stop = anchors[index + 1][0] if index + 1 < len(anchors) else min(len(text), position + 400)
        chunk = text[position:stop]
        entry = merged.setdefault(name, {"class": name, "rating": "", "provisional": "",
                                         "amount_text": "", "coupon_text": "", "series_context": ""})
        if name not in order:
            order.append(name)
        rating = re.search(RATING, chunk)
        if rating and not entry["rating"]:
            notch = f" {rating.group(2)}" if rating.group(2) else ""
            entry["rating"] = " ".join(bit for bit in (rating.group(1) + notch,
                                                       f"({rating.group(3)})" if rating.group(3) else "") if bit)
            entry["provisional"] = ("provisional"
                                    if re.search(r"\(P\)|provisional|Provis\.?-?Final", chunk, re.I)
                                    else "final or unstated")
        amount = re.search(r"((?:EUR|GBP|USD|\$|\u20ac|\u00a3)\s?[\d,.]+\s?(?:billion|million|bn|mm)?)",
                           chunk)
        if amount and not entry["amount_text"]:
            entry["amount_text"] = amount.group(1).strip()
        coupon = (re.search(r"coupon of\s([\d.]+%)", chunk, re.I)
                  or re.search(r"([\d.]+)%\s?coupon", chunk, re.I))
        if coupon and not entry["coupon_text"]:
            entry["coupon_text"] = coupon.group(1)
        series = re.findall(r"Series\s(20\d\d-[A-Z]?\d+)", text[:position])
        if series and not entry["series_context"]:
            entry["series_context"] = series[-1]
    return [merged[name] for name in order if merged[name]["rating"]]


METRIC_PATTERNS = {
    "data_centers": r"secured by\s+([\d,]+)\s+(?:multi[- ]?customer enterprise\s+)?data centers",
    "sellable_sf": r"([\d,]+)\s+sellable square feet|([\d,]+)\s+square feet \(sf\) of data center space",
    "critical_load_mw": r"([\d.]+)\s+megawatts \(MW\) of critical load",
    "annualized_revenue_musd": r"approximately\s+\$([\d.]+)\s+million of Annualized Revenue",
    "aanoi_musd": r"\$([\d.]+)\s+million of Annualized Adjusted Net Operating Income",
    "properties_named": r"(\d+)\s+(?:multi[- ]?customer enterprise\s+)?data centers, located in\s+(\d+)\s+markets",
    # Concentration and lease term decide whether a transfer is concentrated, which is gate 3. Stated on some
    # agency releases and absent from most, so the scorecard treats absence as blank rather than as a pass.
    "largest_tenant_pct": r"(?:largest|top|anchor) tenant[^.]{0,60}?([\d.]+)\s?%",
    "top_tenants_pct": r"(?:top|largest)\s+(?:ten|10)\s+tenants[^.]{0,60}?([\d.]+)\s?%",
    "walt_years": r"(?:weighted average (?:remaining )?lease term|WALT)[^.]{0,40}?([\d.]+)\s?(?:years|yrs)",
    "occupied_pct": r"occupanc[^.]{0,40}?([\d.]+)\s?%",
}


def metrics(text: str) -> dict:
    """Portfolio level operating metrics. Free, and the closest thing to a per deal income statement."""
    out: dict[str, str] = {}
    for name, pattern in METRIC_PATTERNS.items():
        match = re.search(pattern, text, re.I)
        out[name] = next((group for group in match.groups() if group), "") if match else ""
    return out


def main() -> int:
    issuers = sorted({row["issuing_entity"].strip().casefold()
                      for row in csv.DictReader(STRUCTURE.open())
                      if row.get("mentions_data_center") == "True" and row["issuing_entity"]})
    rows: list[dict] = []
    metric_rows: list[dict] = []
    failures: list[str] = []
    for agency, seed, url in SEEDS:
        body = fetch(url)
        if body.startswith("__FETCH_FAILED__"):
            failures.append(f"{agency} | {seed} | {body[:70]}")
            continue
        text = clean(body)
        classes = extract(text)
        matched = next((issuer for issuer in issuers if issuer.split(",")[0] in text.casefold()), "")
        found = metrics(text)
        metric_rows.append({"agency": agency, "seed": seed, "url": url, "page_chars": len(text),
                            "matched_register_issuer": matched, **found})
        for item in classes:
            rows.append({
                "agency": agency, "seed": seed, "url": url,
                "class": item["class"], "rating": item["rating"],
                "provisional": item["provisional"], "amount_text": item["amount_text"],
                "coupon_text": item["coupon_text"],
                "matched_register_issuer": matched, "page_chars": len(text),
            })
        if not classes:
            rows.append({"agency": agency, "seed": seed, "url": url, "class": "", "rating": "",
                         "provisional": "", "amount_text": "", "coupon_text": "",
                         "matched_register_issuer": matched, "page_chars": len(text)})

    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    metrics_csv = OUT_CSV.parent / "deal-operation-metrics.csv"
    metric_fields = ["agency", "seed", "url", "page_chars", "matched_register_issuer", *METRIC_PATTERNS]
    with metrics_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=metric_fields)
        writer.writeheader()
        writer.writerows(metric_rows)

    with_rating = [row for row in rows if row["rating"]]
    deals_covered = sorted({row["seed"] for row in with_rating})
    matched_deals = sorted({row["seed"] for row in with_rating if row["matched_register_issuer"]})
    manifest = {
        "generated_by": "scripts/build_deal_ratings.py",
        "route": "agency press releases, free and fetchable, located by search",
        "seeds_declared": len(SEEDS),
        "seeds_fetched": len(SEEDS) - len(failures),
        "class_rows_with_rating": len(with_rating),
        "deals_covered": deals_covered,
        "deals_matched_to_the_edgar_register": matched_deals,
        "coupon_rows": sum(1 for row in with_rating if row["coupon_text"]),
        "amount_rows": sum(1 for row in with_rating if row["amount_text"]),
        "failures": failures,
        "boundaries": [
            "the seed list is declared, not crawled, so this is a proof of extractability with a measured "
            "coverage rather than a census of all 42 deals",
            "agencies rate deals outside the EDGAR register and the reverse, so matches are reported and "
            "never forced",
            "S&P regulatory pages and some agency pages may refuse a non browser client, which is recorded "
            "as a fetch failure rather than a missing deal",
        ],
        "register_issuers_available": len(issuers),
        "operation_metrics_found": sum(1 for row in metric_rows
                                       if any(row.get(name) for name in METRIC_PATTERNS)),
        "operation_metrics_note": "KBRA releases carry portfolio operating metrics: data center count, "
                                  "sellable square feet, critical load in MW, annualized revenue and annualized "
                                  "adjusted net operating income, with site level revenue defined. The DBRS "
                                  "releases do not.",
        "universe_finding": "the KBRA index shows data center tagged securitizations outside the EDGAR register "
                            "built by name token, including Zayo, TierPoint and FirstLight, whose collateral "
                            "includes data centers but whose issuer names carry no data center token, so the "
                            "EDGAR register under counts the universe",
    }
    OUT_JSON.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"seeds: {len(SEEDS)} declared, {manifest['seeds_fetched']} fetched")
    print(f"class rows with a rating: {len(with_rating)} across {len(deals_covered)} deals")
    print(f"matched to the EDGAR register: {len(matched_deals)} deals")
    print(f"rows carrying a coupon: {manifest['coupon_rows']} | carrying an amount: {manifest['amount_rows']}")
    if failures:
        print("failures:")
        for line in failures:
            print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
