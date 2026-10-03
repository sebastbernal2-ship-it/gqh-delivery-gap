# Probabilistic council pilot

Owner: `lucyrunner`. This is the first engineering slice for the Jev-style council proposal.

## What it runs

`pilot.py` generates a known synthetic binary forecasting problem, fits two small specialist
logistic models on different regimes, calibrates each on a separate partition, learns simple
regime-dependent reliability weights on another partition, calibrates each fused pool on its own
partition, and compares equal-pool and gated-pool probabilities on a final synthetic partition. It
reports log loss, Brier score, and ECE. Every
forecast is a complete `[P(no), P(yes)]` distribution.

`run.slurm` requests a single CPU task and invokes the same script. No model weights, private data,
GPU, quantum package, network access, or account-specific path is needed. See [INTERFACE.md](INTERFACE.md)
for the versioned contract and [the architecture proposal](../../docs/inbox/jev-council-architecture-2026-10-03.md)
for the wider research direction.

## Local run

```sh
python3 pilot.py --seed 20261003 --rows 12000
```

## HiPerGator run

Copy this directory to a writable Blue or scratch location, change into that copy, and submit:

```sh
sbatch run.slurm
```

The job's stdout/stderr is written by Slurm in the submission directory. Do not submit from the Git
checkout or put generated logs, datasets, or checkpoints in this repository. This pilot does not
access the network or Blue storage from inside a job.

## HiPerGator run record

Verified 2026-10-03: Slurm job `44542543` completed in one second with exit code `0` and empty
stderr. It ran the deterministic synthetic fixture and wrote its JSON metrics to the remote Slurm
stdout file in the account home directory. The output was inspected and contains no market data or
model weights; it is an engineering smoke result, not a trading result.

## Promotion gate

Before real inputs or Laya weights are added, define and own a concrete forecast target, verify
weight/data licenses, specify point-in-time partitions and calibration data, and version the
specialist input/output contract. A competition OOS window remains closed until its named owner
opens it under `docs/brief.md`.
