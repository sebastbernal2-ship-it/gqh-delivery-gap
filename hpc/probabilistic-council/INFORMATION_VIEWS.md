# Information combinations: development prototype

## Declaration before the real-data run (2026-10-03)

The experiment asks whether combining information views improves a common probabilistic target.
Seven inputs are compared: A, B, C, AB, AC, BC, ABC. They are early feature fusion, not quantum
superposition, independent economic shocks, or seven independent votes. Each gets a tiny JevLike
and a numeric multinomial logistic comparator. Same seed 20261003 and three epochs for every
JevLike; numeric models use 100 full-batch steps. No search, pretraining or winner-based retuning.
A common training-only standardizer and exactly the same cases/outcomes apply to every view.

Five chronological roles: training, specialist calibration, view/model selection, pool calibration,
engineering evaluation. No episode crosses roles and all labels from an earlier role must mature
before the next starts. The loader rejects the already-spent 2022-10 through 2024-09 project window.
This is development-only engineering; its last block is not a fresh competition holdout.

Combination retention is declared on gate-fit log loss only: a combination must improve over its
best proper subset by more than 0.01 nats/case. This is an exploratory cutoff, not a statistical
significance claim. All views are reported regardless. The best single model is chosen on gate
rows; evaluation never changes that choice. Primary late-fusion comparators equally pool only
A/B/C and calibrate on the separate pool block. Correlated AB/AC/BC/ABC are not blindly added as votes.

## Real-data candidate, chosen from provenance before viewing outcomes

The warehouse acquisition receipt names 86,760 Hyperliquid records, but the public-mirror books
and fills cover different months. The original pilot is documented on the team's
`research/handoff-event-readiness` branch under `src/event_readiness/DATASET_HANDOFF.md` and
`hyperliquid_pilot_plan.json`. It does not supply synchronized order flow and books.

Use only its BTC L2 snapshots from the one declared December 7, 2025 partition for an engineering
smoke test. Do not join July fills to December books; do not claim liquidation identification.
Fix three book-derived views: A top-of-book spread and size imbalance; B five-level depth imbalance
and depth ratio; C trailing 5-second midpoint change and trailing 30-second realized volatility.
These are three information views of one source, not three independent source streams.

Target: midpoint change from the observed snapshot to the first valid snapshot at/after five seconds
past a simulated decision. Assume one second between source clock and simulated availability;
the target is therefore approximately six seconds after the feature snapshot. Classes down/flat/up
use fixed -1/+1bp boundaries (boundaries flat). This latency is an explicit unverified retrospective
assumption, not a measured feed delay. No execution or P&L claim may use it.

Use one decision per at least six seconds; trailing features require 30 seconds of contiguous history;
reject source gaps exceeding two seconds, invalid/crossed books, missing depth, and labels more than
two seconds late. Keep minute episodes together, split their chronological sequence 50/15/15/10/10,
and purge boundary rows whose labels have not matured before the next block. Log exclusions.
The roughly 33-minute source window can test wiring, not generalization, calibration stability,
independent regimes, HFT fills or profitability. No preferred architecture is selected from this run.

The six-second engineering smoke target supplements the original synthetic 75-second fixture. It
is not a revised strategy horizon: 33 minutes provides too few independent 75-second events for a
meaningful five-role experiment. A strategy experiment still needs a larger synchronized history.

## Files and rerun contract

`information_views.py` consumes a JSONL panel and a hash-bound JSON manifest. Each feature needs
its own availability timestamp and source reference; identity, label and timestamps never enter
the input text. Explicit finite features are required; missing values must be handled upstream.
Manifests declare target, ordered features/classes, group indexes, availability basis, allowed
development window, and label rule. A string saying `source_timestamp` is not itself evidence:
the adapter/source audit remains responsible for verifying it.

Outputs: fourteen checkpoints; per-case forecasts for all four post-training roles; calibration
parameters; train-only scaler; gate selection record; every evaluation score; code, input and
artifact hashes. New output directories are required. Data and checkpoints stay out of Git.

The initial synthetic runner remains available in `specialist_lab.py`. Helpers accept declared
feature/outcome names so the real-data path does not mislabel book inputs as open interest.

## Executed result and interpretation

The [generated receipt](experiment_receipts/btc_book_smoke_20261003.json) records the first real
run without retuning. Its source clock spans 2,014.053 seconds (about 33.6 minutes). The adapter
kept 299 cases from 3,567 valid BTC snapshots: 142 train, 47 specialist-calibration, 47 selection,
27 pool-calibration and 36 evaluation. Four rows were removed at role boundaries. Source gaps,
warmup, sampling and late/missing labels are counted separately in the receipt.

The gate selected numeric C (recent movement/volatility). Evaluation log loss was approximately
0.1682, versus 0.1837 for training prevalence, 0.5898 for all-feature JevLike and 0.3296 for the
calibrated equal JevLike pool. **35 of 36 evaluation cases are flat, with zero down cases.**
These are descriptive smoke-test outputs, not performance estimates or evidence for deployment.
An apparent improvement is driven by very few non-flat observations and cannot establish tail
accuracy, robustness, useful calibration, an information edge or architectural superiority.

The exploratory JevLike gate check retained AB and BC; the numeric check retained no combined
view. That disagreement and tiny class counts are reasons to require substantially more data,
not reasons to tune thresholds or add models. No combination is adopted into the main strategy.
Every one of the fourteen models and both equal pools remains in the report. The rule-selected
model is reported separately from the best-looking evaluation result.

### Rerun

Download the CSV produced by [the pinned query](snowflake_book_export.sql) into private storage.
From this directory, using the existing JevLike Python/PyTorch environment:

```sh
python book_panel.py --csv /private/staging/btc-book.csv --output /private/staging/book-panel-001
python information_views.py \
  --panel /private/staging/book-panel-001/panel.jsonl \
  --manifest /private/staging/book-panel-001/manifest.json \
  --output /private/staging/book-run-001 --epochs 3 --seed 20261003
```

The original source and local export stay immutable; each attempt needs a new directory. The
adapter also saves a label audit with exact source/label nanoseconds, source row indexes and
prices. HiPerGator can run the same Python entry points once those private artifacts are staged;
this session ran on local CPU and did not submit a remote job.

Validation: twelve new tests cover group combinations, payload/hash tampering, clocks, source
identity, invalid books, gaps, held-out-window rejection, episode boundaries, future labels,
feature/label separation, and evaluation-label perturbation. Changing evaluation labels leaves
all fourteen model checkpoints, scalers, calibrators and selections unchanged. Together with
prior tests, `make test-hpc` passes 45 tests. The original synthetic lab remains compatible.

Repository-wide `make test` also passed. `make check` still stops on pre-existing structure
issues: `.github` and `.vscode` are not recognized root areas, and `src/factors` / `src/models`
lack READMEs. These are outside this prototype's scope and were not changed. Credential and
whitespace checks pass. No claim that the full repository gate is green is made.
