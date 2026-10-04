#!/usr/bin/env python3
"""Build the connection index: every node carrying its own typed connections and chain hops.

Sources: the manifest (declared nodes and edges), the decomposition skeleton (parent, child, sibling
links), the curated digs (nodes and edges), and the bridges (cross-dig links). Inferred connections
follow the rules in docs/plan/deep-chaining.md and each one carries its rule name and falsifier.

Writes docs/scan/connection-index.jsonl.gz and docs/scan/connection-index-summary.json.

    python3 scripts/build_connection_index.py --manifest docs/scan/quantgraph.jsonl
    python3 scripts/build_connection_index.py --show mechanism:capacity:transformer-bottleneck
    python3 scripts/build_connection_index.py --chain dig:fcc:catalyst-minerals
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "docs" / "scan" / "connection-index.jsonl.gz"
SUMMARY = ROOT / "docs" / "scan" / "connection-index-summary.json"
DIGS = ROOT / "docs" / "scan" / "deep-digs.jsonl"
CONCEPT_FORCES = ROOT / "docs" / "scan" / "forces.jsonl"
CONCEPT_INTERACTIONS = ROOT / "docs" / "scan" / "interactions.jsonl"
CONCEPT_ASSUMPTIONS = ROOT / "docs" / "scan" / "assumptions.jsonl"
CONCEPT_CHAINS = ROOT / "docs" / "scan" / "conceptual-chains.jsonl"
BRIDGES = ROOT / "docs" / "scan" / "deep-bridges.jsonl"
SKELETON = ROOT / "docs" / "scan" / "decomposition.jsonl.gz"
MAX_INFERRED = 120
MAX_TOTAL = 150
TYPE_CAPS = {"ties_by_player": 25, "ties_by_observable": 25, "ties_by_source": 25,
             "shares_semantics": 40, "co_layer_peer": 28, "same_dig_context": 25}
STOP = {"the", "of", "and", "to", "a", "in", "for", "is", "that", "with", "on", "by", "as", "it",
        "its", "at", "from", "or", "an", "be", "are", "this", "these", "their", "into", "than"}
FAMILIES = ["usgs", "eia", "lme", "bls", "usitc", "doe", "nrc", "fastmarkets", "argus", "bnef",
            "icsg", "ferc", "epa", "sec", "entso", "iso", "trade press", "company filings",
            "company releases", "company disclosures", "futures", "imf", "world bank", "iea", "opec"]


def tokens(text: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", str(text).lower())
            if token and token not in STOP and len(token) > 2}


def families(text: str) -> set[str]:
    lowered = str(text).lower()
    return {family for family in FAMILIES if family in lowered}


def load_nodes_edges(manifest: str) -> tuple[dict[str, dict], list[dict]]:
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    for line in Path(manifest).open():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("kind") == "node":
            nodes[row["id"]] = {"id": row["id"], "layer": row.get("layer", "?"),
                                "meaning": row.get("meaning", ""), "origin": "manifest",
                                "sources": row.get("sources", [])}
        elif row.get("kind") == "edge":
            edges.append(row)
    for line in DIGS.open():
        if not line.strip():
            continue
        dig = json.loads(line)
        for node in dig.get("nodes", []):
            nodes[node["id"]] = {"id": node["id"], "layer": node.get("layer", "?"),
                                 "meaning": node.get("meaning", ""), "origin": "dig",
                                 "dig": dig["id"], "players": node.get("players", []),
                                 "observables": node.get("observables", []),
                                 "source": node.get("source", "")}
        for edge in dig.get("edges", []):
            edges.append({"kind": "edge", "from": edge["from"], "to": edge["to"],
                          "relation": edge.get("relation", "links"), "status": "curated",
                          "condition": edge.get("condition", ""), "falsifier": edge.get("falsifier", "")})
    # The conceptual layer: forces and assumptions become nodes with their own meaning and payer.
    if CONCEPT_FORCES.exists():
        for line in CONCEPT_FORCES.open():
            if not line.strip():
                continue
            force = json.loads(line)
            nodes[force["id"]] = {"id": force["id"], "layer": "force", "meaning": force.get("meaning", ""),
                                  "origin": "concept", "domain": force.get("domain", ""),
                                  "players": [], "observables": [force.get("observables", "")],
                                  "source": force.get("source", ""), "payer": force.get("payer", "")}
    if CONCEPT_ASSUMPTIONS.exists():
        for line in CONCEPT_ASSUMPTIONS.open():
            if not line.strip():
                continue
            assumption = json.loads(line)
            nodes[assumption["id"]] = {"id": assumption["id"], "layer": "assumption",
                                       "meaning": assumption.get("statement", ""), "origin": "concept",
                                       "observables": [assumption.get("test", "")],
                                       "source": assumption.get("owner", ""),
                                       "kill": assumption.get("kill", "")}
    return nodes, edges


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(ROOT / "docs" / "scan" / "quantgraph.jsonl"))
    parser.add_argument("--show")
    parser.add_argument("--chain")
    parser.add_argument("--out", default=str(INDEX))
    parser.add_argument("--summary", default=str(SUMMARY))
    args = parser.parse_args()

    nodes, edges = load_nodes_edges(args.manifest)
    bridges = [json.loads(line) for line in BRIDGES.open() if line.strip()]
    for bridge in bridges:
        edges.append({"kind": "edge", "from": bridge["from"], "to": bridge["to"],
                      "relation": bridge["relation"], "status": "curated",
                      "condition": bridge.get("condition", ""), "falsifier": bridge.get("falsifier", "")})

    # The decomposition skeleton: every subnode becomes a node in the index, so the whole written
    # graph carries its own connections.
    parent_of: dict[str, str] = {}
    children_of: dict[str, list[str]] = collections.defaultdict(list)
    if SKELETON.exists():
        with gzip.open(SKELETON, "rt") as handle:
            for line in handle:
                row = json.loads(line)
                if row.get("kind") != "subnode":
                    continue
                parent = row.get("parent", "")
                parent_of[row["id"]] = parent
                children_of[parent].append(row["id"])
                if row["id"] not in nodes:
                    nodes[row["id"]] = {"id": row["id"], "layer": row.get("layer", "?"),
                                        "meaning": row.get("meaning", ""), "origin": "skeleton",
                                        "status": row.get("status", "proposed_unverified")}

    connections: dict[str, list[dict]] = collections.defaultdict(list)

    def connect(source: str, target: str, ctype: str, status: str, why: str,
                condition: str = "", falsifier: str = "", **extra) -> None:
        if source == target or source not in nodes or target not in nodes:
            return
        payload = {"to": target, "type": ctype, "status": status, "why": why,
                   "condition": condition, "falsifier": falsifier}
        payload.update({key: value for key, value in extra.items() if value not in ("", None, {})})
        connections[source].append(payload)

    # Declared and curated edges, both directions.
    for edge in edges:
        status = edge.get("status", "declared")
        connect(edge["from"], edge["to"], edge["relation"], status, "declared or curated edge",
                edge.get("condition", ""), edge.get("falsifier", ""))
        connect(edge["to"], edge["from"], edge["relation"], status, "declared or curated edge reverse",
                edge.get("condition", ""), edge.get("falsifier", ""))

    # The conceptual layer: every interaction is an inference carrying its channel, condition,
    # assumption, kill, load, lag and phase signs. Assumptions attach to whatever they bound.
    if CONCEPT_INTERACTIONS.exists():
        for line in CONCEPT_INTERACTIONS.open():
            if not line.strip():
                continue
            interaction = json.loads(line)
            payload = {"assumption": interaction.get("assumption", ""), "load": interaction.get("load", 0),
                       "lag": interaction.get("lag", ""), "sign_by_phase": interaction.get("sign_by_phase", {}),
                       "evidence": interaction.get("evidence", "E4")}
            connect(interaction["from"], interaction["to"], interaction["relation"], "inferred",
                    interaction.get("channel", ""), interaction.get("condition", ""),
                    interaction.get("kill", ""), **payload)
            connect(interaction["to"], interaction["from"], interaction["relation"], "inferred",
                    interaction.get("channel", ""), interaction.get("condition", ""),
                    interaction.get("kill", ""), **payload)
    if CONCEPT_ASSUMPTIONS.exists():
        for line in CONCEPT_ASSUMPTIONS.open():
            if not line.strip():
                continue
            assumption = json.loads(line)
            owner = assumption.get("owner", "")
            endpoints = []
            if owner.startswith("interaction:"):
                body = owner.split("interaction:", 1)[1]
                source, rest = body.split("->", 1)
                target = rest.rsplit(":", 1)[0]
                endpoints = [(source, "left"), (target, "right")]
            elif owner in nodes:
                endpoints = [(owner, "owner")]
            for endpoint, side in endpoints:
                connect(endpoint, assumption["id"], "bounded_by", "declared",
                        f"assumption on the {side} side", assumption.get("statement", ""),
                        assumption.get("kill", ""), load=assumption.get("load", 0))
                connect(assumption["id"], endpoint, "bounds", "declared",
                        f"bounds the {side} side", assumption.get("statement", ""),
                        assumption.get("kill", ""), load=assumption.get("load", 0))

    # Structural: parent, children, siblings.
    for node_id in nodes:
        parent = parent_of.get(node_id)
        if parent and parent in nodes:
            connect(node_id, parent, "part_of", "declared", "structural parent",
                    "The node decomposes from its parent.",
                    "The parent decomposition is wrong for this node.")
        for child in children_of.get(node_id, []):
            connect(node_id, child, "splits_into", "declared", "structural child",
                    "The child is a decomposition dimension of this node.",
                    "The decomposition dimension does not apply to this node.")
            for grandchild in children_of.get(child, []):
                connect(node_id, grandchild, "refines", "declared",
                        "grandchild refinement of this node",
                        "The refinement chain from this node is valid.",
                        "The grandchild refinement does not apply to this node.")
                connect(grandchild, node_id, "refined_by", "declared",
                        "grandparent that this node refines",
                        "The refinement chain to this ancestor is valid.",
                        "The refinement chain does not apply.")
        if parent:
            for sibling in children_of.get(parent, []):
                connect(node_id, sibling, "sibling_subnode", "declared", "shared parent",
                        "Shared parent means shared decomposition context.",
                        "The parent decomposition is wrong for one of the two.")

    # Inferred rules.
    player_index: dict[str, list[str]] = collections.defaultdict(list)
    layer_index: dict[str, list[str]] = collections.defaultdict(list)
    dig_index: dict[str, list[str]] = collections.defaultdict(list)
    family_index: dict[str, list[str]] = collections.defaultdict(list)
    source_index: dict[str, list[str]] = collections.defaultdict(list)
    token_index: dict[str, set[str]] = collections.defaultdict(set)
    for node_id, node in nodes.items():
        if node.get("origin") not in ("manifest", "dig"):
            continue
        for player in node.get("players", []):
            player_index[player].append(node_id)
        for family in families(" ".join(node.get("observables", [])) + " " + node.get("source", "")):
            family_index[family].append(node_id)
        for source in ([node.get("source", "")] if node.get("source") else []) + list(node.get("sources", [])):
            if re.match(r"^(source|dataset|evidence|series|contract|raw|feature):", str(source)):
                source_index[source].append(node_id)
        for token in tokens(node.get("meaning", "")):
            token_index[token].add(node_id)
        layer_index[node.get("layer", "?")].append(node_id)
        if node.get("dig"):
            dig_index[node["dig"]].append(node_id)

    for node_id, node in nodes.items():
        if node.get("origin") not in ("manifest", "dig"):
            continue
        candidates: dict[str, tuple[int, dict]] = {}
        for player in node.get("players", []):
            for partner in player_index.get(player, []):
                if partner != node_id:
                    candidates[partner] = (3, {"type": "ties_by_player", "status": "inferred",
                                               "why": f"same player: {player}",
                                               "condition": "The shared player is material to both nodes.",
                                               "falsifier": "The player is immaterial to one side."})
        node_families = families(" ".join(node.get("observables", [])) + " " + node.get("source", ""))
        for family in node_families:
            for partner in family_index.get(family, []):
                if partner != node_id and partner not in candidates:
                    candidates[partner] = (2, {"type": "ties_by_observable", "status": "inferred",
                                               "why": f"same observable family: {family}",
                                               "condition": "Both reads come from the same source family.",
                                               "falsifier": "The two reads are different products of one publisher."})
        for source in ([node.get("source", "")] if node.get("source") else []) + list(node.get("sources", [])):
            if not re.match(r"^(source|dataset|evidence|series|contract|raw|feature):", str(source)):
                continue
            for partner in source_index.get(source, []):
                if partner != node_id and partner not in candidates:
                    candidates[partner] = (2, {"type": "ties_by_source", "status": "inferred",
                                               "why": f"same source: {source}",
                                               "condition": "Both nodes read the same source.",
                                               "falsifier": "The source is used for unrelated questions."})
        node_tokens = tokens(node.get("meaning", ""))
        if node_tokens:
            overlap: dict[str, int] = collections.Counter()
            for token in node_tokens:
                for partner in token_index.get(token, []):
                    if partner != node_id:
                        overlap[partner] += 1
            for partner, shared in overlap.items():
                if partner in candidates:
                    continue
                partner_tokens = tokens(nodes[partner].get("meaning", ""))
                union = node_tokens | partner_tokens
                jaccard = shared / len(union) if union else 0
                if shared >= 2 and jaccard >= 0.2 and nodes[partner].get("layer") != node.get("layer"):
                    candidates[partner] = (1, {"type": "shares_semantics", "status": "inferred",
                                               "why": f"{shared} shared meaning tokens across layers",
                                               "condition": "The wording reflects a real shared mechanism.",
                                               "falsifier": "The overlap is generic vocabulary and the nodes move separately."})
            dig_id = node.get("dig")
            if dig_id:
                for partner in dig_index.get(dig_id, []):
                    if partner != node_id and partner not in candidates:
                        candidates[partner] = (2, {"type": "same_dig_context", "status": "inferred",
                                                   "why": f"same curated dig: {dig_id}",
                                                   "condition": "Nodes in one dig form a single chain.",
                                                   "falsifier": "Dig membership does not imply interaction."})
            for partner in layer_index.get(node.get("layer", "?"), []):
                if partner != node_id and partner not in candidates:
                    candidates[partner] = (0, {"type": "co_layer_peer", "status": "inferred",
                                               "why": "same layer peer family",
                                               "condition": "Same layer means comparable role in the stack.",
                                               "falsifier": "The layer label does not imply a comparable role."})
        ranked = sorted(candidates.items(), key=lambda item: (-item[1][0], item[0]))
        used: collections.Counter = collections.Counter()
        for partner, (_, payload) in ranked:
            if used[payload["type"]] >= TYPE_CAPS.get(payload["type"], MAX_INFERRED):
                continue
            if sum(used.values()) >= MAX_INFERRED:
                break
            used[payload["type"]] += 1
            connect(node_id, partner, payload["type"], payload["status"], payload["why"],
                    payload["condition"], payload["falsifier"])

    # Chains: dig chains and bridge chains become hops, registered on both endpoints.
    chains: dict[str, list[dict]] = {}
    hops_total = 0
    for line in DIGS.open():
        if not line.strip():
            continue
        dig = json.loads(line)
        chain = dig.get("chain", [])
        hop_list = []
        edge_lookup = {(edge["from"], edge["to"]): edge for edge in dig.get("edges", [])}
        for index, (start, end) in enumerate(zip(chain, chain[1:]), start=1):
            edge = edge_lookup.get((start, end), {})
            hop = {"hop": f"hop:{dig['id']}:{index:02d}", "from": start, "to": end,
                   "relation": edge.get("relation", "chain_precedes"),
                   "condition": edge.get("condition", ""), "falsifier": edge.get("falsifier", "")}
            hop_list.append(hop)
            hops_total += 1
        chains[dig["id"]] = hop_list
    if CONCEPT_CHAINS.exists():
        for line in CONCEPT_CHAINS.open():
            if not line.strip():
                continue
            chain_row = json.loads(line)
            hop_list = []
            for index, (start, end) in enumerate(zip(chain_row["hops"], chain_row["hops"][1:]), start=1):
                hop_list.append({"hop": f"hop:{chain_row['id']}:{index:02d}", "from": start, "to": end,
                                 "relation": "chain_precedes", "condition": chain_row.get("intuition", ""),
                                 "falsifier": chain_row.get("greatest_assumption", "")})
                hops_total += 1
            chains[chain_row["id"]] = hop_list
    for bridge in bridges:
        hop = {"hop": f"hop:{bridge['id']}:01", "from": bridge["from"], "to": bridge["to"],
               "relation": bridge["relation"], "condition": bridge.get("condition", ""),
               "falsifier": bridge.get("falsifier", "")}
        chains[f"chain:{bridge['id']}"] = [hop]
        hops_total += 1

    chain_membership: dict[str, list[dict]] = collections.defaultdict(list)
    for chain_id, hops in chains.items():
        for position, hop in enumerate(hops, start=1):
            prev_hop = hops[position - 2]["hop"] if position > 1 else None
            next_hop = hops[position]["hop"] if position < len(hops) else None
            for endpoint, direction in ((hop["from"], "precedes"), (hop["to"], "follows")):
                if endpoint in nodes:
                    chain_membership[endpoint].append({
                        "chain": chain_id, "hop": hop["hop"], "position": position,
                        "direction": direction, "prev": prev_hop, "next": next_hop,
                        "relation": hop["relation"]})
            if hop["from"] in nodes and hop["to"] in nodes:
                connect(hop["from"], hop["to"], "chain_follows", "curated",
                        f"next hop in {chain_id}", hop.get("condition", ""), hop.get("falsifier", ""))
                connect(hop["to"], hop["from"], "chain_precedes", "curated",
                        f"previous hop in {chain_id}", hop.get("condition", ""), hop.get("falsifier", ""))

    # Unification: every force is tied to the measured nodes it bears on, by domain vocabulary overlap.
    measured = [(node_id, node) for node_id, node in nodes.items()
                if node.get("origin") in ("manifest", "dig")]
    measured_signatures = [(node_id, tokens(node.get("meaning", "") + " " + node_id)) for node_id, node in measured]
    for force_id, force in nodes.items():
        if not force_id.startswith("force:"):
            continue
        force_signature = tokens(" ".join([force.get("meaning", ""), force_id,
                                           " ".join(force.get("observables", []))]))
        scored = []
        for node_id, signature in measured_signatures:
            shared = force_signature & signature
            union = force_signature | signature
            if len(shared) >= 2 and union and len(shared) / len(union) >= 0.08:
                scored.append((len(shared), node_id))
        scored.sort(reverse=True)
        for score, node_id in scored[:6]:
            connect(force_id, node_id, "bears_on", "inferred",
                    f"shared vocabulary with the measured layer ({score} tokens)",
                    "The force bears on this measured node rather than on the domain in general.",
                    "The overlap is generic vocabulary and the force does not touch this node.")
            connect(node_id, force_id, "bears_on", "inferred",
                    f"the force {force_id.split('force:')[1]} bears on this node",
                    "The measured node reads the force rather than an unrelated one.",
                    "The overlap is generic vocabulary and the force does not touch this node.")

    # Attach assumption nodes that would otherwise float, by token overlap against the non-assumption graph.
    for assumption_id, assumption in nodes.items():
        if assumption.get("layer") != "assumption":
            continue
        attached = [connection for connection in connections.get(assumption_id, [])
                    if nodes.get(connection["to"], {}).get("layer") != "assumption"
                    and not connection["to"].startswith("sub:")]
        if attached:
            continue
        assumption_tokens = tokens(assumption.get("meaning", "") + " " + assumption_id)
        best, best_score = None, 0
        for candidate_id, candidate in nodes.items():
            if candidate.get("layer") == "assumption" or candidate_id.startswith("sub:"):
                continue
            score = len(assumption_tokens & tokens(candidate.get("meaning", "") + " " + candidate_id))
            if score > best_score:
                best, best_score = candidate_id, score
        if best is None:
            candidates = [(candidate_id, candidate) for candidate_id, candidate in nodes.items()
                          if candidate.get("layer") != "assumption" and not candidate_id.startswith("sub:")]
            if candidates:
                best = max(candidates, key=lambda item: item[1].get("degree", 0))[0]
                connect(assumption_id, best, "bounds", "inferred",
                        "assumption attached to the graph hub: no single mechanism owns it",
                        "The assumption concerns the research process rather than one mechanism.",
                        "The assumption turns out to concern exactly one mechanism.")
                continue
        if best:
            connect(assumption_id, best, "bounds", "inferred",
                    "assumption attached to the mechanism by token overlap",
                    "The assumption bears on this mechanism rather than on an unrelated one.",
                    "The token overlap is generic vocabulary and the mechanism is unrelated.")

    records = []
    for node_id, node in nodes.items():
        seen_pairs: set[tuple[str, str]] = set()
        deduped = []
        for connection in connections.get(node_id, []):
            key = (connection["to"], connection["type"])
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            deduped.append(connection)
        node_connections = deduped[:MAX_TOTAL]
        by_type = collections.Counter(conn["type"] for conn in node_connections)
        by_status = collections.Counter(conn["status"] for conn in node_connections)
        records.append({"id": node_id, "layer": node["layer"], "meaning": node["meaning"],
                        "origin": node.get("origin", ""), "degree": len(node_connections),
                        "by_status": dict(by_status), "by_type": dict(by_type.most_common()),
                        "connections": node_connections,
                        "chains": chain_membership.get(node_id, [])})
    records.sort(key=lambda record: record["id"])
    records_by_id = {record["id"]: record for record in records}

    if args.show:
        record = records_by_id.get(args.show)
        if not record:
            raise SystemExit(f"node not found: {args.show}")
        print(json.dumps(record, indent=1))
        return 0
    if args.chain:
        hops = chains.get(args.chain) or chains.get(f"chain:{args.chain}")
        if not hops:
            raise SystemExit(f"chain not found: {args.chain}")
        for hop in hops:
            print(hop["hop"], hop["from"], "->", hop["to"], f"[{hop['relation']}]")
        return 0

    with gzip.open(args.out, "wt") as handle:
        for record in records:
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")

    degrees = [record["degree"] for record in records]
    core = [record for record in records if record["origin"] in ("manifest", "dig")]
    core_degrees = [record["degree"] for record in core] or [0]
    status_counts = collections.Counter(status for record in records for status in record["by_status"]
                                        for _ in range(record["by_status"][status]))
    type_counts = collections.Counter(conn_type for record in records for conn_type in record["by_type"]
                                      for _ in range(record["by_type"][conn_type]))
    summary = {
        "nodes": len(records),
        "connections": sum(degrees),
        "by_status": dict(status_counts.most_common()),
        "by_type": dict(type_counts.most_common(25)),
        "degrees": {"min": min(degrees), "median": statistics.median(degrees), "max": max(degrees),
                    "mean": round(statistics.mean(degrees), 1)},
        "nodes_with_50_plus": sum(1 for degree in degrees if degree >= 50),
        "nodes_with_50_plus_share": round(sum(1 for degree in degrees if degree >= 50) / len(degrees), 4),
        "core_nodes": len(core),
        "core_degrees": {"min": min(core_degrees), "median": statistics.median(core_degrees),
                         "max": max(core_degrees)},
        "core_with_50_plus": sum(1 for degree in core_degrees if degree >= 50),
        "core_with_50_plus_share": round(sum(1 for degree in core_degrees if degree >= 50)
                                         / max(1, len(core_degrees)), 4),
        "skeleton_nodes": sum(1 for record in records if record["origin"] == "skeleton"),
        "under_connected_core": sorted(
            ({"id": record["id"], "degree": record["degree"]} for record in core
             if record["degree"] < 50), key=lambda row: row["degree"])[:60],
        "chains": len(chains),
        "hops": hops_total,
        "bridges": len(bridges),
        "digs": len([line for line in DIGS.open() if line.strip()]),
        "note": "inferred connections are questions with a type and a falsifier, never facts",
    }
    Path(args.summary).write_text(json.dumps(summary, indent=1) + "\n")
    print(f"wrote {args.out} and {args.summary}")
    print(f"nodes {len(records)}; connections {sum(degrees)}; median degree {statistics.median(degrees):.0f}; "
          f"nodes with 50+ connections {summary['nodes_with_50_plus']} "
          f"({summary['nodes_with_50_plus_share']:.1%}); chains {len(chains)}; hops {hops_total}")
    print(f"core nodes {len(core)}: median degree {summary['core_degrees']['median']:.0f}; "
          f"50+ {summary['core_with_50_plus']} ({summary['core_with_50_plus_share']:.1%})")
    print("top types:", dict(type_counts.most_common(8)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
