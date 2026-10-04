"""Descriptive, retrospective comparison of FF5 with a 12-industry control block.

This is a sensitivity audit, not a forecast or a factor-selection procedure. It
intentionally accepts the quarantined retrospective panel while refusing sealed
or production-labelled input. The audit reports overlap and in-sample fit only.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from .core import clock

MAX_DEVELOPMENT_PERIOD_END = "2024-10-02"


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _design(values):
    values = np.asarray(values, dtype=float)
    return np.column_stack((np.ones(len(values)), values))


def _fit(values, returns, asset_names):
    design = _design(values)
    if np.linalg.matrix_rank(design) != design.shape[1]:
        raise ValueError("factor block is rank-deficient with an intercept")
    coefficient = np.linalg.lstsq(design, returns, rcond=None)[0]
    residual = returns - design @ coefficient
    centered = returns - returns.mean(axis=0)
    sst = np.square(centered).sum(axis=0)
    if np.any(sst <= 0):
        raise ValueError("each asset must have nonzero return variance")
    ssr = np.square(residual).sum(axis=0)
    r_squared = 1.0 - ssr / sst
    n, p = design.shape[0], design.shape[1] - 1
    adjusted = 1.0 - (1.0 - r_squared) * (n - 1) / (n - p - 1)
    covariance = np.atleast_2d(np.cov(residual, rowvar=False, ddof=1))
    eigenvalues = np.linalg.eigvalsh(covariance)
    residual_scale = residual.std(axis=0, ddof=1)
    denominator = np.outer(residual_scale, residual_scale)
    residual_correlation = np.divide(covariance, denominator,
                                     out=np.full_like(covariance, np.nan),
                                     where=denominator > 0)
    pairs = []
    for i, left in enumerate(asset_names):
        for j in range(i + 1, len(asset_names)):
            pairs.append({"left": left, "right": asset_names[j],
                          "correlation": float(residual_correlation[i, j])
                          if residual_scale[i] > 0 and residual_scale[j] > 0 else None})
    total_eigenvalue = float(eigenvalues.sum())
    centered_x = values - values.mean(axis=0)
    scales = centered_x.std(axis=0, ddof=0)
    standardized = centered_x / scales
    factor_correlation = np.atleast_2d(np.corrcoef(standardized, rowvar=False))
    off_diagonal = factor_correlation - np.eye(values.shape[1])
    return residual, {
        "factor_count": int(values.shape[1]),
        "design_rank": int(np.linalg.matrix_rank(design)),
        "design_columns_including_intercept": int(design.shape[1]),
        "r_squared": dict(zip(asset_names, map(float, r_squared))),
        "adjusted_r_squared": dict(zip(asset_names, map(float, adjusted))),
        "residual_mse": dict(zip(asset_names, map(float, np.square(residual).mean(axis=0)))),
        "standardized_factor_condition_number": float(np.linalg.cond(standardized)),
        "maximum_absolute_factor_correlation": float(np.max(np.abs(off_diagonal)))
            if off_diagonal.size else 0.0,
        "residual_pair_correlations": pairs,
        "residual_leading_eigenvalue_share": float(eigenvalues[-1] / total_eigenvalue)
            if total_eigenvalue > 0 else None,
    }


def audit(panel_path, industry_path, base_factor_ids=("MKT", "SMB", "HML", "RMW", "CMA")):
    """Compare a declared base model with its base-plus-industry nested model."""
    panel_path, industry_path = Path(panel_path), Path(industry_path)
    panel = json.loads(panel_path.read_text())
    if panel.get("study_role") != "retrospective_only":
        raise ValueError("industry audit requires the quarantined retrospective-only development panel")
    assets = panel.get("assets")
    rows = panel.get("rows")
    specs = panel.get("factor_specs")
    if not assets or not rows or not specs:
        raise ValueError("panel requires assets, rows and factor metadata")
    if len(set(assets)) != len(assets) or len(set(base_factor_ids)) != len(base_factor_ids):
        raise ValueError("asset and base factor identifiers must be unique")
    factor_by_id = {spec["id"]: spec for spec in specs}
    if len(factor_by_id) != len(specs):
        raise ValueError("duplicate factor ids in panel")
    if not set(base_factor_ids) <= factor_by_id.keys():
        raise ValueError("a requested base factor is absent")
    times = [row["period_end"] for row in rows]
    parsed_times = [clock(value) for value in times]
    if parsed_times != sorted(parsed_times) or len(set(parsed_times)) != len(parsed_times):
        raise ValueError("panel dates must be unique and chronological")
    if times[-1][:10] > MAX_DEVELOPMENT_PERIOD_END:
        raise ValueError("panel extends into or past the sealed holdout boundary")
    for row, period_end in zip(rows, parsed_times):
        if clock(row["available_at"]) < period_end:
            raise ValueError("panel availability precedes its period end")
    returns = np.asarray([[row["excess_returns"][asset] for asset in assets]
                          for row in rows], dtype=float)
    base = np.asarray([[row["factors"][factor_id] for factor_id in base_factor_ids]
                       for row in rows], dtype=float)
    if not np.isfinite(returns).all() or not np.isfinite(base).all():
        raise ValueError("panel contains non-finite values")
    with industry_path.open(newline="") as stream:
        industry_rows = list(csv.DictReader(stream))
    if len(industry_rows) != len(rows):
        raise ValueError("industry controls do not cover every panel row")
    control_ids = [key for key in industry_rows[0]
                   if key not in {"session", "period_end", "available_at"}]
    if not control_ids or len(set(control_ids)) != len(control_ids):
        raise ValueError("industry control columns must be named and unique")
    for index, (panel_row, control_row) in enumerate(zip(rows, industry_rows)):
        if control_row.get("session") != panel_row["period_end"][:10]:
            raise ValueError(f"industry control date mismatch at row {index}")
        if control_row.get("period_end") != panel_row["period_end"]:
            raise ValueError(f"industry period-end mismatch at row {index}")
        if clock(control_row["available_at"]) < clock(control_row["period_end"]):
            raise ValueError(f"industry availability precedes period end at row {index}")
    controls = np.asarray([[float(row[key]) for key in control_ids]
                           for row in industry_rows], dtype=float)
    if not np.isfinite(controls).all():
        raise ValueError("industry controls contain non-finite values")
    base_residual, base_report = _fit(base, returns, assets)
    augmented_residual, augmented_report = _fit(np.column_stack((base, controls)), returns, assets)
    delta = {asset: augmented_report["r_squared"][asset] - base_report["r_squared"][asset]
             for asset in assets}
    partial_r_squared = {}
    for index, asset in enumerate(assets):
        denominator = float(np.square(base_residual[:, index]).sum())
        numerator = float(np.square(augmented_residual[:, index]).sum())
        partial_r_squared[asset] = 1.0 - numerator / denominator if denominator > 0 else None
    return {
        "study_role": panel["study_role"],
        "label": "retrospective in-sample sensitivity; not forecast, alpha, causal attribution, or hedge evidence",
        "window": {"first_period_end": times[0], "last_period_end": times[-1], "rows": len(rows)},
        "source_version": panel.get("source_version"),
        "assets": assets,
        "base_factor_ids": list(base_factor_ids),
        "industry_control_ids": control_ids,
        "industry_controls_are_asset_matched": False,
        "models": {"base": base_report, "base_plus_industry12": augmented_report},
        "incremental": {"r_squared_change": delta, "partial_r_squared": partial_r_squared},
        "limitations": [
            "The industry block uses all 12 broad research portfolios; it is not an issuer-to-industry mapping.",
            "The current revised factor and price histories do not establish historical point-in-time availability.",
            "In-sample fit gains with 12 additional regressors are descriptive and are not evidence of a strategy edge.",
            "High overlap can redistribute coefficients; residual structure remains unnamed and unexplained.",
            "The panel cutoff is enforced in code at 2024-10-02; later rows are rejected.",
        ],
        "input_sha256": {"panel": _sha256(panel_path), "industry_controls": _sha256(industry_path)},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--industry-controls", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-factors", default="MKT,SMB,HML,RMW,CMA")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output exists; choose a new path to preserve prior audit artifacts")
    report = audit(args.panel, args.industry_controls,
                   tuple(x for x in args.base_factors.split(",") if x))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output), "rows": report["window"]["rows"],
                      "study_role": report["study_role"], "label": report["label"]}))


if __name__ == "__main__":
    main()
