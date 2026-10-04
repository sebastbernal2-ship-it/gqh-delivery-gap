"""Seven information views on an explicitly declared, development-only JSONL panel."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import platform
import re
import subprocess
import time

import torch
from torch import nn

from council.calibration import fit_temperature
from council.fusion import linear_opinion_pool
from specialist_lab import (CONFIG, PARTITIONS, Standardizer, train_choice, predict_choice)

def stamp(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timezone-aware timestamps required")
    return result


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def seven_views(groups):
    if set(groups) != {"A", "B", "C"} or any(not v for v in groups.values()):
        raise ValueError("three nonempty information groups A, B, C required")
    return {"".join(keys): tuple(i for k in keys for i in groups[k])
            for size in range(1, 4) for keys in combinations("ABC", size)}


@dataclass(frozen=True)
class PanelRow:
    case_id: str
    episode_id: str
    instrument: str
    decision_at: datetime
    label_end: datetime
    label_available_at: datetime
    feature_available_at: tuple[datetime, ...]
    features: tuple[float, ...]
    label: int
    partition: str
    target_id: str
    source_refs: tuple[str, ...]


def load_panel(panel_path, manifest_path):
    spec = json.loads(Path(manifest_path).read_text())
    if spec.get("scope") != "development_only":
        raise ValueError("only explicitly development-only panels are accepted")
    if spec.get("panel_sha256") != digest(panel_path):
        raise ValueError("panel hash differs from manifest")
    features, outcomes = spec["feature_order"], spec["outcome_order"]
    if (not features or len(set(features)) != len(features) or
            any(not re.fullmatch(r"[a-z][a-z0-9_]{0,31}", f) for f in features)):
        raise ValueError("unique short feature identifiers required")
    if len(outcomes) < 2 or len(set(outcomes)) != len(outcomes) or any(not x for x in outcomes):
        raise ValueError("distinct ordered outcomes required")
    if any(len(x.encode()) > CONFIG["option_tokens"] for x in outcomes):
        raise ValueError("outcome exceeds token budget")
    views = seven_views(spec["groups"])
    indexes = views["ABC"]
    if (any(type(i) is not int for i in indexes) or
            sorted(indexes) != list(range(len(features)))):
        raise ValueError("groups must partition feature indexes exactly once")
    if not spec.get("target_id") or not spec.get("label_rule") or not spec.get("availability_note"):
        raise ValueError("target, label rule and availability evidence required")
    if spec.get("availability_basis") not in ("source_timestamp", "retrospective_assumption", "synthetic"):
        raise ValueError("availability basis must be explicit")
    start, end = stamp(spec["development_start"]), stamp(spec["development_end"])
    rows = []
    for line in Path(panel_path).read_text().splitlines():
        raw = json.loads(line)
        for key in ("decision_at", "label_end", "label_available_at"):
            raw[key] = stamp(raw[key])
        raw["feature_available_at"] = tuple(stamp(v) for v in raw["feature_available_at"])
        raw["features"] = tuple(raw["features"])
        raw["source_refs"] = tuple(raw["source_refs"])
        row = PanelRow(**raw)
        if not row.case_id or not row.episode_id or not row.instrument or row.target_id != spec["target_id"]:
            raise ValueError("identity or target mismatch")
        if row.partition not in PARTITIONS:
            raise ValueError("unknown partition")
        if not start <= row.decision_at < row.label_end <= row.label_available_at < end:
            raise ValueError("row or future label outside declared development window")
        # Never reopen the project's already-spent windows, even under another target name.
        if row.decision_at < stamp("2024-10-01T00:00:00+00:00") and row.label_available_at >= stamp("2022-10-01T00:00:00+00:00"):
            raise ValueError("row intersects closed project holdout")
        if (len(row.features) != len(features) or len(row.feature_available_at) != len(features)
                or len(row.source_refs) != len(features) or any(not r for r in row.source_refs)):
            raise ValueError("each feature needs a value, availability time and source reference")
        if not all(type(x) in (float, int) and math.isfinite(x) for x in row.features):
            raise ValueError("finite numeric features required; imputation must be explicit upstream")
        if max(row.feature_available_at) > row.decision_at:
            raise ValueError("feature not available at decision time")
        if type(row.label) is not int or not 0 <= row.label < len(outcomes):
            raise ValueError("invalid outcome label")
        rows.append(row)
    if not rows or len({r.case_id for r in rows}) != len(rows):
        raise ValueError("empty panel or duplicate cases")
    if rows != sorted(rows, key=lambda r: r.decision_at):
        raise ValueError("panel must be chronological")
    parts = {p: [r for r in rows if r.partition == p] for p in PARTITIONS}
    episodes = set()
    for i, p in enumerate(PARTITIONS):
        block = parts[p]
        if not block:
            raise ValueError("all five partitions must be populated")
        current = {r.episode_id for r in block}
        if current & episodes:
            raise ValueError("episode crosses partition boundaries")
        episodes |= current
        if i < len(PARTITIONS) - 1:
            following = parts[PARTITIONS[i + 1]]
            if not following or max(r.label_available_at for r in block) >= min(r.decision_at for r in following):
                raise ValueError("partition labels must mature before next partition")
    return spec, parts, views


def scores(probabilities, rows):
    k = len(probabilities[0])
    return {"log_loss": sum(-math.log(max(1e-12, p[r.label])) for p, r in zip(probabilities, rows)) / len(rows),
            "brier": sum(sum((v - (i == r.label)) ** 2 for i, v in enumerate(p))
                         for p, r in zip(probabilities, rows)) / len(rows),
            "classes": k, "rows": len(rows)}


def select_views(gate_scores, margin=0.01):
    """Keep singletons; admit combinations only above their best proper subset on gate data."""
    result = {"retained": ["A", "B", "C"], "checks": {}, "margin_log_loss": margin}
    for view in ("AB", "AC", "BC", "ABC"):
        subsets = [s for s in gate_scores if set(s) < set(view)]
        best = min(subsets, key=lambda s: (gate_scores[s]["log_loss"], len(s), s))
        gain = gate_scores[best]["log_loss"] - gate_scores[view]["log_loss"]
        result["checks"][view] = {"best_subset": best, "gain": gain, "retained": gain > margin}
        if gain > margin:
            result["retained"].append(view)
    return result


def run(panel_path, manifest_path, output, epochs=3, seed=20261003):
    if epochs < 1:
        raise ValueError("epochs must be positive")
    spec, parts, views = load_panel(panel_path, manifest_path)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(2)
    scaler = Standardizer.fit(parts["training"])
    kwargs = {"feature_names": tuple(spec["feature_order"]), "outcomes": tuple(spec["outcome_order"])}
    predictions = {p: {} for p in PARTITIONS[1:]}
    models, calibration = {}, {}
    for name, view in views.items():
        # Same initialization and batches across views: changes are information, not seed search.
        started = time.perf_counter()
        model, collator, steps = train_choice(parts["training"], view, scaler, epochs, seed, **kwargs)
        key = "jev_" + name
        models[key] = {"parameters": sum(p.numel() for p in model.parameters()),
                       "optimizer_steps": steps, "training_seconds": time.perf_counter() - started,
                       "feature_indexes": view}
        torch.save({"config": CONFIG, "state_dict": model.state_dict()}, output / (key + ".pt"))
        raw = {p: predict_choice(model, collator, parts[p], view, scaler, **kwargs) for p in PARTITIONS[1:]}
        cal = fit_temperature(raw["specialist_calibration"], [r.label for r in parts["specialist_calibration"]])
        calibration[key] = asdict(cal)
        for p in raw:
            predictions[p][key] = [cal.apply(x) for x in raw[p]]

        torch.manual_seed(seed)
        model = nn.Linear(len(view), len(spec["outcome_order"]))
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.03)
        def tensor(block):
            return torch.tensor([[scaler.transform(r)[i] for i in view] for r in block], dtype=torch.float32)
        x = tensor(parts["training"])
        y = torch.tensor([r.label for r in parts["training"]])
        started = time.perf_counter()
        for _ in range(100):
            optimizer.zero_grad(set_to_none=True)
            nn.functional.cross_entropy(model(x), y).backward()
            optimizer.step()
        key = "numeric_" + name
        models[key] = {"parameters": sum(p.numel() for p in model.parameters()), "optimizer_steps": 100,
                       "training_seconds": time.perf_counter() - started, "feature_indexes": view}
        torch.save(model.state_dict(), output / (key + ".pt"))
        with torch.no_grad():
            raw = {p: model(tensor(parts[p])).double().softmax(-1).tolist() for p in PARTITIONS[1:]}
        cal = fit_temperature(raw["specialist_calibration"], [r.label for r in parts["specialist_calibration"]])
        calibration[key] = asdict(cal)
        for p in raw:
            predictions[p][key] = [cal.apply(x) for x in raw[p]]

    gate = {name: scores(values, parts["gate_fit"]) for name, values in predictions["gate_fit"].items()}
    selection = {family: select_views({v: gate[family + "_" + v] for v in views}) for family in ("jev", "numeric")}
    # Selected single is fixed on gate_fit, never on evaluation. Always report every variant.
    selected = min(gate, key=lambda name: (gate[name]["log_loss"], name))
    k = len(spec["outcome_order"])
    prior = tuple((sum(r.label == i for r in parts["training"]) + 1) / (len(parts["training"]) + k) for i in range(k))
    pool_calibrators = {}
    for family in ("jev", "numeric"):
        # Primary pool uses only three disjoint views; correlated combinations are comparisons.
        names = [family + "_" + v for v in "ABC"]
        raw_pools = {}
        for p in ("pool_calibration", "evaluation"):
            raw_pools[p] = [linear_opinion_pool({n: predictions[p][n][i] for n in names}, {n: 1 for n in names})
                            for i in range(len(parts[p]))]
        cal = fit_temperature(raw_pools["pool_calibration"], [r.label for r in parts["pool_calibration"]])
        pool_calibrators[family] = asdict(cal)
        predictions["evaluation"][family + "_equal_pool"] = [cal.apply(x) for x in raw_pools["evaluation"]]
    predictions["evaluation"]["prevalence"] = [prior] * len(parts["evaluation"])
    predictions["evaluation"]["gate_selected"] = predictions["evaluation"][selected]
    for p in PARTITIONS[1:]:
        with (output / (p + ".jsonl")).open("w") as f:
            for i, row in enumerate(parts[p]):
                f.write(json.dumps({"case_id": row.case_id, "episode_id": row.episode_id, "label": row.label,
                                    "predictions": {n: values[i] for n, values in predictions[p].items()}}) + "\n")
    report = {"status": "development_engineering_only", "panel_manifest": spec,
              "manifest_sha256": digest(manifest_path), "seed": seed, "epochs": epochs,
              "environment": {"python": platform.python_version(), "torch": torch.__version__},
              "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent, text=True).strip(),
              "code_sha256": {str(p.relative_to(Path(__file__).parent)): digest(p)
                               for p in sorted(Path(__file__).parent.rglob("*.py"))},
              "standardizer": asdict(scaler), "models": models, "calibration": calibration,
              "pool_calibration": pool_calibrators, "gate_scores": gate, "view_selection": selection,
              "gate_selected_model": selected,
              "evaluation_metrics": {n: scores(p, parts["evaluation"]) for n, p in predictions["evaluation"].items()},
              "partitions": {p: {"rows": len(b), "episodes": len({r.episode_id for r in b}),
                                  "start": b[0].decision_at.isoformat(), "end": b[-1].decision_at.isoformat(),
                                  "class_counts": [sum(r.label == i for r in b) for i in range(k)]}
                             for p, b in parts.items()},
              "artifact_sha256": {p.name: digest(p) for p in sorted(output.iterdir())},
              "limitations": ["development comparison, not untouched competition OOS or trading evidence",
                              "availability evidence is adapter-supplied and requires source review",
                              "seven related views are not independent votes or quantum branches",
                              "retention threshold is exploratory, not a significance or robustness claim",
                              "one seed, fixed budgets differ across model families, decimal text encoding",
                              "no fills, costs, portfolio, latency guarantee, pretraining or quantum advantage"]}
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20261003)
    args = parser.parse_args()
    report = run(args.panel, args.manifest, args.output, args.epochs, args.seed)
    print(json.dumps({"status": report["status"], "selection": report["view_selection"],
                      "evaluation_metrics": report["evaluation_metrics"]}, indent=2))
