"""Context and option sets for the filing text specialist.

The context carries only what was public at the decision: the filing's own header and an excerpt
of its text. The label's value never enters the context, and a missing document is a recorded
skip, never an empty context.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from .text import excerpt

QUESTION = ("Using only the filing below, what will the next obligation revision for this issuer "
            "and metric show relative to the typical seasonal change?")

OPTIONS = (
    "A large negative surprise: the revision is more than five percent below the typical change.",
    "A small negative surprise: the revision is between one and five percent below the typical change.",
    "No material surprise: the revision is within one percent of the typical change.",
    "A small positive surprise: the revision is between one and five percent above the typical change.",
    "A large positive surprise: the revision is more than five percent above the typical change.",
)


def load_panel(path: Path) -> list[dict]:
    return list(csv.DictReader(path.open()))


def load_text(cache: Path, accession: str) -> str | None:
    path = cache / f"{accession}.txt"
    if not path.exists():
        return None
    text = path.read_text(errors="ignore").strip()
    return text or None


def build_context(row: dict, text: str, max_chars: int = 1200) -> str:
    header = (f"Filing: {row['ticker']} {row['filing_form']} with items "
              f"{row.get('filing_items') or 'none'}, decision {row['decision_time'][:10]}.")
    return (f"{header}\nExcerpt from the filing:\n{excerpt(text, max_chars)}\n"
            f"Question: {QUESTION}")


def write_examples(rows: list[dict], cache: Path, output: Path,
                   max_chars: int = 1200) -> dict:
    output.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    missing = []
    with output.open("w") as handle:
        for row in rows:
            text = load_text(cache, row["filing_accession"])
            if text is None:
                missing.append(row["filing_accession"])
                continue
            handle.write(json.dumps({
                "context": build_context(row, text, max_chars),
                "options": list(OPTIONS),
                "label": int(row["label_bin"]),
                "accession": row["filing_accession"],
            }) + "\n")
            written += 1
    return {"examples": written, "missing_texts": missing, "options": len(OPTIONS),
            "output": str(output)}
