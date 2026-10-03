"""Fetch EIA-860M monthly vintages and keep a manifest of exactly what was pulled.

The vintage is the unit of truth. A file is downloaded once, hashed, and never revised:
a point-in-time measure that quietly rewrites its own inputs is worthless.
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://www.eia.gov/electricity/data/eia860m"
MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]

# Older vintages live under archive/xls, the newest under xls. Both are tried.
URL_TEMPLATES = [
    BASE + "/archive/xls/{month}_generator{year}.xlsx",
    BASE + "/xls/{month}_generator{year}.xlsx",
]


def month_index(year: int, month: int) -> int:
    """Months since 2000-01, so date arithmetic is integer arithmetic."""
    return (int(year) - 2000) * 12 + (int(month) - 1)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_xlsx(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 10_000:
        return False
    with path.open("rb") as handle:
        return handle.read(2) == b"PK"


def vintage_path(data_dir: Path, year: int, month: int) -> Path:
    return Path(data_dir) / "raw" / "eia860m" / f"{MONTHS[month - 1]}_{year}.xlsx"


def fetch_vintage(year: int, month: int, data_dir: Path, manifest: dict, force: bool = False) -> Path:
    """Download one vintage if it is not already present and valid."""
    target = vintage_path(data_dir, year, month)
    target.parent.mkdir(parents=True, exist_ok=True)
    key = f"{year}-{month:02d}"

    if target.exists() and is_xlsx(target) and key in manifest and not force:
        return target

    last_error = None
    for template in URL_TEMPLATES:
        url = template.format(month=MONTHS[month - 1], year=year)
        try:
            with urllib.request.urlopen(url, timeout=180) as response:
                payload = response.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            last_error = f"{url}: {exc}"
            continue
        if payload[:2] != b"PK":
            last_error = f"{url}: response was not an xlsx workbook"
            continue
        target.write_bytes(payload)
        manifest[key] = {
            "url": url,
            "bytes": len(payload),
            "sha256": sha256(target),
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        return target

    raise RuntimeError(f"could not fetch EIA-860M {key}: {last_error}")


def fetch_vintages(targets, data_dir: Path, manifest_path: Path, force: bool = False) -> dict:
    """targets: list of (year, month). Returns the updated manifest."""
    data_dir = Path(data_dir)
    manifest_path = Path(manifest_path)
    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
    for year, month in targets:
        fetch_vintage(year, month, data_dir, manifest, force=force)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest
