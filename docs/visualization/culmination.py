#!/usr/bin/env python3
"""One file: load the cached culmination results and render them in this section's dashboard.

Run it and it reads the cached daily ledgers under `results/culmination-ledgers/`, prints the exact
cached metrics, and calls this section's own builder so the figures appear immediately:

    python3 docs/visualization/culmination.py
    python3 docs/visualization/culmination.py --candidate B_two_sleeve_headline
    python3 docs/visualization/culmination.py --all
    python3 docs/visualization/culmination.py --rebuild      # regenerate cache

The ledgers are in this section's daily schema: date, net_return, gross_return, baseline, sample,
regime. The baseline column is the equal-weight basket, the sample column is in-sample before 2019 and
out-of-sample after, and the regime column is the drawdown state the honest walk-forward chose. Nothing
here recomputes a model unless `--rebuild` is passed, so the default path is instant and cannot drift
from the committed artifact `results/culmination.json`.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LEDGERS = ROOT / "results" / "culmination-ledgers"
SUMMARY = ROOT / "results" / "culmination.json"
BEST = "C_conditioned"


def cached_ledgers() -> dict[str, Path]:
    return {path.stem: path for path in sorted(LEDGERS.glob("*.csv"))}


def print_metrics(summary: dict) -> None:
    print("cached results from results/culmination.json")
    print("%-26s %9s %7s %8s %8s %6s" % ("candidate", "net", "vol", "sharpe", "maxDD", "days"))
    for name, block in summary["candidates"].items():
        metrics = block["metrics"]
        print("%-26s %+8.2f%% %6.1f%% %+8.3f %+7.1f%% %6d" % (
            name, metrics["annual_return"] * 100, metrics["annual_vol"] * 100,
            metrics["sharpe"], metrics["max_drawdown"] * 100, block["days"]))
    floor = summary.get("long_floor", {}).get("metrics")
    if floor:
        print("%-26s %+8.2f%% %6.1f%% %+8.3f %+7.1f%% %6s" % (
            "long floor (basket)", floor["annual_return"] * 100, floor["annual_vol"] * 100,
            floor["sharpe"], floor["max_drawdown"] * 100, "n/a"))
    choices = summary.get("honest_choices") or []
    if choices:
        print("\nhonest walk-forward rule: %s %s, chosen in %d of %d years" % (
            choices[0]["definition"], choices[0]["multipliers"], sum(
                1 for choice in choices if choice["multipliers"] == choices[0]["multipliers"]),
            len(choices)))


DEFAULT_OUTPUTS = ("dashboard.html", "reproduction-manifest.json")


def preserved_outputs() -> dict[str, bytes | None]:
    """The builder writes its standard outputs; keep them as they were before this run."""
    saved = {}
    for name in DEFAULT_OUTPUTS:
        path = HERE / name
        saved[name] = path.read_bytes() if path.exists() else None
    return saved


def restore_outputs(saved: dict[str, bytes | None]) -> None:
    for name, payload in saved.items():
        path = HERE / name
        if payload is None:
            if path.exists():
                path.unlink()
        else:
            path.write_bytes(payload)


def build(candidate: str, ledger: Path) -> Path:
    builder = HERE / "reproduce.py"
    if not builder.exists():
        raise SystemExit(f"this section's builder is missing: {builder}")
    saved = preserved_outputs()
    result = subprocess.run([sys.executable, str(builder), "--daily-ledger", str(ledger)],
                            cwd=str(HERE), capture_output=True, text=True)
    if result.returncode != 0:
        restore_outputs(saved)
        raise SystemExit(f"builder failed:\n{result.stdout[-800:]}\n{result.stderr[-800:]}")
    produced = HERE / "dashboard.html"
    target = HERE / f"dashboard-culmination-{candidate}.html"
    target.write_bytes(produced.read_bytes())
    restore_outputs(saved)
    return target


def rebuild() -> None:
    script = ROOT / "scripts" / "run_culmination.py"
    if not script.exists():
        raise SystemExit("scripts/run_culmination.py is missing; cannot rebuild the cache")
    result = subprocess.run([sys.executable, str(script)], cwd=str(ROOT),
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"rebuild failed:\n{result.stdout[-600:]}\n{result.stderr[-600:]}")
    print(result.stdout.strip().splitlines()[-1])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", default=BEST, help="which cached ledger to render")
    parser.add_argument("--all", action="store_true", help="render every cached candidate")
    parser.add_argument("--rebuild", action="store_true", help="regenerate the cache before rendering")
    parser.add_argument("--no-figures", action="store_true",
                        help="skip the figure set under results/figures")
    args = parser.parse_args()

    if args.rebuild:
        rebuild()
    if not args.no_figures:
        renderer = ROOT / "scripts" / "render_culmination.py"
        if renderer.exists():
            result = subprocess.run([sys.executable, str(renderer)], cwd=str(ROOT),
                                    capture_output=True, text=True)
            if result.returncode == 0:
                written = [line for line in result.stdout.splitlines() if line.strip().startswith("results/")]
                print(f"figures written under results/figures/ ({len(written)} files, PNG and SVG, titles inside)")
            else:
                print("figure rendering failed; figures can be rebuilt with "
                      "python3 scripts/render_culmination.py")
    if SUMMARY.exists():
        print_metrics(json.loads(SUMMARY.read_text()))
    ledgers = cached_ledgers()
    if not ledgers:
        raise SystemExit(f"no ledgers under {LEDGERS}; run with --rebuild once to create them")

    wanted = list(ledgers) if args.all else [args.candidate]
    for name in wanted:
        if name not in ledgers:
            raise SystemExit(f"no cached ledger named {name}; available: {', '.join(ledgers)}")
        target = build(name, ledgers[name])
        print(f"\n{name}: {ledgers[name]} -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
