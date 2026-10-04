# Quantum joint sampling on HiPerGator and IBM

One circuit Born machine, three backends, one receipt.

- `numpy`: exact statevector in NumPy. Always available, and what the tests run.
- `aer-gpu`: Qiskit Aer on the HiPerGator L4 with the cuQuantum GPU device.
- `ibm`: IBM Quantum hardware through Qiskit Runtime on the free Open plan.

The object is a joint distribution over bit strings, so the two questions the quantum track
must answer can be scored directly: does the circuit beat the independent product of the
target's own marginals, and does real hardware match the simulator under shot noise. Both
answers are reported as distances, never as a trading claim.

## Why this shape

The coupling layer in `docs/inbox/jev-council-design-2026-10-04.md` needs one joint law over
the specialist marginals. A circuit Born machine is a compact candidate for that law, and the
tensor-network and statevector simulators on HiPerGator run the same circuit class at a size
no device on the free plans can match. The device pilot exists to test whether real hardware
adds anything at small size, with an equal-budget classical comparator.

Superposition, interference and entanglement describe this representation. The financial
observations stay classical, and entanglement alone is not evidence of a better forecast.

## Backends

`numpy` runs anywhere:

```sh
python3 qcbm_joint.py --backend numpy --steps 400 --output /tmp/qcbm-numpy-001
```

`aer-gpu` runs on HiPerGator. Build the environment once in a Blue directory, then submit:

```sh
module load pytorch/2.8.0
python3 -m venv --system-site-packages .venv-quantum
source .venv-quantum/bin/activate
pip install -r requirements-quantum.txt
sbatch run-qcbm-gpu.slurm
```

`ibm` runs on real hardware. Create an account on the IBM Quantum Open plan (about ten
minutes of device time per month), copy the API token from the dashboard, and save it on the
HiPerGator login node. The token lives in the environment, never in this repository:

```sh
export QISKIT_IBM_TOKEN=...            # from the IBM Quantum dashboard
python3 -c "from qiskit_ibm_runtime import QiskitRuntimeService; import os; \
  QiskitRuntimeService.save_account(channel='ibm_quantum_platform', token=os.environ.get('QISKIT_IBM_TOKEN'), overwrite=True)"
python3 qcbm_joint.py --backend ibm --shots 4000 --output /blue/<user>/qcbm-ibm-001
```

## What a receipt holds

`receipt.json` carries the target hash, the code hash, the backend and its metadata, the fitted
distribution, the product baseline, and five distances: model against target, model against
product, product against target, plus KL and log loss. `ready_for_performance_claim` is false
on every receipt, and an unavailable backend is recorded as an error rather than replaced.

## Boundaries

The built-in target is synthetic and exists to test the pipeline. A real run needs a joint
target built from the council's calibrated marginals, with the same chronological partitions
used everywhere else. Neither a simulator nor a device result is evidence of a trading edge.
