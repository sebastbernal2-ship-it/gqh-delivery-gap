# Multi-session causal tape experiment

Historical experiment. Its mixed cluster submission is retired under the user's Jev-only
HiPerGator reservation. Current prepared-cache submission lives in [the execution prototype](EXECUTION_JEV.md).

Follow-up to [the rejected short candidate](SYNCHRONIZED_TAPE.md). This is development-only
forecast engineering. It does not establish an economic trading edge, executable fill model,
liquidation specialist, queue reconstruction, or quantum advantage.

## Declared before acquisition/outcomes

At the same pinned public archive revision, choose the first two nonpartitioned files in each
book/trade family, ordered by numeric filename timestamp, on each of the first six shared UTC
filename dates. Inspect only names, sizes and publisher hashes for selection. A preliminary
10-second filename-pair tolerance failed on catalog offsets; no price data was involved. The
final rule chooses each family independently and audits actual clocks after downloading.
[The complete pinned plan](multisession_plan.json) totals 630,972,972 bytes, below the 750 MB cap.
The previously inspected five-minute candidate is retained as disclosed development data.

Hypothesis: merging the declared files yields enough valid causal cases across six sessions to
exercise the existing seven-view fitting/calibration/selection pipeline with distinct information
streams. Falsifiers: incompatible schema, conflicting duplicate identities, invalid clocks/books,
empty common coverage, gaps preventing causal cases, or an empty chronological role blocks training.
Missing coverage does not become a zero-trade assertion, and overnight gaps are not filled.

Use the recorded timestamp as an unverified availability proxy, explicitly labelled
`retrospective_assumption`. A contains spread/five-level depth imbalance; B contains reported
B-minus-A observed trade size imbalance and log observed volume over 30 seconds; C contains
five-second midpoint movement and trailing 30-second midpoint realized volatility.
No liquidation field is inferred from trade flow. Same instrument BTC and same target for all views.

Fixed target: midpoint change from the latest valid book known at decision to the latest valid
book known at decision+5 seconds, three bins with +/-1 bp boundaries, ties flat. Label availability
is the five-second horizon endpoint on the same proxy clock. Require a newly recorded future book
and a continuous book history through the endpoint. Decision spacing is six seconds; do not claim
independent cases because trailing histories overlap.

Assign the first two filename-date sessions to training, third to specialist calibration, fourth
to gate fitting, fifth to pool calibration and sixth to development evaluation. Never split a
session across roles. Purge labels that mature at/after the first following-role decision. No
architecture/budget changes after evaluation: existing 3-epoch tiny JevLike models and 100-step
numeric baselines, all seven A/B/C combinations, prevalence prior and equal opinion pools,
existing gate increment rule. Report every declared variant and class counts, regardless of results.
This development evaluation is not the competition holdout owned by the frozen brief.

Only public aggregate provenance, coverage and experiment receipts enter Git. Source objects,
normalized states, label audits, models and individual forecasts stay in local artifacts. Download
by the pinned plan, verify bytes/hash, and feed the adapter independently of Snowflake. This
establishes a source adapter; it does not populate or validate a production warehouse panel.

## Run locally or on HiPerGator

Use Python with PyArrow 23.0.1 for parsing and the existing PyTorch environment for models. From
this component directory, after all plan objects have been downloaded under their SHA-256 names:

```sh
python multisession_panel.py --plan multisession_plan.json --objects OBJECTS --output NEW_PANEL
python information_views.py --panel NEW_PANEL/panel.jsonl --manifest NEW_PANEL/manifest.json \
  --output NEW_MODELS --epochs 3 --seed 20261003
```

Panel generation does not require PyTorch. Model loading validates the panel hash, exact target,
feature availability, ordered roles and fully matured labels through the existing panel contract.
Sources that cross midnight stay in their declared acquisition block; actual timestamps determine
chronology. Conflicting identities across blocks fail instead of allowing the same event into
fitting and evaluation roles. All source objects are hash-verified before any panel is written.

The `run-multisession.slurm` wrapper uses an explicit shared repository root; a spooled Slurm
script never guesses it from its own filename or the submission directory. Configure a durable
object directory and a new run directory. It checks the interpreter's PyArrow/PyTorch imports
before starting, pins the declared epochs/seed, stops training if the adapter fails, and refuses
existing runs. Choose the site account/partition at submission, using your existing allocation:

```sh
export GQH_REPO_ROOT=/shared/path/to/checkout
export GQH_TAPE_OBJECTS=/shared/path/to/pinned-objects
export GQH_TAPE_RUN_DIR=/shared/path/to/new-development-run
# Optional: a prepared interpreter with both dependencies; otherwise loads the pytorch module.
export GQH_PYTHON=/shared/path/to/environment/bin/python
sbatch --account=YOUR_ACCOUNT --partition=YOUR_PARTITION \
  "$GQH_REPO_ROOT/hpc/probabilistic-council/run-multisession.slurm"
```

This is a small CPU engineering workload. No GPU/QPU, HFT latency or real cluster execution is
claimed by adding a submission wrapper. Three shell-contract tests exercise an actual spooled
copy from an unrelated directory, missing/relative/wrong roots, output preservation and adapter
failure ordering. Six panel regressions cover identity conflicts, earliest-receipt deduplication,
future-midpoint isolation, gap rejection, whole-session roles, file completeness and byte budget.

## Observed outcome — no retuning

All 24 source objects passed publisher SHA-256/byte verification. The adapter produced 554 cases
and the existing loader accepted their hash, availability and chronological-role contract. All
14 checkpoints and 18 evaluation forecasts were generated. The generated
[full experiment receipt](experiment_receipts/btc_multisession_views_20261003.json) owns the
coverage, exclusions, class counts, variant scores, fitted parameters and artifact hashes.

| Role | Cases | Down / flat / up | Acquisition sessions |
|---|---:|---|---:|
| Training | 183 | 23 / 133 / 27 | 2 |
| Specialist calibration | 96 | 7 / 81 / 8 | 1 |
| Gate fit | 91 | 3 / 86 / 2 | 1 |
| Pool calibration | 91 | 3 / 87 / 1 | 1 |
| Development evaluation | 93 | 25 / 46 / 22 | 1 |

The first acquisition date has a roughly 45-minute missing-book interval. Its many stale cases
were excluded; that elapsed span is not treated as continuous history. Other short interruptions
also triggered stale-book exclusions. Midnight-ending files include preceding-evening observations;
filenames did not determine feature availability. Roles remain strictly chronological after using
actual clocks. Each of the last four roles has just one acquisition session, so this run provides
no estimate of performance across multiple independent evaluation sessions or broad regimes.

| Declared comparison | Evaluation log loss | Multiclass Brier |
|---|---:|---:|
| Gate-selected numeric A | 1.331510 | 0.771610 |
| Training prevalence | 1.160580 | 0.705053 |
| JevLike ABC, full-context comparison | 1.050001 | 0.632528 |
| JevLike equal singleton pool | 1.160685 | 0.705714 |

Lower is better. The gate-selected model **failed to beat prevalence** on the evaluation session.
The gate/pool blocks were about 95% flat, versus about 49% flat in evaluation. This is an observed
change in outcome frequencies, not a proven causal explanation of the loss. JevLike ABC was not
selected by the gate; its lower evaluation score does not authorize replacing the selected model
post hoc. The equal JevLike pool did not beat prevalence. The receipt reports every other view,
including rejected combinations, rather than only these illustrative rows.

The experiment supports the data/model integration, not an architecture winner or trading edge.
Retained JevLike AC was exploratory under the existing gate rule; it is not a significance claim.
No epochs, thresholds, features, weights, targets or selection criteria were changed after
opening development evaluation. Nearby parameter values, independent sessions, execution costs,
latency, liquidity/capacity, regime robustness and meaningful strategy-conditioned targets remain
unvalidated. Quantum was not run and these seven overlapping information views are classical
experiments, not quantum superpositions or independent votes.

Full HPC verification passed 64 tests (17 kdb, 47 council), including nine new panel/job tests.
Root `make test` passed. The Slurm wrapper was exercised locally with spooled-script regressions;
no live HiPerGator submission or measured serving-speed claim follows from those tests.

Next: prospectively declare a broader session sample and evaluate stability across multiple
sessions per fitting/evaluation role. Preserve this run as negative evidence for the frozen gate
and pool, rather than tuning it to the inspected evaluation session. Verify receive clocks and
trade-feed completeness before treating this research panel as an executable market replay.
