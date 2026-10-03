#!/usr/bin/env python3
"""Small exact-statevector QCBM fit with synthetic joint-distribution baselines."""

from __future__ import annotations

import argparse
import json
import math
import random
import time


QUBITS = 3
LAYERS = 3
EPSILON = 1e-12
TARGET = (0.29, 0.17, 0.12, 0.16, 0.11, 0.08, 0.05, 0.02)


def ry_layer(state: list[complex], qubit: int, angle: float) -> None:
    """Apply a real-valued Y rotation in-place to a little-endian statevector."""
    mask = 1 << qubit
    cosine = math.cos(angle / 2.0)
    sine = math.sin(angle / 2.0)
    for index in range(len(state)):
        if index & mask == 0:
            partner = index | mask
            zero, one = state[index], state[partner]
            state[index] = cosine * zero - sine * one
            state[partner] = sine * zero + cosine * one


def cnot_layer(state: list[complex], control: int, target: int) -> None:
    control_mask = 1 << control
    target_mask = 1 << target
    for index in range(len(state)):
        if index & control_mask and index & target_mask == 0:
            partner = index | target_mask
            state[index], state[partner] = state[partner], state[index]


def qcbm_probabilities(parameters: list[float]) -> list[float]:
    if len(parameters) != QUBITS * LAYERS:
        raise ValueError("parameter count does not match circuit layout")
    state: list[complex] = [0j] * (1 << QUBITS)
    state[0] = 1.0 + 0j
    parameter = 0
    for _ in range(LAYERS):
        for qubit in range(QUBITS):
            ry_layer(state, qubit, parameters[parameter])
            parameter += 1
        cnot_layer(state, 0, 1)
        cnot_layer(state, 1, 2)
    probabilities = [abs(amplitude) ** 2 for amplitude in state]
    total = sum(probabilities)
    if not math.isfinite(total) or total <= 0.0:
        raise ValueError("circuit produced invalid state")
    return [probability / total for probability in probabilities]


def sample_counts(probabilities: tuple[float, ...] | list[float], count: int,
                  rng: random.Random) -> list[int]:
    cumulative: list[float] = []
    running = 0.0
    for probability in probabilities:
        running += probability
        cumulative.append(running)
    result = [0] * len(probabilities)
    for _ in range(count):
        draw = rng.random()
        low, high = 0, len(cumulative)
        while low < high:
            middle = (low + high) // 2
            if draw < cumulative[middle]:
                high = middle
            else:
                low = middle + 1
        result[min(low, len(result) - 1)] += 1
    return result


def fit_qcbm(counts: list[int], seed: int, steps: int) -> tuple[list[float], int]:
    """Fit by SPSA against empirical cross-entropy using exact circuit probabilities."""
    rng = random.Random(seed)
    parameters = [rng.uniform(-0.4, 0.4) for _ in range(QUBITS * LAYERS)]
    total = sum(counts)
    evaluations = 0

    def loss(values: list[float]) -> float:
        nonlocal evaluations
        probabilities = qcbm_probabilities(values)
        evaluations += 1
        return -sum(count * math.log(max(EPSILON, probability))
                    for count, probability in zip(counts, probabilities)) / total

    best_parameters = parameters[:]
    best_loss = loss(parameters)
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
    return best_parameters, evaluations


def independent_baseline(counts: list[int], alpha: float = 1.0) -> list[float]:
    total = sum(counts)
    marginals = [
        (sum(count for state, count in enumerate(counts) if state & (1 << bit)) + alpha)
        / (total + 2.0 * alpha)
        for bit in range(QUBITS)
    ]
    distribution = []
    for state in range(1 << QUBITS):
        probability = 1.0
        for bit, marginal in enumerate(marginals):
            probability *= marginal if state & (1 << bit) else 1.0 - marginal
        distribution.append(probability)
    return distribution


def categorical_baseline(counts: list[int], alpha: float = 1.0) -> list[float]:
    denominator = sum(counts) + alpha * len(counts)
    return [(count + alpha) / denominator for count in counts]


def score(prediction: list[float], test_counts: list[int]) -> dict[str, float]:
    kl = sum(target * math.log(target / max(EPSILON, estimate))
             for target, estimate in zip(TARGET, prediction))
    total_variation = 0.5 * sum(abs(target - estimate)
                               for target, estimate in zip(TARGET, prediction))
    test_total = sum(test_counts)
    empirical = [count / test_total for count in test_counts]
    test_log_loss = -sum(count * math.log(max(EPSILON, probability))
                         for count, probability in zip(test_counts, prediction)) / test_total
    expected_brier = sum(
        count * (sum(probability * probability for probability in prediction)
                 + 1.0 - 2.0 * prediction[state])
        for state, count in enumerate(test_counts)
    ) / test_total
    tail_indices = (7,)
    target_tail = sum(TARGET[index] for index in tail_indices)
    predicted_tail = sum(prediction[index] for index in tail_indices)
    observed_tail = sum(empirical[index] for index in tail_indices)
    return {
        "kl_target_to_model": kl,
        "total_variation": total_variation,
        "absolute_tail_mass_error_state_111": abs(target_tail - predicted_tail),
        "predicted_tail_mass_state_111": predicted_tail,
        "test_multiclass_log_loss_nats": test_log_loss,
        "test_expected_multiclass_brier": expected_brier,
        "test_observed_tail_mass_state_111": observed_tail,
        "test_absolute_tail_mass_error_state_111": abs(observed_tail - predicted_tail),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20261003)
    parser.add_argument("--train-samples", type=int, default=5000)
    parser.add_argument("--steps", type=int, default=160)
    args = parser.parse_args()
    if args.train_samples < 100 or args.steps < 1:
        parser.error("--train-samples must be >= 100 and --steps must be >= 1")

    rng = random.Random(args.seed)
    training_counts = sample_counts(TARGET, args.train_samples, rng)
    test_counts = sample_counts(TARGET, 20000, random.Random(args.seed + 2))
    started = time.perf_counter()
    parameters, evaluations = fit_qcbm(training_counts, args.seed + 1, args.steps)
    qcbm_seconds = time.perf_counter() - started
    qcbm_distribution = qcbm_probabilities(parameters)
    predictions = {
        "qcbm_exact_statevector": qcbm_distribution,
        "classical_independent_bernoulli": independent_baseline(training_counts),
        "classical_smoothed_joint_categorical": categorical_baseline(training_counts),
    }
    report = {
        "contract": "qcbm-joint-distribution-0.1.0",
        "data": "synthetic_three_bit_distribution_only",
        "seed": args.seed,
        "training_samples": args.train_samples,
        "independent_test_samples": sum(test_counts),
        "target_probabilities_state_000_to_111": list(TARGET),
        "known_target_distribution_scores": {
            name: score(values, test_counts) for name, values in predictions.items()
        },
        "experiment": {
            "qubits": QUBITS,
            "rotation_layers": LAYERS,
            "trainable_parameters": len(parameters),
            "optimizer": "SPSA with exact statevector objective",
            "optimizer_steps": args.steps,
            "statevector_evaluations": evaluations,
            "qcbm_fit_wall_seconds": round(qcbm_seconds, 6),
            "classical_baseline_fit": "closed-form from the same training sample",
            "budget_note": "same observations; compute and parameter budgets are reported, not equalized",
        },
        "limitations": [
            "synthetic fixture only; no market data or financial decision",
            "statevector simulation is classical computation, not QPU execution or quantum advantage",
            "exact noiseless probabilities; finite-shot error, hardware noise, and error mitigation are absent",
            "one fixed circuit layout and SPSA run; no architecture search or independent-restart analysis",
        ],
    }
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
