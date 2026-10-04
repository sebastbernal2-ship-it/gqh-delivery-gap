#!/usr/bin/env python3
"""Certify raw, normalized, KDB-X, and OCaml replay row boundaries."""

import argparse
import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def _canonical_row(row):
    row = dict(row)
    value = row.get("received_time")
    if isinstance(value, str):
        if len(value) >= 11 and value[4] == "." and value[7] == "." and value[10] == "D":
            value = f"{value[:4]}-{value[5:7]}-{value[8:10]}T{value[11:]}"
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        row["received_time"] = parsed.astimezone(timezone.utc).isoformat()
    return row


def _json_rows(path: Path, allow_q_noise: bool = False):
    rows = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            text = line.strip()
            if not text:
                continue
            if allow_q_noise and not text.startswith("{"):
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{number}: invalid JSON") from error
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{number}: row is not an object")
            rows.append(_canonical_row(row))
    return rows


def _raw_row_count(path: Path):
    count = 0
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if line.strip():
                count += 1
    return count


def _compare_kdb(expected, path: Path | None):
    if path is None:
        return None
    actual = _json_rows(path, allow_q_noise=True)
    if actual != expected:
        raise ValueError("KDB-X export does not match normalized rows")
    return len(actual)


def _compare_ocaml(expected_count: int, path: Path | None):
    if path is None:
        return None
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("invalid OCaml certification report") from error
    if report.get("rows") != expected_count or not isinstance(report.get("states"), int) or report["states"] <= 0:
        raise ValueError("OCaml certification report does not match normalized rows")
    return report


def certify(capture: Path, normalized: Path, kdb_export: Path | None = None, ocaml_report: Path | None = None):
    raw_sha256 = hashlib.sha256(capture.read_bytes()).hexdigest()
    normalized_rows = _json_rows(normalized)
    if _raw_row_count(capture) != len(normalized_rows):
        raise ValueError("normalized row count does not match raw capture")
    for number, row in enumerate(normalized_rows, 1):
        if row.get("source_sha256") != raw_sha256:
            raise ValueError(f"normalized row {number} has the wrong source hash")

    report = {
        "capture": str(capture),
        "raw_sha256": raw_sha256,
        "raw_rows": _raw_row_count(capture),
        "normalized": str(normalized),
        "normalized_sha256": hashlib.sha256(normalized.read_bytes()).hexdigest(),
        "normalized_rows": len(normalized_rows),
    }
    report["kdb_rows"] = _compare_kdb(normalized_rows, kdb_export)
    ocaml = _compare_ocaml(len(normalized_rows), ocaml_report)
    report["ocaml_rows"] = None if ocaml is None else ocaml["rows"]
    report["ocaml_states"] = None if ocaml is None else ocaml["states"]
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("normalized", type=Path)
    parser.add_argument("--kdb-export", type=Path)
    parser.add_argument("--ocaml-report", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(certify(args.capture, args.normalized, args.kdb_export, args.ocaml_report), sort_keys=True))
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
