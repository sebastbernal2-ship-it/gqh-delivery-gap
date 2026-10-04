#!/usr/bin/env python3
"""A generic council evaluation over several data blocks, with the design's three numbers.

Blocks are data bundles, not architectures: each block owns one information family and enters the
council as a specialist. The evaluation reports, on a held-out block:

- incremental information: the proper-score gain of the fused council over the best single block
  and over naive concatenation;
- redundancy: how similar the blocks' distributions are, so a pair that only repeats itself is
  visible rather than hidden inside a fused score;
- marginal contribution: the leave-one-out council loss when a block is removed.

Every paired difference carries an issuer-blocked bootstrap interval, because rows are not
independent when many filings share one issuer.

Reuses the building blocks already tested in `filing_council.py`.
"""
from __future__ import annotations

import numpy as np

from council import CouncilModel
from filing_council import BlockSpecialist, case_from, clock, fit_block, four_way
from filing_specialist.model import matrix_from_rows, prevalence, score


def total_variation(left: np.ndarray, right: np.ndarray) -> float:
    """Mean total-variation distance between two sets of distributions."""
    return float(0.5 * np.abs(np.asarray(left) - np.asarray(right)).sum(axis=1).mean())


def top_probability_correlation(left: np.ndarray, right: np.ndarray) -> float:
    """Correlation of the two blocks' confidence across rows, a redundancy proxy."""
    left_top = np.asarray(left).max(axis=1)
    right_top = np.asarray(right).max(axis=1)
    if left_top.std() == 0 or right_top.std() == 0:
        return 0.0
    return float(np.corrcoef(left_top, right_top)[0, 1])


def row_log_loss(probabilities: np.ndarray, labels: np.ndarray) -> np.ndarray:
    matrix = np.asarray(probabilities, dtype=float)
    truth = np.asarray(labels, dtype=int)
    picked = np.clip(matrix[np.arange(len(truth)), truth], 1e-15, 1.0)
    return -np.log(picked)


def blocked_bootstrap(difference: np.ndarray, groups: list[str], resamples: int = 1000,
                      seed: int = 20261004, lower: float = 2.5, upper: float = 97.5) -> dict:
    """Percentile interval for a paired difference, resampling whole issuers."""
    order = np.argsort(np.asarray(groups))
    sorted_groups = np.asarray(groups)[order]
    values = np.asarray(difference, dtype=float)[order]
    boundaries = np.searchsorted(sorted_groups, np.unique(sorted_groups), side="left")
    boundaries = np.append(boundaries, len(sorted_groups))
    unique = np.unique(sorted_groups)
    sizes = np.diff(boundaries)
    rng = np.random.default_rng(seed)
    means = np.empty(resamples)
    for draw in range(resamples):
        picks = rng.integers(0, len(unique), len(unique))
        total = 0.0
        weight = 0.0
        for pick in picks:
            start, size = boundaries[pick], sizes[pick]
            total += values[start:start + size].sum()
            weight += size
        means[draw] = total / weight
    return {
        "point": float(values.mean()),
        "lower": float(np.percentile(means, lower)),
        "upper": float(np.percentile(means, upper)),
        "share_favouring_the_first": float((means > 0).mean()),
        "issuers": int(len(unique)),
        "resamples": int(resamples),
    }


def evaluate_blocks(rows: list[dict], blocks: dict[str, tuple[str, ...]],
                    fractions: tuple[float, float, float, float] = (0.42, 0.10, 0.10, 0.10),
                    steps: int = 600, seed: int = 20261004,
                    version: str = "panel-council-v1") -> dict:
    """Fit one specialist per data block, fuse them, and score singles, fusion and concatenation."""
    if len(blocks) < 2:
        raise ValueError("a council needs at least two data blocks")
    matrices = {name: matrix_from_rows(rows, features)[0] for name, features in blocks.items()}
    training, calibration, gate, pool, evaluation = four_way(rows, fractions)
    index_of = {id(row): position for position, row in enumerate(rows)}
    train_index = [index_of[id(row)] for row in training]
    cal_index = [index_of[id(row)] for row in calibration]
    gate_index = [index_of[id(row)] for row in gate]
    pool_index = [index_of[id(row)] for row in pool]
    eval_index = [index_of[id(row)] for row in evaluation]

    train_labels = np.array([int(row["label_bin"]) for row in training], dtype=int)
    eval_labels = np.array([int(row["label_bin"]) for row in evaluation], dtype=int)
    classes = tuple(sorted({int(label) for label in train_labels}))
    prior = prevalence(training, classes)

    specialists: dict[str, BlockSpecialist] = {
        name: fit_block(matrix[train_index], train_labels, f"evidence:{name}",
                        f"{name}-softmax-v1", version, steps, seed)
        for name, matrix in matrices.items()
    }
    combined = np.column_stack([matrices[name] for name in blocks])
    concatenated_specialist = fit_block(combined[train_index], train_labels, "evidence:concatenated",
                                        "concatenated-v1", version, steps, seed)

    def case_at(split_rows: list[dict], indices: list[int], stage: str):
        cases = []
        for position, row in enumerate(split_rows):
            index = indices[position]
            prior_available = split_rows[position - 1]["label_available"] if position else None
            cutoff, forecast_time, valid_until = clock(row, prior_available)
            forecasts = tuple(
                specialists[name].forecast(list(matrices[name][index]), f"{stage}-{index}", cutoff,
                                           forecast_time, valid_until)
                for name in blocks)
            cases.append(case_from(row, index, forecasts, stage))
        return cases

    calibration_cases = case_at(calibration, cal_index, "calibration")
    gate_cases = case_at(gate, gate_index, "gate")
    pool_cases = case_at(pool, pool_index, "pool")
    council = CouncilModel.fit(calibration_cases, gate_cases, pool_cases, fusion_method="linear")

    def evaluation_forecasts(position: int, keep: tuple[str, ...]):
        row = evaluation[position]
        index = eval_index[position]
        prior_available = evaluation[position - 1]["label_available"] if position else None
        cutoff, forecast_time, valid_until = clock(row, prior_available)
        return tuple(specialists[name].forecast(list(matrices[name][index]), f"evaluation-{index}",
                                                cutoff, forecast_time, valid_until)
                     for name in keep)

    def predict_all() -> dict[str, np.ndarray]:
        fused, singles = [], {name: [] for name in blocks}
        for position in range(len(evaluation)):
            forecasts = evaluation_forecasts(position, tuple(blocks))
            for name, forecast in zip(blocks, forecasts):
                singles[name].append(list(forecast.probabilities))
            fused.append(council.predict(forecasts).probabilities)
        return {"council": np.array(fused),
                **{name: np.array(values) for name, values in singles.items()}}

    everything = predict_all()
    concatenated_rows = np.vstack([
        concatenated_specialist.probability_vector(list(combined[index])) for index in eval_index])

    models = {"prevalence": np.tile(prior, (len(evaluation), 1)),
              "concatenated": concatenated_rows,
              "council": everything["council"],
              **{name: everything[name] for name in blocks}}
    scores = {name: score(values, eval_labels, classes) for name, values in models.items()}
    single_names = [name for name in blocks]
    best_single = min(single_names, key=lambda name: scores[name]["log_loss"])

    leave_one_out = {}
    for drop in single_names:
        keep = tuple(name for name in blocks if name != drop)
        reduced_calibration, reduced_gate, reduced_pool = [], [], []
        for split_rows, indices, stage in ((calibration, cal_index, "calibration"),
                                           (gate, gate_index, "gate"),
                                           (pool, pool_index, "pool")):
            bucket = {"calibration": reduced_calibration, "gate": reduced_gate,
                      "pool": reduced_pool}[stage]
            for position, row in enumerate(split_rows):
                index = indices[position]
                prior_available = split_rows[position - 1]["label_available"] if position else None
                cutoff, forecast_time, valid_until = clock(row, prior_available)
                forecasts = tuple(
                    specialists[name].forecast(list(matrices[name][index]), f"{stage}-{index}",
                                               cutoff, forecast_time, valid_until)
                    for name in keep)
                bucket.append(case_from(row, index, forecasts, stage))
        reduced = CouncilModel.fit(reduced_calibration, reduced_gate, reduced_pool,
                                   fusion_method="linear")
        fused = [reduced.predict(evaluation_forecasts(position, keep)).probabilities
                 for position in range(len(evaluation))]
        leave_one_out[drop] = score(np.array(fused), eval_labels, classes)

    council_loss = row_log_loss(everything["council"], eval_labels)
    single_loss = row_log_loss(everything[best_single], eval_labels)
    concatenated_loss = row_log_loss(concatenated_rows, eval_labels)
    issuers = [str(row["ticker"]) for row in evaluation]
    diagnostics = {
        "best_single": best_single,
        "council_minus_best_single": blocked_bootstrap(single_loss - council_loss, issuers),
        "council_minus_concatenated": blocked_bootstrap(concatenated_loss - council_loss, issuers),
        "leave_one_out_log_loss": {name: leave_one_out[name]["log_loss"] for name in blocks},
        "marginal_contribution": {name: leave_one_out[name]["log_loss"] - scores["council"]["log_loss"]
                                  for name in blocks},
        "redundancy": {},
    }
    names = list(blocks)
    for left in range(len(names)):
        for right in range(left + 1, len(names)):
            first, second = names[left], names[right]
            diagnostics["redundancy"][f"{first}|{second}"] = {
                "total_variation": total_variation(everything[first], everything[second]),
                "top_probability_correlation": top_probability_correlation(everything[first],
                                                                           everything[second]),
                "argmax_agreement": float((everything[first].argmax(axis=1)
                                           == everything[second].argmax(axis=1)).mean()),
            }
    return {
        "blocks": {name: len(features) for name, features in blocks.items()},
        "features": {name: list(features) for name, features in blocks.items()},
        "split": {"training": len(training), "calibration": len(calibration), "gate": len(gate),
                  "pool": len(pool), "evaluation": len(evaluation),
                  "train_through": max(row["label_available"] for row in training),
                  "evaluation_from": min(row["label_available"] for row in evaluation)},
        "classes": list(classes),
        "scores": scores,
        "diagnostics": diagnostics,
        "row_detail": {
            "labels": [int(label) for label in eval_labels],
            "issuers": issuers,
            "council": everything["council"].tolist(),
            **{name: everything[name].tolist() for name in blocks},
            "concatenated": concatenated_rows.tolist(),
        },
        "fusion": "linear opinion pool",
        "steps": steps,
        "seed": seed,
    }
