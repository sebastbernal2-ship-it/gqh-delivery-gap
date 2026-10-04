"""Offline validation for imagery labels, scenes, and probe rows."""
from __future__ import annotations

import datetime as dt
import math
from typing import Mapping


def _month(value: object, name: str) -> None:
    try:
        dt.datetime.strptime(str(value), "%Y-%m")
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM") from exc


def validate_label(row: Mapping[str, object]) -> Mapping[str, object]:
    for name in ("plant_id", "generator_id", "promised", "realized"):
        if not str(row.get(name, "")).strip():
            raise ValueError(f"missing {name}")
    _month(row["promised"], "promised")
    _month(row["realized"], "realized")
    try:
        lat, lon = float(row["latitude"]), float(row["longitude"])
        capacity = float(row["capacity_mw"])
        slip = int(row["slip_months"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("label coordinates, capacity, and slip must be numeric") from exc
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("label coordinates are out of range")
    if not math.isfinite(capacity) or capacity < 0:
        raise ValueError("label capacity must be nonnegative and finite")
    if slip != month_index(str(row["realized"])) - month_index(str(row["promised"])):
        raise ValueError("slip_months does not match promised and realized months")
    return row


def month_index(value: str) -> int:
    year, month = (int(part) for part in value.split("-"))
    return year * 12 + month


def validate_scene(item: Mapping[str, object]) -> Mapping[str, object]:
    bbox = item.get("bbox")
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        raise ValueError("scene bbox must have four coordinates")
    west, south, east, north = (float(value) for value in bbox)
    if not west < east or not south < north:
        raise ValueError("scene bbox is degenerate")
    cloud = float((item.get("properties") or {}).get("eo:cloud_cover", 101))
    if not math.isfinite(cloud) or not 0 <= cloud <= 100:
        raise ValueError("scene cloud cover is invalid")
    stamp = (item.get("properties") or {}).get("datetime")
    if not isinstance(stamp, str) or not stamp.strip():
        raise ValueError("scene datetime is missing")
    parsed = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("scene datetime must include a timezone")
    href = ((item.get("assets") or {}).get("visual") or {}).get("href", "")
    if not str(href).startswith("https://"):
        raise ValueError("scene visual asset must be HTTPS")
    return item


def validate_probe_row(row: Mapping[str, object]) -> Mapping[str, object]:
    for name in ("plant_id", "promise_scene", "realized_scene", "promise_brightness", "realized_brightness"):
        if not str(row.get(name, "")).strip():
            raise ValueError(f"probe row missing {name}")
    if row["promise_scene"] == row["realized_scene"]:
        raise ValueError("probe must use two distinct scenes")
    for name in ("promise_brightness", "realized_brightness", "brightness_did"):
        value = float(row[name])
        if not math.isfinite(value):
            raise ValueError(f"probe value {name} is not finite")
    return row
