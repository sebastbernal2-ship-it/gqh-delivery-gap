#!/usr/bin/env python3
"""Contracts for filing text extraction, excerpting and selection."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.text import excerpt, html_to_text, text_sha256  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
from fetch_filing_texts import select_rows  # noqa: E402


def test_html_to_text_strips_scripts_and_collapses_space():
    html = ("<html><head><style>p{color:red}</style></head><body>"
            "<script>var x = 1;</script><p>Item&nbsp;1.01  Entry</p>"
            "<table><tr><td>A</td><td>B</td></tr></table></body></html>")
    text = html_to_text(html)
    assert "script" not in text and "color:red" not in text
    assert "Item 1.01 Entry" in text
    assert "A" in text and "B" in text
    assert "  " not in text


def test_excerpt_prefers_the_focus_heading_and_stays_bounded():
    text = "cover page " * 200 + "Item 2.02 Results of Operations " + "body " * 100
    window = excerpt(text, max_chars=600)
    assert "Item 2.02" in window
    assert len(window) <= 600
    assert window == excerpt(text, max_chars=600)


def test_excerpt_falls_back_to_the_head_and_rejects_tiny_bounds():
    text = "no declared items here " * 50
    window = excerpt(text, max_chars=400)
    assert window.startswith("no declared items")
    assert len(window) <= 400
    try:
        excerpt(text, max_chars=100)
    except ValueError:
        pass
    else:
        raise AssertionError("a tiny bound must be refused")


def test_text_hash_is_stable():
    assert text_sha256("abc") == text_sha256("abc")
    assert text_sha256("abc") != text_sha256("abd")


def test_selection_requires_a_ticker_a_form_and_a_url():
    rows = [
        {"ticker": "PWR", "form": "8-K", "document_url": "https://x/1"},
        {"ticker": "PWR", "form": "10-Q", "document_url": "https://x/2"},
        {"ticker": "ETN", "form": "8-K/A", "document_url": "https://x/3"},
        {"ticker": "EME", "form": "8-K", "document_url": "https://x/4"},
        {"ticker": "DLR", "form": "8-K", "document_url": ""},
    ]
    selected = select_rows(rows, {"PWR", "ETN"}, ("8-K",))
    assert [row["document_url"] for row in selected] == ["https://x/1", "https://x/3"]


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} filing text contract(s) held")
