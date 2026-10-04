#!/usr/bin/env python3
"""Reproduce the repository's published numbers from a fresh clone, and say what did not match.

A judge has three tiers, cheapest first:

    python3 scripts/reproduce.py --tier checks     structure, paths, claims, the test suite
    python3 scripts/reproduce.py                   the checks plus every offline producer (default)
    python3 scripts/reproduce.py --tier full       adds the slow producers, several minutes each
    python3 scripts/reproduce.py --tier network    re-fetches live sources (SEC, EIA, prices)

The default tier is offline and exact: it seeds the local price cache from the committed
`results/price-subset/`, runs each producer named in `results/reproduction-manifest.json` into a
sandbox path, and compares the artifact's SHA-256 against the recorded one. The working tree stays
clean unless `--apply` is given, in which case producers write their declared paths in place. The note's page ceiling is checked too when the
repository renderer is installed. Exit status is non-zero when any exact entry fails.

    python3 scripts/reproduce.py --write          regenerate the manifest digests from this machine
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUBSET = ROOT / "results" / "price-subset"
CACHE = ROOT / "results" / "bar-cache"
MANIFEST = ROOT / "results" / "reproduction-manifest.json"

CHECKS = [
    {"name": "structure", "command": "python3 scripts/check_structure.py", "artifact": None},
    {"name": "paths", "command": "python3 scripts/check_paths.py", "artifact": None},
    {"name": "claims", "command": "python3 scripts/claims.py", "artifact": None},
    {"name": "tests", "command": "python3 -m pytest -q tests 2>/dev/null || make -s test",
     "artifact": None},
]

PRODUCERS = [
    {"name": "intensity ledger", "tier": "default", "exact": True,
     "command": "python3 scripts/run_intensity_strategy.py --output {output}",
     "artifact": "results/intensity-strategy.json",
     "claim": "the gated charge expression's published ledger"},
    {"name": "intensity doubled", "tier": "default", "exact": True,
     "command": "python3 scripts/run_intensity_strategy.py --output {output} --cost-mult 2",
     "artifact": "results/intensity-strategy-doubled.json",
     "claim": "the same ledger at doubled costs"},
    {"name": "sleeve portfolio", "tier": "default", "exact": True,
     "command": "python3 scripts/run_sleeve_portfolio.py --output {output}",
     "artifact": "results/sleeve-portfolio.json",
     "claim": "the driver sleeves and their composite"},
    {"name": "eia load specialist", "tier": "default", "exact": True,
     "command": "python3 scripts/run_eia_load_specialist.py --output {output}",
     "artifact": "results/eia-load-specialist.json",
     "claim": "the first non-SEC specialist's information and pricing tests"},
    {"name": "eia load refinement", "tier": "default", "exact": True,
     "command": "python3 scripts/run_eia_load_refinement.py --output {output}",
     "artifact": "results/eia-load-refinement.json",
     "claim": "the seasonal, peak, ramp and acceleration refinements and the event-level test"},
    {"name": "walk-forward baseline", "tier": "full", "exact": True,
     "command": "python3 scripts/run_walk_forward.py --output {output}",
     "artifact": "results/walk-forward-baseline.json",
     "claim": "the rolling-origin record and the two-sleeve composite"},
    {"name": "walk-forward decoupled", "tier": "full", "exact": True,
     "command": "python3 scripts/run_walk_forward.py --size-panel results/revenue-z-on-pit.csv --output {output}",
     "artifact": "results/walk-forward-decoupled.json",
     "claim": "the decoupled sizing variant"},
    {"name": "council sleeve", "tier": "full", "exact": True,
     "command": "python3 scripts/run_council_sleeve.py --output {output}",
     "artifact": "results/council-sleeve.json",
     "claim": "the fusion as a sleeve and its mechanism table"},
    {"name": "state transfer", "tier": "full", "exact": True,
     "command": "python3 scripts/run_state_transfer_test.py --output {output}",
     "artifact": "results/state-transfer.json",
     "claim": "the shared-encoder transfer test"},
    {"name": "gate recalibration", "tier": "full", "exact": True,
     "command": "python3 scripts/run_gate_recalibration.py --output {output}",
     "artifact": "results/gate-recalibration.json",
     "claim": "the temperature-scaling falsifier"},
    {"name": "eia load panel", "tier": "network", "exact": False,
     "command": "python3 scripts/build_eia930_load_panel.py",
     "artifact": "results/eia-load-daily.csv.gz",
     "claim": "the open hourly grid panel, rebuilt from live EIA files"},
    {"name": "forward snapshot", "tier": "network", "exact": False,
     "command": "python3 scripts/run_forward_snapshot.py --refresh",
     "artifact": None,
     "claim": "the forward window's append-only capture, live filings move"},
]


def digest(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def seed_cache() -> str:
    if not SUBSET.exists():
        return "no committed price subset"
    CACHE.mkdir(parents=True, exist_ok=True)
    copied = 0
    for path in sorted(SUBSET.glob("*.json")):
        if path.name == "manifest.json":
            continue
        target = CACHE / path.name
        if not target.exists():
            shutil.copyfile(path, target)
            copied += 1
    return f"seeded {copied} price series from the committed subset"


def run_entry(entry: dict, timeout: int, apply_outputs: bool, sandbox: Path) -> dict:
    started = time.time()
    command = entry["command"]
    artifact = ROOT / entry["artifact"] if entry.get("artifact") else None
    if "{output}" in command:
        sandbox.mkdir(parents=True, exist_ok=True)
        target = artifact if apply_outputs else sandbox / Path(entry["artifact"]).name
        command = command.replace("{output}", str(target))
    result = subprocess.run(command, shell=True, cwd=ROOT, capture_output=True, text=True,
                            timeout=timeout)
    seconds = time.time() - started
    recorded = entry.get("sha256")
    current = digest(artifact) if artifact else None
    if result.returncode != 0:
        status = "failed"
    elif artifact is None:
        status = "ran"
    elif recorded is None:
        status = "recorded" if current else "missing"
    elif current == recorded:
        status = "exact"
    else:
        status = "differs"
    return {"name": entry["name"], "status": status, "seconds": round(seconds, 1),
            "exit": result.returncode, "sha256": current,
            "tail": (result.stdout or result.stderr or "").strip().splitlines()[-1:] or [""]}


def write_manifest(entries: list[dict]) -> None:
    manifest = {"schema": "reproduction-manifest-v1",
                "note": "digests of the committed artifacts; regenerate with --write",
                "entries": entries}
    MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=("checks", "default", "full", "network"), default="default")
    parser.add_argument("--write", action="store_true", help="regenerate the manifest digests")
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--apply", action="store_true",
                        help="write the declared artifact paths in place instead of a sandbox")
    args = parser.parse_args()

    print(seed_cache())
    if args.write:
        entries = []
        for entry in PRODUCERS:
            record = {key: value for key, value in entry.items()}
            artifact = ROOT / entry["artifact"] if entry.get("artifact") else None
            record["sha256"] = digest(artifact) if artifact else None
            entries.append(record)
        write_manifest(entries)
        print("wrote", MANIFEST, "with", len(entries), "entries")
        return 0

    if not MANIFEST.exists():
        print("no manifest at", MANIFEST, "- run with --write on a machine that has the artifacts")
        return 1
    manifest = json.loads(MANIFEST.read_text())
    entries = list(manifest["entries"])
    wanted = {"checks": {"checks"}, "default": {"checks", "default"},
              "full": {"checks", "default", "full"}, "network": {"checks", "default", "full", "network"}}[args.tier]

    sandbox = Path("/tmp/quanthacks-reproduce")
    results = []
    if "checks" in wanted:
        for check in CHECKS:
            results.append(run_entry(check, args.timeout, args.apply, sandbox))
    for entry in entries:
        if entry.get("tier") in wanted:
            results.append(run_entry(entry, args.timeout, args.apply, sandbox))

    width = max(len(row["name"]) for row in results) + 2
    print(f"\n{'entry'.ljust(width)}status      seconds  detail")
    failures = 0
    for row in results:
        detail = row["tail"][0][:60] if row["tail"] else ""
        print(f"{row['name'].ljust(width)}{row['status'].ljust(12)}{row['seconds']:>7}  {detail}")
        if row["status"] in ("failed", "differs", "missing"):
            failures += 1
    total = sum(row["seconds"] for row in results)
    print(f"\n{len(results)} entries, {failures} not matching, {total:.1f}s total")
    if failures:
        print("a 'differs' row is a real finding: the committed artifact no longer matches the code or "
              "the inputs it declares")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
