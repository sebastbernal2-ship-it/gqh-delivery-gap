#!/usr/bin/env python3
import gzip
import json
import tempfile
from pathlib import Path

from certify_replay import certify
from normalize_capture import validate_and_normalize


def capture_line(received, data):
    return f"{received} " + json.dumps({"stream": "btcusdt@depth@100ms", "data": data}) + "\n"


def test_certifies_matching_boundaries():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        capture = root / "capture.jsonl.gz"
        with gzip.open(capture, "wt", encoding="utf-8") as handle:
            handle.write(capture_line("2026-01-01T00:00:00Z", {
                "e": "depthUpdate", "E": 1767225600000, "s": "BTCUSDT",
                "U": 10, "u": 10, "pu": 9, "b": [["100.00", "1.0"]], "a": [["101.00", "2.0"]],
            }))
            handle.write(capture_line("2026-01-01T00:00:01Z", {
                "lastUpdateId": 10, "E": 1767225601000, "bids": [["100.00", "1.0"]],
                "asks": [["101.00", "2.0"]],
            }))
            handle.write(capture_line("2026-01-01T00:00:02Z", {
                "e": "depthUpdate", "E": 1767225602000, "s": "BTCUSDT",
                "U": 11, "u": 11, "pu": 10, "b": [["100.00", "0.5"]], "a": [],
            }))
        rows = validate_and_normalize(capture)
        assert [row["received_time"] for row in rows] == sorted(
            row["received_time"] for row in rows
        )
        normalized = root / "normalized.jsonl"
        normalized.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows))
        kdb = root / "kdb.jsonl"
        kdb_rows = [json.loads(line) for line in normalized.read_text().splitlines()]
        kdb_rows[0]["received_time"] = "2026-01-01T00:00:00.000000000"
        kdb.write_text(
            "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in kdb_rows)
            + "-1\n"
        )
        ocaml = root / "ocaml-report.json"
        ocaml.write_text(json.dumps({"rows": 3, "states": 2, "symbol": "BTCUSDT"}))

        report = certify(capture, normalized, kdb, ocaml)
        assert report["raw_rows"] == 3
        assert report["normalized_rows"] == 3
        assert report["kdb_rows"] == 3
        assert report["ocaml_rows"] == 3

        broken = root / "broken.jsonl"
        broken.write_text(normalized.read_text().replace("BTCUSDT", "ETHUSDT", 1))
        try:
            certify(capture, normalized, broken, None)
        except ValueError as error:
            assert "does not match normalized" in str(error)
        else:
            raise AssertionError("expected certification failure")


if __name__ == "__main__":
    test_certifies_matching_boundaries()
    print("replay certification checks passed")
