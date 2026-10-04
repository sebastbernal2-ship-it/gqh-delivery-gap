#!/usr/bin/env python3
"""Validate the truth ledger: docs/truths.md

The ledger records what we know about the world, with the evidence behind each claim and the scope
in which it holds. It is added to and corrected, never rewritten, so the rules here keep it
readable and keep its links resolvable:

  structure    every entry is a section "## T<n>. <title>" carrying a Statement, an Evidence, a
               Scope and a Consequence, in that order, none of them empty
  sequence     the ids run T1..Tn with no gap and no repeat, because the ledger grows at the tail
  links        every backticked path an entry cites resolves, and a glob matches at least once

What it cannot check is whether a truth is true, or whether its evidence is sufficient. It only
guarantees that a claim is not recorded without its fields, its scope, or a resolvable link. The
honest limit is stated rather than hidden.

Run by `make check`.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs" / "truths.md"

FIELDS = ("Statement", "Evidence", "Scope", "Consequence")
HEADING = re.compile(r"^##\s+T(\d+)\.\s+(.+?)\s*$")
FIELD = re.compile(r"^\*\*(Statement|Evidence|Scope|Consequence)\*\*:\s*(.*)$")
BACKTICK = re.compile(r"`([^`]+)`")
PATHISH = re.compile(r"[A-Za-z0-9_./-]+/[A-Za-z0-9_./*-]+\.(csv|json|jsonl|md|txt|py|sh|html|pdf)$")
OTHER_HEADING = re.compile(r"^#{1,2}(?!#)\s")


def entries(text: str) -> list[dict]:
    """Split the ledger into one record per truth section."""
    found: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        heading = HEADING.match(line)
        if heading:
            if current:
                found.append(current)
            current = {"number": int(heading.group(1)), "title": heading.group(2), "lines": []}
            continue
        if OTHER_HEADING.match(line):
            if current:
                found.append(current)
                current = None
            continue
        if current is not None:
            current["lines"].append(line)
    if current:
        found.append(current)
    return found


def fields_of(lines: list[str]) -> tuple[dict[str, str], list[str]]:
    values: dict[str, str] = {}
    order: list[str] = []
    current: str | None = None
    for line in lines:
        match = FIELD.match(line)
        if match:
            current = match.group(1)
            values[current] = match.group(2).strip()
            order.append(current)
            continue
        if current and line.strip():
            values[current] = (values[current] + " " + line.strip()).strip()
    return values, order


def repo_exists(token: str) -> bool:
    token = token.strip()
    if "{" in token or "}" in token:
        return True  # brace shorthand is prose, not a literal link
    if "*" in token:
        return any(ROOT.glob(token))
    return (ROOT / token).exists()


def problems(text: str, exists=None) -> list[str]:
    """Return a list of problems. Empty means valid."""
    exists = exists or repo_exists
    out: list[str] = []
    found = entries(text)
    if not found:
        return ["no truth entries: the ledger records nothing"]
    numbers = [entry["number"] for entry in found]
    if len(set(numbers)) != len(numbers):
        repeated = sorted({n for n in numbers if numbers.count(n) > 1})
        out.append("duplicate ids: " + ", ".join(f"T{n}" for n in repeated))
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        out.append(f"ids must run T1..T{len(numbers)} in order, found {numbers}")
    for entry in found:
        label = f"T{entry['number']}"
        values, order = fields_of(entry["lines"])
        if len(set(order)) != len(order):
            out.append(f"{label}: a field is declared twice")
        for name in FIELDS:
            if name not in values:
                out.append(f"{label}: missing {name}")
            elif not values[name]:
                out.append(f"{label}: empty {name}")
        present = [name for name in order if name in FIELDS]
        if present != [name for name in FIELDS if name in values]:
            out.append(f"{label}: fields out of order, found {' '.join(present)}")
        body = "\n".join(entry["lines"])
        for token in BACKTICK.findall(body):
            candidate = token.strip()
            if PATHISH.fullmatch(candidate) and not exists(candidate):
                out.append(f"{label}: cited path does not resolve: {candidate}")
    return out


def main() -> int:
    if not LEDGER.exists():
        print("no truth ledger yet (docs/truths.md)")
        return 0
    text = LEDGER.read_text()
    found = entries(text)
    print(f"truth ledger: {len(found)} entries")
    found_problems = problems(text)
    for problem in found_problems:
        print(f"  PROBLEM: {problem}")
    if found_problems:
        return 1
    print("truth ledger: consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
