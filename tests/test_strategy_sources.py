#!/usr/bin/env python3
"""Offline checks for typed source adapters."""
from pathlib import Path
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from strategy.sources import read_typed_csv  # noqa: E402

row = "event_id,source,source_receipt,entity_key,vintage,observed_at,available_at,usable_at,unit,evidence_status,expectation_kind,prior_value,current_value,missingness_reason\ne1,s,receipt,e,v,2024-01-01T00:00:00+00:00,2024-01-01T00:00:00+00:00,2024-01-01T00:00:01+00:00,MW,downloaded,public_plan,1,2,\n"
with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "events.csv"
    path.write_text(row)
    assert len(read_typed_csv(path, "events")) == 1
    path.write_text("event_id\ne1\n")
    try:
        read_typed_csv(path, "events")
    except ValueError as exc:
        assert "missing columns" in str(exc)
    else:
        raise AssertionError("missing schema was accepted")
print("strategy sources: 2/2 passed")
