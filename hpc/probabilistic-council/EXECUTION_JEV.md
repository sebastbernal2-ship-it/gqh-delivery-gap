# Structured JevLike execution prototype

The current next experiment separates learned movement risk from known order
costs: [movement risk with analytical costs](EXECUTION_RISK.md). The older
[action-conditioned scaffold](ACTION_CONDITIONED_EXECUTION.md) remains a research
comparator awaiting action/fill labels. The categorical experiment below is
historical context, not evidence that either model has a trading edge.

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

## Implementation and reproduction

`execution_dataset.py` verifies every raw object against the acquisition plan before parsing.
It writes supervised `features.npy`, `targets.npy`, `clocks.npy`, `roles.npy`, plus a separate
`pretraining_features.npy` corpus, a manifest and a private label provenance audit. The extra
unlabeled corpus is built only from the two whole training sessions, at a fixed 10-second stride;
calibration, gate, pool-calibration and evaluation blocks never enter masked pretraining or the
normalizer. Every numerical array is hash-verified and loaded without pickle, using memory mapping.
Training currently materializes the small prepared cache in CPU RAM; GPU transfers are bounded
minibatches (32 training, 128 inference). A genuinely out-of-core/sharded trainer remains future
work, rather than an assumed scaling property.

`execution_model.py` projects 24 typed numerical features per step into width 32, adds learned
positions and uses one temporal transformer layer. The vendored JevLike `AttentionHead` scores
60 learned option vectors, grouped into twelve five-bin distributions, using that one shared
sequence encoding. This is a new structured JevLike research variant, not TypeSafe Jev or Laya.
It has no generic pretrained weights and is not compatible with the existing tiny byte-scorer's
C++ exporter. Native/compiled serving and latency benchmarking require a separate acceptance gate.

`execution_train.py` uses the prepared cache only. It fits standardization on the larger, training-
only unlabeled corpus in double precision, transfers minibatches to the chosen device, runs the two
fixed model schedules, calibrates each query on calibration cases and chooses on gate cases.
Pretrained and scratch variants share the supervised shuffle seed and budget; the pretrained
variant receives additional explicitly disclosed reconstruction compute. Nonfinite losses or
invalid probability vectors fail. All twelve labels share their parent case; neither the loss nor
query count establishes independence.

Prepare data **off-cluster**, from this component directory:

```sh
python execution_dataset.py --plan multisession_plan.json --objects OBJECTS --output NEW_CACHE
python execution_train.py --dataset NEW_CACHE --output NEW_MODELS \
  --epochs 3 --pretraining-epochs 3 --device cpu
```

Parsing requires NumPy and PyArrow 23.0.1. Model training/inference require NumPy and PyTorch;
PyArrow is not required on HiPerGator. The reported local run used Python 3.12, NumPy 2.5.3,
PyTorch 2.14.1 and CPU execution. Transfer only the prepared arrays and manifest for model fitting;
retain the raw acquisition and full label audit outside Git/off-cluster.

```sh
export GQH_REPO_ROOT=/shared/path/to/checkout
export GQH_JEV_DATASET=/shared/path/to/validated-cache
export GQH_TAPE_RUN_DIR=/shared/path/to/new-model-run
export GQH_PYTHON=/shared/path/to/model-environment/bin/python
# CPU default. For GPU training, set GQH_JEV_DEVICE=cuda and request your allocation's GPU.
sbatch --account=YOUR_ACCOUNT --partition=YOUR_PARTITION \
  "$GQH_REPO_ROOT/hpc/probabilistic-council/run-execution.slurm"
```

The job verifies the cache before fitting and refuses missing/relative/wrong roots or existing
output directories. Its source never invokes acquisition, label construction, a strategy backtest
or classical model fitting. `run-multisession.slurm` is retired and fails closed; its older
submission instructions are historical. The prevalence reference in the report is a count-based
training-label diagnostic, not a separately trained classical model workload.

`ExecutionPredictor` in `execution_predict.py` verifies the expected checkpoint hash, loads the
structured checkpoint once, and applies its saved train-only normalizer and query calibrators.
One finite 16x24 sequence returns arrays ordered `[horizon][side][task][bin]`; adverse threshold
tails are sums of bin mass and therefore monotone across increasing thresholds. Monotonicity
across horizons is NOT enforced, and these marginals are not a joint scenario distribution.

```sh
python execution_predict.py --checkpoint MODEL.pt --sha256 EXPECTED_SHA256 \
  --sequence ONE_NUMERIC_SEQUENCE.json
```

The output is a development forecast, not a trade instruction. Quote age, own order size/impact,
fees, fill uncertainty, strategy urgency and cost of waiting require separate policy validation.
No passive-fill probability or automatic trade timing is supplied by this interface.

## Fixed smoke outcome

The unedited [experiment receipt](experiment_receipts/btc_execution_jev_smoke_20261003.json)
owns the actual metrics, source/array/code hashes, training losses, calibration and artifact hashes.
There are 41 parent cases: 13 training, 7 calibration, 6 gate, 7 reserved/unused pool calibration
and 8 development evaluation. Sixty-second label maturity, sixty-five-second stride and gap/stale
rejection reduce cases relative to the earlier five-second overlapping-history experiment. These
are different targets and samples; their scores cannot be compared as architecture improvement.
Twelve queries per parent do not turn eight evaluation cases into 96 independent observations.

| Fixed variant | Mean query log loss | Mean query multiclass Brier |
|---|---:|---:|
| Scratch (gate selected) | 1.641925 | 0.812573 |
| Masked-sequence pretrained | 1.639551 | 0.812242 |
| Smoothed training prevalence | 1.590406 | 0.798483 |

Neither variant beats the frequency reference. Scratch remains the gate-selected variant; the
slightly lower pretrained evaluation score does not authorize switching selection post hoc.
No target edges, architectures, epochs, labels or selection rules were changed after evaluating
this smoke target. This demonstrates implementation, not pretraining effectiveness, trustworthy
tails, latency, stable calibration, execution improvement or quantum advantage. Wider prepared
session coverage is required before spending substantial HiPerGator training budget.

## Follow-on pretraining expansion

The first smoke model had only 13 supervised training cases and reused those sequences for masked
reconstruction. The follow-on cache now extracts 106 unlabeled 16x24 windows at a fixed 10-second
stride from the same two training sessions, an 8.2x increase in pretraining windows. The windows
overlap heavily and come from only two short development blocks, so this is a pipeline/data-volume
improvement, not eight times more independent evidence. A single local CPU epoch over this cache
completed with finite reconstruction and supervised losses. The development evaluation partition
was not opened for that check; no updated predictive score or model-selection claim is made.

For substantially more unsupervised history, Hyperliquid's [official archive](https://hyperliquid.gitbook.io/hyperliquid-docs/historical-data)
documents hourly L2 book snapshots and says coverage may be delayed or missing; the requester pays
transfer costs. Its separate node-fill archives require a distinct adapter and reconciliation.
The archive documentation gives event-time history, not proof of the feed arrival time available to
a live strategy. Therefore historical snapshots can be screened as Jev pretraining data after
schema, gap and cost audits, but must not silently become receipt-time supervised labels or HFT
execution validation. Start a durable live WebSocket capture of book/trade messages with both
exchange and local receipt clocks, sequence numbers, and reconnect-gap records. Use Snowflake only
for timestamped context that the execution decision can actually observe; slower filings or
fundamental factors belong upstream as strategy/regime context, not as fabricated microsecond book
signals.

Regression checks cover future-path isolation, observed-gap rejection, cache/hash/schema guards,
shared-query probabilities, pretraining gradients, checkpoint inference parity and monotone
threshold tails. Altering only evaluation labels leaves trained tensors, normalization, losses,
calibration, gate scores and selection unchanged. Spool tests isolate the new Jev-only workload,
and the retired mixed job starts nothing. Live HiPerGator execution remains unverified.

## A/B/A+B view ablation

The next Jev experiment holds the target, sequence length, model width, initialization, supervised
budget and split rule fixed while varying inputs: A is order-book state, B is observed reported
trade flow, and A+B is early fusion. The exact question, feature mapping, gate rule and caveats live
in the [A/B/A+B plan](../../../docs/inbox/aidan-2026-10-03/jev-ablation-plan.md). The metadata-only
sample is pinned in [synchronized_ablation_plan.json](synchronized_ablation_plan.json). Its 30 dates
span December 2025–July 2026, with a long December-to-May gap; this cannot test long-run regimes.

`execution_ablation.py` trains three same-shape Jev instances. Omitted inputs are standardized to
zero, preserving parameter count and shared initialization. The first comparison is scratch-only;
masked sequence pretraining is held for a later experiment so it cannot confound the input-view
question. It reports an A/B equal probability pool as an additional late-fusion comparison. The new
`run-execution-ablation.slurm` runs only these Jev fits. Fetching, parsing, synchronization, labels,
normalization and classical baselines run off-cluster.

After the public source and clock audit passes, prepare a private cache off-cluster:

```sh
python fetch_public_plan.py --plan synchronized_ablation_plan.json \
  --objects /private/staging/hl-objects --workers 4
python execution_dataset.py --plan synchronized_ablation_plan.json \
  --objects /private/staging/hl-objects --output /private/staging/jev-ab-cache
```

Transfer only the validated numerical cache and manifest to HiPerGator, then set the same job
variables documented above and submit `run-execution-ablation.slurm`. The pinned plan is 1.92 GB;
it is metadata-selected but its objects have not yet passed the downstream schema, completeness or
availability checks. No HPG run or performance conclusion is implied by the plan or local smoke.

## Source-clock gate and direct capture

The [source QA and contiguous capture record](../../docs/inbox/aidan-2026-10-03/jev-data-clock-gate.md)
owns the new historical/live audits, pinned collector references, acquisition commands and remaining
gates. `source_clock_audit.py` only opens exact training-role subsets of the frozen acquisition and
emits clocks/counts without features or labels. `record_execution_tape.py` captures projected public
BTC messages off-cluster; `export_execution_capture.py` produces hash-pinned sources separated by
reconnect/clock/date segment. Its source inventory is deliberately not a trainable dataset. A new
segment-aware adapter and frozen chronological roles are required before using it for Jev training.

## First HiPerGator real-data package

The [training-package record](../../docs/inbox/aidan-2026-10-03/jev-first-training-package.md) owns
the captain's successful L4 setup check, discovered partition, ZIP-deployment fixes, first private
real-data pilot bundle and wider acquisition status. `execution_linear_reference.py` fits a fixed
latest-state reference off-cluster without scoring evaluation. `package_execution_training.py`
validates and packages numerical arrays, pre-fitted reference probabilities and pinned code; the
included launcher verifies hashes and submits the fixed three-view Jev job. This first 41-case
package is development wiring only, not adequate model-selection or trading evidence.
