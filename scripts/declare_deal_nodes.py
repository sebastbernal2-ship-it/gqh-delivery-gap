#!/usr/bin/env python3
"""Declare the named data center securitizations in the QuantGraph, with their connectors.

Why: `docs/plan/per-deal-credit-sources.md` establishes 42 named deals from SEC filings. A deal that exists
only in a results file is invisible to the graph, and the graph is the research object. This script moves the
deal layer into the node space with the boundary written into every node.

Rules it follows, all of them the manifest's own:

- **Idempotent.** It removes its own previous block before writing, so a rerun cannot duplicate a node or
  leave an orphan. The block is identified by id prefix, not by line number.
- **Every node connected.** The manifest fails on an orphan, so each deal gets an edge to the register that
  contains it and an edge to the blocked price node that names what is missing.
- **The boundary is in the node.** Identity and parties are declared; coupon, size and price are not reachable
  from a free source, and that sentence lives in the node's availability field rather than in a comment.

Usage:
    python3 scripts/declare_deal_nodes.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STRUCTURE = ROOT / "results" / "deal-structure.csv"
MANIFEST = ROOT / "docs" / "scan" / "quantgraph.jsonl"
AGENCY = ROOT / "results" / "agency-only-deals.csv"
AGENCY_DATASET_ID = "dataset:agency:datacenter-deals"
AGENCY_PREFIX = "asset:agency-deal:"

REGISTER_ID = "dataset:sec:datacenter-deal-register"
BOND_ID = "asset:credit:per-site-bond"
DEAL_PREFIX = "asset:datacenter-deal:"
EDGE_PREFIX = "e-deal-"
AVAILABILITY = ("identity, parties, series and filing dates from SEC EDGAR Form ABS-15G; no coupon, no size "
                "and no price is reachable for this deal from a free source")


def slug(entity: str, series: str) -> str:
    """The series is never truncated. A first version cut the whole slug at 84 characters, which sliced the
    series off long issuer names and collapsed two Compass series into one id. The manifest refused it."""
    name = re.sub(r"[^a-z0-9]+", "-", entity.casefold()).strip("-")
    name = re.sub(r"-{2,}", "-", name)[:56].strip("-")
    tail = re.sub(r"[^a-z0-9]+", "-", series.casefold()).strip("-")
    return f"{name}-s{tail}"


def disambiguate(entity: str, series: str) -> str:
    import hashlib
    digest = hashlib.sha1(f"{entity}|{series}".encode("utf-8")).hexdigest()[:8]
    return digest


def main() -> int:
    rows = [row for row in csv.DictReader(STRUCTURE.open())
            if row.get("mentions_data_center") == "True" and row["deal_series"] and row["issuing_entity"]]
    # One node per deal. Two deals are filed by two securitizer CIKs each, Compass Issuer II 2024-1 and
    # Vantage Issuer 2018-1, and a deal is one deal. The CIKs are kept in the availability text instead, so
    # the traceability survives the deduplication.
    grouped: dict[tuple[str, str], dict] = {}
    for row in rows:
        entry = grouped.setdefault((row["issuing_entity"].strip(), row["deal_series"].strip()),
                                   {"ciks": set(), "pool_type": row.get("pool_type", "")})
        entry["ciks"].add(row["securitizer_cik"])
    deals = sorted((entity, series, ",".join(sorted(entry["ciks"])), entry["pool_type"])
                   for (entity, series), entry in grouped.items())
    if not deals:
        raise SystemExit("no named data center deals in results/deal-structure.csv")

    seen: dict[str, str] = {}
    nodes: list[dict] = []
    edges: list[dict] = []
    for entity, series, cik, pool_type in deals:
        mixed = pool_type == "mixed_pool_conduit"
        node_id = DEAL_PREFIX + slug(entity, series)
        if node_id in seen:
            node_id = f"{node_id}-{disambiguate(entity, series)}"
        seen[node_id] = entity
        nodes.append({
            "kind": "node", "id": node_id, "layer": "asset", "type": "asset",
            "meaning": f"{entity}, Series {series}: a ring fenced data center securitization issuer "
                       f"whose collateral is tenant leases on data center property"
                       + (". MIXED POOL: the data center loan sits inside a diversified conduit pool, so the "
                          "site's constraint is diluted before the note" if mixed else ""),
            "status": "declared", "unit": "note, series and class level",
            "availability": AVAILABILITY + f". Filed under securitizer CIK {cik}",
            "sources": ["source:sec:edgar"], "roles": ["outcome", "execution"],
            "falsifier": "The issuer files no data center securitization, or the filing names no data center "
                         "property, or the deal does not survive the six gates",
        })
        edges.append({
            "kind": "edge", "id": f"{EDGE_PREFIX}{node_id.split(':')[-1]}-register", "from": REGISTER_ID,
            "to": node_id, "relation": "contains", "status": "declared",
            "condition": "The deal appears in a Form ABS-15G filing whose own text names data center terms",
            "falsifier": "Remove the deal when its filing is withdrawn or its text carries no data center term",
        })
        edges.append({
            "kind": "edge", "id": f"{EDGE_PREFIX}{node_id.split(':')[-1]}-bond", "from": node_id, "to": BOND_ID,
            "relation": "candidate_for", "status": "declared",
            "condition": "The deal is the object in which one site's constraint is priced, so it is the "
                         "candidate instrument for the per site credit claim",
            "falsifier": "Drop the candidate when the tranche is unreachable at a size a small book can hold, "
                         "which is the open instrument gate",
        })

    register = {
        "kind": "node", "id": REGISTER_ID, "layer": "dataset", "type": "dataset",
        "meaning": f"The named data center securitization deals recovered from SEC filings, {len(deals)} of them",
        "status": "declared", "unit": "deal",
        "availability": "results/deal-structure.csv, regenerated by make deal-structure, and "
                        "results/deal-diligence.csv for the due diligence record",
        "sources": ["source:sec:edgar"], "roles": ["provenance"],
        "falsifier": "A deal listed here fails to resolve to a filing on EDGAR",
    }

    # Agency named deals that no filing reaches. They are declared as blocked with the blocker stated, because
    # the gate that decides a trade is concentration and the agencies state operating terms for deals the SEC
    # register does not hold.
    agency_rows = [row for row in csv.DictReader(AGENCY.open())
                   if row.get("in_register") == "False" and row.get("issuer")] if AGENCY.exists() else []
    agency_nodes: list[dict] = []
    agency_edges: list[dict] = []
    seen_agency: set[str] = set()
    for row in agency_rows:
        name = row["issuer"].strip()
        slugged = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")[:52]
        series = re.sub(r"[^a-z0-9]+", "-", (row.get("series") or "series-unstated").casefold()).strip("-")
        node_id = f"{AGENCY_PREFIX}{slugged}-s{series}"
        if node_id in seen_agency:
            continue
        seen_agency.add(node_id)
        terms = []
        if row.get("largest_tenant_pct"):
            terms.append(f"largest tenant {row['largest_tenant_pct']} percent")
        if row.get("data_centers"):
            terms.append(f"{row['data_centers']} data centers")
        if row.get("critical_load_mw"):
            terms.append(f"{row['critical_load_mw']} MW of critical load")
        if row.get("aanoi_musd"):
            terms.append(f"AANOI {row['aanoi_musd']} million")
        agency_nodes.append({
            "kind": "node", "id": node_id, "layer": "asset", "type": "asset",
            "meaning": f"{name}" + (f", Series {row['series']}" if row.get("series") else "")
                       + (". Agency stated terms: " + "; ".join(terms) if terms else ""),
            "status": "blocked", "unit": "note",
            "availability": "named by a rating agency publication. No SEC filing was located for this deal in "
                            "the register pass",
            "blocker": row.get("blocker") or "no filing located",
            "sources": ["source:rating-agency"], "roles": ["candidate", "outcome"],
            "falsifier": "The deal resolves to an SEC filing, or the agency withdraws the rating",
        })
        agency_edges.append({
            "kind": "edge", "id": f"e-agency-{slugged}-{series}-belongs", "from": node_id,
            "to": AGENCY_DATASET_ID, "relation": "belongs_to", "status": "declared",
            "condition": "The deal appears in an agency publication tagged as a data center securitisation",
            "falsifier": "Remove the deal if the publication is withdrawn or mis-tagged",
        })
        agency_edges.append({
            "kind": "edge", "id": f"e-agency-{slugged}-{series}-bond", "from": node_id, "to": BOND_ID,
            "relation": "candidate_for", "status": "declared",
            "condition": "A ring fenced deal whose terms an agency states, with no filing located yet",
            "falsifier": "Drop the candidate when the blocker never clears",
        })
    agency_dataset = {
        "kind": "node", "id": AGENCY_DATASET_ID, "layer": "dataset", "type": "dataset",
        "meaning": f"Data center securitizations named by rating agency publications that no SEC filing in this "
                   f"register reaches, {len(agency_nodes)} of them",
        "status": "declared", "unit": "deal",
        "availability": "results/agency-only-deals.csv, regenerated by make agency-deals",
        "sources": ["source:rating-agency"], "roles": ["provenance"],
        "falsifier": "A listed deal resolves to a filing, which moves it into the SEC register",
    }

    kept: list[str] = []
    removed = 0
    for line in MANIFEST.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        identifier = str(record.get("id", ""))
        if (identifier.startswith(DEAL_PREFIX) or identifier.startswith(EDGE_PREFIX)
                or identifier == REGISTER_ID or identifier.startswith(AGENCY_PREFIX)
                or identifier.startswith("e-agency-") or identifier == AGENCY_DATASET_ID):
            removed += 1
            continue
        kept.append(line)

    with MANIFEST.open("w") as handle:
        for line in kept:
            handle.write(line + "\n")
        for record in [register, agency_dataset] + nodes + agency_nodes + edges + agency_edges:
            handle.write(json.dumps(record) + "\n")

    print(f"removed {removed} previous deal lines, wrote 2 dataset nodes, {len(nodes)} filing backed deals, "
          f"{len(agency_nodes)} agency only deals, {len(edges) + len(agency_edges)} edges")
    return 0


if __name__ == "__main__":
    sys.exit(main())
