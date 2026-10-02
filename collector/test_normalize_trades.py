#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path

from normalize_trades import validate_and_normalize


def line(trade_id=42, received="2024-01-01T00:00:00.100Z"):
    data = {
        "e": "aggTrade",
        "E": 1704067200100,
        "s": "BTCUSDT",
        "a": trade_id,
        "p": "100.10",
        "q": "0.5",
        "T": 1704067200099,
        "m": True,
    }
    envelope = {"stream": "btcusdt@aggTrade", "data": data}
    return f"{received} {json.dumps(envelope)}\n"


def test_futures_trade_event():
    data = {
        "e": "trade",
        "E": 1704067200100,
        "s": "BTCUSDT",
        "t": 42,
        "p": "100.10",
        "q": "0.5",
        "T": 1704067200099,
        "m": True,
    }
    capture = Path(tempfile.mkdtemp()) / "trades.jsonl"
    capture.write_text(
        "2024-01-01T00:00:00.100Z "
        + json.dumps({"stream": "btcusdt@trade", "data": data})
        + "\n"
    )
    rows = validate_and_normalize(capture)
    assert rows[0]["trade_id"] == 42


def main():
    with tempfile.TemporaryDirectory() as directory:
        capture = Path(directory) / "trades.jsonl"
        capture.write_text(line() + line(43, "2024-01-01T00:00:00.200Z"))
        rows = validate_and_normalize(capture)
        assert len(rows) == 2
        assert rows[0]["trade_id"] == 42
        assert rows[0]["buyer_is_maker"] is True

        capture.write_text(line(43) + line(42, "2024-01-01T00:00:00.200Z"))
        try:
            validate_and_normalize(capture)
        except ValueError as error:
            assert "not monotonic" in str(error)
        else:
            raise AssertionError("expected trade ID rejection")


if __name__ == "__main__":
    test_futures_trade_event()
    main()
    print("trade normalization checks passed")
