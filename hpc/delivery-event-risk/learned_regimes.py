#!/usr/bin/env python3
"""Fit a past-only Gaussian HMM to SPY returns and classify event-date states.

This emits an exploratory sidecar. It does not read event outcomes or select a
trading rule. The HMM is re-fit using only observations available before each
event, and the reported probability is computed with the forward filter rather
than hmmlearn's full-sequence smoothed posterior.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from hmmlearn.hmm import GaussianHMM
import hmmlearn


def event_utc_date(stamp: str) -> dt.date:
    value = dt.datetime.fromisoformat(stamp.strip().replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError("event timestamp must include a timezone")
    return value.astimezone(dt.timezone.utc).date()


def read_spy_returns(path: Path, sealed_start: dt.date) -> tuple[list[str], np.ndarray]:
    closes: dict[str, float] = {}
    rows: list[tuple[str, float]] = []
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        required = {"date", "sym", "close_px_e8usd"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"bars TSV must contain {sorted(required)}")
        seen: set[str] = set()
        for row in reader:
            if row["sym"] != "SPY":
                continue
            day = dt.date.fromisoformat(row["date"])
            if day >= sealed_start:
                raise ValueError("bars include sealed-period data; stage a development-only prefix")
            if row["date"] in seen:
                raise ValueError(f"duplicate SPY date: {row['date']}")
            seen.add(row["date"])
            close = int(row["close_px_e8usd"]) / 100_000_000.0
            if not math.isfinite(close) or close <= 0:
                raise ValueError(f"invalid SPY close on {row['date']}")
            closes[row["date"]] = close
    dates = sorted(closes)
    for prior, current in zip(dates, dates[1:]):
        rows.append((current, math.log(closes[current] / closes[prior])))
    if not rows:
        raise ValueError("no SPY returns in bars input")
    return [day for day, _ in rows], np.asarray([value for _, value in rows], dtype=float)


def filtered_probabilities(model: GaussianHMM, observations: np.ndarray) -> np.ndarray:
    """Return causal forward probabilities using fitted HMM parameters."""
    means = np.asarray(model.means_, dtype=float)
    variances = np.asarray(model.covars_, dtype=float)
    if variances.ndim == 3:
        variances = np.diagonal(variances, axis1=1, axis2=2)
    variances = np.maximum(variances, 1e-12)
    log_transition = np.log(np.maximum(model.transmat_, 1e-300))
    log_initial = np.log(np.maximum(model.startprob_, 1e-300))
    log_two_pi = math.log(2.0 * math.pi)
    alpha = log_initial.copy()
    for observation in observations:
        residual = observation[None, :] - means
        emission = -0.5 * np.sum(log_two_pi + np.log(variances) + residual * residual / variances, axis=1)
        prior = np.asarray([_logsumexp(alpha + log_transition[:, state])
                            for state in range(model.n_components)])
        alpha = prior + emission
        alpha -= _logsumexp(alpha)
    probabilities = np.exp(alpha)
    return probabilities / probabilities.sum()


def _logsumexp(values: np.ndarray) -> float:
    maximum = float(np.max(values))
    return maximum + math.log(float(np.exp(values - maximum).sum()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--bars", type=Path, required=True)
    parser.add_argument("--sealed-start", type=dt.date.fromisoformat, required=True)
    parser.add_argument("--minimum-history", type=int, default=504,
                        help="minimum past daily returns before fitting (default: 504)")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.minimum_history < 252:
        parser.error("minimum history must be at least 252 daily returns")

    bar_dates, daily_returns = read_spy_returns(args.bars, args.sealed_start)
    with args.events.open(newline="", encoding="utf-8") as stream:
        event_reader = csv.DictReader(stream)
        if not event_reader.fieldnames or "event_id" not in event_reader.fieldnames or "available_at_utc" not in event_reader.fieldnames:
            parser.error("events CSV must contain event_id and available_at_utc")
        events = list(event_reader)
    for event in events:
        if event_utc_date(event["available_at_utc"]) >= args.sealed_start:
            parser.error("events CSV contains a sealed-date event")
        if event.get("in_sealed_window", "").strip().lower() in {"true", "1", "yes"}:
            parser.error("events CSV contains a row marked in_sealed_window")

    fields = ["event_id", "event_date_utc", "asof_session", "model", "state", "high_vol_probability",
              "low_state_return_mean", "high_state_return_mean", "low_state_abs_return_mean",
              "high_state_abs_return_mean", "training_observations", "training_start", "training_end",
              "hmmlearn_version", "status"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        fit_cache: dict[str, dict[str, str]] = {}
        for event in events:
            event_date = event_utc_date(event["available_at_utc"])
            asof = next((i for i in range(len(bar_dates) - 1, -1, -1)
                         if dt.date.fromisoformat(bar_dates[i]) < event_date), None)
            base = {"event_id": event["event_id"], "event_date_utc": event_date.isoformat(),
                    "model": "GaussianHMM(2, diagonal Gaussian)", "hmmlearn_version": hmmlearn.__version__}
            if asof is None or asof + 1 < args.minimum_history:
                writer.writerow({**base, "status": "warmup_insufficient_history"})
                continue
            asof_date = bar_dates[asof]
            if asof_date not in fit_cache:
                # Returns are dated at their ending close. The final observation is
                # therefore the last completed SPY session strictly before the event.
                raw = daily_returns[:asof + 1]
                observations = np.column_stack((raw, np.abs(raw)))
                model = GaussianHMM(n_components=2, covariance_type="diag", n_iter=200,
                                    tol=1e-4, min_covar=1e-6, random_state=17,
                                    implementation="log")
                model.fit(observations)
                probs = filtered_probabilities(model, observations)
                abs_means = model.means_[:, 1]
                high_state = int(np.argmax(abs_means))
                low_state = 1 - high_state
                fit_cache[asof_date] = {
                    "event_id": "", "event_date_utc": "", "asof_session": asof_date,
                    "model": "GaussianHMM(2, diagonal Gaussian)",
                    "state": "high_vol" if probs[high_state] >= 0.5 else "low_vol",
                    "high_vol_probability": f"{probs[high_state]:.12g}",
                    "low_state_return_mean": f"{model.means_[low_state, 0]:.12g}",
                    "high_state_return_mean": f"{model.means_[high_state, 0]:.12g}",
                    "low_state_abs_return_mean": f"{model.means_[low_state, 1]:.12g}",
                    "high_state_abs_return_mean": f"{model.means_[high_state, 1]:.12g}",
                    "training_observations": str(len(raw)), "training_start": bar_dates[0],
                    "training_end": asof_date, "hmmlearn_version": hmmlearn.__version__, "status": "fit",
                }
            writer.writerow({**fit_cache[asof_date], "event_id": event["event_id"],
                             "event_date_utc": event_date.isoformat()})

    receipt = {
        "model": "two-state Gaussian HMM; emissions are SPY daily log return and absolute log return",
        "training_protocol": "refit per unique event as-of session, using only SPY returns ending on or before that session",
        "inference": "causal forward filtering over observations used to fit; no full-sample smoothing",
        "state_naming": "high_vol is the fitted state with greater mean absolute daily return",
        "events_sha256": hashlib.sha256(args.events.read_bytes()).hexdigest(),
        "bars_sha256": hashlib.sha256(args.bars.read_bytes()).hexdigest(),
        "sealed_start": args.sealed_start.isoformat(), "hmmlearn_version": hmmlearn.__version__,
    }
    args.output.with_suffix(args.output.suffix + ".manifest.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
