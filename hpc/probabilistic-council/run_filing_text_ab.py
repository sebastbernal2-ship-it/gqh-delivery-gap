#!/usr/bin/env python3
"""Run the declared text-versus-metadata A/B on the four-firm filing panel.

Protocol: docs/plan/filing-specialist.md, text section. The frozen encoder runs in the ignored
`.venv-text` environment; the comparison itself is pure NumPy. Development only.

    .venv-text/bin/python hpc/probabilistic-council/run_filing_text_ab.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.panel import FEATURES, FLAG_FEATURES  # noqa: E402
from filing_specialist.text_ab import DEFAULT_COMPONENTS, three_way  # noqa: E402

MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def load_examples(path: Path) -> dict[str, str]:
    out = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        out[record["accession"]] = record["context"]
    return out


def embed(contexts: list[str]) -> np.ndarray:
    import torch
    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    encoder = AutoModel.from_pretrained(MODEL)
    encoder.eval()
    vectors = []
    with torch.no_grad():
        for start in range(0, len(contexts), 8):
            batch = tokenizer(contexts[start:start + 8], padding=True, truncation=True,
                              max_length=512, return_tensors="pt")
            hidden = encoder(**batch).last_hidden_state
            mask = batch["attention_mask"].unsqueeze(-1)
            pooled = (hidden * mask).sum(1) / mask.sum(1).clamp_min(1)
            vectors.append(pooled.numpy())
    return np.vstack(vectors)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path,
                        default=ROOT / "results" / "filing-specialist-events.csv")
    parser.add_argument("--examples", type=Path,
                        default=ROOT / "results" / "edgar-cache" / "filing-examples.jsonl")
    parser.add_argument("--embeddings", type=Path,
                        default=ROOT / "results" / "edgar-cache" / "filing-text-embeddings.npy")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results" / "filing-text-ab.json")
    parser.add_argument("--split", type=float, default=0.7)
    parser.add_argument("--components", type=int, default=DEFAULT_COMPONENTS)
    args = parser.parse_args()

    rows = list(csv.DictReader(args.panel.open()))
    examples = load_examples(args.examples)
    contexts = []
    kept = []
    for row in rows:
        context = examples.get(row["filing_accession"])
        if context:
            kept.append(row)
            contexts.append(context)
    if len(kept) != len(rows):
        raise SystemExit(f"{len(rows) - len(kept)} panel rows have no context; rebuild the examples")
    if args.embeddings.exists():
        embeddings = np.load(args.embeddings)
    else:
        embeddings = embed(contexts)
        args.embeddings.parent.mkdir(parents=True, exist_ok=True)
        np.save(args.embeddings, embeddings)
    if embeddings.shape[0] != len(kept):
        raise SystemExit("the cached embeddings do not match the panel; delete the cache")

    report = three_way(kept, FEATURES + FLAG_FEATURES, embeddings, fraction=args.split,
                       components=args.components)
    report.update({
        "schema": "filing-text-ab-v1",
        "scope": "development_only",
        "protocol": "docs/plan/filing-specialist.md",
        "encoder": MODEL,
        "rows": len(kept),
        "ready_for_performance_claim": False,
        "limitations": [
            "81 labels, PWR dominated; an A/B here cannot establish general text value",
            "text is reduced to the declared components with training-only PCA",
            "the encoder is frozen; nothing in it was fitted on this task",
        ],
    })
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"rows": report["rows"], "split": report["split"],
                      "prevalence": report["prevalence"],
                      "metadata_only": report["metadata_only"],
                      "text_only": report["text_only"],
                      "metadata_and_text": report["metadata_and_text"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
