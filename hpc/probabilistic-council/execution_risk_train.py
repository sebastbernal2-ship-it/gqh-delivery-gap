"""Jev-only fitting and a fixed A/B/AB risk-quantile comparison on prepared arrays."""
import argparse
import json
from pathlib import Path
import platform

import numpy as np
import torch

from execution_action_model import QUANTILES, pinball_loss
from execution_risk_dataset import load_risk_cache
from execution_risk_model import ExecutionRiskJev
from runtime_provenance import git_revision
from synchronized_tape import digest

VIEWS = {"A": tuple(range(21)) + (23,), "B": (21, 22), "AB": tuple(range(24))}
SEED = 20261004


def metrics(prediction, target):
    p, y = np.asarray(prediction), np.asarray(target)
    if p.shape != y.shape + (3,) or not np.isfinite(p).all() or not np.isfinite(y).all():
        raise ValueError("risk scoring shape/finite mismatch")
    error = y[..., None] - p
    q = np.asarray(QUANTILES)
    losses = np.maximum(q * error, (q - 1) * error)
    return {"mean_parent_pinball_bps": float(losses.reshape(len(y), -1).mean(1).mean()),
            "median_mae_bps": float(np.abs(y - p[..., 1]).mean()),
            "interval_80_coverage": float(((y >= p[..., 0]) & (y <= p[..., 2])).mean()),
            "interval_80_width_bps": float((p[..., 2] - p[..., 0]).mean()),
            "query_quantile_hit_rates": (y[..., None] <= p).mean(0).tolist(),
            "query_pinball_bps": losses.mean(0).tolist(), "parent_cases": len(y)}


def view_tensor(x, view):
    mask = torch.zeros(x.shape[-1], dtype=x.dtype, device=x.device)
    mask[list(VIEWS[view])] = 1
    return x * mask


def fit(x, y, view, epochs, seed, device, target_scale):
    torch.manual_seed(seed)
    model = ExecutionRiskJev().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    losses = []
    x = view_tensor(x, view)
    for _ in range(epochs):
        for indexes in torch.randperm(len(x)).split(32):
            optimizer.zero_grad()
            prediction = model(x[indexes].to(device))
            loss = pinball_loss(prediction, y[indexes].to(device) / target_scale)
            if not torch.isfinite(loss):
                raise ValueError("nonfinite risk training loss")
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach()))
    return model.eval(), losses


def forecast(model, x, view, target_scale):
    device = next(model.parameters()).device
    with torch.no_grad():
        outputs = [model(view_tensor(batch, view).to(device)).double().cpu().numpy() * target_scale
                   for batch in x.split(128)]
    p = np.concatenate(outputs)
    if (not np.isfinite(p).all() or (np.diff(p, axis=-1) < -1e-6).any()
            or (p[:, :, :, 1] < 0).any()):
        raise ValueError("invalid risk forecast")
    return p


def run(dataset, output, epochs=3, seed=SEED, device="cpu", allow_development_smoke=False):
    if type(epochs) is not int or epochs < 1 or type(seed) is not int:
        raise ValueError("positive epochs and integer seed required")
    if device.startswith("cuda") and not torch.cuda.is_available():
        raise ValueError("CUDA unavailable")
    spec, arrays = load_risk_cache(dataset)
    roles, labels = arrays["roles"], np.asarray(arrays["targets"])
    role_sessions = {name: sorted({spec["sessions"][i] for i in np.flatnonzero(roles == role)})
                     for role, name in enumerate(spec["partitions"])}
    scarce = [name for name in ("training", "gate_fit", "evaluation") if len(role_sessions[name]) < 3]
    if scarce and not allow_development_smoke:
        raise ValueError("insufficient independent sessions; explicitly allow a development smoke run")
    torch.set_num_threads(2)
    raw = np.asarray(arrays["features"], dtype=np.float64)
    mean = raw[roles == 0].mean((0, 1))
    scale = raw[roles == 0].std((0, 1))
    scale = np.where(scale < 1e-6, 1.0, scale)
    target_scale = max(float(labels[roles == 0].std()), 0.1)
    x = torch.tensor((raw - mean) / scale, dtype=torch.float32)
    y = torch.tensor(labels, dtype=torch.float32)
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    models, losses, gate = {}, {}, {}
    for view in VIEWS:
        model, losses[view] = fit(x[roles == 0], y[roles == 0], view, epochs, seed, device, target_scale)
        models[view] = model
        gate[view] = metrics(forecast(model, x[roles == 2], view, target_scale), labels[roles == 2])
    prior = np.moveaxis(np.quantile(labels[roles == 0], QUANTILES, axis=0), 0, -1)
    gate["empirical_quantiles"] = metrics(np.broadcast_to(prior, (int(sum(roles == 2)),) + prior.shape), labels[roles == 2])
    selected = min(gate, key=lambda name: gate[name]["mean_parent_pinball_bps"])
    # Selection is frozen before evaluation is scored. All four variants are retained.
    forecasts = {view: forecast(model, x[roles == 4], view, target_scale) for view, model in models.items()}
    forecasts["empirical_quantiles"] = np.broadcast_to(prior, (int(sum(roles == 4)),) + prior.shape)
    scores = {name: metrics(p, labels[roles == 4]) for name, p in forecasts.items()}
    eval_sessions = np.asarray(spec["sessions"])[roles == 4]
    session_scores = {name: {session: metrics(p[eval_sessions == session], labels[roles == 4][eval_sessions == session])
                             for session in sorted(set(eval_sessions))} for name, p in forecasts.items()}
    for name in forecasts:
        model = models.get(name)
        payload = {"schema_version": "execution-risk-jev-v1", "variant": name,
                   "config": model.config if model is not None else None,
                   "state": {k: v.detach().cpu().clone() for k, v in model.state_dict().items()} if model is not None else None,
                   "prior_quantiles": prior.tolist() if model is None else None,
                   "mean": mean.tolist(), "scale": scale.tolist(), "target_scale": target_scale,
                   "quantiles": list(QUANTILES), "feature_order": spec["feature_order"],
                   "dataset_manifest_sha256": digest(Path(dataset) / "manifest.json"),
                   "scope": "development_only", "calibrated": False}
        torch.save(payload, out / (name + ".pt"))
        np.save(out / (name + "_evaluation.npy"), forecasts[name], allow_pickle=False)
    report = {"status": "development_engineering_only", "comparison_count": 4,
              "declared_views": {name: list(indexes) for name, indexes in VIEWS.items()},
              "epochs": epochs, "seed": seed, "device": device, "pretraining": False,
              "dataset_manifest": spec, "dataset_manifest_sha256": digest(Path(dataset) / "manifest.json"),
              "git_revision": git_revision(Path(__file__).parent),
              "code_sha256": {name: digest(Path(__file__).with_name(name)) for name in
                              ("execution_risk_train.py", "execution_risk_model.py", "execution_model.py", "execution_action_model.py", "execution_risk_dataset.py")},
              "normalizer": {"mean": mean.tolist(), "scale": scale.tolist(), "target_scale": target_scale},
              "losses": losses, "role_sessions": role_sessions,
              "role_cases": {name: int(sum(roles == i)) for i, name in enumerate(spec["partitions"])},
              "gate_metrics": gate, "gate_selected": selected, "evaluation_metrics": scores,
              "evaluation_by_session": session_scores, "unused_roles": ["specialist_calibration", "pool_calibration"],
              "environment": {"python": platform.python_version(), "numpy": np.__version__, "torch": torch.__version__},
              "artifacts": {path.name: digest(path) for path in out.iterdir()},
              "limitations": ["previously inspected development cases; no fresh OOS or trading edge",
                              "correlated heads and sessions; candidate size expansion adds no independent cases",
                              "three quantiles, no calibrated full density, confidence guarantee or joint tails",
                              "uncalibrated; coverage is a descriptive diagnostic, especially at zero-mass atoms",
                              "scarce used roles: " + ", ".join(scarce),
                              "known entry costs are hypothetical snapshot calculations; no latency/fills/own impact/funding/exit cost evaluation"]}
    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--allow-development-smoke", action="store_true")
    args = parser.parse_args()
    report = run(args.dataset, args.output, device=args.device, allow_development_smoke=args.allow_development_smoke)
    print(json.dumps({"selected": report["gate_selected"], "scores": report["evaluation_metrics"]}, indent=2))
