#!/usr/bin/env python3
"""Hash inputs and record the code revision for a reproducible strategy run."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUTS = [
    "docs/entity-crosswalk.csv", "results/capacity-event-ledger.csv",
    "results/issuer-exposure-ledger.csv", "results/market-control-panel.csv",
    "results/tradeability-panel.csv", "results/physical-observation-ledger.csv",
]


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def build_manifest(paths: list[Path], command: list[str]) -> dict:
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    return {"code_revision": revision, "command": command,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "inputs": [{"path": str(path.relative_to(ROOT)), "sha256": digest(path),
                        "bytes": path.stat().st_size} for path in paths]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", dest="inputs")
    parser.add_argument("--out", default="results/run-manifest.json")
    args = parser.parse_args(argv)
    names = args.inputs or DEFAULT_INPUTS
    paths = [ROOT / name for name in names]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise SystemExit("missing inputs: " + ", ".join(missing))
    manifest = build_manifest(paths, ["python3", "scripts/build_run_manifest.py", *names])
    out = ROOT / args.out
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {args.out} ({len(paths)} inputs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
