#!/usr/bin/env python3
"""Contracts for the filing text option sets: labels, leakage, missing documents."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.options import OPTIONS, build_context, write_examples  # noqa: E402

ROW = {
    "ticker": "PWR",
    "filing_form": "8-K",
    "filing_items": "1.01,2.02",
    "filing_accession": "0001-26-000001",
    "decision_time": "2024-11-01T14:00:00+00:00",
    "label_bin": 3,
    "label_surprise": 123456.0,
}


def test_five_options_one_per_bin():
    assert len(OPTIONS) == 5
    assert len(set(OPTIONS)) == 5
    assert all(option.strip().endswith(".") for option in OPTIONS)


def test_context_holds_the_header_the_excerpt_and_the_question_but_never_the_label():
    text = "cover page " * 120 + "Item 2.02 Results of Operations " + "detail " * 200
    context = build_context(ROW, text, max_chars=800)
    assert "PWR 8-K" in context and "items 1.01,2.02" in context
    assert "Item 2.02" in context
    assert "Question:" in context
    assert "123456" not in context
    assert len(context) <= 800 + 400


def test_write_examples_counts_missing_documents_instead_of_faking_them():
    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp) / "cache"
        cache.mkdir()
        (cache / f"{ROW['filing_accession']}.txt").write_text("Item 1.01 Entry into an agreement")
        output = Path(tmp) / "examples.jsonl"
        report = write_examples([ROW, {**ROW, "filing_accession": "missing"}], cache, output)
        assert report["examples"] == 1
        assert report["missing_texts"] == ["missing"]
        record = json.loads(output.read_text().splitlines()[0])
        assert record["label"] == 3
        assert record["options"] == list(OPTIONS)
        assert "123456" not in record["context"]


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} filing option contract(s) held")
