#!/usr/bin/env python3
"""Offline check for reproducibility manifest hashing."""
from pathlib import Path
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_run_manifest import digest  # noqa: E402
with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "input.txt"
    path.write_text("alpha")
    first = digest(path)
    path.write_text("beta")
    assert first != digest(path)
print("run manifest: 1/1 passed")
