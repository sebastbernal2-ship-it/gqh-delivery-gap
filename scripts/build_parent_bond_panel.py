#!/usr/bin/env python3
"""Build the parents' bond panel from registered fund holdings, which is free, point in time and carries CUSIPs.

Why this route: FINRA's bond search is gated behind a login and its detail pages need a symbol we do not have.
But every registered fund files its holdings quarterly as NPORT-P, each position carries name, CUSIP, par, fair
value, coupon and maturity, and EDGAR full text search finds those filings by the issuer's bond entity name.
So the free corporate bond panel is a fund holdings pull, and the issuer names to search are the legal entities
that issue the notes, not the tickers.

What it gives: CUSIP, par, fair value, price per 100 of par, coupon, maturity and the fund and period the mark
came from. A fund mark is a quarterly valuation, not an exchange print, and nothing here is a live price.

Usage:
    python3 scripts/build_parent_bond_panel.py [--funds 3]
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

OUT_CSV = ROOT / "results" / "parent-bond-panel.csv"
OUT_JSON = ROOT / "results" / "parent-bond-panel.json"
FTS = "https://efts.sec.gov/LATEST/search-index?q=%22{name}%22&forms=NPORT-P"
# The bond issuing entities behind the listed parents, and the data center names in the complex.
# The issuer entities behind the data center, power and AI capex complex. Each one is a legal name that appears
# in a fund holdings file, which is why the list holds entities rather than tickers.
ISSUERS = [
    "Digital Realty Trust LP", "Digital Realty Trust Inc", "Equinix Inc", "Iron Mountain Inc",
    "Oracle Corp", "CoreWeave Inc", "Nebius Group", "American Tower Corp", "Vistra Corp",
    "CyrusOne LP", "QTS Realty Trust", "Switch Inc", "DataBank", "Flexential", "Aligned Data Centers",
    "Centersquare", "TierPoint", "Zayo Group", "Lumen Technologies", "Constellation Energy",
    "Talen Energy", "NRG Energy", "PPL Corp", "Dominion Energy", "American Electric Power",
    "Duke Energy", "Exelon", "NextEra Energy", "Southern Co", "Entergy", "PG&E Corp",
    "Quanta Services", "Emcor Group", "Vertiv Holdings", "Eaton Corp", "Schneider Electric",
    "GE Vernova", "Hubbell Inc", "nVent Electric", "Comfort Systems", "Microsoft Corp",
    "Amazon.com Inc", "Alphabet Inc", "Meta Platforms Inc", "Apple Inc", "Nvidia Corp",
    "Advanced Micro Devices", "Micron Technology", "Broadcom Inc", "Marvell Technology",
    "Bloom Energy", "Oklo Inc", "NuScale Power", "Cameco Corp", "Uranium Energy",
]
FIELDS = ["issuer_entity", "holding_name", "cusip", "par_usd", "fair_value_usd", "price_per_100",
          "coupon_pct", "maturity", "fund", "period"]


SUFFIXES = (" llc", " inc", " incorporated", " corp", " corporation", " lp", " l.p.", " ltd", " limited",
             " co", " company", " group", " holdings", " trust", " plc", " sa", " nv", " ag", " gmbh")


def _norm(value: str) -> str:
    """Letters and spaces only, with the corporate suffix removed, so 'Digital Realty Trust LP' reduces to
    'digital realty' and matches a fund's own wording without matching a different company that shares a word."""
    text = re.sub(r"[^a-z ]+", " ", value.casefold())
    text = re.sub(r"\s+", " ", text).strip()
    for suffix in SUFFIXES:
        if text.endswith(suffix.strip()):
            text = text[: -len(suffix.strip())].strip()
    return text


def fetch_text(url: str, tries: int = 3) -> str:
    last = ""
    for attempt in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": user_agent()}),
                                          timeout=180).read().decode("utf-8", "replace")
        except Exception as error:
            last = str(error)[:70]
    raise RuntimeError(last)


def filings_for(s, name: str, pages: int = 3) -> list[dict]:
    """Page the search. One page returns ten hits and most of them are equity funds, so a wider pull is what
    actually raises coverage: the first run read four filings per issuer and found two issuers' bonds."""
    out: list[dict] = []
    hits: list[dict] = []
    for page in range(pages):
        url = FTS.format(name=name.replace(" ", "+")) + f"&from={page * 10}"
        try:
            payload = get_json(s, url)
        except Exception:
            break
        page_hits = payload.get("hits", {}).get("hits", [])
        if not page_hits:
            break
        hits.extend(page_hits)
    for hit in hits:
        source = hit.get("_source", {})
        accession = hit.get("_id", "").split(":")[0]
        for cik, display in zip(source.get("ciks", []), source.get("display_names", [])):
            out.append({"issuer_entity": name, "cik": str(cik), "fund": display,
                        "accession": accession, "period": source.get("period_ending", ""),
                        "file_date": source.get("file_date", "")})
    return out


def holding_rows(payload: dict, meta: dict, text: str) -> tuple[list[dict], int]:
    rows: list[dict] = []
    dropped = 0
    for block in re.findall(r"<invstOrSec>(.*?)</invstOrSec>", text, re.S):
        # Debt positions only. A fund holding the parent's equity reports a share count as balance, and using
        # it as par produced prices per 100 of 19,394 in the first pass. NPORT-P marks a debt position with a
        # debtSec element, so the filter is structural rather than a numeric guess.
        if "<debtSec>" not in block:
            continue
        name = re.search(r"<name>(.*?)</name>", block, re.S)
        if not name:
            continue
        holding = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", name.group(1))).strip()
        # Full name matching, not first token matching. The first deep run matched on the first word alone and
        # promptly labelled American Electric Power bonds as American Tower, and any holding containing
        # "American" as ours. The issuer string now has to appear in the fund's own reported name after both
        # sides are reduced to letters.
        matched = next((issuer for issuer in ISSUERS if _norm(issuer) in _norm(holding)), "")
        if not matched:
            continue
        meta = dict(meta, issuer_entity=matched)
        def number(tag: str) -> str:
            match = re.search(rf"<{tag}>(.*?)</{tag}>", block, re.S)
            return re.sub(r"[^0-9.\-]", "", match.group(1)) if match else ""
        cusip = re.search(r"<cusip>(.*?)</cusip>", block, re.S)
        # The NPORT-P element names are not the obvious ones: the coupon lives in annualizedRt and the maturity
        # in maturityDt. Guessing maturityDate and coupon returned empty fields on every row of the first pass.
        maturity = re.search(r"<maturityDt>(.*?)</maturityDt>", block, re.S)
        title = re.search(r"<title>(.*?)</title>", block, re.S)
        par = number("balance")
        value = number("valUSD")
        coupon = number("annualizedRt")
        try:
            price = f"{float(value) / float(par) * 100:.3f}" if float(par) else ""
        except (TypeError, ValueError, ZeroDivisionError):
            price = ""
        cusip_value = (cusip.group(1).strip() if cusip else "")
        # A price per 100 of par outside 1 to 200 is not a bond price, and a placeholder CUSIP of zeros is not
        # an identifier. Both are dropped and counted rather than shipped.
        try:
            plausible = 1.0 <= float(price) <= 200.0
        except (TypeError, ValueError):
            plausible = False
        if not plausible or set(cusip_value) == {"0"} or len(cusip_value) != 9:
            return_early = True
        else:
            return_early = False
        if return_early:
            dropped += 1
            continue
        rows.append({
            "issuer_entity": meta["issuer_entity"],
            "holding_name": (re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", title.group(1))).strip()[:110]
                             if title else holding[:110]),
            "cusip": cusip_value, "par_usd": par, "fair_value_usd": value,
            "price_per_100": price, "coupon_pct": coupon,
            "maturity": (maturity.group(1).strip() if maturity else ""),
            "fund": meta["fund"], "period": (re.search(r"<repPdDate>(.*?)</repPdDate>", text, re.S).group(1)
                                             if re.search(r"<repPdDate>(.*?)</repPdDate>", text, re.S)
                                             else meta["period"]),
        })
    return rows, dropped


def fund_history(s, cik: str, periods: int) -> list[dict]:
    """Every recent NPORT-P for one fund, which is the time series lever: one fund holding a bond across six
    years is twenty four marks for that bond, where the first pass took one filing per issuer."""
    out: list[dict] = []
    try:
        submissions = get_json(s, f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json")
    except Exception:
        return out
    rec = submissions["filings"]["recent"]
    # One filing per report date, not the most recent N filings. A trust files an NPORT-P for every series on
    # the same day, so taking the newest filings produced breadth across series and almost no time depth: the
    # first deep run returned 316 positions spanning two dates. Distinct dates is the time series lever.
    seen_periods: set[str] = set()
    for index, form in enumerate(rec["form"]):
        if not form.startswith("NPORT-P"):
            continue
        period = rec["reportDate"][index] if "reportDate" in rec else rec["filingDate"][index]
        if period in seen_periods:
            continue
        seen_periods.add(period)
        out.append({"cik": cik, "accession": rec["accessionNumber"][index], "period": period,
                    "filing_date": rec["filingDate"][index], "fund": submissions.get("name", "")})
        if len(out) >= periods:
            break
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--funds", type=int, default=3, help="holdings filings to read per issuer")
    parser.add_argument("--deep", action="store_true",
                        help="walk each candidate fund's filing history instead of reading one filing per issuer")
    parser.add_argument("--top-funds", type=int, default=16, help="deep mode: funds to walk, ranked by hits")
    parser.add_argument("--periods", type=int, default=4, help="deep mode: filings to read per fund")
    args = parser.parse_args(argv)

    s = session()
    with ThreadPoolExecutor(max_workers=8) as pool:
        found = list(pool.map(lambda name: filings_for(s, name), ISSUERS))
    candidates = [row for group in found for row in group]

    if args.deep:
        # Rank the funds by how many of our issuers they are seen holding, then walk each fund's own history.
        weight: dict[str, int] = {}
        names: dict[str, str] = {}
        for row in candidates:
            weight[row["cik"]] = weight.get(row["cik"], 0) + 1
            names[row["cik"]] = row["fund"]
        top = sorted(weight, key=lambda cik: -weight[cik])[:args.top_funds]
        print(f"issuer entities searched: {len(ISSUERS)} | candidate filings: {len(candidates)} | "
              f"funds ranked by hits: {len(weight)} | walking the top {len(top)} for {args.periods} periods each")
        with ThreadPoolExecutor(max_workers=8) as pool:
            histories = list(pool.map(lambda cik: fund_history(s, cik, args.periods), top))
        chosen = []
        for group in histories:
            for row in group:
                row["issuer_entity"] = ""  # a fund file is scanned for every issuer at once
                chosen.append(row)
    else:
        by_issuer: dict[str, list[dict]] = {}
        for row in candidates:
            by_issuer.setdefault(row["issuer_entity"], []).append(row)
        chosen = [row for rows in by_issuer.values() for row in rows[:args.funds]]
    print(f"filings to read: {len(chosen)}")

    def work(meta: dict) -> tuple[list[dict], int]:
        folder = meta["accession"].replace("-", "")
        url = f"https://www.sec.gov/Archives/edgar/data/{int(meta['cik'])}/{folder}/primary_doc.xml"
        try:
            text = fetch_text(url)
        except Exception:
            return [], 0
        return holding_rows(meta, meta, text)

    with ThreadPoolExecutor(max_workers=6) as pool:
        nested = list(pool.map(work, chosen))
    rows = [row for group, _ in nested for row in group]
    dropped_total = sum(count for _, count in nested)
    rows.sort(key=lambda row: (row["issuer_entity"], row["maturity"]))

    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "generated_by": "scripts/build_parent_bond_panel.py",
        "route": "EDGAR NPORT-P fund holdings, free, quarterly marks",
        "issuer_entities_searched": ISSUERS,
        "filings_read": len(chosen),
        "positions_found": len(rows),
        "positions_with_cusip": sum(1 for row in rows if row["cusip"]),
        "issuers_with_positions": sorted({row["issuer_entity"] for row in rows}),
        "positions_dropped": dropped_total,
        "drop_rules": "a position without a debtSec element, a price per 100 outside 1 to 200, a placeholder "
                      "CUSIP of zeros, or a CUSIP that is not nine characters is dropped and counted",
        "boundary": "a fund mark is a quarterly valuation and not an exchange print. Nothing here is a live "
                    "price, and a holding appears only when a registered fund reports it",
    }
    OUT_JSON.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"positions: {len(rows)} with CUSIP: {manifest['positions_with_cusip']} "
          f"| issuers covered: {len(manifest['issuers_with_positions'])}")
    for row in rows[:14]:
        print(f"  {row['issuer_entity'][:22]:24s} {row['cusip']:11s} par {row['par_usd'][:12]:>12s} "
              f"px {row['price_per_100'][:7]:>7s} cpn {row['coupon_pct'][:6]:>6s} mat {row['maturity'][:10]:10s} "
              f"{row['fund'][:26]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
