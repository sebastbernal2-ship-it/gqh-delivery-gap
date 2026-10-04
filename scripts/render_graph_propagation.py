#!/usr/bin/env python3
"""Render the deepening pass: delineation, hidden objects, distributions, propagation paths.

    python3 scripts/render_graph_propagation.py
"""
from __future__ import annotations

import gzip
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN = ROOT / "docs" / "scan"
OUT_MD = SCAN / "graph-propagation.md"
OUT_HTML = SCAN / "graph-propagation.html"


def table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(cell if cell is not None else "" for cell in row) + " |")
    return "\n".join(lines)


def main() -> int:
    summary = json.loads((ROOT / "results" / "graph-propagation-summary.json").read_text())
    delineation = json.loads((SCAN / "graph-delineation.json").read_text())
    hidden = [json.loads(line) for line in (SCAN / "hidden-objects.jsonl").open() if line.strip()]
    distributions = [json.loads(line) for line in (SCAN / "distributions.jsonl").open() if line.strip()]
    propagation = [json.loads(line) for line in (SCAN / "propagation.jsonl").open() if line.strip()]

    concept = json.loads((SCAN / "conceptual-summary.json").read_text())
    interactions = [json.loads(line) for line in (SCAN / "interactions.jsonl").open() if line.strip()]
    assumptions = [json.loads(line) for line in (SCAN / "assumptions.jsonl").open() if line.strip()]
    concept_chains = [json.loads(line) for line in (SCAN / "conceptual-chains.jsonl").open() if line.strip()]
    heaviest = sorted(interactions, key=lambda row: (-row["load"], row["from"]))[:20]
    by_kind = summary["hidden_objects"]["by_kind"]
    top_paths = propagation[:25]
    volatile = sorted([entry for entry in distributions if entry["sample"] not in ("",)],
                      key=lambda entry: -(entry["stats"].get("monthly_log_return_sd_annualised") or 0))[:12]
    tails = sorted(distributions, key=lambda entry: -(entry["stats"].get("tail_ratio_p90_median") or 0))[:12]

    md = ["# Graph propagation and delineation", "",
          "Method owner: `docs/plan/graph-propagation.md`. Classification is decomposed or not yet",
          "decomposed. Nothing here grades a path as dead.", "",
          "## The graph, expanded", "",
          f"- Nodes: **{summary['nodes']:,}**",
          f"- Typed connections: **{summary['connections']:,}**",
          f"- Distributions written down: **{summary['distributions']}** samples",
          f"- Propagation paths: **{summary['propagation']['paths']:,}** from {summary['propagation']['seeds']} seeds",
          f"- Hidden objects: **{summary['hidden_objects']['total']}** "
          f"(nodes {by_kind.get('hidden_node', 0)}, edges {by_kind.get('hidden_edge', 0)}, "
          f"gaps {by_kind.get('hidden_gap', 0)}, assumptions {by_kind.get('hidden_assumption', 0)})", "",
          "## Delineation", "",
          f"- Layers: " + ", ".join(f"`{layer}` {count:,}" for layer, count in list(delineation["by_layer"].items())[:8]),
          f"- Connection status: " + ", ".join(f"`{status}` {count:,}" for status, count in delineation["by_status"].items()),
          f"- Every connection carries a condition and a falsifier: "
          f"{delineation['coverage']['connections_with_condition_pct']}% and "
          f"{delineation['coverage']['connections_with_falsifier_pct']}%",
          f"- Components: {delineation['components']['count']}, largest {delineation['components']['largest']:,}, "
          f"unreachable from anchors {delineation['unreachable_from_anchors']}", "",
          "## Distributions, centre, spread, tails", "",
          "Top samples by annualised monthly volatility:", "",
          table(["Sample", "n", "mean", "sd", "median", "p90/median", "skew", "excess kurtosis"],
                [[entry["sample"], str(entry["stats"].get("n")), str(entry["stats"].get("mean")),
                  str(entry["stats"].get("sd")), str(entry["stats"].get("median")),
                  str(entry["stats"].get("tail_ratio_p90_median")), str(entry["stats"].get("skew")),
                  str(entry["stats"].get("excess_kurtosis"))] for entry in volatile]),
          "", "Top samples by tail ratio (p90 over median):", "",
          table(["Sample", "dataset", "n", "p90/median", "top 1 percent share"],
                [[entry["sample"], entry["dataset"].split("/")[-1], str(entry["stats"].get("n")),
                  str(entry["stats"].get("tail_ratio_p90_median")), str(entry["stats"].get("top1pct_share"))]
                 for entry in tails]),
          "", "## The conceptual layer", "",
          f"- Forces: **{concept['forces']}** across {len(concept['forces_by_domain'])} domains",
          f"- Interactions: **{concept['interactions']}** typed pushes, mean assumption load "
          f"{concept['mean_load']}, {concept['high_load_links']} at load four or five, "
          f"{concept['phase_conditional_interactions']} with phase dependent signs",
          f"- Assumptions as nodes: **{concept['assumptions_total']}**",
          f"- Conceptual chains: **{concept['chains']}** carrying {concept['chain_hops']} hops", "",
          "Relations in use: " + ", ".join(f"{name} {count}" for name, count in list(concept["interactions_by_relation"].items())[:12]) + ".", "",
          "### The heaviest links", "",
          table(["From", "Relation", "To", "Load", "Channel", "Kill"],
                [[f"`{row['from']}`", row["relation"], f"`{row['to']}`", str(row["load"]),
                  row["channel"], row["kill"]] for row in heaviest]),
          "", "### Conceptual chains", "",
          table(["Chain", "Hops", "Intuition", "Greatest assumption"],
                [[f"`{chain['id']}`", " -> ".join(hop.split(":")[-1] for hop in chain["hops"]),
                  chain["intuition"], chain["greatest_assumption"]] for chain in concept_chains]),
          "", "### Assumptions as first class nodes", "",
          table(["Assumption", "Statement", "Kill", "Load"],
                [[f"`{row['id'].split('assumption:')[1]}`", row["statement"], row["kill"],
                  str(row.get("load", ""))] for row in assumptions[:30]]),
          "", "## Hidden layer", "",
          table(["Kind", "Id", "Reason", "Action"],
                [[entry["kind"], f"`{entry.get('id') or (entry.get('from', '') + ' -> ' + entry.get('to', ''))}`",
                  entry["reason"], entry.get("action", "")] for entry in hidden[:30]]),
          "", "## Propagation paths, truth to payer", "",
          table(["Seed", "Path", "Hops", "Floor", "Data in hand", "Greatest assumption"],
                [[f"`{entry['seed']}`",
                  " -> ".join(f"`{node}`" for node in entry["path"]),
                  str(entry["hops"]), entry["evidence_floor"],
                  ", ".join(path.split("/")[-1] for path in entry["testable"]["data_in_hand"]) or "needs data",
                  entry["greatest_assumption"]["condition"] or entry["greatest_assumption"]["status"] or ""]
                 for entry in top_paths]),
          "", "## Reproduce", "",
          "    python3 scripts/build_graph_propagation.py",
          "    python3 scripts/render_graph_propagation.py", ""]
    OUT_MD.write_text("\n".join(md))

    def rows_html(rows: list[list[str]]) -> str:
        return "".join("<tr>" + "".join(f"<td>{html.escape(cell or '')}</td>" for cell in row) + "</tr>"
                       for row in rows)

    OUT_HTML.write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Graph propagation and delineation</title>
<style>
 body{{font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;padding:2rem;background:#0e1116;color:#e6edf3}}
 main{{max-width:1350px;margin:0 auto}} h1{{font-size:1.6rem}} h2{{font-size:1.25rem;margin-top:2.5rem}}
 code{{background:#161b22;padding:.1rem .25rem;border-radius:4px;font-size:.85em}}
 table{{border-collapse:collapse;width:100%;font-size:.78rem;margin-top:.6rem}}
 th,td{{border:1px solid #30363d;padding:.35rem .5rem;vertical-align:top;text-align:left}} th{{background:#161b22}}
 .meta{{color:#8b949e}}
</style></head><body><main>
<h1>Graph propagation and delineation</h1>
<p class="meta">Method owner: docs/plan/graph-propagation.md. Classification is decomposed or not yet decomposed.</p>
<ul>
<li>{summary['nodes']:,} nodes, {summary['connections']:,} typed connections</li>
<li>{summary['distributions']} distributions written down, {summary['propagation']['paths']:,} propagation paths from {summary['propagation']['seeds']} seeds</li>
<li>{summary['hidden_objects']['total']} hidden objects: {by_kind.get('hidden_node', 0)} nodes, {by_kind.get('hidden_edge', 0)} edges, {by_kind.get('hidden_gap', 0)} gaps, {by_kind.get('hidden_assumption', 0)} assumptions</li>
<li>Coverage: {delineation['coverage']['connections_with_condition_pct']}% of connections carry a condition and a falsifier</li>
</ul>
<h2>Layers</h2>
<table><thead><tr><th>Layer</th><th>Nodes</th></tr></thead><tbody>
{''.join(f"<tr><td>{html.escape(layer)}</td><td>{count:,}</td></tr>" for layer, count in delineation['by_layer'].items())}
</tbody></table>
<h2>Distributions, centre, spread, tails</h2>
<table><thead><tr><th>Sample</th><th>n</th><th>mean</th><th>sd</th><th>median</th><th>p90/median</th><th>skew</th><th>excess kurtosis</th></tr></thead>
<tbody>{rows_html([[entry['sample'], str(entry['stats'].get('n')), str(entry['stats'].get('mean')), str(entry['stats'].get('sd')), str(entry['stats'].get('median')), str(entry['stats'].get('tail_ratio_p90_median')), str(entry['stats'].get('skew')), str(entry['stats'].get('excess_kurtosis'))] for entry in volatile])}</tbody></table>
<h2>The conceptual layer</h2>
<ul>
<li>{concept['forces']} forces across {len(concept['forces_by_domain'])} domains</li>
<li>{concept['interactions']} typed interactions, mean load {concept['mean_load']}, {concept['high_load_links']} at load four or five</li>
<li>{concept['assumptions_total']} assumptions as nodes, {concept['chains']} conceptual chains with {concept['chain_hops']} hops</li>
</ul>
<table><thead><tr><th>From</th><th>Relation</th><th>To</th><th>Load</th><th>Channel</th><th>Kill</th></tr></thead>
<tbody>{rows_html([[row['from'], row['relation'], row['to'], str(row['load']), row['channel'], row['kill']] for row in heaviest[:12]])}</tbody></table>
<table><thead><tr><th>Chain</th><th>Hops</th><th>Intuition</th></tr></thead>
<tbody>{rows_html([[chain['id'], ' -> '.join(hop.split(':')[-1] for hop in chain['hops']), chain['intuition']] for chain in concept_chains])}</tbody></table>
<h2>Hidden layer</h2>
<table><thead><tr><th>Kind</th><th>Id</th><th>Reason</th><th>Action</th></tr></thead>
<tbody>{rows_html([[entry['kind'], entry.get('id') or (entry.get('from', '') + ' -> ' + entry.get('to', '')), entry['reason'], entry.get('action', '')] for entry in hidden[:30]])}</tbody></table>
<h2>Propagation paths, truth to payer</h2>
<table><thead><tr><th>Seed</th><th>Path</th><th>Hops</th><th>Floor</th><th>Data in hand</th></tr></thead>
<tbody>{rows_html([[entry['seed'], ' -> '.join(entry['path']), str(entry['hops']), entry['evidence_floor'], ', '.join(path.split('/')[-1] for path in entry['testable']['data_in_hand']) or 'needs data'] for entry in top_paths])}</tbody></table>
</main></body></html>
""")
    print(f"wrote {OUT_MD.relative_to(ROOT)} and {OUT_HTML.relative_to(ROOT)}")
    print(f"hidden {len(hidden)}; paths {len(propagation)}; distributions {len(distributions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
