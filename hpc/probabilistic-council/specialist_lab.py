"""Synthetic-only, five-block comparison of one JevLike and three feature specialists."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import subprocess
import time

import torch
from torch import nn

from council import CouncilModel, LabeledCase, SpecialistForecast
from council.calibration import fit_temperature
from council.fusion import linear_opinion_pool
from jevlike.data import ChoiceExample
from jevlike.model import make_system, trainable_state
from modular_pilot import metric

FEATURES = ("price_move_z", "oi_change_fraction", "book_imbalance", "spread_bps",
            "realized_vol_bps", "basis_bps")
VIEWS = {"flow": (0, 1), "liquidity": (2, 3), "context": (4, 5)}
OUTCOMES = ("down", "flat", "up")
TARGET = "synthetic-mid-return-75s-bins-minus5-plus5bps-v1"
CONFIG = {"encoder": "tiny", "hf_model": "unused", "width": 16, "rank": 8,
          "context_tokens": 256, "option_tokens": 16}
PARTITIONS = ("training", "specialist_calibration", "gate_fit", "pool_calibration", "evaluation")


@dataclass(frozen=True)
class EventRow:
    case_id: str
    episode_id: str
    instrument: str
    available_at: datetime
    decision_at: datetime
    label_end: datetime
    label_available_at: datetime
    features: tuple[float, ...]
    return_bps: float
    target_id: str = TARGET

    @property
    def label(self):
        return 0 if self.return_bps < -5 else 2 if self.return_bps > 5 else 1

    def validate(self):
        if not self.case_id or not self.episode_id or not self.instrument or self.target_id != TARGET:
            raise ValueError("case, episode, instrument and the common target are required")
        times = (self.available_at, self.decision_at, self.label_end, self.label_available_at)
        if any(t.tzinfo is None or t.utcoffset() is None for t in times):
            raise ValueError("timestamps must be timezone-aware")
        if not self.available_at <= self.decision_at < self.label_end <= self.label_available_at:
            raise ValueError("feature availability and label timestamps are inconsistent")
        if self.label_end - self.decision_at != timedelta(seconds=75):
            raise ValueError("all rows must share the declared 75-second target")
        if len(self.features) != len(FEATURES) or not all(math.isfinite(x) for x in self.features):
            raise ValueError("six finite ordered numeric features required")
        if not math.isfinite(self.return_bps):
            raise ValueError("finite realized return required")


def synthetic_rows(count: int, seed: int) -> list[EventRow]:
    rng = random.Random(seed)
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    rows = []
    for i in range(count):
        z = [rng.gauss(0, 1) for _ in FEATURES]
        features = (z[0], 0.01 * z[1], math.tanh(z[2]), math.exp(z[3]),
                    10 * math.exp(z[4] / 3), 5 * z[5])
        outcome = 5 * z[0] - 2 * z[1] + 6 * features[2] + 2 * z[5] + rng.gauss(0, 6)
        decision = start + timedelta(seconds=90 * i)
        rows.append(EventRow(f"case-{i}", f"episode-{i}", "SYNTHETIC",
                             decision - timedelta(seconds=1), decision,
                             decision + timedelta(seconds=75), decision + timedelta(seconds=76),
                             features, outcome))
    return rows


def split_rows(rows: list[EventRow]) -> dict[str, list[EventRow]]:
    if len(rows) < 100:
        raise ValueError("at least 100 fixture rows required")
    for row in rows:
        row.validate()
    if len({row.case_id for row in rows}) != len(rows):
        raise ValueError("duplicate case ids")
    if any(a.decision_at > b.decision_at for a, b in zip(rows, rows[1:])):
        raise ValueError("rows must arrive in chronological order")
    n = len(rows)
    edges = (0, n // 2, n * 65 // 100, n * 80 // 100, n * 90 // 100, n)
    parts = {name: rows[edges[i]:edges[i + 1]] for i, name in enumerate(PARTITIONS)}
    seen_episodes = set()
    for i, name in enumerate(PARTITIONS):
        block = parts[name]
        episodes = {row.episode_id for row in block}
        if episodes & seen_episodes:
            raise ValueError("an episode crosses partition boundaries")
        seen_episodes.update(episodes)
        if i + 1 < len(PARTITIONS):
            next_start = parts[PARTITIONS[i + 1]][0].decision_at
            if max(row.label_available_at for row in block) >= next_start:
                raise ValueError("earlier partition labels must mature before the next partition")
    return parts


@dataclass(frozen=True)
class Standardizer:
    mean: tuple[float, ...]
    scale: tuple[float, ...]

    @classmethod
    def fit(cls, rows: list[EventRow]):
        columns = list(zip(*(row.features for row in rows)))
        means = tuple(sum(col) / len(col) for col in columns)
        scales = tuple(max(1e-8, math.sqrt(sum((x - m) ** 2 for x in col) / len(col)))
                       for col, m in zip(columns, means))
        return cls(means, scales)

    def transform(self, row: EventRow):
        return tuple((x - m) / s for x, m, s in zip(row.features, self.mean, self.scale))


def choice(row: EventRow, view: tuple[int, ...], scaler: Standardizer) -> ChoiceExample:
    values = scaler.transform(row)
    text = "; ".join(f"{FEATURES[i]}={values[i]:+.3f}" for i in view)
    if len(text.encode("utf-8")) > CONFIG["context_tokens"]:
        raise ValueError("feature text exceeds context budget")
    return ChoiceExample(text, OUTCOMES, row.label)


def train_choice(rows, view, scaler, epochs, seed):
    torch.manual_seed(seed)
    model, collator = make_system(CONFIG, torch.device("cpu"))
    examples = [choice(row, view, scaler) for row in rows]
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.002, weight_decay=1e-4)
    steps = 0
    model.train()
    for _ in range(epochs):
        for indexes in torch.randperm(len(rows)).split(64):
            batch = collator([examples[i] for i in indexes.tolist()])
            loss = nn.functional.cross_entropy(model(batch), batch["labels"])
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            steps += 1
    model.eval()
    return model, collator, steps


@torch.no_grad()
def predict_choice(model, collator, rows, view, scaler):
    result = []
    for offset in range(0, len(rows), 64):
        batch = collator([choice(row, view, scaler) for row in rows[offset:offset + 64]])
        # The probability contract is tighter than float32 summation error.
        result.extend(tuple(p) for p in model(batch).double().softmax(-1).tolist())
    return result


def cases_for(rows, forecasts, data_hash):
    return [LabeledCase("global", row.label, tuple(SpecialistForecast(
        specialist_id=name, outcome_space=OUTCOMES, probabilities=values[i], context="global",
        forecast_time=row.decision_at.isoformat(), valid_until=row.label_end.isoformat(),
        information_cutoff=row.available_at.isoformat(), model_version=f"lab-{name}-v1",
        data_version=data_hash) for name, values in forecasts.items()), row.case_id)
        for i, row in enumerate(rows)]


def run(output: Path, count=1000, epochs=3, seed=20261003):
    if epochs < 1:
        raise ValueError("epochs must be positive")
    rows = synthetic_rows(count, seed)
    parts = split_rows(rows)
    output.mkdir(parents=True, exist_ok=False)
    data = "".join(json.dumps(asdict(row), default=str, sort_keys=True) + "\n" for row in rows)
    (output / "synthetic.jsonl").write_text(data)
    data_hash = hashlib.sha256(data.encode()).hexdigest()
    scaler = Standardizer.fit(parts["training"])
    torch.set_num_threads(2)
    models = {}
    predictions = {name: {} for name in PARTITIONS[1:]}
    all_features = tuple(range(len(FEATURES)))
    for offset, (name, view) in enumerate({"single": all_features, **VIEWS}.items()):
        start = time.perf_counter()
        model, collator, steps = train_choice(parts["training"], view, scaler, epochs, seed + offset)
        models[name] = {"training_seconds": time.perf_counter() - start,
                        "parameters": sum(p.numel() for p in model.parameters()),
                        "optimizer_steps": steps, "features": [FEATURES[i] for i in view],
                        "seed": seed + offset}
        torch.save({"config": CONFIG, "state_dict": trainable_state(model)}, output / f"{name}.pt")
        for partition in PARTITIONS[1:]:
            predictions[partition][name] = predict_choice(model, collator, parts[partition], view, scaler)

    # A strong simple comparator for the deliberately partly-linear synthetic generator.
    torch.manual_seed(seed)
    numeric = nn.Linear(len(FEATURES), len(OUTCOMES))
    x = torch.tensor([scaler.transform(row) for row in parts["training"]], dtype=torch.float32)
    y = torch.tensor([row.label for row in parts["training"]])
    optimizer = torch.optim.AdamW(numeric.parameters(), lr=0.03)
    start = time.perf_counter()
    for _ in range(100):
        optimizer.zero_grad(set_to_none=True)
        nn.functional.cross_entropy(numeric(x), y).backward()
        optimizer.step()
    models["numeric"] = {"parameters": sum(p.numel() for p in numeric.parameters()),
                         "training_seconds": time.perf_counter() - start, "optimizer_steps": 100,
                         "features": list(FEATURES), "seed": seed}
    torch.save(numeric.state_dict(), output / "numeric.pt")
    with torch.no_grad():
        for partition in PARTITIONS[1:]:
            x = torch.tensor([scaler.transform(row) for row in parts[partition]], dtype=torch.float32)
            predictions[partition]["numeric"] = [tuple(p) for p in numeric(x).double().softmax(-1).tolist()]

    def specialist_cases(partition):
        return cases_for(parts[partition], {name: predictions[partition][name] for name in VIEWS}, data_hash)

    # Disable context-specific fits: this first fixture has a single declared global context.
    council = CouncilModel.fit(*(specialist_cases(p) for p in PARTITIONS[1:4]), minimum_context_rows=count + 1)
    evaluation = specialist_cases("evaluation")
    scored = {"council": [council.predict(case.forecasts).probabilities for case in evaluation]}
    labels = [row.label for row in parts["specialist_calibration"]]
    temperatures = {}
    for name in models:
        calibrator = fit_temperature(predictions["specialist_calibration"][name], labels)
        temperatures[name] = asdict(calibrator)
        scored[name] = [calibrator.apply(p) for p in predictions["evaluation"][name]]

    def equal_pool(partition):
        return [linear_opinion_pool({name: council.specialist_calibrators[name].apply(
            predictions[partition][name][i]) for name in VIEWS}, {name: 1.0 for name in VIEWS})
            for i in range(len(parts[partition]))]

    equal_cal = fit_temperature(equal_pool("pool_calibration"), [r.label for r in parts["pool_calibration"]])
    scored["equal_pool"] = [equal_cal.apply(p) for p in equal_pool("evaluation")]
    counts = [sum(row.label == i for row in parts["training"]) for i in range(len(OUTCOMES))]
    scored["prevalence"] = [tuple((n + 1) / (len(parts["training"]) + 3) for n in counts)] * len(evaluation)
    with (output / "evaluation.jsonl").open("w") as handle:
        for i, row in enumerate(parts["evaluation"]):
            handle.write(json.dumps({"case_id": row.case_id, "label": row.label,
                                    "predictions": {name: values[i] for name, values in scored.items()}}) + "\n")
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent,
                              text=True, capture_output=True, check=True).stdout.strip()
    code_root = Path(__file__).resolve().parent
    code_hashes = {str(p.relative_to(code_root)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(code_root.rglob("*.py"))}
    report = {
        "status": "synthetic_engineering_only", "target": TARGET, "outcome_order": OUTCOMES,
        "seed": seed, "epochs": epochs, "data_sha256": data_hash, "git_revision": revision,
        "code_sha256": code_hashes,
        "environment": {"python": platform.python_version(), "torch": torch.__version__},
        "feature_order": FEATURES, "standardizer": asdict(scaler), "model_config": CONFIG,
        "partitions": {name: {"rows": len(block), "start": block[0].decision_at.isoformat(),
                              "end": block[-1].decision_at.isoformat(),
                              "labels_available_through": max(r.label_available_at for r in block).isoformat()}
                       for name, block in parts.items()},
        "models": models, "specialist_calibration": temperatures,
        "gate_weights": dict(council.gate.global_weights),
        "pool_calibration": asdict(council.pool_calibrator), "equal_pool_calibration": asdict(equal_cal),
        "evaluation_metrics": {name: metric(evaluation, values) for name, values in scored.items()},
        "artifact_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())},
        "limitations": ["synthetic rows and proxy features; no market data or confirmed liquidations",
                        "fixed fixture target; no fills, costs, P&L, HFT latency or edge claim",
                        "tiny JevLike trained from scratch; numerical text encoding is experimental",
                        "training budgets differ; no equal-budget architecture claim",
                        "single global gate; no pretrained encoder, student or quantum model",
                        "five-way engineering split is not a competition OOS split"],
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20261003)
    args = parser.parse_args()
    report = run(args.output, args.rows, args.epochs, args.seed)
    print(json.dumps({"status": report["status"], "evaluation_metrics": report["evaluation_metrics"]}, indent=2))


if __name__ == "__main__":
    main()
