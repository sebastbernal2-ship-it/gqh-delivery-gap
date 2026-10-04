#!/usr/bin/env python3
"""Contracts for the matched-universe test: only names with history before the cutoff qualify."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_matched_universe import matched_tickers  # noqa: E402


def panel_companies(count: int = 3) -> list[str]:
    """Real complex panel members, so the fixture tests the filter and not the panel contents."""
    panel = json.loads((ROOT / "results" / "market-panel.json").read_text())
    names = [series["ticker"] for group, payload in panel.get("groups", {}).items()
             for series in payload.get("series", [])
             if not series["ticker"].startswith("^") and "=" not in series["ticker"]]
    return sorted(set(names))[:count]


def test_only_names_with_history_before_the_cutoff_are_matched():
    early, late, empty = panel_companies(3)
    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp)
        (cache / f"{early}.json").write_text(json.dumps({"2013-01-02": 10.0, "2014-01-02": 11.0}))
        (cache / f"{late}.json").write_text(json.dumps({"2018-01-02": 10.0}))
        (cache / f"{empty}.json").write_text(json.dumps({}))
        names = matched_tickers(cache, cutoff="2017-01-01")
        assert early in names and late not in names and empty not in names


def test_names_outside_the_complex_panel_are_ignored():
    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp)
        (cache / "ZZZ_not_in_panel.json").write_text(json.dumps({"2010-01-02": 5.0}))
        assert "ZZZ_not_in_panel" not in matched_tickers(cache, cutoff="2017-01-01")


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} matched-universe contract(s) held")
