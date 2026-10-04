#!/usr/bin/env python3
"""Render the connection index: summary, one worked node record, one worked chain, the bridges.

    python3 scripts/render_connection_index.py
"""
from __future__ import annotations

import gzip
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "docs" / "scan" / "connection-index.jsonl.gz"
SUMMARY = ROOT / "docs" / "scan" / "connection-index-summary.json"
BRIDGES = ROOT / "docs" / "scan" / "deep-bridges.jsonl"
DIGS = ROOT / "docs" / "scan" / "deep-digs.jsonl"
OUT_MD = ROOT / "docs" / "scan" / "connection-index.md"
OUT_HTML = ROOT / "docs" / "scan" / "connection-index.html"
EXAMPLE_NODE = "mechanism:capacity:transformer-bottleneck"
EXAMPLE_CHAIN = "dig:fcc:catalyst-minerals"


def main() -> int:
    summary = json.loads(SUMMARY.read_text())
    bridges = [json.loads(line) for line in BRIDGES.open() if line.strip()]
    digs = [json.loads(line) for line in DIGS.open() if line.strip()]
    example = None
    with gzip.open(INDEX, "rt") as handle:
        for line in handle:
            record = json.loads(line)
            if record["id"] == EXAMPLE_NODE:
                example = record
                break
    if example is None:
        raise SystemExit(f"example node missing from index: {EXAMPLE_NODE}")
    problems = []
    for record in [example]:
        if record["degree"] != len(record["connections"]):
            problems.append(f"{record['id']}: degree mismatch")
        for conn in record["connections"]:
            if not conn.get("type") or not conn.get("status") or not conn.get("falsifier"):
                problems.append(f"{record['id']}: incomplete connection to {conn.get('to')}")
    if problems:
        raise SystemExit("; ".join(problems))

    chain_dig = next(dig for dig in digs if dig["id"] == EXAMPLE_CHAIN)
    chain = chain_dig["chain"]
    edge_lookup = {(edge["from"], edge["to"]): edge for edge in chain_dig["edges"]}
    hops = []
    for position, (start, end) in enumerate(zip(chain, chain[1:]), start=1):
        edge = edge_lookup.get((start, end), {})
        hops.append({"hop": f"hop:{EXAMPLE_CHAIN}:{position:02d}", "from": start, "to": end,
                     "relation": edge.get("relation", "chain_precedes"),
                     "condition": edge.get("condition", ""), "falsifier": edge.get("falsifier", "")})

    md = ["# Connection index", "",
          "Method owner: `docs/plan/deep-chaining.md`. Every node carries its own typed connections and",
          "its chain hops. Inferred connections are questions with a type and a falsifier.", "",
          f"- Nodes indexed: **{summary['nodes']:,}** ({summary['core_nodes']} core nodes from the manifest",
          f"  and the digs, {summary['skeleton_nodes']:,} skeleton sub-nodes)",
          f"- Typed connections: **{summary['connections']:,}**",
          f"- Core degree: min {summary['core_degrees']['min']}, median {summary['core_degrees']['median']:.0f}, "
          f"max {summary['core_degrees']['max']}; **{summary['core_with_50_plus']} core nodes at 50+ connections "
          f"({summary['core_with_50_plus_share']:.1%})**",
          f"- Skeleton degree: structural only, median {summary['degrees']['median']:.0f}",
          f"- Chains {summary['chains']}, hops {summary['hops']}, bridges {summary['bridges']}", "",
          "## Connection types", "", "| Type | Count |", "|---|---|"]
    for conn_type, count in list(summary["by_type"].items())[:18]:
        md.append(f"| `{conn_type}` | {count:,} |")
    md += ["", "## Worked node record", "",
           f"`{example['id']}` ({example['layer']}), degree {example['degree']}. "
           f"Statuses: {example['by_status']}.", "",
           "| Connected to | Type | Status | Why | Falsifier |", "|---|---|---|---|---|"]
    for conn in example["connections"][:60]:
        md.append(f"| `{conn['to']}` | {conn['type']} | {conn['status']} | {conn['why']} | "
                  f"{conn['falsifier']} |")
    md += ["", f"Chain memberships for this node: " +
           (", ".join(f"`{m['chain']}` at {m['hop']}" for m in example["chains"]) or "none") + ".", "",
           "## Worked chain, with hop addresses", "",
           f"`{EXAMPLE_CHAIN}` resolves hop by hop, so any node downstream carries its own sub-address:", "",
           "| Hop | From | To | Relation | Condition | Falsifier |", "|---|---|---|---|---|---|"]
    for hop in hops:
        md.append(f"| `{hop['hop']}` | `{hop['from']}` | `{hop['to']}` | {hop['relation']} | "
                  f"{hop['condition']} | {hop['falsifier']} |")
    md += ["", "The same chain in the captain's form: `dig:fcc:catalyst-inventory` holds "
           "`dig:fcc:y-zeolite` with the edge `requires`, and the zeolite node holds "
           "`dig:fcc:rare-earth-stabilisers` as chain step 5, resolvable from either end.", "",
           "## Bridges, the cross-dig links", "",
           "| Bridge | From | To | Relation | Condition | Falsifier |", "|---|---|---|---|---|---|"]
    for bridge in bridges:
        md.append(f"| `{bridge['id']}` | `{bridge['from']}` | `{bridge['to']}` | {bridge['relation']} | "
                  f"{bridge['condition']} | {bridge['falsifier']} |")
    md += ["", "## Under-connected core nodes, the research queue", "",
           "These core nodes do not yet reach fifty typed connections. The gap is the list of digs still",
           "to write, not a licence to pad:", "",
           "| Node | Degree |", "|---|---|"]
    for row in summary["under_connected_core"][:30]:
        md.append(f"| `{row['id']}` | {row['degree']} |")
    md.append("")
    OUT_MD.write_text("\n".join(md) + "\n")

    example_rows = "\n".join(
        f"<tr><td><code>{html.escape(c['to'])}</code></td><td>{c['type']}</td><td>{c['status']}</td>"
        f"<td>{html.escape(c['why'])}</td><td>{html.escape(c['falsifier'])}</td></tr>"
        for c in example["connections"][:80])
    hop_rows = "\n".join(
        f"<tr><td><code>{hop['hop']}</code></td><td><code>{html.escape(hop['from'])}</code></td>"
        f"<td><code>{html.escape(hop['to'])}</code></td><td>{hop['relation']}</td>"
        f"<td>{html.escape(hop['condition'])}</td><td>{html.escape(hop['falsifier'])}</td></tr>"
        for hop in hops)
    bridge_rows = "\n".join(
        f"<tr><td><code>{html.escape(b['id'])}</code></td><td><code>{html.escape(b['from'])}</code></td>"
        f"<td><code>{html.escape(b['to'])}</code></td><td>{b['relation']}</td>"
        f"<td>{html.escape(b['condition'])}</td><td>{html.escape(b['falsifier'])}</td></tr>"
        for b in bridges)
    queue_rows = "\n".join(
        f"<tr><td><code>{html.escape(row['id'])}</code></td><td>{row['degree']}</td></tr>"
        for row in summary["under_connected_core"][:40])
    OUT_HTML.write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Connection index</title>
<style>
 body{{font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;padding:2rem;background:#0e1116;color:#e6edf3}}
 main{{max-width:1250px;margin:0 auto}} h1{{font-size:1.6rem}} h2{{font-size:1.25rem;margin-top:2.5rem}}
 code{{background:#161b22;padding:.1rem .25rem;border-radius:4px;font-size:.85em}}
 table{{border-collapse:collapse;width:100%;font-size:.8rem;margin-top:.6rem}}
 th,td{{border:1px solid #30363d;padding:.35rem .5rem;vertical-align:top;text-align:left}} th{{background:#161b22}}
 .meta{{color:#8b949e}}
</style></head><body><main>
<h1>Connection index</h1>
<p class="meta">Method owner: docs/plan/deep-chaining.md. Inferred connections are questions with a type and a falsifier.</p>
<ul>
<li>{summary['nodes']:,} nodes indexed: {summary['core_nodes']} core, {summary['skeleton_nodes']:,} skeleton</li>
<li>{summary['connections']:,} typed connections</li>
<li>Core degree median {summary['core_degrees']['median']:.0f}; {summary['core_with_50_plus']} core nodes at 50+ ({summary['core_with_50_plus_share']:.1%})</li>
<li>{summary['chains']} chains, {summary['hops']} hops, {summary['bridges']} bridges</li>
</ul>
<h2>Worked node record: {html.escape(example['id'])} (degree {example['degree']})</h2>
<table><thead><tr><th>Connected to</th><th>Type</th><th>Status</th><th>Why</th><th>Falsifier</th></tr></thead>
<tbody>{example_rows}</tbody></table>
<h2>Worked chain: {EXAMPLE_CHAIN}</h2>
<table><thead><tr><th>Hop</th><th>From</th><th>To</th><th>Relation</th><th>Condition</th><th>Falsifier</th></tr></thead>
<tbody>{hop_rows}</tbody></table>
<h2>Bridges</h2>
<table><thead><tr><th>Bridge</th><th>From</th><th>To</th><th>Relation</th><th>Condition</th><th>Falsifier</th></tr></thead>
<tbody>{bridge_rows}</tbody></table>
<h2>Under-connected core nodes, the research queue</h2>
<table><thead><tr><th>Node</th><th>Degree</th></tr></thead><tbody>{queue_rows}</tbody></table>
</main></body></html>
""")
    print(f"wrote {OUT_MD.relative_to(ROOT)} and {OUT_HTML.relative_to(ROOT)}")
    print(f"example degree {example['degree']}; chain hops {len(hops)}; bridges {len(bridges)}; "
          f"under-connected core listed {len(summary['under_connected_core'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
