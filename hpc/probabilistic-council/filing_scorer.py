#!/usr/bin/env python3
"""Score the JevLike text specialist on the filing panel against the metadata baseline.

Protocol: docs/plan/filing-specialist.md. Development only: 81 labels, one issuer dominates, and
both competition windows are spent. The split is the same chronological split the metadata
baseline used, so the comparison is exact.

    python3 filing_scorer.py --examples <jsonl> --panel ../../results/filing-specialist-events.csv \
      --output ../../results/filing-text-scores.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as torch_softmax

COUNCIL = Path(__file__).resolve().parent
ROOT = COUNCIL.parents[1]
sys.path.insert(0, str(COUNCIL))
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.model import (apply_scaler, chronological_split, fit_scaler,  # noqa: E402
                                     fit_softmax, matrix_from_rows, predict_softmax,
                                     prevalence, score)
from filing_specialist.panel import FEATURES, FLAG_FEATURES  # noqa: E402
from jevlike.data import ByteCollator, validate  # noqa: E402
from jevlike.model import make_system  # noqa: E402
from jevlike.train import move  # noqa: E402

CONFIG = {"encoder": "tiny", "width": 64, "rank": 64, "context_tokens": 192, "option_tokens": 32}
DEFAULT_HF_MODEL = "prajjwal1/bert-tiny"


def make_config(encoder: str = "tiny", hf_model: str = DEFAULT_HF_MODEL) -> dict:
    config = dict(CONFIG)
    config["encoder"] = encoder
    config["hf_model"] = hf_model
    return config


def hf_revision(model: str, cache: Path | None = None) -> str | None:
    """The cached snapshot commit for a model name, so a run names its exact weights."""
    cache = cache or Path.home() / ".cache" / "huggingface" / "hub"
    ref = cache / ("models--" + model.replace("/", "--")) / "refs" / "main"
    if ref.exists():
        value = ref.read_text().strip()
        return value or None
    snapshots = cache / ("models--" + model.replace("/", "--")) / "snapshots"
    if snapshots.exists():
        names = sorted(path.name for path in snapshots.iterdir() if path.is_dir())
        return names[-1] if names else None
    return None


def load_examples(path: Path) -> tuple[list, list]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return [validate(row) for row in rows], [row.get("accession") for row in rows]


def load_panel(path: Path) -> list[dict]:
    import csv
    return list(csv.DictReader(path.open()))


def train_model(examples: list, epochs: int, seed: int, config: dict, batch_size: int = 16,
                learning_rate: float = 2e-3) -> tuple:
    torch.manual_seed(seed)
    device = torch.device("cpu")
    model, collator = make_system(config, device)
    parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    optimiser = torch.optim.AdamW(parameters, lr=learning_rate, weight_decay=1e-4)
    generator = torch.Generator().manual_seed(seed)
    trajectory = []
    for epoch in range(epochs):
        order = torch.randperm(len(examples), generator=generator).tolist()
        model.train()
        total = 0.0
        count = 0
        for start in range(0, len(order), batch_size):
            chunk = [examples[index] for index in order[start:start + batch_size]]
            batch = move(collator(chunk), device)
            loss = torch.nn.functional.cross_entropy(model(batch), batch["labels"])
            optimiser.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(parameters, 1.0)
            optimiser.step()
            total += float(loss.detach()) * batch["labels"].numel()
            count += batch["labels"].numel()
        trajectory.append(total / count)
    return model, collator, device, trajectory


def predict(model, collator, device, examples: list) -> np.ndarray:
    model.eval()
    with torch.no_grad():
        batch = move(collator(examples), device)
        probabilities = torch_softmax.softmax(model(batch), dim=-1)
    return probabilities.cpu().numpy()


def run(examples: list, baseline_split: tuple | None, fraction: float, epochs: int,
        seed: int, config: dict | None = None) -> dict:
    config = dict(config) if config else dict(CONFIG)
    if baseline_split is not None:
        train_rows, test_rows = baseline_split
        if len(train_rows) + len(test_rows) != len(examples):
            raise ValueError("the panel split and the examples disagree on the row count")
        split = len(train_rows)
    else:
        test_rows = None
        split = max(1, min(len(examples) - 1, int(round(len(examples) * fraction))))
    train_examples, test_examples = examples[:split], examples[split:]
    model, collator, device, trajectory = train_model(train_examples, epochs, seed, config)
    probabilities = predict(model, collator, device, test_examples)
    labels = np.array([example.label for example in test_examples], dtype=int)
    classes = tuple(sorted({example.label for example in train_examples}))
    encoder_info = {"parameters": int(sum(parameter.numel() for parameter in model.parameters())),
                    "trainable": int(sum(parameter.numel() for parameter in model.parameters()
                                        if parameter.requires_grad))}
    if config.get("encoder") == "hf":
        encoder_info["model"] = config.get("hf_model")
        encoder_info["revision"] = hf_revision(config.get("hf_model", ""))
    report = {
        "split": {"train": len(train_examples), "test": len(test_examples),
                  "classes": list(classes), "fraction": fraction},
        "config": config, "encoder_info": encoder_info, "epochs": epochs, "seed": seed,
        "train_nll_trajectory": [round(value, 6) for value in trajectory],
        "text": score(probabilities, labels, classes),
    }
    if test_rows is not None:
        report["prevalence"] = score(np.tile(prevalence(train_rows, classes), (len(labels), 1)),
                                     labels, classes)
        train_matrix, train_labels = matrix_from_rows(train_rows, FEATURES + FLAG_FEATURES)
        stats = fit_scaler(train_matrix)
        parameters = fit_softmax(apply_scaler(train_matrix, stats), train_labels, classes)
        test_matrix, test_labels = matrix_from_rows(test_rows, FEATURES + FLAG_FEATURES)
        report["metadata_softmax"] = score(predict_softmax(parameters, apply_scaler(test_matrix, stats)),
                                           test_labels, classes)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--examples", type=Path, required=True)
    parser.add_argument("--panel", type=Path,
                        default=ROOT / "results" / "filing-specialist-events.csv")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results" / "filing-text-scores.json")
    parser.add_argument("--split", type=float, default=0.7)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20261004)
    parser.add_argument("--encoder", choices=("tiny", "hf"), default="tiny")
    parser.add_argument("--hf-model", default=DEFAULT_HF_MODEL)
    args = parser.parse_args()

    examples, accessions = load_examples(args.examples)
    panel = load_panel(args.panel)
    covered = [row for row in panel if row.get("filing_accession") in set(accessions)]
    if len(covered) != len(examples):
        raise SystemExit("the panel and the examples disagree; rebuild the examples")
    train_rows, test_rows = chronological_split(covered, args.split)
    report = run(examples, (train_rows, test_rows), args.split, args.epochs, args.seed,
                 make_config(args.encoder, args.hf_model))
    report.update({
        "schema": "filing-text-comparison-v1",
        "scope": "development_only",
        "protocol": "docs/plan/filing-specialist.md",
        "examples": str(args.examples),
        "ready_for_performance_claim": False,
        "limitations": [
            "81 labels, PWR dominated, three of four candidate firms have no obligations",
            f"{args.encoder} encoder on {report['split']['train']} training rows, "
            f"{args.epochs} declared epochs",
            "the excerpt is a 1200 character window; a missing document is a recorded skip",
        ],
    })
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"split": report["split"], "text": report["text"],
                      "prevalence": report.get("prevalence"),
                      "metadata_softmax": report.get("metadata_softmax")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
