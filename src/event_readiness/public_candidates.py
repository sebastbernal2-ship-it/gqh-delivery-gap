"""Retrieve public queue vintages and Ornn benchmarks with original bytes retained."""
import argparse
from datetime import datetime, timezone
import math
from pathlib import Path
from urllib.parse import quote

from .acquisition import Retrieval, atomic_json, records_file, strict_json
from .pull_candidates import record
from .queue_data import queue_records, summarize

QUEUES = {
    2020: "queues_2020_clean_data.xlsx",
    2021: "queues_2021_clean_data.xlsx",
    2022: "queues_2022_clean_data_0.xlsx",
    2023: "queues_2023_clean_data_r1.xlsx",
    2024: "2025-08/lbnl_ix_queue_data_file_thru2024_v2.xlsx",
    2025: "2026-05/lbnl_ix_queue_data_file_thru2025.xlsx",
}
ERCOT_LIST = "https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=15933"


def queues(client, quality):
    for year, name in QUEUES.items():
        _, receipt = client.fetch("https://eta-publications.lbl.gov/sites/default/files/" + name,
                                  max_bytes=25_000_000)
        rows = list(queue_records(client.root / "objects" / receipt["sha256"], year, receipt))
        quality[str(year)] = summarize(rows)
        print(f"queue {year}: {len(rows)} rows", flush=True)
        yield from rows


def ornn(client, quality):
    for gpu in ("H100 SXM", "H200", "B200", "A100 SXM4"):
        data, receipt = client.fetch("https://api.ornnai.com/api/gpu/" + quote(gpu, safe="") + "/index-history")
        page = strict_json(data)
        if page.get("success") is not True or page.get("gpu_type") != gpu or page.get("access") != "public-3mo":
            raise ValueError("unexpected Ornn response")
        seen = set()
        for row in page["data"]:
            stamp, value = row["timestamp"], row["index_value"]
            datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if stamp in seen or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError("invalid or repeated Ornn observation")
            seen.add(stamp)
            yield record("ornn_public_daily_index", {"gpu_type": gpu, "access": page["access"], "units": "USD/GPU-hour"},
                         receipt, row, usage="transaction_derived_benchmark_not_individual_executions",
                         quality_flags=["publication_clock_unverified", "no_underlying_transaction_volume"])
        if not seen:
            raise ValueError("empty Ornn series")
        quality[gpu] = {"rows": len(seen), "start": min(seen), "end": max(seen)}


def ercot(client, quality):
    data, listing = client.fetch(ERCOT_LIST)
    docs = [d["Document"] for d in strict_json(data)["ListDocsByRptTypeRes"]["DocumentList"]]
    selected = [d for d in docs if d["FriendlyName"].lower().startswith("gis") and d["Extension"] == "xlsx"]
    if not selected or sum(int(d["ContentSize"]) for d in selected) > 100_000_000:
        raise ValueError("empty or oversized ERCOT listing; review plan")
    seen = set()
    for i, doc in enumerate(selected, 1):
        identity = doc["DocID"]
        if not identity.isdigit() or identity in seen or doc["SecurityStatus"] != "P":
            raise ValueError("invalid ERCOT document identity or access")
        seen.add(identity)
        datetime.fromisoformat(doc["PublishDate"])
        data, receipt = client.fetch("https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId=" + identity,
                                      max_bytes=5_000_000)
        if len(data) != int(doc["ContentSize"]) or not data.startswith(b"PK"):
            raise ValueError("ERCOT workbook size or signature mismatch")
        yield record("ercot_gis_workbook", {"doc_id": identity, "listing_sha256": listing["sha256"]}, receipt, doc,
                     reported_posted_at_utc=datetime.fromisoformat(doc["PublishDate"]).astimezone(timezone.utc).isoformat(),
                     quality_flags=["original_publication_unverified", "may_be_republication", "project_rows_not_normalized"])
        if i % 10 == 0:
            print(f"ERCOT {i}/{len(selected)} workbooks", flush=True)
    quality.update(workbooks=len(selected), declared_bytes=sum(int(d["ContentSize"]) for d in selected),
                   earliest_reported_posting=min(d["PublishDate"] for d in selected),
                   latest_reported_posting=max(d["PublishDate"] for d in selected))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("kind", choices=["queues", "ornn", "ercot"])
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if (args.out / "complete.json").exists():
        raise ValueError("completed run exists; select a new output directory")
    client = Retrieval(args.out)
    quality = {}
    result = records_file(args.out / "records.jsonl", globals()[args.kind](client, quality))
    result.update(kind=args.kind, strategy_ready=False, quality=quality,
                  completed_at_utc=datetime.now(timezone.utc).isoformat())
    atomic_json(args.out / "complete.json", result)
    print(f"{args.kind}: {result['rows']} records complete", flush=True)


if __name__ == "__main__":
    main()
