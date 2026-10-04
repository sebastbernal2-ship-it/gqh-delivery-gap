#!/usr/bin/env python3
"""Build a canonical engine fixture from local normalized capture files.

The Tiger export path needs a database. The VM needs none, so this tool reads
the normalized JSONL that `normalize_capture.py` and `normalize_trades.py`
write and produces the same canonical rows through the same converters, in
fixture order.

The rows match the Tiger export after provenance is stripped, except for the
last update id on snapshots the database recorded differently. Replay results
are identical either way, which the tests assert against the checked-in
ninety-minute fixture.

Fixture order is the contract that makes a multi-window capture replayable:
rows are bucketed by a five-minute wall-clock window of their receive time,
snapshots come first inside their bucket, then rows follow receive time.
Ordering by file order instead loses which updates a snapshot already contains.

Usage:
  build_fixture.py --kind depth --input normalized/ --output depth.jsonl --manifest depth.manifest.json
  build_fixture.py --kind trades --input trades/ --output trades.jsonl --manifest trades.manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent / "tiger"))

from export_fixture import manifest_for, row_to_canonical_depth, row_to_canonical_trade

BUCKET_SECONDS = 300
DEFAULT_VENUE = "binance-futures"
RECEIVED_PATTERN = re.compile(
    r"^(?P<date>\d{4}\.\d{2}\.\d{2})D(?P<time>\d{2}:\d{2}:\d{2})\.(?P<fraction>\d{1,9})$"
)


class FixtureError(Exception):
    """Raised for input that cannot become a fixture."""


def parse_received(text: str) -> tuple[int, int]:
    """Return (seconds, nanoseconds) for the normalizer's receive timestamp.

    The normalizer writes nine fractional digits, which strptime refuses, so the
    fraction is parsed by hand.
    """
    match = RECEIVED_PATTERN.match(str(text).strip())
    if match is None:
        raise FixtureError(f"invalid received_time: {text!r}")
    date = match.group("date").replace(".", "-")
    fraction = match.group("fraction").ljust(9, "0")
    from datetime import datetime, timezone

    moment = datetime.strptime(f"{date}T{match.group('time')}", "%Y-%m-%dT%H:%M:%S")
    moment = moment.replace(tzinfo=timezone.utc)
    return int(moment.timestamp()), int(fraction)


def row_kind(row: dict[str, object]) -> str:
    """Trade rows carry no kind field, only a trade id."""
    kind = row.get("kind")
    if kind:
        return str(kind)
    return "trade" if "trade_id" in row else ""


def bucket_of(received: str) -> int:
    seconds, _ = parse_received(received)
    return seconds // BUCKET_SECONDS


def to_iso(received: str) -> str:
    """Translate the normalizer's stamp into ISO-8601 for the shared converters."""
    seconds, nanoseconds = parse_received(received)
    from datetime import datetime, timezone

    moment = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S") + f".{nanoseconds:09d}+00:00"


def fixture_key(row: dict[str, object], index: int) -> tuple:
    """Order rows so a snapshot precedes the updates it contains."""
    seconds, nanoseconds = parse_received(str(row["received_time"]))
    snapshot_first = 0 if row_kind(row) == "snapshot" else 1
    return (
        seconds // BUCKET_SECONDS,
        snapshot_first,
        seconds,
        nanoseconds,
        str(row.get("source_path") or ""),
        index,
    )


def load_rows(paths: list[Path], wanted: set[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise FixtureError(f"{path}:{number}: {exc}") from exc
                if row_kind(row) not in wanted:
                    continue
                # Rows the normalizer did not apply are kept, exactly as the
                # Tiger export keeps them, and the shared converter marks them
                # with a quality reason.
                rows.append(row)
    return rows


def collect_inputs(values: list[str]) -> list[Path]:
    paths: list[Path] = []
    for value in values:
        path = Path(value)
        if path.is_dir():
            paths.extend(sorted(path.glob("*.jsonl")))
        elif path.is_file():
            paths.append(path)
        else:
            raise FixtureError(f"no such input: {value}")
    return paths


def convert(row: dict[str, object], kind: str, venue: str) -> dict[str, object]:
    if kind == "depth":
        shaped = dict(row)
        shaped["received_time"] = to_iso(str(row["received_time"]))
        return row_to_canonical_depth(shaped, venue)
    trade = dict(row)
    trade["received_time"] = to_iso(str(row["received_time"]))
    if "trade_time_ms" not in trade and "event_time_ms" in trade:
        trade["trade_time_ms"] = trade["event_time_ms"]
    return row_to_canonical_trade(trade, venue)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a canonical fixture from local captures")
    parser.add_argument("--kind", choices=["depth", "trades"], default="depth")
    parser.add_argument("--input", action="append", required=True, help="normalized file or directory")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--venue", default=DEFAULT_VENUE)
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--start", default=None, help="inclusive receive time, e.g. 2026-10-04T00:00:00Z")
    parser.add_argument("--end", default=None, help="exclusive receive time")
    args = parser.parse_args()

    wanted = {"snapshot", "update"} if args.kind == "depth" else {"trade"}
    paths = collect_inputs(args.input)
    if not paths:
        print("no normalized input files found", file=sys.stderr)
        return 1
    rows = load_rows(paths, wanted)
    if args.symbol:
        rows = [row for row in rows if str(row.get("symbol")).upper() == args.symbol.upper()]
    if args.start or args.end:
        def inside(row: dict[str, object]) -> bool:
            seconds, nanoseconds = parse_received(str(row["received_time"]))
            stamp = seconds * 1_000_000_000 + nanoseconds
            if args.start:
                from datetime import datetime, timezone
                start = datetime.fromisoformat(args.start.replace("Z", "+00:00")).astimezone(timezone.utc)
                if stamp < int(start.timestamp()) * 1_000_000_000:
                    return False
            if args.end:
                from datetime import datetime, timezone
                end = datetime.fromisoformat(args.end.replace("Z", "+00:00")).astimezone(timezone.utc)
                if stamp >= int(end.timestamp()) * 1_000_000_000:
                    return False
            return True
        rows = [row for row in rows if inside(row)]
    if not rows:
        print("no rows matched", file=sys.stderr)
        return 1

    ordered = sorted(range(len(rows)), key=lambda index: fixture_key(rows[index], index))
    events = [convert(rows[index], args.kind, args.venue) for index in ordered]
    lines = [json.dumps(event, separators=(",", ":")) for event in events]
    document = "\n".join(lines) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(document, encoding="utf-8")
    digest = hashlib.sha256(document.encode("utf-8")).hexdigest()
    if args.manifest is not None:
        meta = SimpleNamespace(
            kind=args.kind, venue=args.venue, symbol=args.symbol, start=args.start, end=args.end
        )
        manifest = manifest_for(str(args.output), events, meta, digest)
        manifest["source"] = "local-normalized"
        manifest["source_paths"] = sorted({str(row.get("source_path")) for row in rows})
        args.manifest.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(f"rows={len(events)} sha256={digest} output={args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FixtureError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
