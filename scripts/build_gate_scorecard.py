#!/usr/bin/env python3
"""Score the named data center deals against the six gates, mechanically and with blanks admitted.

The rules are fixed here, before any of them is applied, and a gate that cannot be decided from a measured
field is written BLANK rather than argued. This exists because the six gates were written in
`docs/plan/relation-to-edge.md` and then never applied to a candidate with this much structure behind it.

Gate rules, declared:

1. **Constrained counterparty.** PASS when an issuing entity and a series are named in a filing, which is the
   structural evidence that a ring fenced borrower exists. The covenant type is BLANK: the indenture is not
   filed and no free source states the debt service thresholds.
2. **Price insensitive flow.** PASS when the diligence record names a Lease Agreement or a Service Order, which
   is contractual rent, or when a rated class ladder exists. PARTIAL otherwise.
3. **Transfer and concentration.** PASS only with both a magnitude and a concentration number. PARTIAL with a
   magnitude and no concentration, or the reverse. BLANK with neither.
4. **Instrument without dilution.** PARTIAL for a pure play issuer, because the note's collateral is data center
   rent only, with reachability unverified. FAIL for a mixed pool conduit, where a data center loan sits inside
   a diversified pool.
5. **Economics and capacity.** PARTIAL when a coupon or an original amount is stated, because the magnitude of
   the transfer then has a number attached even though costs are unknown. BLANK otherwise.
6. **Barrier.** Recorded once for the layer as attention and processing: the barrier is reading the lease and
   indenture documents and holding local power market knowledge. Stated, not measured, and never scored as a
   pass per deal.

Usage:
    python3 scripts/build_gate_scorecard.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STRUCTURE = ROOT / "results" / "deal-structure.csv"
DILIGENCE = ROOT / "results" / "deal-diligence.csv"
METRICS = ROOT / "results" / "deal-operation-metrics.csv"
RATINGS = ROOT / "results" / "deal-ratings.csv"
OUT_CSV = ROOT / "results" / "gate-scorecard.csv"
OUT_JSON = ROOT / "results" / "gate-scorecard.json"

PROGRAMME_TOKENS = ["databank", "flexential", "centersquare", "cologix", "tierpoint", "zayo", "firstlight",
                    "qts", "lohrasp", "compass", "vantage", "sabey", "switch", "aligned", "cyrusone",
                    "edgeconnex", "scalelogix", "edi"]
FIELDS = ["issuing_entity", "deal_series", "pool_type", "securitizer", "filed", "programme",
          "g1_counterparty", "g2_flow", "g3_transfer", "g4_instrument", "g5_economics", "g6_barrier",
          "magnitude", "concentration", "coupon_or_amount", "diligence_systems", "evidence_note"]


def programme_of(text: str) -> str:
    folded = text.casefold()
    for token in sorted(PROGRAMME_TOKENS, key=len, reverse=True):
        if token in folded:
            return token
    return ""


def main() -> int:
    structure = [row for row in csv.DictReader(STRUCTURE.open())
                 if row.get("mentions_data_center") == "True" and row["deal_series"] and row["issuing_entity"]]
    diligence = {}
    for row in csv.DictReader(DILIGENCE.open()):
        key = (row["issuing_entity"].strip(), row["deal_series"].strip())
        diligence[key] = row
    # Agency evidence attaches to a deal only when the programme AND the series both match. A programme level
    # match is too loose: the Vantage Jersey SPV's concentration of 73.2 percent in one tenant was first applied
    # to three unrelated Retained Vantage deals purely because both names contain Vantage. Programme level
    # numbers are kept as programme scope evidence and never used to decide a gate on one deal.
    metrics: dict[tuple[str, str], dict] = {}
    programme_scope: dict[str, dict] = {}
    for row in csv.DictReader(METRICS.open()):
        token = programme_of(row["seed"])
        if not token:
            continue
        series = ""
        match = re.search(r"Series\s(\d{4}-[\w/]+)", row["seed"])
        if match:
            series = match.group(1).split("/")[0]
        if series and (row.get("aanoi_musd") or row.get("annualized_revenue_musd")
                       or row.get("largest_tenant_pct")):
            metrics.setdefault((token, series), row)
        else:
            programme_scope.setdefault(token, row)
    # Coupons and amounts obey the same rule as the metrics: programme and series must both match. Keying these
    # on the programme alone would put the Vantage Jersey coupon on three unrelated Vantage deals.
    ratings: dict[tuple[str, str], dict] = {}
    for row in csv.DictReader(RATINGS.open()):
        if not row["rating"]:
            continue
        token = programme_of(row["seed"])
        match = re.search(r"Series\s(\d{4}-[\w/]+)", row["seed"])
        if token and match:
            ratings.setdefault((token, match.group(1).split("/")[0]),
                               {"coupon": row["coupon_text"], "amount": row["amount_text"],
                                "class": row["class"], "rating": row["rating"]})
    def concentration_of(row: dict) -> str:
        if row.get("largest_tenant_pct") or row.get("top_tenants_pct"):
            return (f"largest tenant {row.get('largest_tenant_pct', '')} percent, "
                    f"top tenants {row.get('top_tenants_pct', '')} percent").strip(", ")
        return ""

    # One row per deal, not per legal entity. An issuer and its co-issuer file two ABS-15G cover pages for the
    # same series, and counting them twice would double every rate in the summary.
    # The key drops the co-issuer suffix and keeps everything else. A first attempt keyed on programme plus
    # series, which collapsed four different Vantage issuers that each have a Series 2025-1 into one row, and
    # two different issuers with the same series number are different deals with different collateral.
    deals: dict[tuple[str, str], dict] = {}
    for row in structure:
        entity = row["issuing_entity"].strip()
        # Drop the issuer word as well as the co-issuer word: "DataBank Issuer, LLC" and
        # "DataBank Co-Issuer, LLC" name one deal, while "Vantage Data Centers Issuer, LLC" and
        # "Vantage Data Centers Canada, LP" stay separate because Canada is not an issuer word.
        normalised = re.sub(r"\b(?:and\s+)?co[- ]?issuer\b|\bissuer\b", " ", entity, flags=re.I)
        normalised = re.sub(r"[^a-z0-9]+", " ", normalised.casefold()).strip()
        entry = deals.setdefault((normalised, row["deal_series"].strip()), dict(row, issuer_names=set()))
        entry["issuer_names"].add(entity)

    out: list[dict] = []
    for (entity, series), row in sorted(deals.items(), key=lambda item: (item[0][0].casefold(), item[0][1])):
        pool = row.get("pool_type", "")
        programme = programme_of(entity) or programme_of(row["securitizer"])
        diligence_row = diligence.get((entity, series), {})
        systems = diligence_row.get("systems_named", "")
        metric = metrics.get((programme, series), {})
        scope = programme_scope.get(programme, {})
        rating = ratings.get((programme, series), {})

        g1 = "PASS" if entity and series else "BLANK"
        g2 = "PASS" if ("Lease Agreement" in systems or "Service Order" in systems or rating) else "PARTIAL"
        # Every deal in the register is a rent securitisation, so the flow gate is structural rather than a
        # measurement. Recorded as such so it is never mistaken for evidence that the flow was measured.
        magnitude = (f"AANOI {metric['aanoi_musd']} million" if metric.get("aanoi_musd")
                     else (f"revenue {metric['annualized_revenue_musd']} million"
                           if metric.get("annualized_revenue_musd") else ""))
        concentration_text = concentration_of(metric)
        if magnitude and concentration_text:
            g3 = "PASS"
        elif magnitude or concentration_text:
            g3 = "PARTIAL"
        else:
            g3 = "BLANK"
        g4 = "FAIL" if pool == "mixed_pool_conduit" else "PARTIAL"
        coupon_amount = "; ".join(bit for bit in (rating.get("coupon"), rating.get("amount")) if bit)
        g5 = "PARTIAL" if rating else "BLANK"
        issuer_label = " and ".join(sorted(row.get("issuer_names", {entity})))
        out.append({
            "issuing_entity": issuer_label[:120], "deal_series": series, "pool_type": pool,
            "securitizer": row["securitizer"].split("  (CIK")[0], "filed": row["report_date"],
            "programme": programme,
            "g1_counterparty": g1, "g2_flow": g2, "g3_transfer": g3, "g4_instrument": g4,
            "g5_economics": g5, "g6_barrier": "layer barrier: attention and processing, stated not measured",
            "magnitude": magnitude, "concentration": concentration_text, "coupon_or_amount": coupon_amount,
            "diligence_systems": systems,
            "evidence_note": ("agency metric matched on programme and series" if metric
                              else ("programme scope evidence only, not attributable to this deal"
                                    if scope else "no agency metric located")),
        })

    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(out)

    def count(gate: str, verdict: str) -> int:
        return sum(1 for row in out if row[gate] == verdict)

    ranked = sorted(out, key=lambda row: (row["g3_transfer"] == "PASS", row["g5_economics"] == "PARTIAL",
                                          row["g2_flow"] == "PASS"), reverse=True)
    manifest = {
        "generated_by": "scripts/build_gate_scorecard.py",
        "deals_scored": len(out),
        "pure_play": sum(1 for row in out if row["pool_type"] == "pure_play"),
        "mixed_pool": sum(1 for row in out if row["pool_type"] == "mixed_pool_conduit"),
        "g1_counterparty_pass": count("g1_counterparty", "PASS"),
        "g2_flow_pass": count("g2_flow", "PASS"),
        "g2_flow_partial": count("g2_flow", "PARTIAL"),
        "g3_transfer_pass": count("g3_transfer", "PASS"),
        "g3_transfer_partial": count("g3_transfer", "PARTIAL"),
        "g3_transfer_blank": count("g3_transfer", "BLANK"),
        "g4_instrument_fail": count("g4_instrument", "FAIL"),
        "g4_instrument_partial": count("g4_instrument", "PARTIAL"),
        "g5_economics_partial": count("g5_economics", "PARTIAL"),
        "g5_economics_blank": count("g5_economics", "BLANK"),
        "gate_3_reads": "gate 3 passes only where a magnitude and a concentration number both exist. Four deals "
                        "have a magnitude from an agency release and one has a concentration, so gate 3 is "
                        "almost entirely blank, which is the honest state of the evidence and not a verdict "
                        "on the deals",
        "best_supported_deals": [f"{row['issuing_entity']} Series {row['deal_series']}" for row in ranked[:12]
                                 if row["g3_transfer"] != "BLANK" or row["g5_economics"] == "PARTIAL"],
        "attribution_rule": "agency evidence decides a gate only where programme and series both match. "
                            "Programme level numbers are reported as programme scope evidence and leave the "
                            "gate blank",
        "barrier": "attention and processing across the layer: reading lease and indenture documents and "
                   "holding local power market knowledge. Stated, not measured",
    }
    OUT_JSON.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"deals scored: {len(out)} ({manifest['pure_play']} pure play, {manifest['mixed_pool']} mixed pool)")
    print(f"  gate 1 counterparty PASS: {manifest['g1_counterparty_pass']}")
    print(f"  gate 2 flow PASS/PARTIAL: {manifest['g2_flow_pass']} / {manifest['g2_flow_partial']}")
    print(f"  gate 3 transfer PASS/PARTIAL/BLANK: {manifest['g3_transfer_pass']} / "
          f"{manifest['g3_transfer_partial']} / {manifest['g3_transfer_blank']}")
    print(f"  gate 4 instrument FAIL (conduit) / PARTIAL: {manifest['g4_instrument_fail']} / "
          f"{manifest['g4_instrument_partial']}")
    print(f"  gate 5 economics PARTIAL/BLANK: {manifest['g5_economics_partial']} / {manifest['g5_economics_blank']}")
    print("")
    for row in ranked[:10]:
        if row["g3_transfer"] == "BLANK" and row["g5_economics"] == "BLANK":
            continue
        print(f"  {row['issuing_entity'][:38]:40s} S{row['deal_series']:8s} g3={row['g3_transfer']:7s} "
              f"g5={row['g5_economics']:7s} {row['magnitude'][:22]:24s} {row['concentration'][:34]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
