#!/usr/bin/env python3
"""Render the node sheets: every node, what it is, what we measured, what it connects to.

Three owners feed this view:

  docs/scan/nodes.jsonl             the measured layer: 27 declared nodes, each with a
                                    representation, a clock, an availability rule and a blocker
  docs/scan/quantgraph.jsonl        the expanded manifest and its typed edges
  docs/scan/node-measurements.jsonl the modelling ledger: one row per node with the rung the
                                    evidence reached, the measured summary, and the evidence paths
  docs/scan/node-crosswalk.jsonl    the explicit measured-to-manifest identity map

Writes docs/scan/node-sheets.md and docs/scan/node-sheets.html. The renderer validates the
ledger and crosswalk: nodes resolve, rungs and results are from the declared vocabulary, evidence
paths exist (globs allowed), and every crosswalk target exists in the manifest.

    python3 scripts/render_node_sheets.py
"""
from __future__ import annotations

import html
import json
from pathlib import Path

from check_scan_artifacts import crosswalk_problems

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "docs" / "scan" / "nodes.jsonl"
MANIFEST = ROOT / "docs" / "scan" / "quantgraph.jsonl"
LEDGER = ROOT / "docs" / "scan" / "node-measurements.jsonl"
CROSSWALK = ROOT / "docs" / "scan" / "node-crosswalk.jsonl"
MARKDOWN = ROOT / "docs" / "scan" / "node-sheets.md"
HTML = ROOT / "docs" / "scan" / "node-sheets.html"

RUNGS = ("documentation", "entitlement", "downloaded", "point_in_time_panel", "correct_label",
         "calibrated_forecast", "joint_tails", "trades_after_costs")
RESULTS = ("measured", "tested_null", "blocked", "open", "thin")


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def validate(registry, manifest, ledger, crosswalk) -> list[str]:
    problems: list[str] = []
    problems.extend(crosswalk_problems(registry, manifest, crosswalk))
    known = {node["id"] for node in registry} | {node["id"] for node in manifest if node.get("kind") == "node"}
    seen: set[str] = set()
    manifest_ids = {node["id"] for node in manifest if node.get("kind") == "node"}
    for row in ledger:
        node = row.get("node", "")
        label = node or "(row without a node)"
        if node not in known:
            problems.append(f"{label}: not a declared node")
        if node in seen:
            problems.append(f"{label}: measured twice")
        seen.add(node)
        if row.get("rung") not in RUNGS:
            problems.append(f"{label}: rung '{row.get('rung')}' is not one of {RUNGS}")
        if row.get("result") not in RESULTS:
            problems.append(f"{label}: result '{row.get('result')}' is not one of {RESULTS}")
        for path in row.get("evidence", []):
            if "*" in path:
                if not list(ROOT.glob(path)):
                    problems.append(f"{label}: evidence glob matches nothing: {path}")
            elif not (ROOT / path).exists():
                problems.append(f"{label}: evidence path does not exist: {path}")
        for bridge in row.get("manifest_ids", []):
            if bridge not in manifest_ids:
                problems.append(f"{label}: manifest id does not exist: {bridge}")
    return problems


def neighbours(manifest_edges: list[dict], ids: set[str], limit: int = 6) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for edge in manifest_edges:
        if edge.get("from") in ids or edge.get("to") in ids:
            other = edge["to"] if edge.get("from") in ids else edge["from"]
            counts[other] = counts.get(other, 0) + 1
    return sorted(counts.items(), key=lambda item: -item[1])[:limit]


def degree_of(manifest_edges: list[dict]) -> dict[str, int]:
    degree: dict[str, int] = {}
    for edge in manifest_edges:
        degree[edge["from"]] = degree.get(edge["from"], 0) + 1
        degree[edge["to"]] = degree.get(edge["to"], 0) + 1
    return degree


def format_stats(stats: dict) -> str:
    if not stats:
        return ""
    parts = [f"{key} = {value}" for key, value in stats.items()]
    return "stats: " + "; ".join(parts)


CROSSWALK_BY_NODE: dict[str, dict] = {}


def sheet(record: dict, measurement: dict | None, manifest_nodes: dict, manifest_edges: list[dict],
          degree: dict[str, int], as_html: bool) -> str:
    esc = html.escape if as_html else (lambda text: text)
    node = record["id"]
    heading = f"## {node}" if not as_html else f"<h2>{html.escape(node)}</h2>"
    lines: list[str] = [heading]
    if measurement:
        lines.append(f"**{measurement['rung']} / {measurement['result']}**" if not as_html
                     else f"<p class=\"tag\"><strong>{html.escape(measurement['rung'])} / "
                          f"{html.escape(measurement['result'])}</strong></p>")
        lines.append(esc(measurement["summary"]) if not as_html else f"<p>{esc(measurement['summary'])}</p>")
        stats = format_stats(measurement.get("stats", {}))
        if stats:
            lines.append(f"*{esc(stats)}*" if not as_html else f"<p class=\"stats\">{esc(stats)}</p>")
        if measurement.get("evidence"):
            evidence = ", ".join(f"`{path}`" for path in measurement["evidence"]) if not as_html \
                else ", ".join(f"<code>{html.escape(path)}</code>" for path in measurement["evidence"])
            lines.append(f"Evidence: {evidence}" if not as_html else f"<p>Evidence: {evidence}</p>")
    else:
        lines.append("*No measurement recorded yet. The representation below exists; the modelling "
                     "write-up is the gap.*" if not as_html
                     else "<p><em>No measurement recorded yet. The representation below exists; the "
                          "modelling write-up is the gap.</em></p>")
    meaning = record.get("meaning", "")
    if meaning:
        lines.append(f"What it is: {esc(meaning)}" if not as_html else f"<p>What it is: {esc(meaning)}</p>")
    if record.get("representations"):
        rows = []
        for representation in record["representations"]:
            rows.append(f"{representation.get('kind')} | {representation.get('source')} | "
                        f"{representation.get('clock')} | {representation.get('availability')} | "
                        f"{representation.get('status')}" +
                        (f" | blocker: {representation.get('blocker')}" if representation.get("blocker") else ""))
        body = "<br>".join(esc(row) for row in rows) if not as_html else \
            "<br>".join(html.escape(row) for row in rows)
        lines.append(f"Representation: {body}" if not as_html else f"<p>Representation: {body}</p>")
    bridges = [record["id"]] if record["id"] in manifest_nodes else []
    bridges += CROSSWALK_BY_NODE.get(record["id"], {}).get("manifest_ids", [])
    bridges += next((row.get("manifest_ids", []) for row in MEASUREMENTS if row["node"] == record["id"]), [])
    bridges = list(dict.fromkeys(bridges))
    if bridges:
        top = neighbours(manifest_edges, set(bridges))
        total = sum(degree.get(bridge, 0) for bridge in bridges)
        connection = f"Connects to {total} edges in the expanded manifest; densest: " + \
            ", ".join(f"{name} ({count})" for name, count in top)
        lines.append(connection if not as_html else f"<p>{esc(connection)}</p>")
    else:
        lines.append("Connections: no counterpart in the expanded manifest yet, so this node's "
                     "relations are not crosswalked." if not as_html
                     else "<p>Connections: no counterpart in the expanded manifest yet, so this "
                          "node's relations are not crosswalked.</p>")
    if measurement and measurement.get("note"):
        lines.append(f"Note: {esc(measurement['note'])}" if not as_html
                     else f"<p>Note: {esc(measurement['note'])}</p>")
    return "\n\n".join(lines)


MEASUREMENTS: list[dict] = []


def build_markdown(registry, manifest, ledger, crosswalk) -> str:
    global MEASUREMENTS, CROSSWALK_BY_NODE
    MEASUREMENTS = ledger
    CROSSWALK_BY_NODE = {row["node"]: row for row in crosswalk}
    manifest_nodes = {node["id"]: node for node in manifest if node.get("kind") == "node"}
    manifest_edges = [record for record in manifest if record.get("kind") == "edge"]
    degree = degree_of(manifest_edges)
    by_node = {row["node"]: row for row in ledger}
    measured_registry = sum(1 for node in registry if node["id"] in by_node)
    out = [
        "# Node sheets: what each node is, and what we measured",
        "",
        "Generated by `scripts/render_node_sheets.py` from `docs/scan/nodes.jsonl` (the measured layer), "
        "`docs/scan/quantgraph.jsonl` (the expanded manifest) and `docs/scan/node-measurements.jsonl` (the "
        "modelling ledger). Do not edit by hand.",
        "",
        f"- Modelling ledger: **{len(ledger)}** nodes written down; "
        f"{sum(1 for row in ledger if row['result'] in ('measured', 'tested_null'))} with a completed "
        f"measurement, {sum(1 for row in ledger if row['result'] == 'blocked')} blocked by access, "
        f"{sum(1 for row in ledger if row['result'] in ('open', 'thin'))} with the representation "
        f"declared and the write-up open or thin.",
        f"- Measured layer: **{len(registry)}** declared nodes, **{measured_registry}** with a ledger row.",
        f"- Expanded manifest: **{len(manifest_nodes)}** nodes and **{len(manifest_edges)}** edges.",
        f"- Crosswalk: {sum(1 for row in crosswalk if row['status'] != 'unmapped')} of {len(registry)} "
        "measured nodes have explicit manifest targets; unresolved nodes remain recorded as unmapped.",
        "",
        "The rung is the highest step of the confidence ladder the evidence reached: documentation, "
        "entitlement, downloaded, point in time panel, correct label, calibrated forecast, joint tails, "
        "trades after costs. A result of `tested_null` means the measurement exists and the test failed; "
        "`blocked` means access, not modelling, is the obstruction.",
        "",
        "## The measured layer",
        "",
    ]
    for node in sorted(registry, key=lambda item: (item.get("family", ""), item["id"])):
        out.append(sheet(node, by_node.get(node["id"]), manifest_nodes, manifest_edges, degree, as_html=False))
        out.append("")
    out += ["## Other measured nodes", ""]
    registry_ids = {node["id"] for node in registry}
    for row in ledger:
        if row["node"] in registry_ids:
            continue
        out.append(sheet({"id": row["node"], "meaning": ""}, row, manifest_nodes, manifest_edges,
                         degree, as_html=False))
        out.append("")
    out += ["## The declared layer, in full", ""]
    for layer in sorted({node.get("layer", "") for node in manifest_nodes.values()}):
        layer_nodes = sorted((node for node in manifest_nodes.values() if node.get("layer") == layer),
                             key=lambda item: -degree.get(item["id"], 0))
        out.append(f"### {layer} ({len(layer_nodes)} nodes)")
        out.append("")
        out.append("| node | status | degree | measured |")
        out.append("|---|---|---|---|")
        for node in layer_nodes:
            measured = "yes" if node["id"] in by_node else ""
            out.append(f"| `{node['id']}` | {node.get('status', '')} | {degree.get(node['id'], 0)} | {measured} |")
        out.append("")
    return "\n".join(out) + "\n"


def build_html(markdown_text: str) -> str:
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<title>Node sheets</title><style>body{font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;"
            "max-width:1000px;margin:0 auto;padding:24px;color:#111}h1{font-size:22px}"
            "h2{font-size:16px;margin-top:26px;border-bottom:1px solid #dde3ea;padding-bottom:4px}"
            "code{background:#f2f4f7;padding:1px 4px;border-radius:3px}"
            ".stats{color:#556}.tag{color:#1a4a7a}</style></head><body>\n"
            "<p><em>Generated by <code>scripts/render_node_sheets.py</code>. The markdown owner is "
            "<code>docs/scan/node-sheets.md</code>.</em></p>\n"
            + render_markdown_body(markdown_text) + "\n</body></html>\n")


def render_markdown_body(markdown_text: str) -> str:
    out: list[str] = []
    table: list[str] = []

    def flush() -> None:
        if not table:
            return
        rows = []
        for index, line in enumerate(table):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if index == 1 and all(set(cell) <= {"-"} for cell in cells):
                continue
            tag = "th" if index == 0 else "td"
            rows.append("<tr>" + "".join(f"<{tag}>{inline(cell)}</{tag}>" for cell in cells) + "</tr>")
        out.append("<table>" + "".join(rows) + "</table>")
        table.clear()

    for line in markdown_text.splitlines():
        if line.startswith("|"):
            table.append(line)
            continue
        flush()
        if line.startswith("# "):
            out.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("### "):
            out.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.strip() == "":
            out.append("")
        else:
            out.append(f"<p>{inline(line)}</p>")
    flush()
    return "\n".join(out)


def inline(text: str) -> str:
    escaped = html.escape(text)
    while "**" in escaped:
        escaped = escaped.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
    if escaped.startswith("*") and escaped.endswith("*") and len(escaped) > 2:
        escaped = "<em>" + escaped[1:-1] + "</em>"
    return escaped


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(MANIFEST),
                        help="manifest to render; use a committed export to avoid a dirty tree")
    args = parser.parse_args()
    registry, manifest, ledger = load(REGISTRY), load(Path(args.manifest)), load(LEDGER)
    crosswalk = load(CROSSWALK)
    problems = validate(registry, manifest, ledger, crosswalk)
    if problems:
        print("node sheets: invalid ledger")
        for problem in problems:
            print(f"  PROBLEM: {problem}")
        return 1
    markdown_text = build_markdown(registry, manifest, ledger, crosswalk)
    MARKDOWN.write_text(markdown_text)
    HTML.write_text(build_html(markdown_text))
    measured = {row["node"] for row in ledger}
    print(f"wrote {MARKDOWN.relative_to(ROOT)} ({len(markdown_text):,} chars) and "
          f"{HTML.relative_to(ROOT)}")
    print(f"measured layer: {len(registry)} nodes, {sum(1 for node in registry if node['id'] in measured)} "
          f"with a ledger row")
    print(f"ledger rows: {len(ledger)}; manifest: "
          f"{sum(1 for node in manifest if node.get('kind') == 'node')} nodes, "
          f"{sum(1 for edge in manifest if edge.get('kind') == 'edge')} edges")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
