"""Turn an EIA-860M workbook into normalized frames.

Sheet layout, verified on the January 2025 vintage: row 1 is a title, row 2 is blank,
row 3 is the header. Every sheet carries Plant ID and Generator ID, so a unit is
identified by the pair. Each sheet ends with free-text notes, so rows without a numeric
Plant ID are dropped.

EIA's own note on every sheet, kept because it belongs in the note's limitations:
capacity from facilities under 1 MW is excluded, the data is preliminary and not fully
verified, and there may be discrepancies between the status and the commercial operation
date.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

HEADER_ROW = 2
MONTH_NAMES = {name: i + 1 for i, name in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"])}
SHEETS = {
    "planned": "Planned",
    "operating": "Operating",
    "cancelled": "Canceled or Postponed",
}
COMMON = {
    "Plant ID": "plant_id",
    "Generator ID": "generator_id",
    "Nameplate Capacity (MW)": "mw",
    "Balancing Authority Code": "ba_code",
    "Plant State": "state",
    "Technology": "technology",
    "Energy Source Code": "energy_source",
    "Sector": "sector",
    "Entity Name": "entity",
    "Plant Name": "plant_name",
}
CACHE_DIR = Path("data/derived/vintages")


def _to_month(value):
    """EIA writes 1..12, sometimes a month name, sometimes blank."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, str):
        text = value.strip().lower()
        if not text:
            return None
        if text in MONTH_NAMES:
            return MONTH_NAMES[text]
        match = re.match(r"^(\d{1,2})", text)
        if not match:
            return None
        value = match.group(1)
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None
    return number if 1 <= number <= 12 else None


def _to_int(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def month_index_from(year, month):
    if year is None or month is None:
        return None
    return (year - 2000) * 12 + (month - 1)


def sheet_names(path: Path):
    return list(pd.ExcelFile(path).sheet_names)


def read_sheet(path: Path, sheet_key: str) -> pd.DataFrame:
    """Normalized frame for one sheet of one vintage: string ids, float MW."""
    raw = pd.read_excel(path, sheet_name=SHEETS[sheet_key], header=HEADER_ROW)
    raw = raw.dropna(how="all")

    # Drop the trailing notes block: those rows have no numeric Plant ID.
    plant = pd.to_numeric(raw.get("Plant ID"), errors="coerce")
    raw = raw[plant.notna()].copy()

    frame = pd.DataFrame(index=raw.index)
    for source, target in COMMON.items():
        if source in raw.columns:
            frame[target] = raw[source]
    for column in ("plant_id", "generator_id", "mw", "ba_code", "state", "technology",
                   "energy_source", "sector", "entity", "plant_name"):
        if column not in frame.columns:
            frame[column] = ""

    frame["plant_id"] = ["" if _to_int(v) is None else str(_to_int(v)) for v in frame["plant_id"]]
    frame["generator_id"] = [str(v).strip() for v in frame["generator_id"]]
    frame["mw"] = [_to_float(v) for v in frame["mw"]]
    for column in ("ba_code", "state", "technology", "energy_source", "sector",
                   "entity", "plant_name"):
        frame[column] = ["" if v is None else str(v).strip() for v in frame[column]]
    frame = frame[frame["plant_id"] != ""].reset_index(drop=True)

    if sheet_key == "planned":
        years = [_to_int(v) for v in raw.get("Planned Operation Year", pd.Series(dtype=object))]
        months = [_to_month(v) for v in raw.get("Planned Operation Month", pd.Series(dtype=object))]
        frame["planned_year"] = pd.Series(years, dtype="Int64")
        frame["planned_month"] = pd.Series(months, dtype="Int64")
        frame["month_index"] = pd.Series([month_index_from(y, m) for y, m in zip(years, months)],
                                         dtype="Int64")
    elif sheet_key == "operating":
        years = [_to_int(v) for v in raw.get("Operating Year", pd.Series(dtype=object))]
        months = [_to_month(v) for v in raw.get("Operating Month", pd.Series(dtype=object))]
        frame["operating_year"] = pd.Series(years, dtype="Int64")
        frame["operating_month"] = pd.Series(months, dtype="Int64")
        frame["operating_month_index"] = pd.Series(
            [month_index_from(y, m) for y, m in zip(years, months)], dtype="Int64")
    return frame


def read_vintage(path: Path, cache: bool = True, cache_dir=None):
    """All sheets this pipeline needs from one vintage, keyed by sheet role.

    Parsed frames are cached as parquet. Parsing the Operating sheet takes about 40
    seconds and the panel reads many vintages.
    """
    path = Path(path)
    available = sheet_names(path)
    target = Path(cache_dir) if cache_dir else CACHE_DIR
    out = {}
    for key, name in SHEETS.items():
        if name not in available:
            raise KeyError(f"{path.name}: expected sheet {name!r}, found {available}")
        cached = target / f"{path.stem}__{key}.parquet"
        if cache and cached.exists():
            out[key] = pd.read_parquet(cached)
            continue
        frame = read_sheet(path, key)
        if cache:
            cached.parent.mkdir(parents=True, exist_ok=True)
            frame.to_parquet(cached, index=False)
        out[key] = frame
    return out
