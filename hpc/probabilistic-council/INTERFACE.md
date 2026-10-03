# Synthetic council pilot interface

Contract version: `0.1.0`
Owner: `lucyrunner`
Purpose: verify that specialists can publish full binary distributions and that calibration,
context gating, probabilistic fusion, and proper-score reporting compose in one reproducible CPU
job. This fixture is synthetic and makes no financial forecast.

## Input and output

The fixture generator creates synthetic rows with a binary outcome (`no`, `yes`), one numeric
feature, and a discrete regime. Specialist adapters return both outcome probabilities summing to
one, the context they cover, and a stable specialist id. The pilot has two transparent synthetic
specialists. It does not load Laya weights or external data.

The pipeline uses disjoint chronological partitions for fitting, regime-conditional specialist
temperature calibration, regime-conditional reliability weighting, pool-level temperature
calibration, and final evaluation. The final report
contains log loss, Brier score, and equal-width-bin expected calibration error for climatology,
equal pooling, and gated pooling. The gate uses only its reliability partition. The evaluation
partition is scored once after those choices are fixed.

## Semantics

- Probability vectors use the fixed class order `[no, yes]`, contain finite values in `[0, 1]`, and
  sum to one within `1e-9`.
- Missing or unsupported specialist output is an error in this pilot; a production council needs an
  explicit abstention/fallback contract.
- Fusion is a linear opinion pool. It does not assume specialists are independent and it preserves
  their outcome support. It does not reconstruct a general joint distribution.
- Context reliability weights use inverse Brier score with a small floor. This is a transparent
  baseline, not an endorsed production gating algorithm.
- Specialist calibration, gate selection, pool calibration, and final evaluation use separate rows. The synthetic evaluation
  partition is not the competition's sealed OOS period.

## Run

```sh
python3 pilot.py --seed 20261003 --rows 12000
```

The script uses only the Python standard library, writes one JSON report to stdout, and writes no
data or results file. On HiPerGator, submit `run.slurm` from a writable scratch or Blue directory so
Slurm logs do not land in the repository.

## Limits

This pilot validates code paths and a basic artifact shape only. It does not train a neural model,
validate RLCD reproduction, use market observations, establish calibration on real data, define a
financial target/horizon, establish quantum advantage, or qualify for a trading decision. Future
components need their own owner and versioned contract before they are added.

## Quantum distribution experiment (`qcbm_pilot.py`)

The input is a seeded synthetic joint categorical distribution over three binary variables. The
target generator, training sample count, optimization budget, and tail event are explicit in the
script. A QCBM adapter returns all eight probabilities in lexicographic bit-state order `000` to
`111`; the vector must be finite, nonnegative, and sum to one. Classical comparators use the same
training samples. Model distributions are scored against the exactly known synthetic target; no
held-out sample is used for fitting or model selection. The script also draws an independent
synthetic test sample for finite-sample estimates of log loss, multiclass Brier score, and tail-mass
error; this fixture split is not the competition's sealed OOS period.

The report includes oracle KL(target || model), total variation, and tail error, alongside test-sample
log loss, multiclass Brier score, and tail error; it also includes parameter count, simulator
evaluations, and wall time. The quantum-inspired model
is a parameterized circuit evaluated by an exact statevector simulator, but all computation
is classical and noiseless. The bounded experiment has no QPU execution, finite-shot uncertainty,
error mitigation, broad architecture search, or finance interpretation. It is a software path and
measurement contract for a later simulator/QPU adapter, not evidence for using QCBM in the council.
