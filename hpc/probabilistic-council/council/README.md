# Council runtime API

Contract: `council-distribution-0.2.0`. Python standard library only; compatible with Python 3.9+.

## Modules

- `distributions.py` defines immutable `SpecialistForecast` objects. Every output carries an ordered
  outcome space, complete probability vector, context, forecast/validity timestamps, information
  cutoff, model/data versions, optional epistemic uncertainty, and abstention status. Timestamps
  must be timezone-aware and satisfy `information_cutoff <= forecast_time < valid_until`. Joint
  forecasts can declare named dimensions and one state tuple per probability; `marginalize()` keeps
  the fitted joint distribution intact while deriving a requested marginal.
- `calibration.py` fits multiclass temperature scaling by minimum log loss.
- `gating.py` learns global and sufficiently supported context weights from multiclass Brier loss.
  A minimum weight prevents any specialist from receiving zero weight during fit.
- `fusion.py` implements linear and normalized logarithmic opinion pools. Linear pooling preserves
  dependence when labels enumerate a joint state space; neither pool assumes independent experts.
- `council.py` fits specialist calibration, the context gate, and final pool calibration from three
  separately supplied partitions. `predict()` handles an abstaining subset by renormalizing active
  weights, and returns the final distribution, entropy, disagreement proxy, and input uncertainty.
  `predict_parallel()` runs specialist callables in a bounded thread pool before fusion; it makes no
  latency guarantee and propagates a specialist failure with its identity.
- `jevlike_adapter.py` wraps an initialized JevLike scorer as a categorical specialist, preserving
  caller-supplied option order and requiring explicit model/data version strings. The separate C++
  `JevLikeTinyScorer` supports the exported tiny byte encoder.

## Minimal use

Construct `LabeledCase` rows for each fit partition, then call:

```python
model = CouncilModel.fit(
    specialist_calibration_cases,
    gate_fit_cases,
    pool_calibration_cases,
    fusion_method="linear",
)
prediction = model.predict(forecasts_for_one_decision)
```

The forecast `outcome_space` order and any joint-state schema must match across specialists and
partitions. Joint/multivariate forecasts enumerate their joint states; the API does not silently
infer dependence from marginal distributions. Every `LabeledCase` has a stable `case_id`; the fit
method rejects repeated cases across fit partitions and requires strictly chronological specialist
calibration, gate-fit, then pool-calibration windows. Predictions must be later than the latest fit
timestamp. The caller still owns the final evaluation split and must keep it out of every fit method.

## Scope limits

Temperature scaling, inverse-Brier reliability weights, and opinion pools are transparent baselines.
The disagreement value is a between-model diagnostic, not a complete Bayesian epistemic posterior;
entropy is the final distribution's predictive entropy. All-abstain behavior deliberately raises
instead of inventing a fallback. There is no data loader, persisted model registry, online update
path, execution policy, or quantum runtime in this package yet. The JevLike adapter is an inference
seam only; it does not fine-tune JevLike or calibrate its raw output. See the parent `STACK.md` for
the implementation plan and current limitations.
