# Structured JevLike execution prototype

HiPerGator is reserved for JevLike model work: training, model pretraining, calibration and
model evaluation. Acquisition, raw parsing, feature/label construction, classical model training,
strategy backtests and unrelated research run elsewhere. The existing BTC mirror is an engineering
pilot; deployment on equities requires that venue's data and action validation.

## Protocol declared before this target is opened

Use the already pinned six-session development acquisition. Earlier five-second outcomes have
been inspected; this is NOT a pristine holdout. Build one parent case with a 16-step sequence at
2-second spacing (30-second history), relative five-level book prices and depth fractions, spread,
observed five-second trade flow/volume and book age. Validate the whole historical book path;
use only recorded messages available at each sequence step. Record original source provenance.
Decision stride is 65 seconds; maximum label horizon is 60 seconds. This reduces label overlap
without asserting statistical independence. Acquisition blocks stay in their existing five roles.

For each horizon 5/15/60 seconds and each proposed side buy/sell, label terminal signed midpoint
movement and worst observed adverse midpoint excursion. Both sides come from the same path and
remain one training case, not independent examples. Use the latest book known at the endpoint,
with newly recorded future observations, a <=2-second staleness limit and no intervening event
clock gap above two seconds. Excursions are OBSERVED snapshot excursions; unobserved movements
between snapshots cannot be recovered. These are pre-trade market forecasts for small orders,
not causal estimates of own impact, fill probability or executable P&L.

Terminal bins have edges -2/-0.5/0.5/2 bp; adverse bins have edges 0.5/1/2/5 bp. Bins are left-closed
(right insertion at edges). Every output is a five-bin probability distribution; threshold-tail
probabilities are sums of bin mass. Horizons/heads are marginal forecasts, not an identified joint
path distribution. Future labels and raw identities never enter the model input.

One shared structured sequence encoder feeds the vendored JevLike option attention scorer.
Horizon/side/task-specific learned option vectors replace decimal-text tokenization. Compute the
sequence representation once for all 12 queries. Compare two fixed variants: scratch versus
training-only masked-token reconstruction pretraining. Pretraining masks 20% of past tokens and
reconstructs numerical features; it is market-sequence pretraining, not a pretrained language
model, RLCD reproduction or TypeSafe Jev. Same supervised budget/seed/architecture for both.
Use 3 supervised epochs and 3 pretraining epochs for the bounded smoke run. No production
architecture choice follows from this sample or budget.

Train-only standardization; calibrate on specialist-calibration cases; choose between the two
variants on gate cases by mean log loss; pool-calibration stays reserved/unused. Report both
variants and a smoothed train-frequency baseline on development evaluation. No choice on that
block. Hypothesis: structured input and shared queries can train, calibrate and serialize without
leakage. Falsifiers: empty chronological roles, broken clocks/gaps, source/hash mismatch,
nonfinite targets/probabilities or failure of future-isolation/checkpoint tests blocks acceptance.
Improved execution or stable predictive edge is a separate hypothesis requiring broader data.

Numeric caches and manifests are prepared outside HiPerGator. The cluster job reads only those
validated caches and runs JevLike model operations. Historical mixed preprocessing/baseline
submission is disabled. No live cluster job, quantum integration, distillation, order-impact model
or production deployment is implied by this prototype.
