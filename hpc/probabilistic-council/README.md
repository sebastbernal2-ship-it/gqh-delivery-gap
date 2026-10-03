# Probabilistic council pilot

Owner: `lucyrunner`. This is the first engineering slice for the Jev-style council proposal.

## What it runs

`pilot.py` generates a known synthetic binary forecasting problem, fits two small specialist
logistic models on different regimes, calibrates each on a separate partition, learns simple
regime-dependent reliability weights on another partition, calibrates each fused pool on its own
partition, and compares equal-pool and gated-pool probabilities on a final synthetic partition. It
reports log loss, Brier score, and ECE. Every
forecast is a complete `[P(no), P(yes)]` distribution.

`qcbm_pilot.py` is a bounded quantum research fixture. It trains a three-qubit parameterized
Born machine in an exact statevector simulator against a synthetic correlated distribution, then
compares the fitted distribution with independent-Bernoulli and smoothed full-categorical classical
baselines. It reports exact target-distribution KL/total-variation/tail diagnostics plus proper
log-loss and multiclass Brier scores on an independent synthetic test sample. It also reports circuit
evaluations and runtime. The exact simulator has no shot noise or hardware noise and is classical
computation; this experiment cannot establish quantum advantage. `run-qcbm.slurm` submits it as a
small CPU job.

## Laya integration boundary

Upstream inspection on 2026-10-03 confirms Apache-2.0 licensing in both the Laya source repository
and its Hugging Face model card. Laya exposes typed categorical decisions and RLCD training, so it
is a candidate text specialist; it does not natively provide general joint financial distributions.
Its own model card warns that its base checkpoints can be near chance on typed decisions and that
raw probabilities need domain calibration. Treat it as a base for specialization and evaluate every
checkpoint on our own data before council admission.

The documented package requires Python 3.10 or newer, while the previously used HiPerGator default
Python was 3.9.25. Before any Laya install or weight download, select and record a supported Python
module/environment, inspect the checkpoint and dataset provenance, and keep downloaded weights and
caches outside Git. This pilot has not installed Laya, downloaded weights, or reproduced RLCD.
See the [upstream code](https://github.com/NandhaKishorM/laya) and
[model card](https://huggingface.co/convaiinnovations/laya).

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

For the quantum-distribution fixture, submit `sbatch run-qcbm.slurm` from the same writable
working directory.

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
