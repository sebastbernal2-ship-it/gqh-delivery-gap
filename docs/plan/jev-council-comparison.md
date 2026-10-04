# Declared comparison: the council against every single specialist and the references

Status: declared before the run, development only. Owner: sebas. Date: 2026-10-04.

## Question

Does the calibrated council beat every single checkpoint and the training-prevalence reference on
the evaluation role of the execution-risk cache, in pinball loss and in proper categorical scores,
and does the quantile-to-categorical conversion change the ranking?

## Data

The execution-risk cache prepared by `execution_risk_dataset.py`: `features.npy` of shape
(cases, 16, 24), `targets.npy` of shape (cases, 3, 2, 2) continuous in basis points, `roles.npy`
with 0 training, 1 specialist calibration, 2 gate fit, 3 pool calibration and 4 evaluation, and
`clocks.npy`. Roles keep their existing chronological assignment. No case moves between roles.

## Specialists

The nine published checkpoints in `hpc/probabilistic-council/checkpoints/hpg-44665003/`, loaded by
manifest hash: the A, B and AB views, each as scratch three epochs, scratch six epochs, and masked
pretraining plus three supervised epochs.

## Council

Two councils, one per task, because terminal loss and observed adverse excursion use different bin
edges. Each council fits a per-specialist temperature on the specialist-calibration role, a
reliability gate on the gate-fit role, and one pool temperature on the pool-calibration role. The
pool is the linear opinion pool. One labeled case is one case, horizon and side, so the twelve
outputs of a case are never treated as twelve independent observations.

## Baselines

1. Every single specialist on its own, in both its native pinball scale and the categorical scale.
2. The training-prevalence distribution per horizon, side and task, fitted on the training role.
3. The checkpoint manifest's published evaluation pinball, recomputed and compared. A mismatch
   beyond 1e-6 is reported as a reproducibility failure, not hidden.

## Metrics

Primary: pinball loss in basis points, averaged over the evaluation role per marginal. Secondary:
multiclass log loss and Brier score on the binned categoricals, plus 80 percent interval coverage
as a diagnostic. Everything is reported per horizon, side and task, and per specialist.

## Falsifier

The council does not beat the best single specialist and the prevalence reference on the evaluation
role. Either outcome is reported.

## Ceiling

Reused development data. The evaluation role was already inspected during the checkpoint campaign,
so this is not a fresh holdout and it supports no trading claim. Both sealed competition windows
stay spent.

## Reproduce

```sh
python3 hpc/probabilistic-council/council_comparison.py \
  --cache <prepared cache> \
  --checkpoints hpc/probabilistic-council/checkpoints/hpg-44665003 \
  --output <new directory>
```
