"""Run fixed baseline comparisons on an explicit development panel or synthetic fixture."""
import argparse
import csv
import hashlib
import json
import platform
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
from .core import BASELINES, Factor, Panel, fit, attribute, evaluate


def fixture():
    rng = np.random.default_rng(19)
    n, assets = 420, ("owner", "contractor", "equipment", "unrelated")
    ids = ("MKT", "SMB", "HML", "RMW", "CMA", "MOM")
    specs = tuple(Factor(f, "market" if f == "MKT" else "style", f,
                         "return_factor", "decimal_return", "synthetic", f) for f in ids)
    x = rng.normal(0, 0.01, (n, len(ids)))
    x[:, 2] += 0.5 * x[:, 1]
    beta = np.array([[1.1, 1.2, 0.9, 0.7], [0.2, 0.4, 0.1, 0.0],
                     [-0.2, 0.3, 0.5, 0.1], [0.1, -0.2, 0.4, 0.2],
                     [0.3, 0.1, -0.2, 0.0], [0.1, 0.3, 0.2, -0.2]])
    shared_unobserved = rng.normal(0, 0.005, (n, 1))
    y = x @ beta + rng.normal(0, 0.004, (n, 4)) + shared_unobserved @ np.array([[1, 1, 1, 0]])
    start = datetime(2020, 1, 1, 21, tzinfo=timezone.utc)
    stamps = tuple((start + timedelta(days=i)).isoformat() for i in range(n))
    available = tuple((start + timedelta(days=i, hours=1)).isoformat() for i in range(n))
    return Panel(stamps, available, y, x, assets, specs, "USD", "synthetic_day", "synthetic", "seed19-v1")


def load_panel(path):
    """JSON deliberately requires an explicit clock and immutable version for each export."""
    raw = json.loads(Path(path).read_text())
    rows = raw["rows"]
    specs = tuple(Factor(**f) for f in raw["factor_specs"])
    assets = tuple(raw["assets"])
    return Panel(tuple(r["period_end"] for r in rows), tuple(r["available_at"] for r in rows),
                 np.array([[r["excess_returns"][a] for a in assets] for r in rows], float),
                 np.array([[r["factors"][f.id] for f in specs] for r in rows], float),
                 assets, specs, raw["currency"], raw["horizon"], raw["study_role"], raw["source_version"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    data = parser.add_mutually_exclusive_group(required=True)
    data.add_argument("--synthetic", action="store_true")
    data.add_argument("--panel", type=Path)
    parser.add_argument("--cutoff", help="ISO training cutoff; includes data availability")
    parser.add_argument("--weights", help="comma-separated signed NAV weights in panel asset order")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--garch", action="store_true", help="also fit optional CCC-GARCH risk models")
    args = parser.parse_args()
    panel = fixture() if args.synthetic else load_panel(args.panel)
    panel.validate()
    if not args.synthetic and (not args.cutoff or not args.weights):
        parser.error("real development panels require a predeclared cutoff and weights")
    cutoff = args.cutoff or panel.available_at[299]
    from .core import clock
    later = np.array([clock(t) > clock(cutoff) for t in panel.times])
    evaluation = panel.subset(later)
    weights = np.array([float(x) for x in args.weights.split(",")]) if args.weights else np.array([0.4, 0.3, 0.2, 0.1])
    available_ids = {f.id for f in panel.specs}
    report = {"study_role": panel.study_role, "source_version": panel.source_version,
              "runtime": {"python": platform.python_version(), "numpy": np.__version__},
              "code_sha256": {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                              for name in ("core.py", "run.py")},
              "factor_specs": [asdict(f) for f in panel.specs],
              "cutoff": cutoff,
              "input_sha256": hashlib.sha256(args.panel.read_bytes()).hexdigest() if args.panel else None,
              "weights": weights.tolist(), "models": {}, "skipped": {},
              "warning": "No strategy P&L, causal discovery, sealed test or universal risk identification."}
    artifacts = {}
    garch_artifacts = {}
    if args.garch:
        from importlib.metadata import version
        from .garch import fit_garch, compare_risk
        report["runtime"].update({name: version(name) for name in ("arch", "scipy", "pandas")})
        report["code_sha256"]["garch.py"] = hashlib.sha256(Path(__file__).with_name("garch.py").read_bytes()).hexdigest()
    # Fixed grid; never automatically select the best evaluation result.
    for name, ids in BASELINES.items():
        if not set(ids) <= available_ids:
            report["skipped"][name] = "required factors absent"
            continue
        model = fit(panel, cutoff, ids, covariance_method="ewma", shrinkage=0.05)
        report["models"][name] = {"diagnostics": model.diagnostics,
                                   "risk": attribute(model, weights),
                                   "evaluation": evaluate(model, evaluation)}
        artifacts[name] = model
        if args.garch:
            try:
                risk = fit_garch(panel, cutoff, ids)
                comparison, variance_forecasts = compare_risk(risk, panel, weights)
                report["models"][name]["garch"] = {
                    "status": "fitted", "diagnostics": risk.diagnostics,
                    "next_period_risk": attribute(risk.at_horizon(), weights),
                    "comparison": comparison}
                garch_artifacts[name] = (risk, variance_forecasts)
            except ValueError as exc:
                report["models"][name]["garch"] = {"status": "rejected", "reason": str(exc)}
    if not artifacts:
        raise ValueError("no baseline can be fitted")
    args.output.mkdir(parents=True, exist_ok=False)
    capm_mse = report["models"].get("CAPM", {}).get("evaluation", {}).get("residual_mse")
    if capm_mse is not None:
        for record in report["models"].values():
            record["evaluation"]["mse_change_vs_CAPM"] = record["evaluation"]["residual_mse"] - capm_mse
    for name, model in artifacts.items():
        np.savez(args.output / f"{name}.npz", beta=model.beta, intercept=model.intercept,
                 factor_mean=model.factor_mean, joint_cov=model.joint_cov,
                 factor_ids=np.array([f.id for f in model.specs]), assets=np.array(model.assets))
    for name, (risk, forecasts) in garch_artifacts.items():
        np.savez(args.output / f"{name}_garch.npz", parameters=risk.parameters,
                 next_variance=risk.next_variance, correlation=risk.correlation,
                 evaluation_period_end=np.array(evaluation.times), **forecasts)
    with (args.output / "exposures.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["model", "asset", "factor", "beta"])
        for name, model in artifacts.items():
            for i, spec in enumerate(model.specs):
                for j, asset in enumerate(model.assets):
                    writer.writerow([name, asset, spec.id, model.beta[i, j]])
    report["artifact_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted(args.output.iterdir()) if p.is_file()}
    (args.output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"models": list(artifacts), "output": str(args.output), "role": panel.study_role}))


if __name__ == "__main__":
    main()
