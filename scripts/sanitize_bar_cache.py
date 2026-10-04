#!/usr/bin/env python3
"""Keep only ISO trading dates in the bar cache.

Some fetched series carry stray timestamps or malformed keys. The engines build their calendar from
the union of every key, so a handful of dirty strings inflate the date list and dilute every
annualised statistic. This rewrites each series in place, keeping date-shaped keys only, and reports
what it dropped. The cache is ignored by git, so no artifact changes.

    python3 scripts/sanitize_bar_cache.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "results" / "bar-cache"
PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def main() -> int:
    cleaned = emptied = 0
    dropped = 0
    for path in sorted(CACHE.glob("*.json")):
        try:
            series = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if not isinstance(series, dict):
            continue
        keep = {key: value for key, value in series.items() if PATTERN.match(str(key))}
        if len(keep) != len(series):
            dropped += len(series) - len(keep)
            if keep:
                path.write_text(json.dumps(keep))
                cleaned += 1
            else:
                path.write_text(json.dumps({}))
                emptied += 1
    print(json.dumps({"series_rewritten": cleaned, "series_emptied": emptied,
                      "keys_dropped": dropped}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
