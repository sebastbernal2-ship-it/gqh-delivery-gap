#!/usr/bin/env python3
"""Deepen the graph: quantitative distributions, hidden objects, propagation paths, delineation.

The classification throughout is decomposed or not yet decomposed. Nothing here grades a node as dead.
Writes docs/scan/distributions.jsonl, docs/scan/hidden-objects.jsonl, docs/scan/propagation.jsonl,
docs/scan/graph-delineation.json and results/graph-propagation-summary.json.

    python3 scripts/build_graph_propagation.py
"""
from __future__ import annotations

import collections
import csv
import gzip
import json
import math
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN = ROOT / "docs" / "scan"
RESULTS = ROOT / "results"
INDEX = SCAN / "connection-index.jsonl.gz"
DIGS = SCAN / "deep-digs.jsonl"
BRIDGES = SCAN / "deep-bridges.jsonl"
CHAINS = SCAN / "connection-chains.jsonl"
MEASUREMENTS = SCAN / "node-measurements.jsonl"
QUEUE = RESULTS / "queue-panel.csv"
COMPUTE = RESULTS / "compute-price-monthly.csv"
CAPEX = RESULTS / "provider-capex-quarterly.csv"
OUT_DIST = SCAN / "distributions.jsonl"
OUT_HIDDEN = SCAN / "hidden-objects.jsonl"
OUT_PROP = SCAN / "propagation.jsonl"
OUT_DELIN = SCAN / "graph-delineation.json"
OUT_SUMMARY = RESULTS / "graph-propagation-summary.json"

PROP_TYPES = {"drives", "feeds", "conditions", "requires", "exposes", "supports", "gates", "anchors",
              "refines", "ties_by_observable", "ties_by_source", "chain_precedes", "chain_follows",
              "belongs_to", "candidate_for", "shares_semantics"}
FUNDAMENTAL = ["constraint", "price", "margin", "capex", "cash_flow", "equity"]
CASCADE = ["disclosure", "flow", "depth", "dislocation", "reversion"]
DOMAIN_TOKENS = {
    "constraint": ["capacity", "constraint", "bottleneck", "scarcity", "queue", "gate", "lead", "congestion", "interconnect"],
    "price": ["price", "rental", "rate", "tariff", "spot", "cost", "pricing"],
    "margin": ["margin", "spread", "profitability"],
    "capex": ["capex", "order", "backlog", "spending", "plan"],
    "cash_flow": ["cash", "revenue", "revision", "earnings", "ebitda", "cash-flow"],
    "equity": ["equity", "basket", "multiple", "valuation", "agent", "share"],
    "disclosure": ["disclosure", "8k", "8-k", "filing", "sec", "event-stamp", "prompt", "material"],
    "flow": ["flow", "forced", "deleveraging", "liquidation", "funding", "hedge", "hedging"],
    "depth": ["depth", "liquidity", "book"],
    "dislocation": ["dislocation", "drift", "reversal", "gap", "stress", "shock"],
    "reversion": ["reversion", "revert", "mean-reversion", "recovery"],
    "policy": ["policy", "subsidy", "mandate", "rate-case", "rate-base"],
}
DATA_INVENTORY = {
    "results/queue-panel.csv": ["queue", "interconnect", "withdraw"],
    "results/compute-price-monthly.csv": ["compute", "rental"],
    "results/provider-capex-quarterly.csv": ["provider", "capex"],
    "results/delivery-revisions.csv": ["revision", "delivery", "promise"],
    "results/cascade-tape.json": ["cascade", "flow", "dislocation", "depth"],
    "results/capacity-strategy.csv": ["capacity", "strategy", "constraint"],
    "results/bottleneck-factors.csv": ["bottleneck", "factor"],
    "results/capacity-event-ledger.csv": ["event", "ledger", "8k", "disclosure"],
    "results/exposure-panel.csv": ["exposure"],
    "results/credit-deal-registry.csv": ["credit", "deal"],
    "results/agency-universe.csv": ["agency"],
    "results/dscr-thresholds.csv": ["dscr", "threshold"],
    "results/implied-vol-test.json": ["implied", "vol", "smile", "option"],
    "results/delivery-model-coefficients.csv": ["delivery", "model", "coefficient"],
}
STOPWORDS = {"the", "a", "an", "of", "and", "to", "for", "with", "in", "on", "per", "by", "as", "at",
             "or", "sub", "dig", "chain", "node", "factor", "layer", "state", "new", "all", "its"}


def tokens(text: str) -> list[str]:
    return [token for token in re.split(r"[-_:/ .]+", text.lower())
            if token and token not in STOPWORDS and len(token) > 2]


def quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return float("nan")
    position = q * (len(sorted_values) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return sorted_values[low]
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (position - low)


def shape(values: list[float]) -> dict:
    """Centre, spread, shape and tails of one sample."""
    clean = [value for value in values if value is not None and math.isfinite(value)]
    if not clean:
        return {"n": 0, "status": "to_be_sampled"}
    ordered = sorted(clean)
    n = len(clean)
    mean = sum(clean) / n
    variance = sum((value - mean) ** 2 for value in clean) / n if n > 1 else 0.0
    sd = math.sqrt(variance)
    if sd > 0 and n > 2:
        skew = sum(((value - mean) / sd) ** 3 for value in clean) / n
        kurtosis = sum(((value - mean) / sd) ** 4 for value in clean) / n - 3
    else:
        skew = kurtosis = 0.0
    median = quantile(ordered, 0.5)
    p90 = quantile(ordered, 0.9)
    total = sum(abs(value) for value in clean)
    top_count = max(1, int(0.01 * n))
    top_share = sum(abs(value) for value in ordered[-top_count:]) / total if total else 0.0
    return {"n": n, "mean": round(mean, 4), "sd": round(sd, 4), "median": round(median, 4),
            "p10": round(quantile(ordered, 0.1), 4), "p90": round(p90, 4), "p99": round(quantile(ordered, 0.99), 4),
            "max": round(ordered[-1], 4), "tail_ratio_p90_median": round(p90 / median, 3) if median else None,
            "skew": round(skew, 3), "excess_kurtosis": round(kurtosis, 3), "top1pct_share": round(top_share, 3)}


def autocorr(values: list[float]) -> float:
    if len(values) < 3:
        return float("nan")
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values)
    if variance == 0:
        return float("nan")
    return sum((values[i] - mean) * (values[i + 1] - mean) for i in range(len(values) - 1)) / variance


def domain_tags(identifier: str, meaning: str = "") -> set[str]:
    text = (identifier + " " + meaning).lower()
    tags = set()
    for domain, needles in DOMAIN_TOKENS.items():
        if any(needle in text for needle in needles):
            tags.add(domain)
    return tags


def main() -> int:
    # ---------- load ----------
    nodes = {}
    with gzip.open(INDEX, "rt") as handle:
        for line in handle:
            record = json.loads(line)
            nodes[record["id"]] = record
    digs = [json.loads(line) for line in DIGS.open() if line.strip()]
    bridges = [json.loads(line) for line in BRIDGES.open() if line.strip()]
    chains = [json.loads(line) for line in CHAINS.open() if line.strip()]
    measurements = [json.loads(line) for line in MEASUREMENTS.open() if line.strip()]

    # ---------- delineation ----------
    by_layer = collections.Counter(record["layer"] for record in nodes.values())
    by_status = collections.Counter()
    by_type = collections.Counter()
    degree_histogram = collections.Counter()
    with_condition = with_falsifier = 0
    total_connections = 0
    reference_pairs = set()
    for record in nodes.values():
        for conn in record["connections"]:
            total_connections += 1
            by_status[conn.get("status", "unknown")] += 1
            by_type[conn.get("type", "unknown")] += 1
            if conn.get("condition"):
                with_condition += 1
            if conn.get("falsifier"):
                with_falsifier += 1
            pair = "\u241f".join(sorted([record["id"], conn["to"]]))
            reference_pairs.add(pair)
        bucket = min(record["degree"] // 10 * 10, 150)
        degree_histogram[bucket] += 1

    parent = {identifier: identifier for identifier in nodes}

    def find(identifier: str) -> str:
        while parent[identifier] != identifier:
            parent[identifier] = parent[parent[identifier]]
            identifier = parent[identifier]
        return identifier

    def union(a: str, b: str) -> None:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_a] = root_b

    for record in nodes.values():
        for conn in record["connections"]:
            if conn["to"] in nodes:
                union(record["id"], conn["to"])
    components = collections.Counter(find(identifier) for identifier in nodes)
    biggest = components.most_common(1)[0] if components else (None, 0)
    anchor_ids = [identifier for identifier in nodes
                  if identifier.startswith(("mechanism:", "truth:", "asset:", "factor:", "entity:"))]
    reachable = set()
    adjacency = collections.defaultdict(set)
    for record in nodes.values():
        for conn in record["connections"]:
            if conn["to"] in nodes:
                adjacency[record["id"]].add(conn["to"])
                adjacency[conn["to"]].add(record["id"])
    stack = list(anchor_ids)
    while stack:
        current = stack.pop()
        if current in reachable:
            continue
        reachable.add(current)
        stack.extend(adjacency[current] - reachable)
    delineation = {
        "nodes": len(nodes), "connections": total_connections,
        "by_layer": dict(by_layer.most_common()), "by_status": dict(by_status.most_common()),
        "by_type": dict(by_type.most_common(30)),
        "degree_histogram": {str(key): value for key, value in sorted(degree_histogram.items())},
        "coverage": {"connections_with_condition_pct": round(100 * with_condition / total_connections, 2),
                     "connections_with_falsifier_pct": round(100 * with_falsifier / total_connections, 2)},
        "components": {"count": len(components), "largest": biggest[1],
                       "nodes_in_components_of_3_or_less": sum(value for value in components.values() if value <= 3)},
        "anchors": len(anchor_ids), "reachable_from_anchors": len(reachable),
        "unreachable_from_anchors": len(nodes) - len(reachable),
    }

    # ---------- distributions ----------
    distributions = []
    queue_rows = list(csv.DictReader(QUEUE.open()))
    for key in ("type_clean", "state"):
        groups = collections.defaultdict(list)
        for row in queue_rows:
            groups[row[key]].append(row)
        minimum = 50 if key == "state" else 200
        for name, group in sorted(groups.items()):
            if len(group) < minimum:
                continue
            mw_values = []
            days_ia, days_wd = [], []
            withdrawn = 0
            for row in group:
                try:
                    mw_values.append(max(0.0, float(row["mw1"] or 0)))
                except ValueError:
                    pass
                for field, sink in (("days_ir_to_ia", days_ia), ("days_ir_to_wd", days_wd)):
                    try:
                        sink.append(float(row[field]))
                    except (ValueError, KeyError):
                        pass
                withdrawn += 1 if row["q_status"] == "withdrawn" else 0
            stats = shape(mw_values)
            stats["withdrawal_share"] = round(withdrawn / len(group), 4)
            distributions.append({"node": f"queue:{key}:{name}", "dataset": "results/queue-panel.csv",
                                  "sample": f"{key}={name}", "stats": stats,
                                  "days_ir_to_ia": shape(days_ia), "days_ir_to_wd": shape(days_wd),
                                  "note": "distribution of this sample, not a verdict"})
    families = collections.defaultdict(list)
    for row in csv.DictReader(COMPUTE.open()):
        families[row["family"]].append(float(row["median_usd_per_instance_hour"]))
    for family, prices in sorted(families.items()):
        logs = [math.log(price) for price in prices if price > 0]
        returns = [logs[i + 1] - logs[i] for i in range(len(logs) - 1)]
        stats = shape(prices)
        stats["monthly_log_return_sd_annualised"] = round(statistics.pstdev(returns) * math.sqrt(12), 4) if len(returns) > 2 else None
        stats["log_return_autocorr1"] = round(autocorr(returns), 3) if len(returns) > 2 else None
        distributions.append({"node": f"compute:family:{family}", "dataset": "results/compute-price-monthly.csv",
                              "sample": family, "stats": stats, "note": "distribution of this sample, not a verdict"})
    tickers = collections.defaultdict(list)
    for row in csv.DictReader(CAPEX.open()):
        try:
            tickers[row["ticker"]].append((row["period_end"], float(row["value_usd"])))
        except ValueError:
            pass
    for ticker, rows in sorted(tickers.items()):
        rows.sort()
        values = [value for _, value in rows]
        growth = [(values[i + 1] - values[i]) / abs(values[i]) for i in range(len(values) - 1) if values[i]]
        stats = shape(values)
        stats["yoy_growth_mean"] = round(statistics.mean(growth), 4) if growth else None
        stats["yoy_growth_sd"] = round(statistics.pstdev(growth), 4) if len(growth) > 1 else None
        stats["quarters"] = len(rows)
        distributions.append({"node": f"provider:{ticker}:capex", "dataset": "results/provider-capex-quarterly.csv",
                              "sample": ticker, "stats": stats, "note": "distribution of this sample, not a verdict"})
    OUT_DIST.write_text("".join(json.dumps(entry) + "\n" for entry in distributions))

    # ---------- hidden objects ----------
    hidden = []
    referenced = set()
    for record in nodes.values():
        for conn in record["connections"]:
            referenced.add(conn["to"])
    for dig in digs:
        for node in dig["nodes"]:
            referenced.add(node["id"])
    for bridge in bridges:
        referenced.add(bridge["from"])
        referenced.add(bridge["to"])
    for chain in chains:
        referenced.add(chain["anchor_node"])
        referenced.add(chain["outcome_node"])
    for identifier in sorted(referenced - set(nodes)):
        hidden.append({"kind": "hidden_node", "id": identifier, "reason": "referenced but no node record",
                       "action": "add the node record with meaning, observables and payer"})

    child_groups = collections.defaultdict(list)
    for identifier in nodes:
        if identifier.startswith("sub:") and identifier.count(":") >= 2:
            head, child = identifier.rsplit(":", 1)
            child_groups[head].append((identifier, child))
    proposals = 0
    for head, children in child_groups.items():
        if len(children) < 2:
            continue
        for left in range(len(children)):
            for right in range(left + 1, len(children)):
                if proposals >= 800:
                    break
                id_a, name_a = children[left]
                id_b, name_b = children[right]
                if "\u241f".join(sorted([id_a, id_b])) in reference_pairs:
                    continue
                shared = set(tokens(name_a)) & set(tokens(name_b))
                if len(shared) >= 2:
                    hidden.append({"kind": "hidden_edge", "from": id_a, "to": id_b,
                                   "reason": f"shared tokens {sorted(shared)} under {head} with no direct connection",
                                   "condition": "The two sub-nodes move with the same observable",
                                   "falsifier": "The shared tokens are naming coincidence and the observables differ",
                                   "action": "add the edge with its type once the observable is checked"})
                    proposals += 1

    chain_hops = collections.defaultdict(dict)
    for record in nodes.values():
        for member in record.get("chains", []):
            chain_hops[member["chain"]][member["position"]] = member
    for chain_id, positions in sorted(chain_hops.items()):
        ordered = sorted(positions)
        for position in range(min(ordered), max(ordered) + 1):
            if position not in positions:
                hidden.append({"kind": "hidden_gap", "id": f"hop:{chain_id.split(':', 1)[1]}:{position:02d}",
                               "reason": f"chain {chain_id} is missing hop {position:02d}",
                               "action": "write the missing hop or shorten the chain"})
    for dig in digs:
        for node in dig["nodes"]:
            if not node.get("payer"):
                hidden.append({"kind": "hidden_gap", "id": node["id"],
                               "reason": f"node in dig {dig['id']} has no payer",
                               "action": "write the payer or declare it absent"})
            if not node.get("evidence"):
                hidden.append({"kind": "hidden_assumption", "id": node["id"],
                               "reason": "node carries no evidence tier",
                               "action": "assign an evidence tier from E1 to E4"})
    missing_condition = missing_falsifier = 0
    for record in nodes.values():
        for conn in record["connections"]:
            if conn.get("status") == "inferred":
                if not conn.get("condition"):
                    missing_condition += 1
                if not conn.get("falsifier"):
                    missing_falsifier += 1
    for chain in chains:
        for position, link in enumerate(chain["links"], start=1):
            if link.get("load") == "high" and link.get("evidence") in ("E3", "E4"):
                hidden.append({"kind": "hidden_assumption", "id": f"{chain['id']}:{position:02d}",
                               "reason": "high-load link resting on weak evidence",
                               "detail": link.get("assumption", ""), "kill": link.get("kill", ""),
                               "action": "test this link first, it decides the chain"})
    # Cross-dig hidden edges: nodes from different digs that share tokens and observables but no edge.
    dig_node_ids = []
    for dig in digs:
        for node in dig["nodes"]:
            dig_node_ids.append((dig["id"], node))
    cross_pairs = 0
    for left in range(len(dig_node_ids)):
        if cross_pairs >= 400:
            break
        for right in range(left + 1, len(dig_node_ids)):
            if cross_pairs >= 400:
                break
            dig_left, node_left = dig_node_ids[left]
            dig_right, node_right = dig_node_ids[right]
            if dig_left == dig_right:
                continue
            id_left, id_right = node_left["id"], node_right["id"]
            if "\u241f".join(sorted([id_left, id_right])) in reference_pairs:
                continue
            shared_name = set(tokens(id_left)) & set(tokens(id_right))
            shared_obs = set(tokens(" ".join(node_left.get("observables", [])))) & set(
                tokens(" ".join(node_right.get("observables", []))))
            if shared_name and shared_obs:
                hidden.append({"kind": "hidden_edge", "from": id_left, "to": id_right,
                               "reason": f"cross-dig pair sharing {sorted(shared_name)} and observable tokens {sorted(shared_obs)}",
                               "condition": "The two nodes respond to the same observable",
                               "falsifier": "The shared observable does not transmit between the two nodes",
                               "action": "add the typed edge or record why the shared observable stops here"})
                cross_pairs += 1

    # Bridge endpoints must be connected to each other in the index.
    for bridge in bridges:
        pair = "\u241f".join(sorted([bridge["from"], bridge["to"]]))
        if bridge["from"] in nodes and bridge["to"] in nodes and pair not in reference_pairs:
            hidden.append({"kind": "hidden_gap", "id": bridge["id"],
                           "reason": "bridge endpoints carry no direct connection in the index",
                           "action": "connect the bridge endpoints or split the bridge"})

    # Chains with no data path in hand, and digs outside every chain.
    for chain in chains:
        chain_tokens = set(tokens(chain["anchor_node"])) | set(tokens(chain["outcome_node"]))
        if not any(chain_tokens & set(needles) for needles in DATA_INVENTORY.values()):
            hidden.append({"kind": "hidden_gap", "id": chain["id"],
                           "reason": "no repository dataset matches this chain's endpoints",
                           "action": "name the dataset that would test it, or mark it needs_data"})
    bridge_ends = set()
    for bridge in bridges:
        bridge_ends.add(bridge["from"])
        bridge_ends.add(bridge["to"])
    for dig in digs:
        if dig["id"] not in bridge_ends and dig.get("root") not in bridge_ends:
            hidden.append({"kind": "hidden_gap", "id": dig["id"],
                           "reason": "dig has no bridge in either direction",
                           "action": "bridge the dig to the chain it feeds, or declare it standalone"})

    # Under-connected core nodes.
    for identifier, record in nodes.items():
        if record["degree"] < 50 and not identifier.startswith("sub:"):
            hidden.append({"kind": "hidden_gap", "id": identifier,
                           "reason": f"core node at degree {record['degree']}, under the 50 connection target",
                           "action": "add the missing connections as questions with falsifiers"})
    hidden.append({"kind": "hidden_assumption", "id": "index-wide",
                   "reason": f"{missing_condition} inferred connections lack a condition, {missing_falsifier} lack a falsifier",
                   "action": "keep filling conditions and falsifiers as part of every deepening pass"})
    OUT_HIDDEN.write_text("".join(json.dumps(entry) + "\n" for entry in hidden))

    # ---------- propagation ----------
    measured_nodes = [entry["node"] for entry in measurements]
    evidence_nodes = []
    for dig in digs:
        for node in dig["nodes"]:
            if node.get("evidence") in ("E1", "E2"):
                evidence_nodes.append(node["id"])
    seeds = sorted(set(measured_nodes + evidence_nodes))
    seed_set = set(seeds)
    edges = collections.defaultdict(list)
    for record in nodes.values():
        for conn in record["connections"]:
            if conn["to"] in nodes and conn.get("type") in PROP_TYPES:
                edges[record["id"]].append((conn["to"], conn))

    status_tier = {"curated": "E2", "declared": "E2", "inferred": "E3", "proposed": "E4", "blocked": "E5"}
    tier_rank = {"E1": 1, "E2": 2, "E3": 3, "E4": 4, "E5": 5, "undeclared": 6}
    paths = []
    seen = set()
    for seed in seeds:
        if seed not in nodes:
            continue
        stack = [([seed], [])]
        while stack and len(paths) < 3000:
            path, hops = stack.pop()
            if len(path) >= 5:
                continue
            current = path[-1]
            current_tags = domain_tags(current, nodes[current].get("meaning", ""))
            for target, conn in edges[current]:
                if target in path:
                    continue
                target_tags = domain_tags(target, nodes[target].get("meaning", ""))
                moved = False
                for order in (FUNDAMENTAL, CASCADE):
                    positions = [order.index(tag) for tag in current_tags if tag in order]
                    targets = [order.index(tag) for tag in target_tags if tag in order]
                    if positions and targets and max(targets) > min(positions):
                        moved = True
                if not moved:
                    continue
                new_path = path + [target]
                new_hops = hops + [conn]
                key = tuple(new_path)
                if key not in seen:
                    seen.add(key)
                    paths.append((new_path, new_hops))
                stack.append((new_path, new_hops))
    ranked = []
    for path, hops in paths:
        tiers = [status_tier.get(hop.get("status", ""), "undeclared") for hop in hops]
        floor = min(tiers, key=lambda tier: tier_rank[tier]) if tiers else "undeclared"
        weakest = min(hops, key=lambda hop: tier_rank[status_tier.get(hop.get("status", ""), "undeclared")])
        endpoint_tokens = set(tokens(path[0])) | set(tokens(path[-1]))
        matched = [file for file, needles in DATA_INVENTORY.items()
                   if endpoint_tokens & set(needles)]
        inner_tokens = set()
        for identifier in path[1:-1]:
            inner_tokens.update(tokens(identifier))
        inner_matched = [file for file, needles in DATA_INVENTORY.items()
                         if inner_tokens & set(needles)]
        if matched:
            test_status = "testable_now"
        elif inner_matched:
            test_status = "partially_testable"
            matched = inner_matched
        else:
            test_status = "needs_data"
        ranked.append({"seed": path[0], "path": path, "hops": len(hops),
                       "rules": [hop.get("type") for hop in hops],
                       "evidence_floor": floor,
                       "greatest_assumption": {"edge": f"{path[len(hops) - 1]}->{path[len(hops)]}",
                                               "status": weakest.get("status"),
                                               "condition": weakest.get("condition", ""),
                                               "falsifier": weakest.get("falsifier", "")},
                       "testable": {"data_in_hand": matched, "status": test_status},
                       "payer": path[-1] if path[-1].startswith(("asset:", "entity:", "outcome:")) else None})
    status_order = {"testable_now": 0, "partially_testable": 1, "needs_data": 2}
    ranked.sort(key=lambda entry: (status_order[entry["testable"]["status"]],
                                   tier_rank[entry["evidence_floor"]], entry["hops"], entry["seed"]))
    ranked = ranked[:1500]
    OUT_PROP.write_text("".join(json.dumps(entry) + "\n" for entry in ranked))

    summary = {"nodes": len(nodes), "connections": total_connections,
               "distributions": len(distributions),
               "hidden_objects": {"total": len(hidden),
                                  "by_kind": dict(collections.Counter(entry["kind"] for entry in hidden)),
                                  "hidden_nodes": sum(1 for entry in hidden if entry["kind"] == "hidden_node"),
                                  "hidden_edges": sum(1 for entry in hidden if entry["kind"] == "hidden_edge")},
               "propagation": {"seeds": len(seeds), "paths": len(ranked),
                               "testable_now": sum(1 for entry in ranked if entry["testable"]["status"] == "testable_now"),
                               "partially_testable": sum(1 for entry in ranked if entry["testable"]["status"] == "partially_testable"),
                               "needs_data": sum(1 for entry in ranked if entry["testable"]["status"] == "needs_data"),
                               "payers": sum(1 for entry in ranked if entry["payer"]),
                               "evidence_floor": dict(collections.Counter(entry["evidence_floor"] for entry in ranked))},
               "delineation": delineation}
    OUT_DELIN.write_text(json.dumps(delineation, indent=1) + "\n")
    OUT_SUMMARY.write_text(json.dumps(summary, indent=1) + "\n")
    print(f"distributions {len(distributions)}; hidden objects {len(hidden)} "
          f"({summary['hidden_objects']['by_kind']}); propagation paths {len(ranked)} "
          f"({summary['propagation']['testable_now']} testable now, {summary['propagation']['payers']} to a payer)")
    print(f"delineation: {len(nodes):,} nodes, {total_connections:,} connections, "
          f"{delineation['unreachable_from_anchors']} unreachable from anchors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
