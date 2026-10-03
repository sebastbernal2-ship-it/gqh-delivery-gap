# Specialist lab: first experiment, declared before execution

Status: engineering prototype, not an adopted strategy. This experiment does not reopen either
competition holdout. The first command accepts only a generated synthetic fixture.

## Question and falsifier

Can the existing JevLike scorer learn from a declared feature view, and can three independent
scorers pass through the existing calibration/fusion engine without mixing targets or leaking
future labels? Once a permitted development panel exists, the research question is whether
specialization improves log loss/Brier over one all-feature JevLike and a numeric baseline.
Equal pooling is a required comparator for learned gating. No design wins by construction or by
its model count. Synthetic scores cannot answer the market question.

The first comparison fixes the seed, epochs, feature groups, outcome order and chronological
split before execution. There is no hyperparameter search or winner-based configuration change.

## Contract

Each row names a decision, episode, instrument, feature-availability timestamp, decision timestamp,
label horizon and label-availability timestamp. Features are the following six ordered quantities:

| Proposed view | Features and units |
|---|---|
| flow proxy | price move in trailing standard deviations; fractional open-interest change |
| liquidity | dimensionless book imbalance; spread in basis points |
| context | realized volatility in basis points; mark/oracle basis in basis points |

They are synthetic placeholders for a future audited adapter. The flow view is a **proxy**, not
confirmed liquidation activity. The current 15-second tape cannot measure queue position, all
cancellations, exact fills, or microsecond response. No event-specific model is fitted to it here.

Engineering target: midpoint return at 75 seconds, bins `down`, `flat`, `up`, with fixed boundaries
at -5 and +5 basis points. Boundary values belong to `flat`. This is a fixed fixture contract,
not an economically selected horizon, threshold, trade trigger or cost assumption. All specialists
predict this same target. Fill probabilities and trade utility are different targets.

Input normalization is fitted on training rows only. Model input is explicitly constructed from
the selected feature names and normalized values; case IDs, timestamps and future returns never
enter the scorer text. The numeric comparator receives the identical unrounded normalized values.
JevLike receives signed decimal text rounded to three places; this representation is itself an
experimental limitation. The scorer rejects text exceeding its context budget rather than
silently dropping late features.

Five chronological blocks have distinct roles: 50% train, 15% specialist calibration, 15% gate
fit, 10% pool calibration, 10% engineering evaluation. Every earlier block's labels must have
become available strictly before the next block begins. An episode cannot cross a block boundary.
The validator rejects overlap rather than silently purging or changing the requested split.
Real clustered events will need an explicit episode grouping and purging policy before adoption.

## Models and compute budget

- Training-prevalence control, fitted on training labels only.
- Numeric multinomial logistic regression over all six features.
- One tiny JevLike over all features.
- Three independently initialized tiny JevLike models, one per feature view.
- Equal pool of calibrated specialists, independently pool-calibrated.
- Existing Brier-reliability linear council, followed by pool calibration.

The tiny JevLike models are trained from scratch. No pretrained language model, RLCD, quantum
runtime, distillation or remote serving is present. The baseline uses 100 full-batch optimizer
steps; JevLike uses a declared fixed epoch count and batch size 64. Parameter counts, optimizer
steps and training wall time are reported. Budgets differ, so this is not an equal-budget
architecture contest. Reproducibility excludes wall-clock timing fields.

Start small: one seed and three epochs. Preserve every report; later sweeps require a declared
variant list and fresh development comparisons. The synthetic generator includes linear signal
and noise; the numeric linear model should be a meaningful control, not a deliberately weak foil.

## Run

From `hpc/probabilistic-council`, with PyTorch installed:

```sh
python specialist_lab.py --rows 1000 --epochs 3 --output /private/staging/jev-lab-001
```

Output must be a new directory. It contains the synthetic JSONL, four compatible tiny checkpoints,
numeric baseline state, per-evaluation-row probabilities and a report with source/artifact hashes,
exact split timestamps, model/calibration settings, metrics and limitations. Keep these artifacts
out of Git. The CLI requires no credentials, data purchase or cluster allocation.

`make test-hpc` from the repo root discovers the additional lab tests. They cover feature/label
separation, training-only preprocessing, target consistency and chronological label maturity.

## Bottlenecks and next steps

1. Build and review the historical event adapter: identify actual print/source semantics, timestamp
   availability, instrument IDs, book gaps, episode boundaries and target prices. A public archive
   link is not a validated training panel. Do not conflate cascade proxies with forced liquidations.
2. Count independent events per regime and date block. Five roles consume data; hundreds of rows
   from one cascade do not supply hundreds of independent examples. Use simpler global calibration
   when a regime lacks enough development observations.
3. Benchmark on a new, explicitly development-only panel. Add source/regime ablations, event-level
   uncertainty intervals and costs/fill replay. Forecast scores alone do not establish tradability.
4. Then compare scratch training with permitted pretraining and numeric encoders. Pretraining must
   respect the cutoff, and a language encoder is not automatically suitable for a numerical book.
5. Use HiPerGator to scale those measured jobs. Benchmark serving end to end separately; retain
   p50/p95/p99 including features, transport and action submission. Hardware alone does not establish HFT.
6. Only if a council adds value, test distillation into a fast student. Quantum scenario sampling
   remains a separate equal-budget research experiment, not part of the live decision path.

Research basis: [deep ensembles](https://arxiv.org/abs/1612.01474) motivates testing useful ensemble
diversity; [distillation](https://arxiv.org/abs/1503.02531) motivates later compression. Neither is
evidence that these particular specialists help this strategy. Existing repository support is
documented in `INTERFACE.md`, `STACK.md` and `VALIDATION.md`.

## First execution record

The declared 1,000-row, three-epoch, seed-20261003 run completed on local CPU with Python 3.12
and PyTorch 2.14.1. It produced the model artifacts and eight sets of evaluation predictions.
Numeric logistic regression achieved lower evaluation log loss and Brier score than either the
single JevLike or the council; the latter two were close to the training-prevalence control.
The global gate was close to equal weighting. We did not change hyperparameters after inspecting
this result. Exact scores, source hashes, timestamps and budgets are generated into `report.json`.

This result is limited to the partly linear synthetic generator, decimal-text representation,
small sample and unequal optimization budgets. It neither establishes a market edge nor rejects
JevLike for other representations or tasks. It establishes that the pipeline can return an
unfavorable comparison for the more complex method without hiding it. Calibration error alone
must not select the model: an uninformative prevalence forecast can look well calibrated.

Validation: all ten new lab tests and all twenty-three prior HPC tests pass. Credential scan and
diff checks pass. No remote allocation, market holdout, real dataset or pretrained download was
used. Existing repository layout failures recorded in `VALIDATION.md` are unaffected.
