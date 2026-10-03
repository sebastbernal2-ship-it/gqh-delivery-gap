#!/usr/bin/env python3
"""Turn reviewed EIA site labels into point-in-time physical observations."""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

FIELDS = ["observation_id", "project_key", "status", "observed_at", "available_at", "source",
          "evidence", "source_receipt", "capacity_mw", "plant_id", "entity_name"]
RECEIPT = "https://www.eia.gov/electricity/data/eia860m/"


def stamp(month: str) -> str:
    year, number = (int(part) for part in month.split("-"))
    import calendar
    return f"{year:04d}-{number:02d}-{calendar.monthrange(year, number)[1]:02d}T23:59:59+00:00"


def build_observations(rows: list[dict]) -> list[dict]:
    observations = []
    for row in rows:
        project = f"eia-plant:{row['plant_id']}:{row['generator_id']}"
        for label, status in (("promise_vintage", "planned"), ("realized_vintage", "operating")):
            vintage = row.get(label, "")
            if not vintage:
                continue
            observations.append({
                "observation_id": f"{project}:{status}",
                "project_key": project,
                "status": status,
                "observed_at": stamp(vintage),
                "available_at": stamp(vintage),
                "source": "eia:860m",
                "evidence": f"results/site-labels.csv:{row['plant_id']}:{row['generator_id']}",
                "source_receipt": RECEIPT,
                "capacity_mw": row.get("capacity_mw", ""),
                "plant_id": row.get("plant_id", ""),
                "entity_name": row.get("entity_name", ""),
            })
    return observations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="results/site-labels.csv")
    parser.add_argument("--out", default="results/physical-observation-ledger.csv")
    args = parser.parse_args(argv)
    with (ROOT / args.input).open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    observations = build_observations(rows)
    out = ROOT / args.out
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(observations)
    print(f"wrote {args.out} ({len(observations)} observations)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
