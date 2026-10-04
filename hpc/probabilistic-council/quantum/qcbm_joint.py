#!/usr/bin/env python3
"""Device-agnostic circuit Born machine for one joint target distribution.

Backends
  numpy    exact statevector in NumPy; always available; used by the tests
  aer-gpu  Qiskit Aer with the cuQuantum GPU device, for HiPerGator L4 runs
  ibm      IBM Quantum hardware through Qiskit Runtime, free Open plan minutes

The target is a JSON object {"states": [bit strings], "probabilities": [...]} or the
built-in correlated default. The receipt compares the fitted circuit against the target,
against the independent product of the target's own marginals, and reports the
target-versus-product distance so dependence is visible instead of assumed.

No performance claim is made. Every receipt carries ready_for_performance_claim false, and
a backend that is unavailable is recorded as an error rather than replaced by another one.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time
from pathlib import Path

EPSILON = 1e-12
DEFAULT_QUBITS = 3
DEFAULT_LAYERS = 3
DEFAULT_TARGET = (0.29, 0.17, 0.12, 0.16, 0.11, 0.08, 0.05, 0.02)


def state_label(index: int, qubits: int) -> str:
    """Bit string with qubit zero leftmost, matching the statevector indexing below."""
    return "".join(str((index >> qubit) & 1) for qubit in range(qubits))


def apply_ry(state: list[complex], qubit: int, angle: float) -> None:
    mask = 1 << qubit
    cosine, sine = math.cos(angle / 2.0), math.sin(angle / 2.0)
    for index in range(len(state)):
        if index & mask == 0:
            partner = index | mask
            zero, one = state[index], state[partner]
            state[index] = cosine * zero - sine * one
            state[partner] = sine * zero + cosine * one


def apply_cnot(state: list[complex], control: int, target: int) -> None:
    control_mask, target_mask = 1 << control, 1 << target
    for index in range(len(state)):
        if index & control_mask and index & target_mask == 0:
            partner = index | target_mask
            state[index], state[partner] = state[partner], state[index]


def circuit_probabilities(parameters: list[float], qubits: int, layers: int) -> list[float]:
    """Exact Born probabilities for RY layers and a CNOT ring."""
    if len(parameters) != qubits * layers:
        raise ValueError("parameter count does not match the circuit layout")
    state: list[complex] = [0j] * (1 << qubits)
    state[0] = 1.0 + 0j
    position = 0
    for _ in range(layers):
        for qubit in range(qubits):
            apply_ry(state, qubit, parameters[position])
            position += 1
        for qubit in range(qubits):
            apply_cnot(state, qubit, (qubit + 1) % qubits)
    probabilities = [abs(amplitude) ** 2 for amplitude in state]
    total = sum(probabilities)
    if not math.isfinite(total) or total <= 0.0:
        raise ValueError("circuit produced an invalid state")
    return [probability / total for probability in probabilities]


def initial_parameters(qubits: int, layers: int, seed: int) -> list[float]:
    rng = random.Random(seed)
    return [rng.uniform(-0.4, 0.4) for _ in range(qubits * layers)]


def fit_spsa(target: list[float], qubits: int, layers: int, steps: int, seed: int) -> dict:
    """Simultaneous perturbation fit of the circuit against the target distribution."""
    rng = random.Random(seed)
    parameters = initial_parameters(qubits, layers, seed)
    evaluations = 0

    def loss(values: list[float]) -> float:
        nonlocal evaluations
        evaluations += 1
        probabilities = circuit_probabilities(values, qubits, layers)
        return -sum(mass * math.log(max(EPSILON, probability))
                    for mass, probability in zip(target, probabilities))

    initial_loss = loss(parameters)
    best_parameters, best_loss = parameters[:], initial_loss
    for step in range(1, steps + 1):
        perturbation = [1.0 if rng.random() < 0.5 else -1.0 for _ in parameters]
        ck = 0.18 / (step ** 0.101)
        plus = [value + ck * delta for value, delta in zip(parameters, perturbation)]
        minus = [value - ck * delta for value, delta in zip(parameters, perturbation)]
        gradient_scale = (loss(plus) - loss(minus)) / (2.0 * ck)
        learning_rate = 0.16 / ((step + 8.0) ** 0.602)
        parameters = [
            (value - learning_rate * gradient_scale / delta) % (2.0 * math.pi)
            for value, delta in zip(parameters, perturbation)
        ]
        current_loss = loss(parameters)
        if current_loss < best_loss:
            best_parameters, best_loss = parameters[:], current_loss
    return {"parameters": best_parameters, "initial_loss": initial_loss,
            "best_loss": best_loss, "evaluations": evaluations}


def load_target(path: Path, qubits: int) -> list[float]:
    document = json.loads(path.read_text())
    states = document.get("states")
    probabilities = document.get("probabilities")
    expected = [state_label(index, qubits) for index in range(1 << qubits)]
    if states != expected:
        raise ValueError("target states must be the full bit-string basis in order")
    if not isinstance(probabilities, list) or len(probabilities) != 1 << qubits:
        raise ValueError("target needs one probability per state")
    if any(not isinstance(value, (int, float)) or value < 0 for value in probabilities):
        raise ValueError("target probabilities must be nonnegative numbers")
    total = sum(probabilities)
    if abs(total - 1.0) > 1e-9:
        raise ValueError("target probabilities must sum to one")
    return [probability / total for probability in probabilities]


def product_distribution(target: list[float], qubits: int) -> list[float]:
    """Independent product of the target's own marginals; the no-dependence baseline."""
    marginals = []
    for qubit in range(qubits):
        mass = sum(target[index] for index in range(1 << qubits)
                   if index & (1 << qubit))
        marginals.append(mass)
    result = []
    for index in range(1 << qubits):
        probability = 1.0
        for qubit, marginal in enumerate(marginals):
            probability *= marginal if index & (1 << qubit) else 1.0 - marginal
        result.append(probability)
    return result


def total_variation(left: list[float], right: list[float]) -> float:
    return 0.5 * sum(abs(a - b) for a, b in zip(left, right))


def kl_divergence(target: list[float], model: list[float]) -> float:
    return sum(mass * math.log(max(EPSILON, mass) / max(EPSILON, probability))
               for mass, probability in zip(target, model))


def log_loss(target: list[float], model: list[float]) -> float:
    return -sum(mass * math.log(max(EPSILON, probability))
                for mass, probability in zip(target, model))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_aer_gpu(parameters: list[float], qubits: int, shots: int) -> dict:
    """Exact statevector on the Aer GPU device. Unverified until the cluster run reports."""
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator
    circuit = QuantumCircuit(qubits)
    position = 0
    layers = len(parameters) // qubits
    for _ in range(layers):
        for qubit in range(qubits):
            circuit.ry(parameters[position], qubit)
            position += 1
        for qubit in range(qubits):
            circuit.cx(qubit, (qubit + 1) % qubits)
    circuit.measure_all()
    backend = AerSimulator(method="statevector", device="GPU")
    result = backend.run(transpile(circuit, backend), shots=shots, seed_simulator=20261004).result()
    counts = result.get_counts()
    total = sum(counts.values())
    probabilities = []
    for index in range(1 << qubits):
        key = state_label(index, qubits)[::-1]  # Qiskit prints the highest qubit first.
        probabilities.append(counts.get(key, 0) / total)
    return {"backend_name": backend.name, "shots": shots, "probabilities": probabilities}


def run_ibm(parameters: list[float], qubits: int, shots: int) -> dict:
    """IBM Quantum hardware through Qiskit Runtime. Requires a saved account and token."""
    from qiskit import QuantumCircuit, transpile
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    service = QiskitRuntimeService()
    backend = service.least_busy(operational=True, simulator=False)
    circuit = QuantumCircuit(qubits)
    position = 0
    layers = len(parameters) // qubits
    for _ in range(layers):
        for qubit in range(qubits):
            circuit.ry(parameters[position], qubit)
            position += 1
        for qubit in range(qubits):
            circuit.cx(qubit, (qubit + 1) % qubits)
    circuit.measure_all()
    compiled = transpile(circuit, backend)
    sampler = SamplerV2(backend)
    job = sampler.run([compiled], shots=shots)
    result = job.result()[0].data.meas.get_counts()
    total = sum(result.values())
    probabilities = []
    for index in range(1 << qubits):
        key = state_label(index, qubits)[::-1]
        probabilities.append(result.get(key, 0) / total)
    return {"backend_name": backend.name, "shots": shots, "probabilities": probabilities,
            "job_id": job.job_id()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("numpy", "aer-gpu", "ibm"), default="numpy")
    parser.add_argument("--target", type=Path, default=None,
                        help="JSON distribution; default is the built-in correlated target")
    parser.add_argument("--qubits", type=int, default=DEFAULT_QUBITS)
    parser.add_argument("--layers", type=int, default=DEFAULT_LAYERS)
    parser.add_argument("--steps", type=int, default=400)
    parser.add_argument("--seed", type=int, default=20261004)
    parser.add_argument("--shots", type=int, default=4000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    started = time.time()
    if args.target is not None:
        target = load_target(args.target, args.qubits)
        target_source = {"file": str(args.target), "sha256": file_sha256(args.target)}
    else:
        if args.qubits != DEFAULT_QUBITS or len(DEFAULT_TARGET) != 1 << args.qubits:
            raise SystemExit("the built-in target has three qubits; pass --target or --qubits 3")
        target = list(DEFAULT_TARGET)
        target_source = {"file": None, "sha256": None}

    fitted = fit_spsa(target, args.qubits, args.layers, args.steps, args.seed)
    model = circuit_probabilities(fitted["parameters"], args.qubits, args.layers)
    product = product_distribution(target, args.qubits)

    backend_metadata: dict = {"requested": args.backend}
    if args.backend in ("aer-gpu", "ibm"):
        try:
            runner = run_aer_gpu if args.backend == "aer-gpu" else run_ibm
            sampled = runner(fitted["parameters"], args.qubits, args.shots)
            backend_metadata.update(sampled)
            model = sampled["probabilities"]
        except Exception as error:  # The backend is reported, never silently replaced.
            backend_metadata["error"] = f"{type(error).__name__}: {error}"

    receipt = {
        "schema": "qcbm-joint-v1",
        "scope": "engineering",
        "backend": args.backend,
        "backend_metadata": backend_metadata,
        "target": target_source,
        "code_sha256": file_sha256(Path(__file__)),
        "qubits": args.qubits,
        "layers": args.layers,
        "steps": args.steps,
        "seed": args.seed,
        "shots": args.shots,
        "evaluations": fitted["evaluations"],
        "wall_seconds": round(time.time() - started, 3),
        "model": {state_label(index, args.qubits): model[index]
                  for index in range(1 << args.qubits)},
        "product": {state_label(index, args.qubits): product[index]
                    for index in range(1 << args.qubits)},
        "metrics": {
            "tv_model_target": total_variation(model, target),
            "kl_model_target": kl_divergence(target, model),
            "log_loss_model_target": log_loss(target, model),
            "tv_product_target": total_variation(product, target),
            "tv_model_product": total_variation(model, product),
            "initial_log_loss": fitted["initial_loss"],
            "best_log_loss": fitted["best_loss"],
        },
        "ready_for_performance_claim": False,
        "limitations": [
            "engineering pilot, not a trading claim",
            "one circuit ansatz, one seed, no hyperparameter search",
            "the built-in target is synthetic; a real joint target must come from the council",
            "a backend error means that backend did not run; no substitution is recorded",
        ],
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps({"backend": args.backend, "metrics": receipt["metrics"],
                      "backend_metadata": backend_metadata}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
