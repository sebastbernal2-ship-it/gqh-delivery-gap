#!/usr/bin/env python3
"""Render the decomposition skeleton and the curated deep digs.

Reads docs/scan/decomposition-summary.json and docs/scan/deep-digs.jsonl, samples the compressed
skeleton for illustration, and writes docs/scan/decomposition.md and .html. Every curated node shows
its six sub-items, because the sub-node law applies to it too.

    python3 scripts/render_decomposition.py
"""
from __future__ import annotations

import gzip
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUMMARY = ROOT / "docs" / "scan" / "decomposition-summary.json"
DIGS = ROOT / "docs" / "scan" / "deep-digs.jsonl"
CYCLES = ROOT / "docs" / "scan" / "analogue-cycles.jsonl"
SKELETON = ROOT / "docs" / "scan" / "decomposition.jsonl.gz"
OUT_MD = ROOT / "docs" / "scan" / "decomposition.md"
OUT_HTML = ROOT / "docs" / "scan" / "decomposition.html"

DIMENSION_TABLE = [
    ("source", "access path, update cadence, revision behavior, entity key, point-in-time guarantee, licensing"),
    ("dataset", "schema, coverage universe, clock, vintage archive, join keys, missingness pattern"),
    ("feature", "construction inputs, measurement clock, normalization, lookahead risk, stability, economic meaning"),
    ("mechanism", "trigger, transmission path, rate limiter, observable, lag profile, payer incidence"),
    ("factor", "measurement proxy, horizon, conditioning state, transmission, crowding, payer incidence"),
    ("entity", "legal structure, segment mapping, identifiers, exposure map, counterparties, disclosure clock"),
    ("asset", "instrument mechanics, liquidity, borrow and short constraints, option surface, credit terms, financing"),
    ("outcome", "measurement window, benchmark, sign convention, accounting bridge, revision behavior, falsifier"),
    ("event", "detection rule, timestamp source, confirmation lag, agenda ambiguity, clustering, placebo design"),
    ("assumption", "test design, failure mode, blast radius, owner, monitoring cadence, kill threshold"),
    ("claim", "mechanism link, evidence requirement, null, multiplicity, horizon, cost ceiling"),
    ("experiment", "design, sample, power, null, placebo, stopping rule"),
    ("evidence", "provenance, extraction method, precision, timestamp, source agreement, decay"),
    ("rule", "statement, scope, override, enforcement point, violation handling, audit trail"),
    ("contract", "obligation, trigger, notice, penalty, assignment, term"),
    ("strategy", "signal, sizing, costs, capacity, kill switch, funding"),
    ("implementation", "interface, state, failure mode, test, observability, rollout"),
    ("physical and raw", "composition, inputs, constraints, observables, substitutes, payers"),
]
SUB_ITEMS = ["composition", "inputs", "constraints", "observables", "substitutes", "payers"]


def main() -> int:
    summary = json.loads(SUMMARY.read_text())
    digs = [json.loads(line) for line in DIGS.open() if line.strip()]
    cycles = [json.loads(line) for line in CYCLES.open() if line.strip()] if CYCLES.exists() else []
    sample = []
    if SKELETON.exists():
        with gzip.open(SKELETON, "rt") as handle:
            for index, line in enumerate(handle):
                if index >= 400:
                    break
                row = json.loads(line)
                if row.get("kind") == "subnode" and len(sample) < 6:
                    sample.append(row)

    lines = ["# Decomposition: the graph at sub-node resolution", "",
             "Method owner: `docs/plan/decomposition.md`. Every node decomposes into at least six children",
             "along the dimensions of its layer, and every child decomposes again. The skeleton is written",
             "out and labelled `proposed_unverified`; the curated digs are where domain knowledge fills the",
             "levels with named minerals, suppliers, observables and payers.", "",
             f"**Written graph: {summary['written_total_with_curated']:,} nodes** "
             f"({summary['manifest_nodes']:,} declared + {summary['subnodes_total']:,} skeleton children + "
             f"{summary['curated_children']:,} children of curated dig nodes), "
             f"{summary['split_edges'] + summary['curated_children']:,} split edges.", "",
             f"- Manifest nodes decomposed: {summary['manifest_nodes']:,}, minimum children per node: "
             f"{summary['children_per_parent_min']}", "",
             f"- Curated dig nodes: {summary['curated_dig_nodes']}, digs: {len(digs)}", "",
             "## The dimensions", "", "| Layer | Six sub-items |", "|---|---|"]
    for layer, dims in DIMENSION_TABLE:
        lines.append(f"| {layer} | {dims} |")
    lines += ["", "## The skeleton, sampled", "",
              "Six rows from `docs/scan/decomposition.jsonl.gz`, one per manifest node family, to show the",
              "schema and the status honesty:", "",
              "| Child id | Parent | Dimension | Meaning | Status |", "|---|---|---|---|---|"]
    for row in sample:
        lines.append(f"| `{row['id']}` | `{row['parent']}` | {row['dimension']} | "
                     f"{row['meaning']} | {row['status']} |")
    lines += ["", "## The curated digs", ""]
    for dig in digs:
        lines += [f"### {dig['title']}", "",
                  f"`{dig['id']}` · root `{dig['root']}` · ceiling **{dig['ceiling']}**"
                  + (f" · nodes {len(dig['nodes'])} · edges {len(dig['edges'])}" if dig.get("nodes") else ""),
                  "", f"**Why.** {dig['why']}", "",
                  f"**Chain.** " + " -> ".join(f"`{node}`" for node in dig.get("chain", [])), "",
                  f"**Greatest assumption.** {dig['greatest_assumption']}", "",
                  f"**Kill test.** {dig['kill_test']}", "",
                  "| Node | Layer | Players | Observables | Payer | Evidence | Source |", "|---|---|---|---|---|---|---|"]
        for node in dig.get("nodes", []):
            players = ", ".join(node.get("players", [])) or "none named"
            observables = "; ".join(node.get("observables", [])) or "to fetch"
            lines.append(f"| **{node['name']}** `{node['id']}` | {node['layer']} | {players} | "
                         f"{observables} | {node['payer']} | {node['evidence']} | {node['source']} |")
        lines += ["", "Sub-items to fetch for every node above: " + ", ".join(SUB_ITEMS) + ".", "",
                  "| Edge | Relation | Condition | Falsifier |", "|---|---|---|---|"]
        for edge in dig.get("edges", []):
            lines.append(f"| `{edge['from']}` -> `{edge['to']}` | {edge['relation']} | "
                         f"{edge['condition']} | {edge['falsifier']} |")
        lines.append("")
    if cycles:
        lines += ["", "## The analogue cycles, the temporal backbone", "",
                  "Nine recorded infrastructure cycles with the same phase ordering. Method owner:",
                  "`docs/plan/regimes.md`. Every claim of a ten to twenty year rationale is checked against",
                  "at least two of these.", "",
                  "| Cycle | Era | Trigger | What persisted | What died |", "|---|---|---|---|---|"]
        for cycle in cycles:
            lines.append(f"| **{cycle['name']}** `{cycle['id']}` | {cycle['era']} | {cycle['trigger']} | "
                         f"{cycle['what_persisted']} | {cycle['what_died']} |")
        for cycle in cycles:
            lines += ["", f"### {cycle['name']}", "", f"`{cycle['id']}` | {cycle['era']}", "",
                      "| Phase | Years | Markers | Outcome |", "|---|---|---|---|"]
            for phase in cycle.get("phases", []):
                lines.append(f"| {phase['phase']} | {phase['years']} | {phase['markers']} | {phase['outcome']} |")
            lines += ["", f"**Funding.** {cycle['funding']}", "",
                      f"**Mapping to current nodes.** " +
                      "; ".join(f"`{m['current_node']}` ({m['relation']}: {m['why']})"
                                for m in cycle.get("mapping_to_current", [])), "",
                      f"**Falsifier.** {cycle['falsifier']}", ""]
    OUT_MD.write_text("\n".join(lines) + "\n")

    def dig_html(dig: dict) -> str:
        node_rows = "\n".join(
            f"<tr><td><b>{html.escape(node['name'])}</b><br><code>{html.escape(node['id'])}</code></td>"
            f"<td>{node['layer']}</td><td>{html.escape(', '.join(node.get('players', [])) or 'none named')}</td>"
            f"<td>{html.escape('; '.join(node.get('observables', [])) or 'to fetch')}</td>"
            f"<td>{html.escape(node['payer'])}</td><td>{node['evidence']}</td>"
            f"<td>{html.escape(node['source'])}</td></tr>" for node in dig.get("nodes", []))
        edge_rows = "\n".join(
            f"<tr><td><code>{html.escape(edge['from'])}</code> -> <code>{html.escape(edge['to'])}</code></td>"
            f"<td>{edge['relation']}</td><td>{html.escape(edge['condition'])}</td>"
            f"<td>{html.escape(edge['falsifier'])}</td></tr>" for edge in dig.get("edges", []))
        return (f"<section><h3>{html.escape(dig['title'])}</h3>"
                f"<p class=\"meta\"><code>{html.escape(dig['id'])}</code> · root "
                f"<code>{html.escape(dig['root'])}</code> · ceiling <b>{dig['ceiling']}</b></p>"
                f"<p><b>Why.</b> {html.escape(dig['why'])}</p>"
                f"<p><b>Chain.</b> {' -> '.join(html.escape(n) for n in dig.get('chain', []))}</p>"
                f"<p><b>Greatest assumption.</b> {html.escape(dig['greatest_assumption'])}</p>"
                f"<p><b>Kill test.</b> {html.escape(dig['kill_test'])}</p>"
                f"<table><thead><tr><th>Node</th><th>Layer</th><th>Players</th><th>Observables</th>"
                f"<th>Payer</th><th>Evidence</th><th>Source</th></tr></thead><tbody>{node_rows}</tbody></table>"
                f"<p class=\"meta\">Sub-items to fetch for every node: {', '.join(SUB_ITEMS)}.</p>"
                f"<table><thead><tr><th>Edge</th><th>Relation</th><th>Condition</th><th>Falsifier</th>"
                f"</tr></thead><tbody>{edge_rows}</tbody></table></section>")

    def cycle_html(cycle: dict) -> str:
        phase_rows = "\n".join(
            f"<tr><td>{phase['phase']}</td><td>{phase['years']}</td><td>{html.escape(phase['markers'])}</td>"
            f"<td>{html.escape(phase['outcome'])}</td></tr>" for phase in cycle.get("phases", []))
        mapping = "; ".join(f"<code>{html.escape(m['current_node'])}</code> ({html.escape(m['relation'])})"
                            for m in cycle.get("mapping_to_current", []))
        return (f"<section><h3>{html.escape(cycle['name'])}</h3>"
                f"<p class=\"meta\"><code>{html.escape(cycle['id'])}</code> · {html.escape(cycle['era'])}</p>"
                f"<p><b>Trigger.</b> {html.escape(cycle['trigger'])}</p>"
                f"<table><thead><tr><th>Phase</th><th>Years</th><th>Markers</th><th>Outcome</th></tr></thead>"
                f"<tbody>{phase_rows}</tbody></table>"
                f"<p><b>Funding.</b> {html.escape(cycle['funding'])}</p>"
                f"<p><b>What persisted.</b> {html.escape(cycle['what_persisted'])} "
                f"<b>What died.</b> {html.escape(cycle['what_died'])}</p>"
                f"<p><b>Mapping.</b> {mapping}</p>"
                f"<p><b>Falsifier.</b> {html.escape(cycle['falsifier'])}</p></section>")
    body = "\n".join(dig_html(dig) for dig in digs)
    cycle_body = ("<h2>The analogue cycles</h2>" + "".join(cycle_html(cycle) for cycle in cycles)) if cycles else ""
    OUT_HTML.write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Decomposition: the graph at sub-node resolution</title>
<style>
 body{{font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;margin:0;padding:2rem;background:#0e1116;color:#e6edf3}}
 main{{max-width:1250px;margin:0 auto}} h1{{font-size:1.6rem}} h2{{font-size:1.3rem;margin-top:2.5rem}} h3{{font-size:1.1rem;margin-top:2rem}}
 code{{background:#161b22;padding:.1rem .25rem;border-radius:4px;font-size:.85em}}
 table{{border-collapse:collapse;width:100%;font-size:.8rem;margin-top:.75rem}}
 th,td{{border:1px solid #30363d;padding:.4rem .5rem;vertical-align:top;text-align:left}} th{{background:#161b22}}
 .meta{{color:#8b949e;font-size:.85rem}}
</style></head><body><main>
<h1>Decomposition: the graph at sub-node resolution</h1>
<p>{summary['written_total_with_curated']:,} written nodes:
{summary['manifest_nodes']:,} declared, {summary['subnodes_total']:,} skeleton children,
{summary['curated_children']:,} children of curated dig nodes. {len(digs)} curated digs.
Method owner: <code>docs/plan/decomposition.md</code>.</p>
{cycle_body}
{body}
</main></body></html>
""")
    print(f"wrote {OUT_MD.relative_to(ROOT)} and {OUT_HTML.relative_to(ROOT)}")
    print(f"digs {len(digs)}; curated nodes {sum(len(d['nodes']) for d in digs)}; "
          f"curated edges {sum(len(d['edges']) for d in digs)}; sample rows {len(sample)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
