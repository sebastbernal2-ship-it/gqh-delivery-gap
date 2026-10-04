"""Evidence-backed ownership review for slipped generation entities.

The EIA entity is not an issuer. This module keeps candidate matches out of the
attribution until a verified crosswalk row carries a source receipt.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Iterable, Mapping
from urllib.parse import urlparse


_REVIEW_FIELDS = (
    "entity_name",
    "slipped_mw",
    "exposure_rows",
    "panel_statuses",
    "attribution_status",
    "ticker",
    "cik",
    "economic_channel",
    "evidence",
    "identity_vintage",
    "source_receipt",
    "reason",
)


def _name_key(value: object) -> str:
    text = str(value or "").casefold()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def _number(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def top_entities(rows: Iterable[Mapping[str, object]], limit: int = 20) -> list[dict]:
    """Aggregate slipped MW by exact normalized entity name.

    Candidate matcher status is retained as coverage context. It never changes
    the attribution status returned by :func:`build_review`.
    """
    if limit < 1:
        raise ValueError("limit must be positive")
    grouped: dict[str, dict] = {}
    for row in rows:
        name = str(row.get("entity_name") or "").strip()
        key = _name_key(name)
        if not key:
            continue
        bucket = grouped.setdefault(key, {
            "entity_name": name,
            "slipped_mw": 0.0,
            "exposure_rows": 0,
            "panel_statuses": set(),
        })
        bucket["slipped_mw"] += _number(row.get("slipped_mw", row.get("capacity_mw")))
        bucket["exposure_rows"] += 1
        status = str(row.get("status") or row.get("match_status") or "").strip()
        if status:
            bucket["panel_statuses"].add(status)

    ranked = sorted(grouped.values(), key=lambda item: (-item["slipped_mw"], item["entity_name"]))[:limit]
    return [{
        **item,
        "slipped_mw": round(item["slipped_mw"], 1),
        "panel_statuses": "|".join(sorted(item["panel_statuses"])),
    } for item in ranked]


def _verified_crosswalk(rows: Iterable[Mapping[str, object]]) -> dict[str, Mapping[str, object]]:
    verified = {}
    for row in rows:
        if str(row.get("status") or "").strip().casefold() != "verified":
            continue
        key = _name_key(row.get("entity_name"))
        if key:
            verified[key] = row
    return verified


def build_review(
    exposure_rows: Iterable[Mapping[str, object]],
    crosswalk_rows: Iterable[Mapping[str, object]],
    *,
    limit: int = 20,
) -> list[dict]:
    """Build a top-entity review without promoting proposed matches."""
    crosswalk = _verified_crosswalk(crosswalk_rows)
    review = []
    for entity in top_entities(exposure_rows, limit=limit):
        match = crosswalk.get(_name_key(entity["entity_name"]))
        if match is None:
            row = {
                **entity,
                "attribution_status": "unresolved",
                "ticker": "",
                "cik": "",
                "economic_channel": "",
                "evidence": "",
                "identity_vintage": "",
                "source_receipt": "",
                "reason": "no evidence-backed crosswalk row",
            }
        else:
            row = {
                **entity,
                "attribution_status": "verified",
                "ticker": str(match.get("ticker") or "").strip(),
                "cik": str(match.get("cik") or "").strip(),
                "economic_channel": str(match.get("economic_channel") or "").strip(),
                "evidence": str(match.get("evidence") or "").strip(),
                "identity_vintage": str(match.get("identity_vintage") or "").strip(),
                "source_receipt": str(match.get("source_receipt") or "").strip(),
                "reason": "evidence-backed crosswalk row",
            }
        validate_review_row(row)
        review.append(row)
    return review


def validate_review_row(row: Mapping[str, object]) -> None:
    """Reject a verified review row that cannot be audited."""
    status = str(row.get("attribution_status") or "").strip()
    if status not in {"verified", "unresolved"}:
        raise ValueError("attribution_status must be verified or unresolved")
    if not str(row.get("entity_name") or "").strip():
        raise ValueError("entity_name is required")
    if _number(row.get("slipped_mw")) < 0:
        raise ValueError("slipped_mw must be nonnegative")
    if status != "verified":
        return
    required = ("ticker", "cik", "economic_channel", "evidence", "identity_vintage", "source_receipt")
    missing = [name for name in required if not str(row.get(name) or "").strip()]
    if missing:
        raise ValueError("verified review row missing: " + ", ".join(missing))
    parsed = urlparse(str(row["source_receipt"]).strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source_receipt must be an HTTP(S) URL")


def review_fields() -> tuple[str, ...]:
    return _REVIEW_FIELDS
