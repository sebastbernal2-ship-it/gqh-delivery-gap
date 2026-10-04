#!/usr/bin/env python3
"""Offline checks for deterministic PDF renderer selection."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_pdf_renderer import select_renderer  # noqa: E402

assert select_renderer(lambda name: "/usr/bin/" + name if name == "chromium" else None, lambda _: None) == "chromium"
assert select_renderer(lambda _: None, lambda _: None) is None
print("pdf renderer: 2/2 passed")
