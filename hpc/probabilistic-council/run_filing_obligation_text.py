#!/usr/bin/env python3
"""Text versus metadata on the four-firm obligation decisions.

Protocol: docs/plan/filing-obligation-panel.md, text section. Each distinct filing document is
embedded once with the frozen encoder in the ignored `.venv-text` environment, then reduced with
training-only PCA and compared three ways on the same chronological split. The every-filing view
reuses each label many times and is reported as a robustness row.

    .venv-text/bin/python hpc/probabilistic-council/run_filing_obligation_text.py
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
sys.path.insert(0, str(ROOT / "scripts"))
from filing_specialist.options import build_context  # noqa: E402
from filing_specialist.text_ab import DEFAULT_COMPONENTS, three_way  # noqa: E402
from run_filing_obligation_panel import FEATURES, prepare  # noqa: E402

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
MAX_CHARS = 1200


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


def contexts_for(rows: list[dict], cache: Path) -> tuple[list[str], list[str]]:
    """One context per distinct accession, in first-appearance order."""
    accessions: list[str] = []
    contexts: list[str] = []
    for row in rows:
        accession = row["filing_accession"]
        if accession in accessions:
            continue
        text_path = cache / f"{accession}.txt"
        if not text_path.exists():
            continue
        text = text_path.read_text(errors="ignore").strip()
        if not text:
            continue
        accessions.append(accession)
        contexts.append(build_context(row, text, max_chars=MAX_CHARS))
    return accessions, contexts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path,
                        default=ROOT / "results" / "filing-obligation-decisions.csv")
    parser.add_argument("--cache", type=Path, default=ROOT / "results" / "edgar-cache")
    parser.add_argument("--embeddings", type=Path,
                        default=ROOT / "results" / "edgar-cache" / "filing-obligation-embeddings.npz")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results" / "filing-obligation-text.json")
    parser.add_argument("--split", type=float, default=0.7)
    parser.add_argument("--components", type=int, default=DEFAULT_COMPONENTS)
    args = parser.parse_args()

    raw = list(csv.DictReader(args.panel.open()))
    covered = [row for row in raw if (args.cache / f"{row['filing_accession']}.txt").exists()]
    deciding_rows = [row for row in covered if row["is_deciding"] == "1"]
    if len(deciding_rows) < 20:
        raise SystemExit("not enough deciding rows with cached text")

    accessions, contexts = contexts_for(covered, args.cache)
    if args.embeddings.exists():
        bundle = np.load(args.embeddings, allow_pickle=True)
        if list(bundle["accessions"]) != accessions:
            raise SystemExit("the cached embeddings do not match the accessions; delete the cache")
        vectors = bundle["vectors"]
    else:
        vectors = embed(contexts)
        args.embeddings.parent.mkdir(parents=True, exist_ok=True)
        np.savez(args.embeddings, accessions=np.array(accessions), vectors=vectors)
    index = {accession: position for position, accession in enumerate(accessions)}

    def build(rows: list[dict]) -> tuple[list[dict], np.ndarray]:
        prepared = [prepare(row) for row in rows]
        matrix = np.vstack([vectors[index[row["filing_accession"]]] for row in rows])
        return prepared, matrix

    deciding, deciding_text = build(deciding_rows)
    every, every_text = build(covered)
    report = {
        "schema": "filing-obligation-text-v1",
        "scope": "development_only",
        "protocol": "docs/plan/filing-obligation-panel.md",
        "encoder": MODEL,
        "documents_embedded": len(accessions),
        "components": args.components,
        "deciding_filing": three_way(deciding, FEATURES, deciding_text, fraction=args.split,
                                     components=args.components),
        "every_filing": three_way(every, FEATURES, every_text, fraction=args.split,
                                  components=args.components),
        "ready_for_performance_claim": False,
        "limitations": [
            "PWR and ETN only; the deciding view has 87 rows over about 50 distinct periods",
            "the every-filing view reuses each label many times and is a robustness row only",
            "frozen encoder, training-only PCA, no returns and no costs",
        ],
    }
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    for view in ("deciding_filing", "every_filing"):
        block = report[view]
        print(view, "train/test", block["split"]["train_rows"], block["split"]["test_rows"])
        for name in ("prevalence", "metadata_only", "text_only", "metadata_and_text"):
            metrics = block[name]
            print("  %-18s log %.4f brier %.4f acc %.3f" % (
                name, metrics["log_loss"], metrics["brier"], metrics["accuracy"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
