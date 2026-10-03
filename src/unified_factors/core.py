"""Small, explicit linear factor baseline with full residual covariance.

All returns are per-period excess returns in decimal units and one declared currency.
Factor columns are realized returns/changes, NOT known future predictors. Attribution
on a later panel is retrospective. Covariance forecasts use training observations only.
"""
from dataclasses import dataclass
from datetime import datetime
import numpy as np

BASELINES = {
    "CAPM": ("MKT",),
    "FF3": ("MKT", "SMB", "HML"),
    "Carhart4": ("MKT", "SMB", "HML", "MOM"),
    "FF5": ("MKT", "SMB", "HML", "RMW", "CMA"),
    "FF5_MOM": ("MKT", "SMB", "HML", "RMW", "CMA", "MOM"),
}


def clock(value):
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("timestamps must include timezone")
    return stamp


@dataclass(frozen=True)
class Factor:
    id: str
    family: str
    economic_channel: str
    role: str  # return_factor, macro_shock, mechanism_signal, latent
    unit: str
    source: str
    canonical_id: str
    hedge: str = "unverified"
    evidence: str = "hypothesis"


def validate_factors(factors):
    if not factors or len({f.id for f in factors}) != len(factors):
        raise ValueError("factor ids must be nonempty and unique")
    if len({f.canonical_id for f in factors}) != len(factors):
        raise ValueError("duplicate canonical factors: aliases cannot count twice")
    for f in factors:
        if not all((f.id, f.family, f.economic_channel, f.unit, f.source, f.canonical_id)):
            raise ValueError("factor metadata incomplete")
        if f.role not in {"return_factor", "macro_shock", "mechanism_signal", "latent"}:
            raise ValueError("unknown factor role")


@dataclass
class Panel:
    times: tuple[str, ...]
    available_at: tuple[str, ...]  # latest availability of ANY value used in row
    returns: np.ndarray
    factors: np.ndarray
    assets: tuple[str, ...]
    specs: tuple[Factor, ...]
    currency: str
    horizon: str
    study_role: str
    source_version: str

    def validate(self):
        validate_factors(self.specs)
        n = len(self.times)
        if self.study_role not in {"synthetic", "development"}:
            raise ValueError("sealed/production studies are not authorized by this runner")
        if not self.currency or not self.horizon or not self.source_version:
            raise ValueError("currency, horizon and immutable source version required")
        if not self.assets or len(set(self.assets)) != len(self.assets):
            raise ValueError("unique assets required")
        t = [clock(v) for v in self.times]
        if n < 3 or t != sorted(t) or len(set(t)) != n:
            raise ValueError("at least three unique chronological observations required")
        if len(self.available_at) != n:
            raise ValueError("availability length mismatch")
        if any(clock(a) < b for a, b in zip(self.available_at, t)):
            raise ValueError("realized returns cannot be available before period end")
        for x, width in ((self.returns, len(self.assets)), (self.factors, len(self.specs))):
            if np.asarray(x).shape != (n, width) or not np.isfinite(x).all():
                raise ValueError("finite, aligned, complete numerical panel required; no implicit imputation")

    def subset(self, mask):
        indices = np.flatnonzero(mask)
        return Panel(tuple(self.times[i] for i in indices),
                     tuple(self.available_at[i] for i in indices),
                     self.returns[indices], self.factors[indices], self.assets,
                     self.specs, self.currency, self.horizon, self.study_role, self.source_version)


def covariance(x, method="sample", decay=0.97, shrinkage=0.0):
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or len(x) < 3 or not np.isfinite(x).all():
        raise ValueError("finite 2D covariance input required")
    if not 0 <= shrinkage <= 1:
        raise ValueError("shrinkage must be in [0,1]")
    if method == "sample":
        c = np.atleast_2d(np.cov(x, rowvar=False, ddof=1))
    elif method == "ewma":
        if not 0 < decay < 1:
            raise ValueError("EWMA decay must be in (0,1)")
        weights = decay ** np.arange(len(x) - 1, -1, -1)
        weights /= weights.sum()
        centered = x - weights @ x
        c = (centered * weights[:, None]).T @ centered / (1 - weights @ weights)
    else:
        raise ValueError("supported covariance estimators: sample, ewma")
    # Fixed diagonal shrinkage, NOT an estimated Ledoit-Wolf shrinkage intensity.
    return (1 - shrinkage) * c + shrinkage * np.diag(np.diag(c))


def overlap(x, specs):
    validate_factors(specs)
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or x.shape[1] != len(specs) or len(x) < 3 or not np.isfinite(x).all():
        raise ValueError("invalid factor matrix")
    scale = x.std(axis=0)
    if np.any(scale <= 1e-14):
        raise ValueError("constant factor is not identifiable alongside the intercept")
    z = (x - x.mean(axis=0)) / scale
    rank = int(np.linalg.matrix_rank(z))
    corr = np.atleast_2d(np.corrcoef(z, rowvar=False))
    pairs = [{"left": specs[i].id, "right": specs[j].id,
              "correlation": float(corr[i, j])}
             for i in range(len(specs)) for j in range(i + 1, len(specs))
             if abs(corr[i, j]) >= 0.8]
    vif = {}
    for j, spec in enumerate(specs):
        others = np.delete(z, j, axis=1)
        residual = z[:, j] - others @ np.linalg.lstsq(others, z[:, j], rcond=None)[0]
        fraction = float(residual @ residual / (z[:, j] @ z[:, j]))
        vif[spec.id] = None if fraction < 1e-12 else 1 / fraction
    return {"rank": rank, "columns": len(specs),
            "condition_number": float(np.linalg.cond(z)) if rank == len(specs) else None,
            "correlated_pairs": pairs, "vif": vif}


@dataclass
class Fitted:
    specs: tuple[Factor, ...]
    assets: tuple[str, ...]
    currency: str
    horizon: str
    fitted_at: str
    intercept: np.ndarray
    beta: np.ndarray  # factors x assets
    factor_mean: np.ndarray
    joint_cov: np.ndarray  # [factors, all asset residuals], retaining cross terms
    diagnostics: dict


def fit(panel, cutoff, factor_ids, covariance_method="sample", decay=0.97, shrinkage=0.0):
    panel.validate()
    if len(set(factor_ids)) != len(factor_ids) or not factor_ids:
        raise ValueError("unique requested factors required")
    index = {f.id: j for j, f in enumerate(panel.specs)}
    if not set(factor_ids) <= index.keys():
        raise ValueError("requested factor absent")
    cols = [index[f] for f in factor_ids]
    # A value dated before cutoff but published later is excluded, not backfilled.
    mask = np.array([clock(t) <= clock(cutoff) and clock(a) <= clock(cutoff)
                     for t, a in zip(panel.times, panel.available_at)])
    x = panel.factors[mask][:, cols]
    y = panel.returns[mask]
    if len(x) < max(20, 3 * (len(cols) + 1)):
        raise ValueError("insufficient training observations")
    specs = tuple(panel.specs[j] for j in cols)
    diagnostics = overlap(x, specs)
    if diagnostics["rank"] != len(cols):
        raise ValueError("rank-deficient factors: unique exposure attribution is impossible")
    scale = x.std(axis=0)
    design = np.column_stack([np.ones(len(x)), (x - x.mean(axis=0)) / scale])
    coeff = np.linalg.lstsq(design, y, rcond=None)[0]
    beta = coeff[1:] / scale[:, None]
    intercept = coeff[0] - x.mean(axis=0) @ beta
    residual = y - intercept - x @ beta
    joint = covariance(np.column_stack([x, residual]), covariance_method, decay, shrinkage)
    diagnostics.update(training_rows=int(mask.sum()), covariance_method=covariance_method,
                       decay=decay, fixed_diagonal_shrinkage=shrinkage,
                       source_version=panel.source_version)
    return Fitted(specs, panel.assets, panel.currency, panel.horizon, cutoff,
                  intercept, beta, x.mean(axis=0), joint, diagnostics)


def attribute(model, weights):
    """Signed Euler VARIANCE contributions sum to total variance, including overlaps.

    Each covariance cross term is allocated symmetrically through v*(C@v).
    This accounting convention is not unique causal identification.
    """
    w = np.asarray(weights, dtype=float)
    if w.shape != (len(model.assets),) or not np.isfinite(w).all():
        raise ValueError("one finite signed NAV weight per asset required")
    k = len(model.specs)
    b = model.beta @ w
    v = np.r_[b, w]
    c = model.joint_cov
    contributions = v * (c @ v)
    variance = float(v @ c @ v)
    factors = {f.id: float(contributions[j]) for j, f in enumerate(model.specs)}
    families = {}
    for f in model.specs:
        families[f.family] = families.get(f.family, 0.0) + factors[f.id]
    residual = c[k:, k:]
    residual_variance = float(w @ residual @ w)
    diagonal_only = float(w @ np.diag(np.diag(residual)) @ w)
    residual_eigen = np.linalg.eigvalsh(residual)
    return {"variance": variance, "volatility": float(np.sqrt(max(variance, 0))),
            "factor_exposures": dict(zip((f.id for f in model.specs), map(float, b))),
            "factor_variance_contributions": factors, "family_variance_contributions": families,
            "unexplained_variance_contribution": float(contributions[k:].sum()),
            "asset_residual_variance_contributions": dict(zip(model.assets, map(float, contributions[k:]))),
            "factor_block_variance": float(b @ c[:k, :k] @ b),
            "residual_block_variance": residual_variance,
            "factor_residual_cross_variance": float(2 * b @ c[:k, k:] @ w),
            "residual_variance_if_uncorrelated": diagonal_only,
            "residual_off_diagonal_effect": residual_variance - diagonal_only,
            "residual_leading_eigenvalue_share": float(residual_eigen[-1] / residual_eigen.sum())
                if residual_eigen.sum() > 1e-20 else None,
            "reconciliation_error": float(contributions.sum() - variance),
            "scope": {"currency": model.currency, "horizon": model.horizon,
                      "assets": list(model.assets), "fitted_at": model.fitted_at},
            "interpretation": "residual is unexplained, not proven diversifiable; signed contributions may be negative"}


def evaluate(model, panel):
    """Frozen-loading retrospective evaluation, NOT a forecast using tomorrow's factors."""
    panel.validate()
    if panel.assets != model.assets or panel.currency != model.currency or panel.horizon != model.horizon:
        raise ValueError("evaluation schema differs from fitted schema")
    if any(clock(t) <= clock(model.fitted_at) for t in panel.times):
        raise ValueError("evaluation must follow training cutoff")
    by_id = {f.id: j for j, f in enumerate(panel.specs)}
    if any(f.id not in by_id or panel.specs[by_id[f.id]] != f for f in model.specs):
        raise ValueError("factor semantics changed")
    x = panel.factors[:, [by_id[f.id] for f in model.specs]]
    error = panel.returns - model.intercept - x @ model.beta
    # Constant training mean is a descriptive comparator, not a tradable forecast claim.
    reference = panel.returns - (model.intercept + model.factor_mean @ model.beta)
    numerator = float(np.square(error).sum())
    denominator = float(np.square(reference).sum())
    return {"rows": len(x), "residual_mse": float(np.square(error).mean()),
            "pooled_r2_vs_training_mean": 1 - numerator / denominator if denominator > 0 else None,
            "label": "development retrospective attribution; realized contemporaneous factors used"}


def hedge_projection(exposure, hedge_exposures):
    """Unconstrained exposure-span diagnostic in caller-scaled factor coordinates.

    No claim of executable hedge: no costs, liquidity, margin, bounds or basis risk.
    Columns are candidate hedge instruments. Must use a declared common scaling.
    """
    b, h = np.asarray(exposure, float), np.asarray(hedge_exposures, float)
    if b.ndim != 1 or h.ndim != 2 or h.shape[0] != len(b) or not np.isfinite(b).all() or not np.isfinite(h).all():
        raise ValueError("invalid hedge coordinates")
    positions = np.linalg.lstsq(h, -b, rcond=None)[0]
    remainder = b + h @ positions
    return {"unconstrained_positions": positions.tolist(), "unspanned_exposure": remainder.tolist(),
            "hedge_matrix_rank": int(np.linalg.matrix_rank(h)), "executable": False}
