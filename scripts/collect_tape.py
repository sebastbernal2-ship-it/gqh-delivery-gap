#!/usr/bin/env python3
"""Collect the tape for the pre-registered cascade protocol.

Reads only the venue's public endpoints. Appends one JSON object per sample to a dated file under `data/`,
which is ignored by git, so the tape stays local and the protocol stays reviewable. Nothing is inferred while
collecting: the trigger rule is applied afterwards, from the recorded rows, so a change of mind about the rule
cannot be mistaken for a property of the data.

Usage:
    python scripts/collect_tape.py --minutes 10
    python scripts/collect_tape.py --minutes 240 --interval 15
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402

from live.hyperliquid import MARKETS, book_row, context_rows, now_iso, safe  # noqa: E402

TAPE_DIR = ROOT / "data" / "tape"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=float, default=10)
    parser.add_argument("--interval", type=float, default=15.0, help="seconds between samples")
    parser.add_argument("--markets", default=",".join(MARKETS))
    args = parser.parse_args(argv)

    markets = [m.strip().upper() for m in args.markets.split(",") if m.strip()]
    TAPE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = TAPE_DIR / f"tape-{stamp}.jsonl"

    session = requests.Session()
    session.headers.update({"User-Agent": "gqh-delivery-gap research research@example.com"})

    deadline = time.time() + args.minutes * 60
    samples = failures = 0
    with path.open("a") as handle:
        while time.time() < deadline:
            started = time.time()
            rows = []
            # A dropped connection, a slow response or a malformed body must cost one sample, not the run.
            contexts = {row["coin"]: row for row in (safe(context_rows, session) or [])}
            for coin in markets:
                book = safe(book_row, session, coin)
                if book is None:
                    failures += 1
                    continue
                rows.append({"record": "book", "observed": now_iso(), **book,
                             **{k: v for k, v in contexts.get(coin, {}).items() if k != "coin"}})
            if rows:
                samples += 1
                for row in rows:
                    handle.write(json.dumps(row) + "\n")
                handle.flush()
                if samples % 4 == 0:
                    mid = {row["coin"]: row["mid"] for row in rows}
                    print(f"  sample {samples}: " + " ".join(f"{c} {v:,.4f}" for c, v in mid.items()))
            time.sleep(max(0.0, args.interval - (time.time() - started)))

    print(f"wrote {path.relative_to(ROOT)}: {samples} samples, {failures} failed reads")
    print("The trigger rule is applied afterwards, from these rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
