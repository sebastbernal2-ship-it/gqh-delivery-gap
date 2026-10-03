"""Two-stage Gaussian QML GARCH(1,1) with constant conditional correlation.

OLS loadings/means and all volatility parameters are fitted before evaluation.
This is a CCC risk baseline, not joint multivariate maximum likelihood or DCC.
"""
from dataclasses import dataclass, replace
import numpy as np
from .core import clock, covariance, fit


@dataclass
class GarchRisk:
    model: object
    parameters: np.ndarray  # omega, alpha, beta in original squared units
    next_variance: np.ndarray
    correlation: np.ndarray
    diagnostics: dict

    def forecast(self, steps=1):
        """Marginal per-period covariance at horizons 1..steps; NOT cumulative risk."""
        if not isinstance(steps, int) or steps < 1:
            raise ValueError("positive integer forecast horizon required")
        omega, alpha, beta = self.parameters.T
        h = self.next_variance.copy()
        result = []
        for _ in range(steps):
            d = np.sqrt(h)
            result.append(self.correlation * np.outer(d, d))
            h = omega + (alpha + beta) * h
        return np.array(result)

    def at_horizon(self, horizon=1):
        return replace(self.model, joint_cov=self.forecast(horizon)[-1],
                       diagnostics={**self.model.diagnostics, "covariance_method": "CCC_GARCH11",
                                    "forecast_horizon_periods": horizon})


def fit_garch(panel, cutoff, factor_ids, correlation_shrinkage=0.05):
    """Fit only a complete available training prefix; each row must be one session.

    The caller attests no missing sessions. Gaps caused by delayed publication fail
    instead of silently compressing the volatility clock. Gaussian QML estimates
    second moments; it is not a Gaussian tail-distribution claim.
    """
    from arch import arch_model
    panel.validate()
    if not 0 <= correlation_shrinkage <= 1:
        raise ValueError("correlation shrinkage must be in [0,1]")
    end = clock(cutoff)
    historic = np.array([clock(t) <= end for t in panel.times])
    if any(clock(a) > end for a, past in zip(panel.available_at, historic) if past):
        raise ValueError("GARCH requires a complete available training prefix; delayed rows present")
    if historic.sum() < 100:
        raise ValueError("GARCH requires at least 100 training observations; this is a numerical floor, not adequacy")
    model = fit(panel, cutoff, factor_ids)
    cols = [{f.id: j for j, f in enumerate(panel.specs)}[f] for f in factor_ids]
    x = panel.factors[historic][:, cols]
    residual = panel.returns[historic] - model.intercept - x @ model.beta
    innovations = np.column_stack([x - model.factor_mean, residual])
    parameters, forecasts, standardized, records = [], [], [], []
    for j in range(innovations.shape[1]):
        series = innovations[:, j]
        scale = float(np.sqrt(np.mean(series ** 2)))
        if scale < 1e-12:
            raise ValueError("zero-variance component cannot support a GARCH fit")
        result = arch_model(series / scale, mean="Zero", vol="GARCH", p=1, q=1,
                            dist="normal", rescale=False).fit(disp="off", show_warning=False)
        p = result.params
        omega, alpha, beta = float(p["omega"]) * scale ** 2, float(p["alpha[1]"]), float(p["beta[1]"])
        if result.convergence_flag != 0:
            raise ValueError(f"GARCH optimizer failed for component {j}: {result.optimization_result.message}")
        if not (omega > 0 and alpha >= 0 and beta >= 0 and alpha + beta < 1 - 1e-8):
            raise ValueError(f"GARCH component {j} is invalid or nonstationary; no silent fallback")
        h_last = float(result.conditional_volatility[-1] ** 2) * scale ** 2
        h_next = omega + alpha * series[-1] ** 2 + beta * h_last
        parameters.append([omega, alpha, beta])
        forecasts.append(h_next)
        standardized.append(np.asarray(result.std_resid))
        records.append({"component": j, "omega": omega, "alpha": alpha, "beta": beta,
                        "persistence": alpha + beta, "convergence_flag": int(result.convergence_flag),
                        "near_boundary": bool(alpha + beta > .995 or min(alpha, beta) < 1e-6)})
    corr = np.corrcoef(np.array(standardized))
    corr = (1 - correlation_shrinkage) * corr + correlation_shrinkage * np.eye(len(corr))
    return GarchRisk(model, np.array(parameters), np.array(forecasts), corr,
                     {"components": records, "training_rows": int(historic.sum()),
                      "correlation_shrinkage": correlation_shrinkage,
                      "component_order": [f"factor:{f.id}" for f in model.specs] +
                                         [f"residual:{a}" for a in model.assets],
                      "method": "two-stage Gaussian QML; constant standardized-innovation correlation",
                      "limitations": "fixed means/betas/correlation; no leverage asymmetry, jumps or tail guarantee"})


def compare_risk(risk, panel, weights):
    """Single frozen origin, no evaluation refits or state updates, no OOS selection.

    Score period-specific portfolio squared innovations against three variance
    forecasts. log(h)+e^2/h is Gaussian QLIKE up to an outcome-only constant.
    """
    from .core import evaluate
    model = risk.model
    later = np.array([clock(t) > clock(model.fitted_at) for t in panel.times])
    evaluation = panel.subset(later)
    evaluate(model, evaluation)  # strict schema and time checks
    w = np.asarray(weights, float)
    if w.shape != (len(model.assets),) or not np.isfinite(w).all():
        raise ValueError("one finite weight per asset required")
    v = np.r_[model.beta @ w, w]
    train = np.array([clock(t) <= clock(model.fitted_at) for t in panel.times])
    if any(clock(a) > clock(model.fitted_at) for a, included in zip(panel.available_at, train) if included):
        raise ValueError("unavailable training row")
    y = panel.returns[train]
    errors = (evaluation.returns - (model.intercept + model.factor_mean @ model.beta)) @ w
    n = len(errors)
    forecasts = {"sample": np.repeat(float(w @ covariance(y) @ w), n),
                 "EWMA": np.repeat(float(w @ covariance(y, "ewma") @ w), n),
                 "CCC_GARCH11": np.einsum("i,tij,j->t", v, risk.forecast(n), v)}
    scores = {}
    for name, h in forecasts.items():
        if np.any(h <= 0) or not np.isfinite(h).all():
            raise ValueError("strictly positive finite portfolio variance required for QLIKE")
        scores[name] = {"mean_qlike": float(np.mean(np.log(h) + errors ** 2 / h)),
                        "variance_mse": float(np.mean((h - errors ** 2) ** 2)),
                        "realized_to_forecast_variance": float(np.sum(errors ** 2) / np.sum(h))}
    return {"design": "single-origin marginal variance forecasts; frozen training fit; lower QLIKE/MSE is better",
            "evaluation_rows": n, "scores": scores,
            "warning": "squared returns are noisy variance proxies; no winner selected, no trading performance"}, forecasts
