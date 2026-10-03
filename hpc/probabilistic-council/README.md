# JevLike probabilistic council

This is the active HiPerGator implementation of our JevLike project. The product target is an
open-source, Jev-inspired one-pass choice model: given a context and a variable set of text
options, it scores all options and returns a probability distribution. We vendor the MIT-licensed
core from [vinnylarouge/jevlike](https://github.com/vinnylarouge/jevlike); source and attribution
are recorded in [`jevlike/README.md`](jevlike/README.md).

JevLike is an independent alternative. It is not TypeSafe Jev and we do not claim to reproduce its
closed architecture or training method. Its upstream implementation trains in Python/PyTorch.
The initial native C++ path supports the tiny byte encoder; a frozen Hugging Face encoder is not
exportable through that path. See [`STACK.md`](STACK.md) for the subsystem-by-subsystem language
choice, HPG/Vultr roles, and build gates.

## Current implementation

- `jevlike/`: vendored model, trainer, evaluation and prediction utilities, plus a checked binary
  export and Python-to-C++ probability parity runner.
- `council/jevlike_adapter.py`: adapts a loaded JevLike model to the council's categorical
  specialist contract.
- `cpp/`: C++ council and a native JevLike tiny-model scorer that emits the same calibrated-ready
  probability interface.
- `run-jevlike.slurm`: HPG synthetic train → evaluate → export → C++ compile → parity workflow.
- `run-cpp.slurm`: compile and run the C++ council smoke workload.
- `INTERFACE.md`: probability, identity, calibration and fusion contracts.

The Slurm workflow uses synthetic choices to validate plumbing and numerical agreement. It is not
evidence of decision quality, finance performance, calibration, or usefulness on a target task.
No real dataset or learned production checkpoint is included. HPG job history and setup guidance
are recorded in [`../../README.md`](../README.md); historical Laya handoffs elsewhere in the repo
are not the current implementation direction.

## Run on HiPerGator

From a login node, submit `run-jevlike.slurm` from this directory with `sbatch`. The job builds
inside its temporary scratch directory and writes Slurm output/error files in the submission
directory. It needs the HPG PyTorch module, Python, a C++17 compiler and CMake/compiler toolchain
available on the compute node. See the script before adapting resource requests to a real training
run.

The job caps OpenMP threads at `SLURM_CPUS_PER_TASK`. Its checkpoints, native executable and
exports are temporary smoke artifacts; successful job cleanup removes them. Preserve artifacts
to an approved durable location explicitly when adapting this to a real training run.

## Local regression suite

From the repository root, with PyTorch installed and a C++17 `g++` available:

```sh
make test-hpc HPC_PYTHON=python3
```

This also runs the kdb exporter/wrapper tests. The JevLike integration test executes the actual
Slurm script from a copied spool location, with only the environment-module command stubbed.
Training, evaluation, export, compilation and parity verification are real local operations.
It clears `PYTHONPATH` so package-import errors cannot be hidden by the caller environment.
Submit the actual JevLike cluster job from this component directory as described above; the
test deliberately reproduces that working-directory contract. Without `g++`, native integration
is reported as skipped, which does not meet the full acceptance gate.

See [VALIDATION.md](VALIDATION.md) for the audit, research sources and remaining cluster gate.

The export includes a SHA-256 manifest. A deployment/serving layer must verify the artifact hashes
before loading; the current C++ loader validates the binary structure and numeric values but does
not itself validate the JSON manifest.

## Boundaries

The current system is a buildable prototype, not the full research program. It does not yet include
real domain data, multi-specialist training, out-of-sample benchmark acceptance, production
calibration, low-latency service measurements, QPU execution, or a Vultr deployment. Quantum
methods remain experimental candidates evaluated against equal-budget classical baselines. Vultr
is scoped as a possible serving/deployment and external-load-test layer for HPG-trained artifacts;
it is not placed in the latency-sensitive request path until measurements support that choice.
