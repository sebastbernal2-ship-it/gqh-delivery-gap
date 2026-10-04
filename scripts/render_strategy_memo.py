#!/usr/bin/env python3
"""Render the strategy memo to the site.

A small markdown subset renderer: headings, tables, lists, bold, code spans, and paragraphs. Enough for
the memo, and no dependency.

    python3 scripts/render_strategy_memo.py
"""
from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "plan" / "strategy-memo.md"
OUT = ROOT / "docs" / "scan" / "strategy-memo.html"


def inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return text


def main() -> int:
    lines = SOURCE.read_text().splitlines()
    body: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("|"):
            header = [cell.strip() for cell in line.strip("|").split("|")]
            index += 2
            rows = []
            while index < len(lines) and lines[index].startswith("|"):
                rows.append([cell.strip() for cell in lines[index].strip("|").split("|")])
                index += 1
            body.append("<table><thead><tr>" + "".join(f"<th>{inline(cell)}</th>" for cell in header)
                        + "</tr></thead><tbody>"
                        + "".join("<tr>" + "".join(f"<td>{inline(cell)}</td>" for cell in row) + "</tr>"
                                  for row in rows) + "</tbody></table>")
            continue
        if line.startswith("### "):
            body.append(f"<h3>{inline(line[4:])}</h3>")
        elif line.startswith("## "):
            body.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("# "):
            body.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.startswith("- "):
            items = [line[2:]]
            index += 1
            while index < len(lines) and lines[index].startswith("  "):
                items.append(lines[index].strip())
                index += 1
            index -= 1
            body.append("<ul>" + "".join(f"<li>{inline(item)}</li>" for item in items) + "</ul>")
        elif re.match(r"^\d+\. ", line):
            items = [re.sub(r"^\d+\. ", "", line)]
            index += 1
            while index < len(lines) and re.match(r"^\d+\. ", lines[index]):
                items.append(re.sub(r"^\d+\. ", "", lines[index]))
                index += 1
            index -= 1
            body.append("<ol>" + "".join(f"<li>{inline(item)}</li>" for item in items) + "</ol>")
        elif not line.strip():
            pass
        else:
            body.append(f"<p>{inline(line)}</p>")
        index += 1
    OUT.write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Strategy memo</title>
<style>
 body{{font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;padding:2.2rem;background:#0e1116;color:#e6edf3}}
 main{{max-width:1050px;margin:0 auto}} h1{{font-size:1.7rem}} h2{{font-size:1.25rem;margin-top:2.2rem;border-top:1px solid #232b3a;padding-top:1rem}}
 h3{{font-size:1.02rem;margin-top:1.5rem;color:#c9d1d9}}
 code{{background:#161b22;padding:.1rem .3rem;border-radius:4px;font-size:.86em}}
 table{{border-collapse:collapse;width:100%;font-size:.84rem;margin:1rem 0}}
 th,td{{border:1px solid #30363d;padding:.35rem .5rem;vertical-align:top;text-align:left}} th{{background:#161b22}}
 p{{margin:.6rem 0}} ul,ol{{margin:.5rem 0 .8rem 1.2rem}} li{{margin:.25rem 0}}
</style></head><body><main>
{chr(10).join(body)}
</main></body></html>
""")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(body)} blocks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
