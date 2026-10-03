#!/usr/bin/env python3
"""Validate the results envelope. A number without a valid envelope cannot be quoted."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = [
    "engine", "generated_at", "git_commit", "universe",
    "in_sample", "out_of_sample", "costs_bps", "variants_tried",
    "metrics", "controls", "falsifiers_triggered", "notes",
]
SHA = re.compile(r"^[0-9a-f]{40}$")


def check(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return [f"{path.name}: not valid JSON ({exc})"]
    if not isinstance(data, dict):
        return [f"{path.name}: top level must be an object"]

    name = path.name
    for key in REQUIRED:
        if key not in data:
            errors.append(f"{name}: missing key '{key}'")

    commit = data.get("git_commit", "")
    if not SHA.match(str(commit)):
        errors.append(f"{name}: git_commit must be a 40 character sha")

    metrics = data.get("metrics", {})
    for window in ("is", "oos"):
        block = metrics.get(window, {}) if isinstance(metrics, dict) else {}
        for field in ("sharpe", "max_drawdown", "turnover", "n_obs"):
            if field not in block:
                errors.append(f"{name}: metrics.{window}.{field} is missing")

    if not isinstance(data.get("falsifiers_triggered"), list):
        errors.append(f"{name}: falsifiers_triggered must be a list")
    return errors


def main() -> int:
    files = sorted((ROOT / "results").glob("*.json"))
    if not files:
        print("no result files yet (results/*.json)")
        return 0
    problems: list[str] = []
    for path in files:
        problems.extend(check(path))
    if problems:
        print("results envelope problems:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"ok: {len(files)} result file(s) valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
