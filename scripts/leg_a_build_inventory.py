#!/usr/bin/env python3
"""Build the node-to-table inventory from the declared node space and verified counts."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODES = ROOT / "docs/scan/nodes.jsonl"
OUTPUT = ROOT / "results/graph-inventory.csv"

# Counts are table totals verified on 2026-10-03. Dates name the table's observation field.
TABLES = {
    "eia": {
        "name": "VECTOR_RESEARCH.RAW.EIA860M_GENERATOR_VINTAGES",
        "rows": 3387221,
        "first": "2016-01",
        "last": "2026-08",
        "clock": "VINTAGE_MONTH; available_at is the point-in-time publication date",
    },
    "sec": {
        "name": "VECTOR_RESEARCH.RAW.SEC_FILING_DOCUMENTS",
        "rows": 12903,
        "first": "2016-01-21",
        "last": "2021-04-29",
        "clock": "FILED_DATE; use ACCEPTANCE_UTC or AVAILABLE_AT for point-in-time availability",
    },
    "records": {
        "name": "public.gqh_source_records",
        "rows": 153527,
        "first": "2015-02-03",
        "last": "2026-09-15",
        "clock": "heterogeneous EVENT_TIME_TEXT; ISO-date rows span this range, so dates are not exhaustive",
    },
    "audit": {
        "name": "public.gqh_source_records",
        "clock": "checked for a matching source series; no matching rows found",
    },
    "aws": {
        "name": "public.aws_gpu_spot_prices",
        "rows": 1592024,
        "first": "2022-05-31",
        "last": "2026-09-30",
        "clock": "PRICE_TIME",
    },
}

NO_BACKING = {
    "promise:power:interconnection-queue-position",
    "water:drought:severity",
    "price:compute:executed-rental",
    "price:power:spot",
    "positioning:perp:funding-rate",
    "price:options:implied-move",
    "flow:index:reconstitution",
    "flow:dealer:hedge-demand",
    "price:datacentre:lease-rate",
    "flow:project:financing-draw",
}


def table_for(node: dict) -> dict | None:
    node_id = node["id"]
    if node_id in NO_BACKING:
        return None
    source = node["representations"][0]["source"]
    if source == "source:eia-860m":
        return TABLES["eia"]
    if source == "source:sec":
        return TABLES["sec"]
    if source == "source:aws-spot":
        return TABLES["aws"]
    if source in {"source:eia-930", "source:fred", "source:market"}:
        return TABLES["records"]
    return None


def main() -> None:
    nodes = [json.loads(line) for line in NODES.read_text().splitlines() if line.strip()]
    rows = []
    for node in nodes:
        table = table_for(node)
        representations = node["representations"]
        kinds = "; ".join(rep["kind"] for rep in representations)
        availability = "; ".join(dict.fromkeys(rep["availability"] for rep in representations))
        status = node["status"]
        if table is None:
            status += "; no suitable backing data; audit table has no matching source series"
            table_name, count, first, last = TABLES["audit"]["name"], 0, "", ""
            availability += "; audit clock: " + TABLES["audit"]["clock"]
        else:
            table_name, count = table["name"], table["rows"]
            first, last = table["first"], table["last"]
            status += "; table total, not node-level usable-row count"
            availability += "; table clock: " + table["clock"]
        rows.append({
            "node": node["id"],
            "family": node["family"],
            "representation": kinds,
            "source_table": table_name,
            "rows": count,
            "first_observation": first,
            "last_observation": last,
            "availability": availability,
            "status": status,
        })

    if len(rows) != len(nodes) or len({row["node"] for row in rows}) != len(rows):
        raise SystemExit("node inventory is not one row per declared node")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "node", "family", "representation", "source_table", "rows",
            "first_observation", "last_observation", "availability", "status",
        ])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} node rows to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
