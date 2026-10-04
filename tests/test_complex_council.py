#!/usr/bin/env python3
"""Contracts for the complex council: the declared peer map and additive block structure."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_complex_council import PEERS, with_peer_flags  # noqa: E402


def test_every_market_panel_group_maps_into_a_declared_peer_set():
    rows = [{"ticker": "A", "group_name": name} for name in
            ("data_center_reit", "compute_and_ai", "hyperscaler", "buildout", "power",
             "fuel_and_nuclear")]
    mapped = with_peer_flags(rows)
    assert all(sum(row[f"group_{peer}"] for peer in PEERS) == 1.0 for row in mapped)
    assert mapped[0]["group_datacenter"] == 1.0 and mapped[1]["group_equipment"] == 1.0
    assert mapped[2]["group_datacenter"] == 1.0 and mapped[3]["group_equipment"] == 1.0
    assert mapped[4]["group_utility"] == 1.0 and mapped[5]["group_utility"] == 1.0


def test_an_unknown_or_empty_group_gets_no_flag_and_no_row_is_dropped():
    rows = [{"ticker": "A", "group_name": "rates_and_credit"}, {"ticker": "B"}]
    mapped = with_peer_flags(rows)
    assert len(mapped) == 2
    assert all(mapped[0][f"group_{peer}"] == 0.0 for peer in PEERS)
    assert all(mapped[1][f"group_{peer}"] == 0.0 for peer in PEERS)


def test_flags_are_added_without_mutating_the_input_rows():
    rows = [{"ticker": "A", "group_name": "power"}]
    with_peer_flags(rows)
    assert "group_utility" not in rows[0]


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} complex council contract(s) held")
