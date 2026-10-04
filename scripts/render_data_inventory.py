#!/usr/bin/env python3
"""Render the data inventory: every dataset, its source, coverage and what it measures.

    python3 scripts/render_data_inventory.py
"""
from __future__ import annotations

import collections
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN = ROOT / "docs" / "scan"
OUT_MD = SCAN / "data-inventory.md"
OUT_HTML = SCAN / "data-inventory.html"


def human(size: float | None) -> str:
    if not size:
        return ""
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def main() -> int:
    entries = [json.loads(line) for line in (SCAN / "datasets.jsonl").open() if line.strip()]
    summary = json.loads((SCAN / "data-inventory-summary.json").read_text())
    curated = [entry for entry in entries if entry.get("coverage")]
    curated.sort(key=lambda entry: entry.get("source", ""))
    auto = [entry for entry in entries if not entry.get("coverage")]
    by_source = collections.defaultdict(list)
    for entry in entries:
        by_source[entry.get("source", "unknown")].append(entry)

    md = ["# Data inventory", "",
          f"Every dataset this repository has looked at: **{summary['datasets']}** entries, "
          f"**{human(summary['total_bytes'])}** on disk, {summary['with_coverage']} with coverage notes and "
          f"{summary['with_measures']} wired to the graph nodes they measure.", "",
          "| Source | Datasets |", "|---|---|"]
    for source, group in sorted(by_source.items(), key=lambda item: -len(item[1])):
        md.append(f"| `{source}` | {len(group)} |")
    md += ["", "## The sets that matter, with coverage", "",
           "| Dataset | Source | Coverage | Rows | Measures | Notes |", "|---|---|---|---|---|---|"]
    for entry in curated:
        md.append(f"| `{entry['path']}` | {entry.get('source', '')} | {entry.get('coverage', '')} | "
                  f"{entry.get('rows') or ''} | {', '.join(f'`{m}`' for m in entry.get('measures', []))} | "
                  f"{entry.get('notes', '')} |")
    md += ["", "## Everything else in hand", "",
           "| Dataset | Path | Rows | Kind |", "|---|---|---|---|"]
    for entry in sorted(auto, key=lambda item: item["id"]):
        md.append(f"| `{entry['id'].split('dataset:')[1]}` | `{entry.get('path', '')}` | "
                  f"{entry.get('rows') or ''} | {entry.get('kind', '')} |")
    OUT_MD.write_text("\n".join(md))

    def rows_html(rows: list[list[str]]) -> str:
        return "".join("<tr>" + "".join(f"<td>{html.escape(cell or '')}</td>" for cell in row) + "</tr>"
                       for row in rows)

    OUT_HTML.write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Data inventory</title>
<style>
 body{{font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;padding:2rem;background:#0e1116;color:#e6edf3}}
 main{{max-width:1350px;margin:0 auto}} h1{{font-size:1.6rem}} h2{{font-size:1.2rem;margin-top:2rem}}
 code{{background:#161b22;padding:.1rem .25rem;border-radius:4px;font-size:.85em}}
 table{{border-collapse:collapse;width:100%;font-size:.78rem;margin-top:.5rem}}
 th,td{{border:1px solid #30363d;padding:.3rem .45rem;vertical-align:top;text-align:left}} th{{background:#161b22}}
 .meta{{color:#8b949e}}
</style></head><body><main>
<h1>Data inventory</h1>
<p class="meta">{summary['datasets']} datasets, {human(summary['total_bytes'])} on disk, {summary['with_coverage']} with coverage notes, {summary['with_measures']} wired to graph nodes.</p>
<h2>By source</h2>
<table><thead><tr><th>Source</th><th>Datasets</th></tr></thead><tbody>
{''.join(f"<tr><td>{html.escape(source)}</td><td>{len(group)}</td></tr>" for source, group in sorted(by_source.items(), key=lambda item: -len(item[1])))}
</tbody></table>
<h2>The sets that matter</h2>
<table><thead><tr><th>Dataset</th><th>Source</th><th>Coverage</th><th>Rows</th><th>Measures</th><th>Notes</th></tr></thead><tbody>
{rows_html([[entry['path'], entry.get('source',''), entry.get('coverage',''), str(entry.get('rows') or ''), ', '.join(entry.get('measures', [])), entry.get('notes','')] for entry in curated])}
</tbody></table>
<h2>Everything else in hand</h2>
<table><thead><tr><th>Dataset</th><th>Path</th><th>Rows</th><th>Kind</th></tr></thead><tbody>
{rows_html([[entry['id'].split('dataset:')[1], entry.get('path',''), str(entry.get('rows') or ''), entry.get('kind','')] for entry in sorted(auto, key=lambda item: item['id'])])}
</tbody></table>
</main></body></html>
""")
    print(f"wrote {OUT_MD.relative_to(ROOT)} and {OUT_HTML.relative_to(ROOT)}: {len(curated)} curated, {len(auto)} auto")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
