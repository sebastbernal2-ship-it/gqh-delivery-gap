#!/usr/bin/env python3
"""The council as the combiner of the two evidence blocks.

Protocol: docs/plan/filing-council.md. Metadata and text each become a specialist; the council
calibrates, gates and pools them on small chronological blocks and is scored on the final block.

    python3 scripts/run_filing_council.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "hpc" / "probabilistic-council"))
from filing_council import as_matrix, evaluate_council, four_way  # noqa: E402
from filing_specialist.model import fill_missing  # noqa: E402
from filing_specialist.panel import FEATURES, FLAG_FEATURES  # noqa: E402
from filing_specialist.text_ab import DEFAULT_COMPONENTS, pca_apply, pca_fit  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path,
                        default=ROOT / "results" / "filing-specialist-events.csv")
    parser.add_argument("--embeddings", type=Path,
                        default=ROOT / "results" / "edgar-cache" / "filing-text-embeddings.npy")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results" / "filing-council-ab.json")
    parser.add_argument("--components", type=int, default=DEFAULT_COMPONENTS)
    parser.add_argument("--steps", type=int, default=600)
    args = parser.parse_args()

    rows = list(csv.DictReader(args.panel.open()))
    embeddings = np.load(args.embeddings)
    if embeddings.shape[0] != len(rows):
        raise SystemExit("the cached embeddings do not match the panel; rerun the text A/B")
    features = FEATURES + FLAG_FEATURES
    metadata = as_matrix([[fill_missing(row.get(name)) for name in features] for row in rows])

    blocks = four_way(list(rows))
    training_count = len(blocks[0])
    center, projection = pca_fit(embeddings[:training_count], args.components)
    text = pca_apply(embeddings, center, projection)

    report = evaluate_council(blocks, metadata, text, features, steps=args.steps)
    report.update({
        "schema": "filing-council-ab-v1",
        "scope": "development_only",
        "protocol": "docs/plan/filing-council.md",
        "rows": len(rows),
        "components": args.components,
        "ready_for_performance_claim": False,
        "limitations": [
            "81 labels, PWR dominated; the three council blocks hold eight rows each",
            "the block specialists are fitted on 34 rows and the council on 24",
            "development only, both sealed windows spent, no returns or costs",
        ],
    })
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({key: report[key] for key in
                      ("blocks", "prevalence", "metadata_only", "text_only", "concatenated",
                       "council", "specialists")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
