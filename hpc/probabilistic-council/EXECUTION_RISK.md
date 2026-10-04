# Jev movement risk with analytical order costs

## Purpose and hypothesis

Given a proposed small marketable trade and its current market state, estimate
short-horizon adverse price movement. The main strategy supplies direction and
desired size; this module provides execution-risk estimates. It does not supply
the economic alpha or an autonomous trading policy.

The falsifiable hypothesis is that book/trade history improves conditional
movement quantiles over unconditional training quantiles on new sessions, after
costs and latency are accounted for. The initial development experiment does not
support promotion. Research, source boundaries and the fixed experiment are in
[the research decision record](../../docs/inbox/aidan-2026-10-03/jev-movement-research-20261004.md).
Measured results belong to [the run receipt](../../docs/inbox/aidan-2026-10-03/jev-movement-result-20261004.md).

## Contract

One raw `16 x 24` sequence contains 30 seconds of history sampled every two
seconds: relative prices/depth for five levels on each side, spread, reported
five-second trade imbalance/volume and book age. A=book channels, B=reported
trade channels, AB=both. Reported trade imbalance is not depth-change OFI.

`ExecutionRiskJev` encodes one state once with a small transformer over past-only
history and the
vendored JevLike option-attention scorer. It emits q10/q50/q90 for each horizon
5/15/60 seconds, side buy/sell and task terminal loss/observed adverse excursion,
shape `[batch, horizon, side, task, quantile]`. One underlying return head supplies
terminal losses: buy quantiles are the negated reversed sell quantiles. Excursion
quantiles are ordered, nonnegative, nondecreasing with horizon, and no smaller
than same-quantile terminal loss. These marginal constraints do not identify a
joint path distribution, a full density, expected loss or calibrated confidence.

The labels are future midpoint movement, in basis points of decision midpoint.
Spread, snapshot-walk VWAP and explicitly supplied taker fees are known at the
decision and stay outside the learned target. With sign `s`, midpoint `m`, VWAP
`v` and fee rate `f` in bps, the deterministic offset is
`s*(v/m-1)*10000 + f*v/m`. Add this to every risk quantile. Fee normalization is
executed notional divided by decision notional. Size changes this cost, not the
future parent observation. Hundreds of candidate orders need one state forecast
and lightweight analytical overlays, not hundreds of independently trained Jevs.

This first contract assumes immediate, full, price-taking execution against the
visible top five levels. It rejects excessive size, stale/future/crossed books,
invalid fee inputs and mismatch between the book and last model input. The result
is hypothetical entry-to-mid markout loss, not a verified fill or completed-order
implementation shortfall. It excludes arrival latency, own impact, partial fills,
funding, exit spread and exit fees. Passive orders are rejected: they need queue
and fill evidence. Doubling entry costs is an explicit cost stress, not latency
simulation or a different future path.

## Reproduce the bounded experiment

All data and checkpoints live outside Git. Run preparation off-cluster:

```bash
python execution_risk_dataset.py --source-cache "$SOURCE_CACHE" --output "$RISK_CACHE"
python execution_risk_train.py --dataset "$RISK_CACHE" --output "$NEW_RUN" \
  --allow-development-smoke
python package_execution_risk_training.py --dataset "$RISK_CACHE" --output "$NEW_ZIP"
```

Use a NumPy/PyTorch environment. Preparation verifies source-cache arrays and the
label-audit hash, reproduces stored categorical bins from continuous labels,
checks provenance and exact feature/clock/role alignment, and writes only four
arrays plus a manifest. Existing six acquisition blocks remain in five whole-
session chronological roles with purged label maturity. Continuous labels do not
turn reused development data into a new holdout. Availability remains an
unverified retrospective assumption.

Three scratch models use identical architecture, seed 20261004 and three epochs.
Feature standardization and one target scale use training cases only. A fourth
comparator is empirical training quantiles. Gate pinball score selects among all
four before evaluation; all four evaluation results are reported. The two
calibration roles remain unused; every checkpoint says `calibrated: false`.
No pretraining, broad search or post-result retuning occurs in this experiment.
The default trainer rejects fewer than three independent sessions in any used
role unless the explicit smoke flag is supplied. This is an engineering guard,
not a statistical sample-size guarantee or a production promotion gate.

On HiPerGator, verify the external ZIP hash, extract it, then:

```bash
cd jev-risk-training
bash submit.sh
```

The bundle hashes each staged dependency and array before submission. Its
bounded job defaults to account/QOS `ai-workshop`, partition `hpg-turin`, one L4,
two CPUs, 4 GB and ten minutes, with the verified `pytorch/2.8.0` module. Override
the account/QOS environment variables only with your actual allocation. This
bundle explicitly runs the scarce-data development experiment. HPG fits/evaluates
Jev only; raw parsing, authoritative replay, label construction, classical model
training and strategy backtests remain off-cluster. The empirical quantile
summary is a non-trained diagnostic of the prepared training labels.

The Slurm script resolves source imports from the absolute supplied bundle root,
works from an unrelated scheduler spool directory, refuses existing run outputs
and validates array hashes before fitting. Reports include dataset/source/code
hashes, environment, role/session counts, all metrics and checkpoint hashes.
Exact GPU/CPU numerical identity is not promised.

For inference, instantiate `ExecutionRiskPredictor(checkpoint, expected_sha256)`
or use its CLI with `--checkpoint`, `--sha256`, `--request`. The JSON request has
the raw sequence, `decision_ns`, a book (`event_ns`, `recorded_ns`, `bids`, `asks`,
`source_ref`) and orders with `side`, `size`, integer `horizon_seconds`, explicit
`taker_fee_bps` and optional `order_type="marketable"`. Checkpoint hashes are
required; Torch loads with `weights_only=True`. No order submission is included.

## Data and acceptance gates

Next, export certified snapshots/trades from the existing orderbook-engine,
preserving venue, sequence, event/receive clocks, source hashes and quality. That
engine owns book reconstruction and gap rejection. Its newer Binance route is
not Hyperliquid history; never mix venues silently. The development adapter in
this change intentionally accepts only the existing retrospective cache contract.
Prospective certified data requires a separately reviewed adapter and manifest.

Build many independent sessions before scaling compute. Freeze training,
validation/calibration and a fresh final evaluation block before outcomes are
opened. Evaluate by session, volatility/liquidity state, venue and instrument;
do not count multiple candidates or overlapping heads as independent cases.
Archive approved immutable provenance before capture retention expires. Compare
empirical quantiles, simple depth/imbalance/volatility quantile regressions fitted
off-cluster, and a small causal neural model before richer specialists.

Accept additional specialists, pretraining, fusion or quantum experiments only
after robust incremental proper-score and downstream policy value. Calibrate on
separate earlier sessions; financial time dependence means no automatic IID
conformal coverage guarantee. Measure batch-one end-to-end p50/p99/p999 on the
actual serving host before calling it HFT. HPG accelerates offline experiments;
parallel classical models are not quantum superposition. Quantum remains a
separate equal-budget research layer with no claimed speed or accuracy advantage.

## Regression coverage

Run `make test-hpc HPC_PYTHON=/path/to/torch/python`. Tests cover candidate-batch
parity in the retained action scaffold, model geometry/gradients, exact book-walk
fee units, invalid liquidity/clocks/state, audit/hash tampering, evaluation-label
perturbation that cannot alter fitting or gate choice, inference/checkpoint
parity for all variants, and extracted-bundle training from scheduler spool.
