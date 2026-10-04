"""Jev-only, fixed-budget A / B / A+B execution-information ablation."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import platform
import subprocess

import numpy as np
import torch

from council.calibration import fit_temperature
from execution_dataset import FEATURES, load_cache
from execution_model import ExecutionJev
from execution_train import apply, probabilities
from synchronized_tape import digest


VIEWS = {
    "A_book": tuple(range(21)) + (23,),
    "B_trades": (21, 22),
    "AB_early_fusion": tuple(range(24)),
}
PARTITIONS = ("training", "specialist_calibration", "gate_fit", "pool_calibration", "evaluation")


def case_metrics(p, y):
    """Average twelve correlated query scores inside each parent decision first."""
    p = np.asarray(p, dtype=np.float64).reshape(-1, 12, 5)
    y = np.asarray(y, dtype=np.int64).reshape(-1, 12)
    selected = np.clip(np.take_along_axis(p, y[..., None], axis=-1)[..., 0], 1e-12, 1.)
    logloss = -np.log(selected).mean(axis=1)
    onehot = np.eye(5, dtype=np.float64)[y]
    brier = ((p - onehot) ** 2).sum(axis=-1).mean(axis=1)
    return logloss, brier


def summarize(p, y, sessions):
    ll, br = case_metrics(p, y)
    by_session = {}
    for session in sorted(set(sessions)):
        mask = np.asarray(sessions) == session
        by_session[session] = {
            "cases": int(mask.sum()),
            "mean_case_log_loss": float(ll[mask].mean()),
            "mean_case_brier": float(br[mask].mean()),
        }
    return {
        "parent_cases": int(len(ll)), "marginal_queries": int(len(ll) * 12),
        "mean_case_log_loss": float(ll.mean()), "mean_case_brier": float(br.mean()),
        "session_metrics": by_session,
        "warning": "Queries within a parent case and cases within a session are dependent.",
    }


def run(dataset, output, epochs=3, seed=20261003, device="cpu"):
    if epochs < 1:
        raise ValueError("epochs must be positive")
    spec, arrays = load_cache(dataset)
    raw = np.asarray(arrays["features"])
    labels = np.asarray(arrays["targets"])
    roles = np.asarray(arrays["roles"])
    sessions = list(spec["sessions"])
    if raw.shape[-1] != len(FEATURES):
        raise ValueError("cache feature order is not the canonical 24-input execution schema")
    if device.startswith("cuda") and not torch.cuda.is_available():
        raise ValueError("CUDA requested but unavailable")

    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(2)
    per_view = {}
    calibrators = {}
    all_predictions = {role: {} for role in range(1, 5)}

    for name, indexes in VIEWS.items():
        selected = np.zeros(len(FEATURES), dtype=bool)
        selected[list(indexes)] = True
        # The scaler is fit on training-role sequences only. The unlabeled corpus is not used in
        # this first comparison: that keeps the test focused on input-view information.
        train_x = raw[roles == 0].astype(np.float64)
        mean = np.zeros(len(FEATURES), dtype=np.float64)
        scale = np.ones(len(FEATURES), dtype=np.float64)
        mean[selected] = train_x[..., selected].mean(axis=(0, 1))
        scale[selected] = train_x[..., selected].std(axis=(0, 1))
        scale[selected] = np.where(scale[selected] < 1e-6, 1., scale[selected])
        x_raw = (raw - mean) / scale
        x_raw[..., ~selected] = 0.
        x = torch.tensor(x_raw, dtype=torch.float32)
        y = torch.tensor(labels, dtype=torch.long)

        torch.manual_seed(seed)
        # Keep the exact same model shape/capacity and initialization across views. Excluded
        # features are zero after standardization and therefore carry no input information.
        model = ExecutionJev(features=len(FEATURES)).to(device)
        # Match the supervised fit loop and schedules across all three views. No masked
        # reconstruction is run in this ablation.
        from torch import nn
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
        losses = []
        torch.manual_seed(seed + 1)
        model.train()
        train_rows = torch.tensor(np.flatnonzero(roles == 0), dtype=torch.long)
        for _ in range(epochs):
            for rows in torch.randperm(len(train_rows)).split(32):
                batch = train_rows[rows]
                optimizer.zero_grad(set_to_none=True)
                loss = nn.functional.cross_entropy(
                    model(x[batch].to(device)).reshape(-1, 5), y[batch].to(device).reshape(-1)
                )
                if not torch.isfinite(loss):
                    raise ValueError("nonfinite Jev loss")
                loss.backward()
                optimizer.step()
                losses.append(float(loss.detach().cpu()))
        model.eval()

        raw_predictions = {}
        for role in range(1, 5):
            raw_predictions[role] = probabilities(model, x[roles == role])
            all_predictions[role][name] = raw_predictions[role]
        cal = [fit_temperature(raw_predictions[1][:, q // 4, (q // 2) % 2, q % 2].tolist(),
                               labels[roles == 1][:, q // 4, (q // 2) % 2, q % 2].tolist())
               for q in range(12)]
        # Fit one calibrator for each horizon x proposed side x task marginal.
        calibrated = {r: apply(p, cal) for r, p in raw_predictions.items()}
        all_predictions_cal = {r: calibrated[r] for r in calibrated}
        for r in all_predictions_cal:
            all_predictions[r][name] = all_predictions_cal[r]
        calibrators[name] = [asdict(item) for item in cal]
        payload = {
            "schema_version": "execution-jev-view-ablation-v1",
            "view": name, "feature_indexes": list(indexes),
            "feature_names": [FEATURES[i] for i in indexes],
            "feature_mask": selected.tolist(),
            "config": model.config,
            "state": {k: v.detach().cpu().clone() for k, v in model.state_dict().items()},
            "mean": mean.tolist(), "scale": scale.tolist(), "calibration": calibrators[name],
            "dataset_manifest_sha256": digest(Path(dataset) / "manifest.json"),
        }
        torch.save(payload, out / f"{name}.pt")
        per_view[name] = {
            "feature_indexes": list(indexes), "feature_names": [FEATURES[i] for i in indexes],
            "parameter_count": sum(p.numel() for p in model.parameters()),
            "optimizer_steps": len(losses), "supervised_losses": losses,
            "pretraining_epochs": 0,
        }

    role_masks = {r: roles == r for r in range(5)}
    gate_scores = {
        name: summarize(all_predictions[2][name], labels[role_masks[2]],
                        [sessions[i] for i in np.flatnonzero(role_masks[2])])
        for name in VIEWS
    }
    singleton = min(("A_book", "B_trades"), key=lambda n: (gate_scores[n]["mean_case_log_loss"], n))
    use_ab = gate_scores["AB_early_fusion"]["mean_case_log_loss"] <= gate_scores[singleton]["mean_case_log_loss"] - 0.01
    selected = "AB_early_fusion" if use_ab else singleton

    # Fixed equal late pool, calibrated only on the reserved pool-calibration role.
    late_raw = {r: (all_predictions[r]["A_book"] + all_predictions[r]["B_trades"]) / 2
                for r in (3, 4)}
    flat_cal = []
    for q in range(12):
        h, side, task = q // 4, (q // 2) % 2, q % 2
        flat_cal.append(fit_temperature(
            late_raw[3][:, h, side, task].tolist(),
            labels[role_masks[3]][:, h, side, task].tolist(),
        ))
    late = {r: apply(late_raw[r], flat_cal) for r in (3, 4)}

    train_labels = labels[role_masks[0]].reshape(-1, 12)
    prior = np.stack([(np.bincount(train_labels[:, q], minlength=5) + 1) /
                      (len(train_labels) + 5) for q in range(12)]).reshape(3, 2, 2, 5)
    prior_eval = np.broadcast_to(prior, (int(role_masks[4].sum()), 3, 2, 2, 5))
    evaluation = {
        name: summarize(all_predictions[4][name], labels[role_masks[4]],
                        [sessions[i] for i in np.flatnonzero(role_masks[4])])
        for name in VIEWS
    }
    evaluation["AB_late_equal_pool"] = summarize(late[4], labels[role_masks[4]],
                                                 [sessions[i] for i in np.flatnonzero(role_masks[4])])
    evaluation["training_prevalence"] = summarize(prior_eval, labels[role_masks[4]],
                                                   [sessions[i] for i in np.flatnonzero(role_masks[4])])
    evaluation["gate_selected"] = evaluation[selected]
    for name, forecast in {**all_predictions[4], "AB_late_equal_pool": late[4],
                           "training_prevalence": prior_eval}.items():
        np.save(out / f"evaluation_{name}.npy", forecast, allow_pickle=False)

    sessions_by_role = {
        PARTITIONS[r]: sorted({sessions[i] for i in np.flatnonzero(role_masks[r])})
        for r in range(5)
    }
    minimum_support = all(len(v) >= 3 for v in sessions_by_role.values())
    report = {
        "status": "development_engineering_only",
        "study": "same structured Jev, same target, three information ablations",
        "views": per_view, "selection_rule": "AB selected only when gate loss is at least 0.01 nats/case below best singleton; otherwise gate-best singleton",
        "gate_metrics": gate_scores, "gate_best_singleton": singleton,
        "gate_selected": selected, "pool_calibration": [asdict(item) for item in flat_cal],
        "evaluation_metrics": evaluation,
        "role_cases": {PARTITIONS[r]: int(role_masks[r].sum()) for r in range(5)},
        "role_sessions": sessions_by_role,
        "minimum_three_sessions_per_role_met": minimum_support,
        "interpretation_gate": "SMOKE_ONLY" if not minimum_support else "DEVELOPMENT_COMPARISON_ONLY",
        "seed": seed, "epochs": epochs, "device": device,
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "torch": torch.__version__},
        "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent, text=True).strip(),
        "code_sha256": {p.name: digest(p) for p in [Path(__file__), Path(__file__).with_name("execution_model.py"),
                                                      Path(__file__).with_name("execution_dataset.py"),
                                                      Path(__file__).with_name("execution_predict.py")]},
        "dataset_manifest": spec,
        "dataset_manifest_sha256": digest(Path(dataset) / "manifest.json"),
        "artifacts": {p.name: digest(p) for p in sorted(out.iterdir())},
        "limitations": [
            "all views use the same small, previously inspected development panel; not competition OOS",
            "fewer than three eligible dates in any role prevents interpreting this as a useful view comparison",
            "all twelve marginals share one parent decision; scores are dependent within case and session",
            "recorded availability is an unverified retrospective proxy; mirror trade completeness and side meaning unresolved",
            "scratch only: pretraining is intentionally excluded to isolate input views",
            "no fills, own impact, costs, HFT latency, live HiPerGator execution or quantum advantage",
        ],
    }
    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20261003)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    report = run(args.dataset, args.output, args.epochs, args.seed, args.device)
    print(json.dumps({"status": report["status"], "gate_selected": report["gate_selected"],
                      "interpretation_gate": report["interpretation_gate"],
                      "evaluation_metrics": report["evaluation_metrics"]}, indent=2))
