#!/usr/bin/env python3
"""Validate the thesis ledger: docs/theses/index.jsonl.

One line per thesis. Appending a line is conflict free, which is what lets several people
move the idea at once without editing one shared document.

Exit 1 on any problem. `make check` runs it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "docs" / "theses" / "index.jsonl"
REQUIRED = ["id", "title", "status", "owner", "date", "note"]
STATUSES = {"active", "parked", "superseded", "retired"}
# An active thesis carries one section per rubric criterion, so the rubric is a structural
# requirement rather than an aspiration.
SECTIONS = ["Hypothesis", "Data", "Structure", "Methodology", "Results", "Novelty",
            "Risk", "Liquidity"]


def missing_sections(note_text: str) -> list[str]:
    """Required section headings absent from a thesis record."""
    headings = [line.lstrip("#").strip().lower() for line in note_text.splitlines()
                if line.strip().startswith("#")]
    out = []
    for section in SECTIONS:
        target = section.lower()
        if not any(target in heading for heading in headings):
            out.append(section)
    return out


def validate_records(records, notes_exist: bool = True, root: Path | None = None,
                     note_texts: dict | None = None) -> list[str]:
    """Return a list of problems. Empty means valid."""
    root = root or ROOT
    errors: list[str] = []
    ids: set[str] = set()

    for i, rec in enumerate(records, 1):
        label = rec.get("id") or f"line {i}"
        if not isinstance(rec, dict):
            errors.append(f"line {i}: not an object")
            continue
        for key in REQUIRED:
            if not rec.get(key):
                errors.append(f"{label}: missing '{key}'")
        status = rec.get("status")
        if status and status not in STATUSES:
            errors.append(f"{label}: status '{status}' is not one of {sorted(STATUSES)}")
        if status == "active":
            if not rec.get("falsifiers"):
                errors.append(f"{label}: an active thesis needs at least one falsifier")
            if not rec.get("owner"):
                errors.append(f"{label}: an active thesis needs an owner")
        rid = rec.get("id")
        if rid:
            if rid in ids:
                errors.append(f"{label}: duplicate id")
            ids.add(rid)

    for i, rec in enumerate(records, 1):
        if not isinstance(rec, dict):
            continue
        label = rec.get("id") or f"line {i}"
        for parent in rec.get("supersedes", []) or []:
            if parent not in ids:
                errors.append(f"{label}: supersedes unknown id '{parent}'")

    texts = dict(note_texts or {})
    for rec in records:
        if not isinstance(rec, dict):
            continue
        note = rec.get("note")
        if not note:
            continue
        if notes_exist and not (root / note).exists():
            errors.append(f"{rec.get('id')}: note file '{note}' does not exist")
        if rec.get("status") != "active":
            continue
        text = texts.get(note)
        if text is None and (root / note).exists():
            text = (root / note).read_text(errors="ignore")
        if text is None:
            continue
        absent = missing_sections(text)
        if absent:
            errors.append(f"{rec.get('id')}: active thesis record is missing section(s) "
                          f"{', '.join(absent)}. See docs/theses/TEMPLATE.md")
    return errors


def load_index(path: Path | None = None) -> list[dict]:
    path = path or INDEX
    if not path.exists():
        return []
    out = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as exc:
            out.append({"_bad_line": i, "_error": str(exc)})
    return out


def main() -> int:
    if not INDEX.exists():
        print("no thesis ledger yet (docs/theses/index.jsonl)")
        return 0
    records = load_index()
    errors = validate_records(records, notes_exist=True)
    print(f"thesis ledger: {len(records)} record(s)")
    if errors:
        for problem in errors:
            print(f"  PROBLEM: {problem}")
        return 1
    active = [r for r in records if r.get("status") == "active"]
    print(f"  active: {len(active)}, parked: "
          f"{len([r for r in records if r.get('status') == 'parked'])}, "
          f"superseded: {len([r for r in records if r.get('status') == 'superseded'])}, "
          f"retired: {len([r for r in records if r.get('status') == 'retired'])}")
    print("  ledger valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
