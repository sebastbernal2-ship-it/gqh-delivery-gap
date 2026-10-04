#!/usr/bin/env python3
"""Validate the conceptual seed and write the four JSONL files the connection index reads.

    python3 scripts/build_conceptual_layer.py
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
SCAN = ROOT / "docs" / "scan"

import conceptual_seed  # noqa: E402
import conceptual_seed_b  # noqa: E402  (imports for their side effects on the shared lists)
import conceptual_seed_c  # noqa: E402
import conceptual_seed_d  # noqa: E402

PHASES = conceptual_seed.PHASES
FORCES = conceptual_seed.FORCES
INTERACTIONS = conceptual_seed.INTERACTIONS
ASSUMPTIONS = conceptual_seed.ASSUMPTIONS
CHAINS = conceptual_seed.CHAINS


def main() -> int:
    force_ids = [force["id"] for force in FORCES]
    duplicates = [identifier for identifier, count in collections.Counter(force_ids).items() if count > 1]
    if duplicates:
        raise SystemExit(f"duplicate force ids: {duplicates[:5]}")
    known = set(force_ids)
    problems = []
    seen_interactions = set()
    for interaction in INTERACTIONS:
        identifier = f"interaction:{interaction['from']}->{interaction['to']}:{interaction['relation']}"
        if identifier in seen_interactions:
            problems.append(f"duplicate interaction {identifier}")
        seen_interactions.add(identifier)
        for field in ("from", "to"):
            if interaction[field] not in known:
                problems.append(f"unknown endpoint {interaction[field]} in {identifier}")
        for field in ("condition", "assumption", "kill", "channel"):
            if not interaction.get(field):
                problems.append(f"{identifier} missing {field}")
        for phase in interaction.get("sign_by_phase", {}):
            if phase not in PHASES:
                problems.append(f"{identifier} unknown phase {phase}")
    chain_hop_addresses = {}
    for chain in CHAINS:
        if len(chain["hops"]) < 2:
            problems.append(f"{chain['id']} has fewer than two hops")
        for position, hop in enumerate(chain["hops"], start=1):
            if hop not in known:
                problems.append(f"{chain['id']} hop {position} unknown force {hop}")
        for phase in chain.get("sign_by_phase", {}):
            if phase not in PHASES:
                problems.append(f"{chain['id']} unknown phase {phase}")
        chain_hop_addresses[chain["id"]] = [f"hop:{chain['id'].split('chain:concept:')[1]}:{position:02d}"
                                            for position in range(1, len(chain["hops"]) + 1)]
    for assumption in ASSUMPTIONS:
        for field in ("statement", "test", "kill", "owner"):
            if not assumption.get(field):
                problems.append(f"{assumption['id']} missing {field}")
    if problems:
        raise SystemExit("conceptual seed invalid:\n  " + "\n  ".join(problems[:20]))

    # Link assumptions: every high load interaction becomes an assumption node of its own.
    link_assumptions = []
    for interaction in INTERACTIONS:
        if interaction["load"] < 4:
            continue
        identifier = f"assumption:link:{interaction['from'].split('force:')[1]}->{interaction['to'].split('force:')[1]}"
        link_assumptions.append({"id": identifier, "statement": interaction["assumption"],
                                 "test": f"Test the link {interaction['from']} to {interaction['to']} directly.",
                                 "kill": interaction["kill"], "owner": f"interaction:{interaction['from']}->{interaction['to']}",
                                 "blast_radius": interaction["channel"], "load": interaction["load"]})
    all_assumptions = ASSUMPTIONS + link_assumptions
    assumption_ids = {entry["id"] for entry in all_assumptions}

    out_degree = collections.Counter()
    in_degree = collections.Counter()
    for interaction in INTERACTIONS:
        out_degree[interaction["from"]] += 1
        in_degree[interaction["to"]] += 1
    force_rows = []
    for force in FORCES:
        force_rows.append({**force, "out_interactions": out_degree[force["id"]],
                           "in_interactions": in_degree[force["id"]],
                           "degree": out_degree[force["id"]] + in_degree[force["id"]]})
    interaction_rows = []
    for interaction in INTERACTIONS:
        interaction_rows.append({**interaction,
                                 "id": f"interaction:{interaction['from']}->{interaction['to']}:{interaction['relation']}",
                                 "load_assumption": (f"assumption:link:{interaction['from'].split('force:')[1]}"
                                                     f"->{interaction['to'].split('force:')[1]}"
                                                     if interaction["load"] >= 4 else None)})
    chain_rows = []
    for chain in CHAINS:
        addresses = chain_hop_addresses[chain["id"]]
        hops = []
        for position, hop in enumerate(chain["hops"]):
            hops.append({"hop": addresses[position], "force": hop, "position": position + 1,
                         "prev": addresses[position - 1] if position else None,
                         "next": addresses[position + 1] if position + 1 < len(addresses) else None})
        chain_rows.append({**chain, "hop_records": hops})

    (SCAN / "forces.jsonl").write_text("".join(json.dumps(row) + "\n" for row in force_rows))
    (SCAN / "interactions.jsonl").write_text("".join(json.dumps(row) + "\n" for row in interaction_rows))
    (SCAN / "assumptions.jsonl").write_text("".join(json.dumps(row) + "\n" for row in all_assumptions))
    (SCAN / "conceptual-chains.jsonl").write_text("".join(json.dumps(row) + "\n" for row in chain_rows))
    summary = {
        "forces": len(FORCES),
        "forces_by_domain": dict(collections.Counter(force["domain"] for force in FORCES).most_common()),
        "interactions": len(INTERACTIONS),
        "interactions_by_relation": dict(collections.Counter(i["relation"] for i in INTERACTIONS).most_common()),
        "interactions_by_evidence": dict(collections.Counter(i["evidence"] for i in INTERACTIONS).most_common()),
        "phase_conditional_interactions": sum(1 for i in INTERACTIONS if i["sign_by_phase"]),
        "mean_load": round(sum(i["load"] for i in INTERACTIONS) / len(INTERACTIONS), 2),
        "high_load_links": sum(1 for i in INTERACTIONS if i["load"] >= 4),
        "assumptions_total": len(all_assumptions),
        "assumptions_seeded": len(ASSUMPTIONS),
        "assumptions_from_links": len(link_assumptions),
        "chains": len(CHAINS),
        "chain_hops": sum(len(chain["hops"]) for chain in CHAINS),
        "isolated_forces": [force["id"] for force in FORCES
                            if out_degree[force["id"]] + in_degree[force["id"]] == 0],
        "note": "every interaction is an inference with a condition, an assumption and a kill",
    }
    (SCAN / "conceptual-summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(f"forces {summary['forces']} across {len(summary['forces_by_domain'])} domains, "
          f"interactions {summary['interactions']} ({summary['phase_conditional_interactions']} phase conditional)")
    print(f"assumptions {summary['assumptions_total']} ({summary['assumptions_from_links']} from high load links), "
          f"chains {summary['chains']} with {summary['chain_hops']} hops")
    print(f"relations: {summary['interactions_by_relation']}")
    if summary["isolated_forces"]:
        print(f"isolated forces (no interaction yet): {summary['isolated_forces']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
