# JevLike training and native parity audit — 2026-10-03

Scope: correctness repairs on main `85c3f31`, with the associated
[kdb wrapper audit](../kdb-timeseries/VALIDATION.md). No market dataset, OOS window, model
architecture or strategy claim changed. Local training uses only synthetic choices.

## Why the best checkpoint was not a snapshot

The CPU trainer calls `trainable_state(model)` when validation improves, continues training,
then writes that dictionary at the end. `detach()` removes autograd history but shares storage;
`cpu()` does not allocate a copy when the tensor already lives on CPU. Consequently the supposedly
saved best weights kept changing during later optimizer steps. Reporting an earlier best
validation loss could accompany a checkpoint containing worse final-epoch weights.

The fix is `parameter.detach().cpu().clone()`, applied only to trainable parameters. This owns
independent CPU storage while retaining the existing configuration/state-dictionary format and
the exclusion of frozen encoder parameters. Its cost is one CPU snapshot of the trainable weights.
No model download or pretrained-encoder integration is needed to test this memory behavior.

Primary references:

- [PyTorch saving/loading guide](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html)
  explicitly warns that keeping a best state by reference lets subsequent iterations overwrite it.
- [Tensor.detach](https://docs.pytorch.org/docs/2.14/generated/torch.Tensor.detach.html) documents
  shared storage after detachment.
- [Tensor.cpu](https://docs.pytorch.org/docs/2.14/generated/torch.Tensor.cpu.html) documents the
  no-copy case for an already-CPU tensor.

Two regressions exercise this contract: direct mutation leaves the snapshot unchanged, and actual
two-epoch optimizer training with controlled validation losses of 0.1 then 0.9 reloads the first
epoch exactly. Only the validation ranking is mocked; model, data loading, optimizer and checkpoint
serialization are real. The test also establishes that second-epoch parameters actually changed.

## Parity invocation and acceptance

Commit `9d2f583` corrected the parity command to `python -m jevlike.verify_cpp_parity`. A later
reconciliation (`1753456`) restored direct file execution, reintroducing the package-import failure.
The module invocation is restored again. Rather than testing only a separately reconstructed
command, the regression executes the current `run-jevlike.slurm` payload itself.

The verifier also formerly compared vectors with `zip`, which can silently ignore a missing tail.
Nonfinite values could bypass a simple numerical-threshold check. It now requires equal nonzero
lengths, finite entries in [0, 1], and normalization within absolute tolerance 2e-5 before measuring
the maximum difference. Unit tests reject truncation, extra entries, NaN, infinity, out-of-range
values and unnormalized vectors. Option identity/order and the existing 2e-5 parity tolerance
remain part of the main verification workflow.

The script sets `OMP_NUM_THREADS` from `SLURM_CPUS_PER_TASK` (default two for local execution).
This bounds the OpenMP thread pool; it is not an end-to-end process/thread quota or latency claim.

## Reproduction and observed result

From the repo root with PyTorch and C++17 `g++` installed:

```sh
make test-hpc HPC_PYTHON=python3
```

Use a virtual-environment interpreter in `HPC_PYTHON` if needed. No credentials, network model
downloads, q license or cluster login are needed. The suite does not install packages.

Observed: **23 tests pass**, comprising the seventeen kdb tests and six model/parity tests.
The JevLike integration test copies the real batch script into a temporary spool location and
runs it from the documented component working directory. Only `module load` is stubbed; it uses
the test interpreter's installed PyTorch. `PYTHONPATH` is cleared to expose import regressions.
The complete synthetic chain is exercised:

1. Generate 256 training / 64 validation / 64 test examples, seed 20261003.
2. Train the tiny scorer on CPU for two epochs; evaluate the synthetic test split.
3. Export the trained checkpoint and compile the native C++ scorer.
4. Verify four cases with 2, 3, 4 and 8 options, including UTF-8 text, against PyTorch within 2e-5.

Environment: macOS 26.6.2 arm64, Python 3.12.0, PyTorch 2.14.1, Bash 3.2.57, Apple Clang 21.
This validates the local toolchain, not the cluster module version. If `g++` is missing the native
test reports a skip; a skipped native test does not satisfy the full gate.

The branch was rebased onto `937001a` before committing, retaining the newer market-map
work and decision entries. The full HPC suite and `make test` also pass on that base.
Repository-wide checks:

- `make test`: passes.
- `git diff --check`: passes.
- Credential scan: passes.
- `make check`: stops at pre-existing structure violations: tracked `.vscode/` is outside the
  allowed root list, and `src/factors/` plus `src/models/` lack README files. These paths are
  unchanged here. Subsequent `make check` stages are not certified by that partial run.

## Cluster gate and operational limits

No actual scheduler or QPU job was run during this repair. Existing historical cluster receipts
do not certify these changed scripts. Submit the JevLike job from `hpc/probabilistic-council` on
an approved Blue checkout with the PyTorch module and compiler available. Retain job ID, revision,
module/compiler versions, stdout/stderr, scheduler exit status and final parity JSON. Both the
job exit and parity record must indicate success.

The current job intentionally leaves its generated checkpoints/export/binary in `$TMPDIR` as
smoke artifacts. UF's [temporary-directory guidance](https://docs.rc.ufl.edu/scheduler/temp_directories/)
states successful-job scratch is removed. A real training/export run therefore needs an explicit
durable artifact-copy step and hash verification before it can become a deployment workflow.
The committed Slurm logs do not by themselves preserve those artifacts.

No HFT latency, finance accuracy, calibration, HF export parity, GPU correctness or quantum
advantage is established by this suite. The synthetic test split is an engineering fixture,
not a reopened strategy holdout. Hippo was unavailable locally; these component records carry
the durable reasoning instead of hand-editing generated shared-memory files.
