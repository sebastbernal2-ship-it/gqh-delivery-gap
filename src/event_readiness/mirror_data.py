"""Inspect/flatten a public mirror pilot; never equate it to complete venue tape."""
import argparse
from collections import Counter
from decimal import Decimal
import math
from pathlib import Path
import shutil

from .acquisition import atomic_json, records_file, sha, strict_json
from .pull_candidates import record


def batches(path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    parquet = pq.ParquetFile(path)
    for batch in parquet.iter_batches(batch_size=2048):
        columns = {}
        for i, name in enumerate(batch.schema.names):
            col = batch.column(i)
            if pa.types.is_timestamp(col.type):
                if col.type.unit != "ns":
                    raise ValueError("unexpected timestamp precision")
                col = col.cast(pa.int64())
            columns[name] = col.to_pylist()
        for i in range(batch.num_rows):
            yield {name: values[i] for name, values in columns.items()}


def normalize(source, output):
    if (output / "complete.json").exists():
        raise ValueError("completed output exists")
    manifest = strict_json((source / "complete.json").read_bytes())
    if sha((source / "records.jsonl").read_bytes()) != manifest["sha256"]:
        raise ValueError("source inventory changed")
    for folder in ("objects", "requests"):
        shutil.copytree(source / folder, output / folder, dirs_exist_ok=True)
    # Keep the exact requested file/revision/hash plan alongside normalized rows.
    shutil.copyfile(source / "plan.json", output / "plan.json")
    inventory = [strict_json(line) for line in (source / "records.jsonl").read_bytes().splitlines()]
    receipts = {r["sha256"]: r for r in (strict_json(p.read_bytes()) for p in (source / "requests").glob("*.json"))}
    quality = {"selection": "BTC/ETH books and account fills, plus every explicit liquidation marker in the fill partition",
               "files": [], "synchronized_backtest_ready": False}
    def rows():
        for item in inventory:
            path = source / "objects" / item["source_sha256"]
            if sha(path.read_bytes()) != item["source_sha256"]:
                raise ValueError("mirror object changed")
            receipt = receipts[item["source_sha256"]]
            counts, coins, times = Counter(), Counter(), []
            kind = item["context"]["kind"]
            first_time = last_time = None
            for number, row in enumerate(batches(path)):
                counts["source_rows"] += 1
                context = {**item["context"], "parquet_row": number, "timestamp_units": "nanoseconds for Arrow timestamp fields"}
                flags = ["third_party_mirror", "venue_equivalence_unverified", "incomplete_pilot_coverage"]
                if kind == "node_fills":
                    events = strict_json(row["events"])
                    if not isinstance(events, list):
                        raise ValueError("unknown fill event layout")
                    t = row["block_time"]
                    for index, event in enumerate(events):
                        if not isinstance(event, list) or len(event) != 2 or not isinstance(event[1], dict):
                            raise ValueError("unknown account fill layout")
                        account, fill = event
                        coin = fill["coin"]
                        coins[coin] += 1; counts["account_fills"] += 1
                        liquidation = fill.get("liquidation")
                        explicit = isinstance(liquidation, dict) and bool(liquidation)
                        if explicit:
                            counts["explicit_liquidation_markers"] += 1
                        if coin not in ("BTC", "ETH") and not explicit:
                            continue
                        for field in ("px", "sz"):
                            value = Decimal(str(fill[field]))
                            if not value.is_finite() or value <= 0:
                                raise ValueError("invalid fill price or size")
                        counts["selected_account_fills"] += 1
                        # Retain raw account identity. These are account-side fills: two sides
                        # of a trade can both appear. Never sum them as unique market volume.
                        yield record("hyperliquid_account_fill", {**context, "event_index": index}, receipt,
                                     {"account": account, "fill": fill, "block_number": row["block_number"],
                                      "block_time_ns": t, "local_time_ns": row["local_time"], "upstream_path": row["_src"]},
                                     explicit_liquidation_marker=explicit, quality_flags=flags)
                elif kind == "l2book":
                    t = row["timestamp"]; coins[row["coin"]] += 1
                    if row["coin"] in ("BTC", "ETH"):
                        invalid = [k for k,v in row.items() if isinstance(v,float) and not math.isfinite(v)]
                        for k in invalid:
                            row[k] = None
                        if invalid: flags.append("nonfinite_fields_replaced_with_null")
                        bid, ask = row.get("bid_px_1"), row.get("ask_px_1")
                        if bid is None or ask is None or bid <= 0 or ask <= 0:
                            flags.append("invalid_best_prices")
                        elif bid >= ask:
                            flags.append("locked_or_crossed_book")
                        counts["selected_book_rows"] += 1
                        yield record("hyperliquid_l2_snapshot", context, receipt, row,
                                     nonfinite_fields=invalid, quality_flags=flags)
                else:
                    raise ValueError("unknown mirror kind")
                if not isinstance(t, int) or t <= 0:
                    raise ValueError("invalid source timestamp")
                first_time = t if first_time is None else min(t,first_time)
                last_time = t if last_time is None else max(t,last_time)
            quality["files"].append({"kind": kind, "source_sha256": item["source_sha256"],
                "counts": dict(counts), "coin_counts": dict(coins), "first_timestamp_ns": first_time, "last_timestamp_ns": last_time})
            print(f"{kind}: {dict(counts)}", flush=True)
    result = records_file(output / "records.jsonl", rows())
    result.update(kind="hyperliquid_mirror_normalized_pilot", strategy_ready=False, quality=quality)
    atomic_json(output / "complete.json", result)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path); p.add_argument("output", type=Path)
    args = p.parse_args()
    normalize(args.source, args.output)
