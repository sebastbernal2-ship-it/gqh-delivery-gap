#!/usr/bin/env python3
"""Render the graded connection chains and compute each chain's greatest assumption.

Validates every chain against the schema in docs/plan/deep-connections.md, checks that anchor nodes
exist in the manifest, computes the greatest assumption as the highest-load link with the weakest
evidence class, and writes docs/scan/connection-chains.md and .html.

    python3 scripts/render_connection_chains.py
"""
from __future__ import annotations

import argparse
import collections
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHAINS = ROOT / "docs" / "scan" / "connection-chains.jsonl"
CANDIDATES = ROOT / "docs" / "scan" / "connection-chain-candidates.json"
OUT_MD = ROOT / "docs" / "scan" / "connection-chains.md"
OUT_HTML = ROOT / "docs" / "scan" / "connection-chains.html"
EVIDENCE_ORDER = {"E1": 0, "E2": 1, "E3": 2, "E4": 3}
LOAD_ORDER = {"high": 0, "medium": 1, "low": 2}
KINDS = {"constraint", "causal", "accounting", "behavioral", "associative"}
CEILINGS = {"testable", "watch"}


def greatest_link(links: list[dict]) -> int:
    """Highest load first, weakest evidence second, earlier link wins ties."""
    ranked = sorted(range(len(links)), key=lambda i: (LOAD_ORDER[links[i]["load"]],
                                                      EVIDENCE_ORDER[links[i]["evidence"]], i))
    return ranked[0]


def validate(chain: dict, node_ids: set[str]) -> list[str]:
    problems = []
    for field in ("id", "title", "anchor_node", "outcome_node", "payer", "ceiling", "links"):
        if not chain.get(field):
            problems.append(f"{chain.get('id', '?')}: missing {field}")
    if chain.get("ceiling") not in CEILINGS:
        problems.append(f"{chain.get('id')}: bad ceiling {chain.get('ceiling')}")
    proposed = {node["id"] for node in chain.get("nodes_to_add", [])}
    for endpoint in ("anchor_node", "outcome_node"):
        value = chain.get(endpoint)
        if value and value not in node_ids and value not in proposed:
            problems.append(f"{chain.get('id')}: {endpoint} {value} is not in the manifest")
    for index, link in enumerate(chain.get("links", [])):
        where = f"{chain.get('id')} link {index + 1}"
        for field in ("claim", "kind", "evidence", "load", "assumption", "kill"):
            if not link.get(field):
                problems.append(f"{where}: missing {field}")
        if link.get("kind") not in KINDS:
            problems.append(f"{where}: bad kind {link.get('kind')}")
        if link.get("evidence") not in EVIDENCE_ORDER:
            problems.append(f"{where}: bad evidence {link.get('evidence')}")
        if link.get("load") not in LOAD_ORDER:
            problems.append(f"{where}: bad load {link.get('load')}")
        if link.get("kind") == "associative" and link.get("load") != "low":
            problems.append(f"{where}: associative links are capped at low load")
    return problems


def md_escape(text: str) -> str:
    return str(text).replace("|", "\\|").strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(ROOT / "docs" / "scan" / "quantgraph.jsonl"))
    parser.add_argument("--chains", default=str(CHAINS))
    args = parser.parse_args()
    node_ids = set()
    for line in Path(args.manifest).open():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("kind") == "node":
            node_ids.add(row["id"])
    chains = []
    problems = []
    for line in Path(args.chains).open():
        if not line.strip():
            continue
        chain = json.loads(line)
        chain["greatest_link"] = greatest_link(chain["links"])
        problems.extend(validate(chain, node_ids))
        chains.append(chain)
    if problems:
        for problem in problems:
            print(f"schema problem: {problem}")
        raise SystemExit(f"{len(problems)} schema problems; nothing rendered")
    chains.sort(key=lambda chain: (chain["ceiling"] != "testable", chain["id"]))
    evidence_counts = collections.Counter(link["evidence"] for chain in chains for link in chain["links"])
    load_counts = collections.Counter(link["load"] for chain in chains for link in chain["links"])
    kind_counts = collections.Counter(link["kind"] for chain in chains for link in chain["links"])

    lines = ["# Connection chains, graded", "",
             "Method owner: `docs/plan/deep-connections.md`. Every link carries its evidence class, its",
             "load and the kill test that would show it wrong. The greatest assumption is computed, not",
             "declared: the highest-load link with the weakest evidence class.", "",
             f"Chains: {len(chains)}. Links: {sum(len(c['links']) for c in chains)}. "
             f"Evidence: {', '.join(f'{k} {v}' for k, v in sorted(evidence_counts.items()))}. "
             f"Loads: {', '.join(f'{k} {v}' for k, v in sorted(load_counts.items()))}.", "",
             "| Chain | Ceiling | Payer | Greatest assumption |", "|---|---|---|---|"]
    for chain in chains:
        link = chain["links"][chain["greatest_link"]]
        lines.append(f"| `{chain['id']}` | {chain['ceiling']} | {md_escape(chain['payer'])} | "
                     f"{md_escape(link['assumption'])} |")
    lines.append("")
    for chain in chains:
        lines += [f"## {chain['title']}", "",
                  f"`{chain['id']}` · anchor `{chain['anchor_node']}` · outcome `{chain['outcome_node']}` · "
                  f"ceiling **{chain['ceiling']}**", "",
                  f"**Payer.** {chain['payer']}", "",
                  f"**Why now.** {chain['why_now']}", ""]
        if chain.get("nodes_to_add"):
            added = ", ".join(f"`{node['id']}` ({node['layer']})" for node in chain["nodes_to_add"])
            lines += [f"**Nodes proposed.** {added}", ""]
        lines += ["| # | Link | Kind | Evidence | Load | Assumption | Kill test |", "|---|---|---|---|---|---|---|"]
        for index, link in enumerate(chain["links"], start=1):
            marker = " **greatest**" if index - 1 == chain["greatest_link"] else ""
            lines.append(f"| {index}{marker} | {md_escape(link['claim'])} | {link['kind']} | "
                         f"{link['evidence']} | {link['load']} | {md_escape(link['assumption'])} | "
                         f"{md_escape(link['kill'])} |")
        lines.append("")
        if chain.get("source"):
            lines += [f"Source: {chain['source']}", ""]
        g = chain["links"][chain["greatest_link"]]
        lines += [f"**Greatest assumption.** {g['assumption']} ({g['evidence']}, load {g['load']})", "",
                  f"**Kill test.** {g['kill']}", ""]
    OUT_MD.write_text("\n".join(lines) + "\n")

    def html_rows(chain: dict) -> str:
        rows = []
        for index, link in enumerate(chain["links"], start=1):
            marker = " class=\"greatest\"" if index - 1 == chain["greatest_link"] else ""
            rows.append(
                f"<tr{marker}><td>{index}</td><td>{html.escape(link['claim'])}</td>"
                f"<td>{link['kind']}</td><td>{link['evidence']}</td><td>{link['load']}</td>"
                f"<td>{html.escape(link['assumption'])}</td><td>{html.escape(link['kill'])}</td></tr>")
        return "\n".join(rows)

    body = []
    for chain in chains:
        g = chain["links"][chain["greatest_link"]]
        body.append(f"<section><h2>{html.escape(chain['title'])}</h2>"
                    f"<p class=\"meta\"><code>{html.escape(chain['id'])}</code> · "
                    f"anchor <code>{html.escape(chain['anchor_node'])}</code> · "
                    f"outcome <code>{html.escape(chain['outcome_node'])}</code> · "
                    f"ceiling <b>{chain['ceiling']}</b></p>"
                    f"<p><b>Payer.</b> {html.escape(chain['payer'])}</p>"
                    f"<p><b>Why now.</b> {html.escape(chain['why_now'])}</p>"
                    f"<table><thead><tr><th>#</th><th>Link</th><th>Kind</th><th>Evidence</th><th>Load</th>"
                    f"<th>Assumption</th><th>Kill test</th></tr></thead><tbody>{html_rows(chain)}</tbody></table>"
                    f"<p class=\"greatest-note\"><b>Greatest assumption.</b> {html.escape(g['assumption'])} "
                    f"({g['evidence']}, load {g['load']})</p>"
                    f"<p class=\"greatest-note\"><b>Kill test.</b> {html.escape(g['kill'])}</p></section>")
    OUT_HTML.write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Connection chains, graded</title>
<style>
 body{{font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;margin:0;padding:2rem;background:#0e1116;color:#e6edf3}}
 main{{max-width:1100px;margin:0 auto}} h1{{font-size:1.6rem}} h2{{font-size:1.2rem;margin-top:2rem}}
 code{{background:#161b22;padding:.1rem .25rem;border-radius:4px;font-size:.85em}}
 table{{border-collapse:collapse;width:100%;font-size:.85rem;margin-top:.75rem}}
 th,td{{border:1px solid #30363d;padding:.4rem .5rem;vertical-align:top;text-align:left}}
 th{{background:#161b22}} tr.greatest{{background:#1f2a1f}} .meta{{color:#8b949e;font-size:.85rem}}
 .greatest-note{{background:#161b22;padding:.6rem .8rem;border-radius:6px}}
</style></head><body><main>
<h1>Connection chains, graded</h1>
<p>{len(chains)} chains, {sum(len(c['links']) for c in chains)} links. Evidence classes:
{', '.join(f'{k} {v}' for k, v in sorted(evidence_counts.items()))}. The greatest assumption of each chain is
the highest-load link with the weakest evidence class, computed by the renderer.</p>
{''.join(body)}
<p class="meta">Method owner: docs/plan/deep-connections.md</p>
</main></body></html>
""")
    print(f"wrote {OUT_MD.relative_to(ROOT)} and {OUT_HTML.relative_to(ROOT)}")
    print(f"chains {len(chains)}; links {sum(len(c['links']) for c in chains)}; "
          f"testable {sum(1 for c in chains if c['ceiling'] == 'testable')}; "
          f"watch {sum(1 for c in chains if c['ceiling'] == 'watch')}")
    print(f"evidence {dict(sorted(evidence_counts.items()))}; loads {dict(sorted(load_counts.items()))}; "
          f"kinds {dict(kind_counts.most_common())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
