#!/usr/bin/env python3
"""Contracts for the live-role plan builder: hashes, whole dates, chronological roles."""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_live_risk_plan import (ROLES, assign_roles, build_plan,  # noqa: E402
                                  capture_dates, file_sha256)


def stamp(day: str, hour: int = 12) -> int:
    year, month, date = (int(part) for part in day.split("-"))
    return int(datetime.datetime(year, month, date, hour, tzinfo=datetime.timezone.utc)
               .timestamp() * 1e9)


def make_capture(root: Path, days: list[str]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    lines = []
    for sequence, day in enumerate(days):
        lines.append(json.dumps({"sequence": sequence, "segment": 1, "receipt_wall_ns": stamp(day),
                                 "receipt_monotonic_ns": 1, "coin": "BTC",
                                 "payload": {"channel": "l2Book"}}))
    (root / "messages.jsonl").write_text("\n".join(lines) + "\n")
    (root / "capture.json").write_text('{"schema": "capture"}\n')


def make_objects(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "inventory.json").write_text('{"schema": "inventory"}\n')


def test_dates_are_distinct_and_ordered_by_first_appearance():
    with tempfile.TemporaryDirectory() as tmp:
        capture = Path(tmp) / "capture"
        make_capture(capture, ["2026-10-04", "2026-10-04", "2026-10-05"])
        assert capture_dates(capture / "messages.jsonl") == ["2026-10-04", "2026-10-05"]


def test_roles_must_match_dates_and_advance():
    assert assign_roles(["2026-10-04", "2026-10-05"], ("training", "gate_fit")) == {
        "2026-10-04": "training", "2026-10-05": "gate_fit"}
    for dates, roles in ((["2026-10-04", "2026-10-05"], ("training",)),
                         (["2026-10-05", "2026-10-04"], ("training", "gate_fit")),
                         (["2026-10-04"], ("training", "training")), (["2026-10-04"], ("nonsense",))):
        try:
            assign_roles(dates, roles)
        except ValueError:
            continue
        raise AssertionError(f"accepted {dates} with {roles}")


def test_plan_pins_hashes_and_assigns_every_captured_date():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        first = (root / "capture-1004", root / "objects-1004")
        second = (root / "capture-1005", root / "objects-1005")
        make_capture(first[0], ["2026-10-04"])
        make_capture(second[0], ["2026-10-05"])
        make_objects(first[1])
        make_objects(second[1])
        plan = build_plan([first, second], ("training", "specialist_calibration"))
        assert plan["schema_version"] == "execution-live-role-plan-v1"
        assert plan["scope"] == "development_only"
        assert plan["session_roles"] == {"2026-10-04": "training",
                                        "2026-10-05": "specialist_calibration"}
        assert plan["captures"][0]["capture_receipt_sha256"] == file_sha256(first[0] / "capture.json")
        assert plan["captures"][1]["inventory_sha256"] == file_sha256(second[1] / "inventory.json")


def test_missing_files_are_refused():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        capture = root / "capture"
        make_capture(capture, ["2026-10-04"])
        try:
            build_plan([(capture, root / "objects")], ("training",))
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("a missing inventory must be refused")


def test_all_five_roles_are_declared():
    assert ROLES == ("training", "specialist_calibration", "gate_fit", "pool_calibration",
                     "evaluation")


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} live-role plan contract(s) held")
