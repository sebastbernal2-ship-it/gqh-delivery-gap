"""Small local adapters for typed strategy CSV packages."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Mapping

from strategy.ledger import validate_rows

SCHEMAS = {
    "events": {"event_id", "source", "source_receipt", "entity_key", "vintage", "observed_at",
               "available_at", "usable_at", "unit", "evidence_status", "expectation_kind",
               "prior_value", "current_value", "missingness_reason"},
    "primary_events": {"event_id", "source", "source_receipt", "entity_key", "vintage", "observed_at",
                    "available_at", "usable_at", "unit", "evidence_status", "expectation_kind",
                    "expectation_status", "prior_value", "current_value", "missingness_reason"},
    "exposures": {"event_id", "issuer", "security", "segment", "direction", "weight",
                  "status", "evidence", "source_receipt", "identity_vintage"},
    "physical": {"observation_id", "project_key", "status", "observed_at", "available_at",
                 "source", "evidence", "source_receipt", "capacity_mw"},
    "trades": {"security", "signal_at", "fill_at", "side", "quantity", "price", "cost_bps",
               "borrow_bps", "source_receipt"},
}


def read_typed_csv(path: Path, kind: str) -> list[dict[str, str]]:
    """Read one typed package, check its header, then validate every row."""
    if kind not in SCHEMAS:
        raise ValueError(f"unknown source kind: {kind}")
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or [])
        missing = sorted(SCHEMAS[kind] - headers)
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(missing)}")
        rows = list(reader)
    validate_rows(rows, kind)
    return rows


def schema(kind: str) -> set[str]:
    try:
        return set(SCHEMAS[kind])
    except KeyError as exc:
        raise ValueError(f"unknown source kind: {kind}") from exc
