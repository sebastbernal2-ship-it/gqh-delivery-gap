#!/usr/bin/env python3
"""Audit the compute-vs-capex study at the unique-quarter unit of observation.

This diagnostic does not replace or overwrite the original declared study. It
prevents a shared quarterly compute shock from being counted once per issuer and
uses only complete calendar quarters in the irregular compute archive.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src" / "central_ingest"))
from research_artifacts import publish_artifacts  # noqa: E402
import sync  # noqa: E402

PRICE_PATH = ROOT / "results/compute-price-monthly.csv"
CAPEX_PATH = ROOT / "results/provider-capex-quarterly.csv"
OUT_CSV = ROOT / "results/compute-lead-dependence-audit.csv"
OUT_JSON = ROOT / "results/compute-lead-dependence-audit.json"
GROUPS = {
    "all": ["MSFT", "AMZN", "GOOGL", "META", "ORCL", "CRWV", "IREN", "HUT", "CORZ", "APLD", "EQIX", "DLR"],
    "hyperscalers": ["MSFT", "AMZN", "GOOGL", "META", "ORCL"],
    "hosts": ["CRWV", "IREN", "HUT", "CORZ", "APLD"],
    "reits": ["EQIX", "DLR"],
}
COMPUTE_MONTHLY_BATCH = "044a082fe24c9afd3410a974f7fa471ce3b5dc12a6f4cf2a651b6accc9d331bb"
PROVIDER_CAPEX_BATCH = "48534d7bf98d785d2e1f738eaa867882dca57056e634b9deaa453e7844e0ee6e"


def snowflake_connection():
    import snowflake.connector

    name = os.getenv("SNOWFLAKE_CONNECTION_NAME")
    if name:
        return snowflake.connector.connect(connection_name=name)
    options = {
        "account": os.environ["SNOWFLAKE_ACCOUNT"],
        "user": os.environ["SNOWFLAKE_USER"],
        "warehouse": os.environ["SNOWFLAKE_WAREHOUSE"],
        "database": "VECTOR_RESEARCH",
        "schema": "RAW",
    }
    if os.getenv("SNOWFLAKE_ROLE"):
        options["role"] = os.environ["SNOWFLAKE_ROLE"]
    if os.getenv("SNOWFLAKE_PRIVATE_KEY_FILE"):
        options["private_key_file"] = os.environ["SNOWFLAKE_PRIVATE_KEY_FILE"]
    else:
        options["password"] = os.environ["SNOWFLAKE_PASSWORD"]
    return snowflake.connector.connect(**options)


def read_batch(connection, source_id: str, batch_sha: str) -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute("""SELECT PAYLOAD_JSON FROM VECTOR_RESEARCH.RAW.SOURCE_RECORDS
            WHERE SOURCE_ID=%s AND BATCH_SHA256=%s ORDER BY ROW_INDEX""", (source_id, batch_sha))
        return [json.loads(row[0]) for row in cursor.fetchall()]


def quarter(month: str) -> str:
    year, m = month.split("-")
    return f"{year}Q{(int(m) - 1) // 3 + 1}"


def adjacent(previous: str, current: str) -> bool:
    py, pq = int(previous[:4]), int(previous[-1])
    cy, cq = int(current[:4]), int(current[-1])
    return (cy * 4 + cq) - (py * 4 + pq) == 1


def next_quarter(value: str) -> str:
    year, q = int(value[:4]), int(value[-1])
    return f"{year + (q == 4)}Q{q % 4 + 1}"


def rank(values: list[float]) -> list[float]:
    ordered = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and values[ordered[j + 1]] == values[ordered[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[ordered[k]] = avg
        i = j + 1
    return ranks


def spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 4:
        return None
    rx, ry = rank(xs), rank(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    numerator = sum((x - mx) * (y - my) for x, y in zip(rx, ry))
    denom = math.sqrt(sum((x - mx) ** 2 for x in rx) * sum((y - my) ** 2 for y in ry))
    return numerator / denom if denom else None


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(price_rows: list[dict] | None = None, capex_input_rows: list[dict] | None = None,
          source_hashes: dict[str, str] | None = None) -> tuple[list[dict], dict]:
    # A quarterly price exists only when all three monthly observations are present.
    family_months: dict[str, dict[str, float]] = defaultdict(dict)
    all_months: set[str] = set()
    if price_rows is None:
        price_rows = list(csv.DictReader(PRICE_PATH.open(newline="", encoding="utf-8")))
    if capex_input_rows is None:
        capex_input_rows = list(csv.DictReader(CAPEX_PATH.open(newline="", encoding="utf-8")))
    for row in price_rows:
        try:
            month, family = row["month"], row["family"]
            value = float(row["median_usd_per_instance_hour"])
        except (KeyError, ValueError):
            continue
        family_months[family][month] = value
        all_months.add(month)

    quarter_family: dict[str, dict[str, float]] = defaultdict(dict)
    months_by_quarter: dict[str, set[str]] = defaultdict(set)
    for month in all_months:
        months_by_quarter[quarter(month)].add(month[-2:])
    complete_quarters = {q for q, months in months_by_quarter.items() if months == {"01", "02", "03"} or
                         months == {"04", "05", "06"} or months == {"07", "08", "09"} or
                         months == {"10", "11", "12"}}
    for family, values in family_months.items():
        by_quarter: dict[str, list[float]] = defaultdict(list)
        for month, value in values.items():
            q = quarter(month)
            if q in complete_quarters:
                by_quarter[q].append(value)
        for q, observations in by_quarter.items():
            # Completeness is checked per family too, not merely somewhere in the aggregate panel.
            year, qn = int(q[:4]), int(q[-1])
            required_months = {f"{year}-{m:02d}" for m in range((qn - 1) * 3 + 1, qn * 3 + 1)}
            if required_months.issubset(values):
                quarter_family[family][q] = statistics.median(
                    values[month] for month in sorted(required_months)
                )

    family_changes: dict[str, dict[str, float]] = defaultdict(dict)
    for family, values in quarter_family.items():
        qs = sorted(values)
        for previous, current in zip(qs, qs[1:]):
            if adjacent(previous, current) and values[previous] > 0 and values[current] > 0:
                family_changes[current][family] = math.log(values[current] / values[previous])
    compute_change = {q: statistics.median(list(changes.values()))
                      for q, changes in family_changes.items() if changes}

    # Choose the latest source period in each issuer/calendar quarter, then require
    # adjacent quarters before computing the logged change.
    capex_rows: dict[str, dict[str, tuple[str, float]]] = defaultdict(dict)
    for row in capex_input_rows:
        try:
            q = quarter(row["period_end"][:7])
            value = float(row["value_usd"])
        except (KeyError, ValueError):
            continue
        ticker, end, filed = row["ticker"], row["period_end"], row.get("filed", "")
        prior = capex_rows[ticker].get(q)
        if prior is None or (end, filed) > prior[0]:
            capex_rows[ticker][q] = ((end, filed), value)
    capex_growth: dict[str, dict[str, float]] = defaultdict(dict)
    for ticker, values in capex_rows.items():
        qs = sorted(values)
        for previous, current in zip(qs, qs[1:]):
            pvalue, cvalue = values[previous][1], values[current][1]
            if adjacent(previous, current) and pvalue > 0 and cvalue > 0:
                capex_growth[ticker][current] = math.log(cvalue / pvalue)

    rows: list[dict] = []
    summary: dict[str, dict] = {}
    for group, tickers in GROUPS.items():
        paired = []
        for compute_q, x in sorted(compute_change.items()):
            outcome_q = next_quarter(compute_q)
            issuer_growth = [capex_growth[t][outcome_q] for t in tickers
                             if t in capex_growth and outcome_q in capex_growth[t]]
            if issuer_growth:
                y = statistics.median(issuer_growth)
                paired.append((compute_q, outcome_q, x, y, len(issuer_growth)))
                rows.append({"group": group, "compute_quarter": compute_q,
                             "capex_outcome_quarter": outcome_q,
                             "compute_median_log_change": x,
                             "median_issuer_capex_log_change": y,
                             "issuers_in_outcome_median": len(issuer_growth),
                             "families_in_compute_median": len(family_changes[compute_q])})
        rho = spearman([p[2] for p in paired], [p[3] for p in paired])
        summary[group] = {
            "unique_quarter_pairs": len(paired),
            "spearman_rho_descriptive_only": rho,
            "p_value": None,
            "period_pairs": [{"compute_quarter": p[0], "outcome_quarter": p[1],
                              "issuers": p[4]} for p in paired],
        }

    report = {
        "status": "development diagnostic; not a strategy signal, trading test, or independent OOS result",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "AWS Spot Price History v2026-09 plus SEC Company Facts capex panel, both read from pinned Snowflake source batches",
        "inputs": {
            "compute_monthly_batch_sha256": (source_hashes or {}).get("compute_monthly", file_hash(PRICE_PATH)),
            "sec_provider_capex_batch_sha256": (source_hashes or {}).get("provider_capex", file_hash(CAPEX_PATH)),
            "monthly_compute_span": [min(all_months), max(all_months)] if all_months else [],
            "complete_compute_quarters": sorted(complete_quarters),
            "families": len(family_months),
            "provider_capex_tickers": sorted(capex_rows),
        },
        "unit_of_observation": "one aggregate compute shock per calendar quarter paired with a within-group median next-quarter capex change; issuers are aggregated, not replicated as independent compute shocks",
        "method": [
            "quarter family price is median of the three monthly family medians; incomplete calendar quarters are excluded",
            "quarter-over-quarter changes require consecutive complete quarters and use natural log changes",
            "next-quarter capex changes require consecutive issuer/calendar quarters and use natural log changes",
            "group outcomes are medians across issuers with observed next-quarter capex; report counts, not inferential p-values",
        ],
        "limitations": [
            "AWS Spot price is per whole instance-hour, not a GPU-hour, executed rental price, capacity/availability measure, or all-provider compute index",
            "March-June 2026 is absent; no interpolation is performed, and adjacent-quarter comparisons across the gap are excluded",
            "AWS historical source event times are not verified as contemporaneously observed availability times; this is retrospective descriptive analysis",
            "few unique quarterly pairs and autocorrelated series preclude a meaningful p-value here",
            "quarterly issuer capex is a financial statement outcome, not an issuer-specific measure of AWS usage or GPU consumption",
            "the prior 42-row test reused the same compute quarter shock across issuers; its row count and p-values should not be read as 42 independent compute events",
        ],
        "groups": summary,
        "output_csv_sha256": None,
    }
    return rows, report


def main() -> int:
    sync.load_local_env()
    connection = snowflake_connection()
    try:
        price_rows = read_batch(connection, "aws_compute_monthly_family", COMPUTE_MONTHLY_BATCH)
        capex_rows = read_batch(connection, "sec_provider_capex_quarterly", PROVIDER_CAPEX_BATCH)
    finally:
        connection.close()
    if len(price_rows) != 566 or len(capex_rows) != 192:
        raise ValueError("pinned compute/capex batches are missing or have unexpected row counts")
    rows, report = build(
        price_rows, capex_rows,
        {"compute_monthly": COMPUTE_MONTHLY_BATCH, "provider_capex": PROVIDER_CAPEX_BATCH},
    )
    with OUT_CSV.open("w", newline="", encoding="utf-8") as stream:
        fields = list(rows[0]) if rows else ["group", "compute_quarter", "capex_outcome_quarter"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    report["output_csv_sha256"] = file_hash(OUT_CSV)
    report["warehouse_artifact_table"] = "VECTOR_RESEARCH.RAW.RESEARCH_ARTIFACTS"
    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    uploaded = publish_artifacts(
        [OUT_CSV, OUT_JSON],
        generated_at=report["generated_at_utc"],
        input_lineage={
            "compute_monthly_batch_sha256": report["inputs"]["compute_monthly_batch_sha256"],
            "sec_provider_capex_batch_sha256": report["inputs"]["sec_provider_capex_batch_sha256"],
            "raw_aws_dataset": "VECTOR_RESEARCH.RAW.AWS_GPU_SPOT_PRICES",
        },
    )
    for name, result in report["groups"].items():
        print(f"{name}: quarter_pairs={result['unique_quarter_pairs']} descriptive_rho={result['spearman_rho_descriptive_only']}")
    print(f"wrote {OUT_CSV.relative_to(ROOT)} and {OUT_JSON.relative_to(ROOT)}")
    print(f"stored {len(uploaded)} exact artifacts in Snowflake VECTOR_RESEARCH.RAW.RESEARCH_ARTIFACTS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
