#!/usr/bin/env python3
"""Build a frozen live-role plan from dated capture/export pairs.

Protocol: hpc/probabilistic-council/LIVE_EXECUTION_RISK.md owns the plan format. This script only
fills it in and validates it: every captured receive date gets exactly one role, roles advance
chronologically, and both pins are real file hashes. Paths stay local and are never committed.

    python3 scripts/build_live_risk_plan.py \
      --pair /local/capture-1004:/local/objects-1004 \
      --pair /local/capture-1005:/local/objects-1005 \
      --roles training,specialist_calibration,gate_fit,pool_calibration,evaluation \
      --output /local/risk-plan.json
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROLES = ("training", "specialist_calibration", "gate_fit", "pool_calibration", "evaluation")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture_dates(journal: Path) -> list[str]:
    """Distinct UTC receive dates in a recorder journal, in first-appearance order."""
    dates: list[str] = []
    for line in journal.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            ns = json.loads(line).get("receipt_wall_ns")
        except ValueError:
            continue
        if not isinstance(ns, int):
            continue
        day = datetime.datetime.fromtimestamp(ns / 1e9, datetime.timezone.utc).date().isoformat()
        if day not in dates:
            dates.append(day)
    return dates


def assign_roles(dates: list[str], roles: tuple[str, ...]) -> dict[str, str]:
    if len(dates) != len(roles):
        raise ValueError(f"{len(dates)} capture date(s) but {len(roles)} role(s); "
                         "every captured date needs exactly one role")
    if sorted(dates) != dates:
        raise ValueError("dates must be given in chronological order")
    if len(set(roles)) != len(roles):
        raise ValueError("a role cannot be assigned twice")
    unknown = [role for role in roles if role not in ROLES]
    if unknown:
        raise ValueError(f"unknown role(s): {', '.join(unknown)}")
    return dict(zip(dates, roles))


def build_plan(pairs: list[tuple[Path, Path]], roles: tuple[str, ...]) -> dict:
    captures = []
    dates: list[str] = []
    for capture, objects in pairs:
        journal = capture / "messages.jsonl"
        receipt = capture / "capture.json"
        inventory = objects / "inventory.json"
        for path in (journal, receipt, inventory):
            if not path.exists():
                raise FileNotFoundError(f"missing {path}")
        for day in capture_dates(journal):
            if day not in dates:
                dates.append(day)
        captures.append({
            "capture": str(capture),
            "objects": str(objects),
            "capture_receipt_sha256": file_sha256(receipt),
            "inventory_sha256": file_sha256(inventory),
        })
    return {
        "schema_version": "execution-live-role-plan-v1",
        "scope": "development_only",
        "captures": captures,
        "session_roles": assign_roles(dates, roles),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", action="append", required=True,
                        help="capture_dir:objects_dir, repeated once per dated capture")
    parser.add_argument("--roles", default=",".join(ROLES),
                        help="comma-separated roles, one per captured date, in date order")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    pairs = []
    for pair in args.pair:
        capture, _, objects = pair.partition(":")
        if not capture or not objects:
            raise SystemExit(f"--pair needs capture_dir:objects_dir, got {pair!r}")
        pairs.append((Path(capture), Path(objects)))
    roles = tuple(item.strip() for item in args.roles.split(",") if item.strip())
    plan = build_plan(pairs, roles)
    args.output.write_text(json.dumps(plan, indent=2) + "\n")
    print(json.dumps({"captures": len(plan["captures"]),
                      "session_roles": plan["session_roles"],
                      "output": str(args.output)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
