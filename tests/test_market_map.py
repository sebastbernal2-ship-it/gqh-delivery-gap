#!/usr/bin/env python3
"""Check the market map validator: it must accept the real map and reject each kind of missing link."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_market_map as checker  # noqa: E402

REAL = ROOT / "docs" / "market" / "map.jsonl"


def rows() -> list[dict]:
    return [json.loads(line) for line in REAL.read_text().splitlines() if line.strip()]


def with_rows(records: list[dict]) -> int:
    """Run the validator against a temporary map, returning its exit code."""
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    for record in records:
        handle.write(json.dumps(record) + "\n")
    handle.close()
    checker.MAP = Path(handle.name)
    return checker.main()


def test_real_map_is_clean() -> None:
    checker.MAP = REAL
    assert checker.main() == 0, "the committed market map must validate"


def test_unknown_participant_fails() -> None:
    records = rows()
    for record in records:
        if record["type"] == "flow":
            record["participant"] = "participant:does-not-exist"
            break
    assert with_rows(records) == 1


def test_unknown_instrument_fails() -> None:
    records = rows()
    for record in records:
        if record["type"] == "flow":
            record["instrument"] = "instrument:does-not-exist"
            break
    assert with_rows(records) == 1


def test_instrument_without_node_or_reason_fails() -> None:
    records = rows()
    for record in records:
        if record["type"] == "instrument":
            record.pop("node", None)
            record.pop("no_node_reason", None)
            break
    assert with_rows(records) == 1


def test_instrument_pointing_at_an_undeclared_node_fails() -> None:
    records = rows()
    for record in records:
        if record["type"] == "instrument":
            record["node"] = "price:nothing:here"
            break
    assert with_rows(records) == 1


def test_mapping_to_an_unknown_flow_fails() -> None:
    records = rows()
    for record in records:
        if record["type"] == "mapping":
            record["flow"] = "flow:does-not-exist"
            break
    assert with_rows(records) == 1


def test_record_without_a_falsifier_fails() -> None:
    records = rows()
    for record in records:
        if record["type"] == "participant":
            record["falsifier"] = ""
            break
    assert with_rows(records) == 1


def test_duplicate_id_fails() -> None:
    records = rows()
    records.append(dict(records[0]))
    assert with_rows(records) == 1


def test_flow_with_no_mapping_fails() -> None:
    records = [r for r in rows() if not (r["type"] == "mapping" and r["flow"] == "flow:queue-position")]
    assert with_rows(records) == 1


def test_unknown_constraint_fails() -> None:
    records = rows()
    for record in records:
        if record["type"] == "participant":
            record["constraint"] = "vibes"
            break
    assert with_rows(records) == 1


def test_unknown_relation_fails() -> None:
    records = rows()
    for record in records:
        if record["type"] == "mapping":
            record["relation"] = "drives"
            break
    assert with_rows(records) == 1


def main() -> int:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"  ok   {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"  FAIL {test.__name__}: {exc}")
    print(f"market map: {len(tests) - failures}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
