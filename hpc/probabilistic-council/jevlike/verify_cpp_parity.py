"""Compare the vendored PyTorch reference and native C++ tiny scorer on synthetic cases."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import torch

from jevlike.data import ChoiceExample
from jevlike.model import load_checkpoint


CASES = (
    ("Choose the exact badge amber badger. Badge: amber badger.",
     ("azure crane", "amber badger", "gold heron")),
    ("Select the northern marker: bronze dolphin. Context notes are quiet.",
     ("coral falcon", "bronze dolphin")),
    ("The signed label is café crane; select the matching candidate.",
     ("cafe crane", "café crane", "gold ibis", "amber jaguar")),
    ("The target is indigo heron. Compare all listed candidates exactly.",
     ("amber badger", "azure crane", "bronze dolphin", "coral falcon",
      "crimson gecko", "gold ibis", "green jaguar", "indigo heron")),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--cpp-binary", type=Path, required=True)
    args = parser.parse_args()
    model_version = sha256(args.checkpoint)
    data_version = "jevlike-synthetic-parity-v1"
    model, collator, _ = load_checkpoint(args.checkpoint, torch.device("cpu"))
    model.eval()
    maximum_error = 0.0

    for index, (text, options) in enumerate(CASES):
        batch = collator([ChoiceExample(text, options, 0)])
        with torch.no_grad():
            reference = model(batch).softmax(-1)[0, :len(options)].tolist()
        forecast_time = 1_800_000_000 + index * 10
        command = [
            str(args.cpp_binary), str(args.weights), model_version, data_version,
            text, "synthetic-context", str(forecast_time), str(forecast_time + 5),
            str(forecast_time - 1), *options,
        ]
        actual = json.loads(subprocess.run(command, check=True, capture_output=True, text=True).stdout)
        if actual["outcome_space"] != list(options):
            raise SystemExit("C++ option order differs from the request")
        error = max(abs(left - right) for left, right in zip(reference, actual["probabilities"]))
        maximum_error = max(maximum_error, error)

    tolerance = 2e-5
    if maximum_error > tolerance:
        raise SystemExit(f"C++/PyTorch probability mismatch {maximum_error:.8g} > {tolerance}")
    print(json.dumps({
        "contract": "jevlike-tiny-cpp-v1",
        "synthetic_cases": len(CASES),
        "option_counts": [len(options) for _, options in CASES],
        "maximum_absolute_probability_error": maximum_error,
        "tolerance": tolerance,
        "result": "parity_ok",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
