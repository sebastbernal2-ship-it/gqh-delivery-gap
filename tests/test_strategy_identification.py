#!/usr/bin/env python3
"""Offline check for clustered event-study statistics."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_group_event_study import cluster_tstat  # noqa: E402

assert cluster_tstat({"a": [0.01, 0.02], "b": [0.03, 0.04], "c": [0.05, 0.06]}) is not None
assert cluster_tstat({"a": [0.01]}) is None
print("strategy identification: 2/2 passed")
