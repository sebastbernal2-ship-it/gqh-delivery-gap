#!/usr/bin/env python3
"""Tests for the thesis ledger: the thing that lets the idea change without a rewrite.

Run: python3 tests/test_thesis_index.py

The idea is expected to move. So there is no single idea document that must be kept
current. Instead there is a ledger: one line per thesis, each with a status, a falsifier,
and a pointer to its own file. The ledger is validated, and the human-readable "current
position" is generated from it, so the summary can never drift from the records.

Rules:
  required      id, title, status, owner, date, note
  status        one of active, parked, superseded, retired
  active        must carry at least one falsifier and an owner
  supersedes    every referenced id must exist in the ledger
  note          the file it points at must exist
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_theses import missing_sections, validate_records  # noqa: E402


def record(**over):
    base = {
        "id": "t-delivery-gap",
        "title": "Announced capacity is not energized capacity",
        "status": "active",
        "owner": "sebastbernal2-ship-it",
        "date": "2026-10-03",
        "note": "docs/theses/t-delivery-gap.md",
        "falsifiers": ["regional transport cost does not predict the relative return"],
        "evidence": ["results/example.json"],
    }
    base.update(over)
    return base


def main() -> int:
    failures = []

    def check(name, errors, expect_empty=True):
        got = len(errors) == 0
        if got != expect_empty:
            failures.append(name)
            print(f"FAIL {name}: {errors}")
        else:
            print(f"ok   {name}")

    check("a complete active record passes", validate_records([record()], notes_exist=False))
    check("missing id fails", validate_records([{k: v for k, v in record().items() if k != "id"}],
                                               notes_exist=False), expect_empty=False)
    check("unknown status fails", validate_records([record(status="maybe")],
                                                   notes_exist=False), expect_empty=False)
    check("active with no falsifier fails", validate_records([record(falsifiers=[])],
                                                             notes_exist=False), expect_empty=False)
    check("active with no owner fails", validate_records([record(owner="")],
                                                         notes_exist=False), expect_empty=False)
    check("duplicate id fails", validate_records([record(), record()],
                                                 notes_exist=False), expect_empty=False)
    check("supersedes a missing id fails",
          validate_records([record(supersedes=["t-nope"])], notes_exist=False), expect_empty=False)
    check("supersedes an existing id passes",
          validate_records([record(id="t-old", status="superseded", falsifiers=[]),
                            record(supersedes=["t-old"])], notes_exist=False))
    check("parked needs no falsifier",
          validate_records([record(status="parked", falsifiers=[])], notes_exist=False))
    check("missing note file fails",
          validate_records([record(note="docs/theses/does-not-exist.md")], notes_exist=True),
          expect_empty=False)

    # An active thesis record follows the Investment Proposal shape, so a reader and a judge
    # both know where to look. Non-active records are exempt.
    def check_eq(name, got, want):
        if got != want:
            failures.append(name)
            print(f"FAIL {name}: got {got!r} want {want!r}")
        else:
            print(f"ok   {name}")

    check_eq("a complete record has no missing sections",
             missing_sections("## Hypothesis\nx\n## Data\ny\n## Methodology\nz\n## Results\nw"), [])
    check_eq("a missing section is named",
             missing_sections("## Hypothesis\nx\n## Data\ny"), ["Methodology", "Results"])
    check_eq("headings are matched case insensitively and with numbering",
             missing_sections("## 1. hypothesis\n## 2. DATA\n## 3. Methodology\n## 4. Results"), [])
    check("an active thesis with a note missing sections fails the ledger",
          validate_records([record()], notes_exist=False,
                           note_texts={"docs/theses/t-delivery-gap.md": "## Hypothesis\nonly"}),
          expect_empty=False)
    check("a non-active thesis is exempt from the sections",
          validate_records([record(status="parked", falsifiers=[])], notes_exist=False,
                           note_texts={"docs/theses/t-delivery-gap.md": "## Hypothesis\nonly"}),
          )

    print(f"\n{15 - len(failures)}/15 passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
