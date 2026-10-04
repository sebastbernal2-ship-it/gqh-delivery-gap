"""Bounded, revision-pinned public Hyperliquid mirror acquisition. No AWS identity used.

Input plan: {files: [{dataset, revision, path, size, sha256, kind}]}. Use SHA-256
from the dataset host's LFS metadata, not the Git pointer or Xet identifier.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path, PurePosixPath
import re
import ssl
from urllib.parse import quote, urlparse
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from .acquisition import Retrieval, atomic_json, canonical, records_file, sha, strict_json
from .pull_candidates import record


def permitted_host(url):
    p = urlparse(url)
    host = p.hostname or ""
    return p.scheme == "https" and not p.username and not p.password and (
        host == "huggingface.co" or host.endswith(".huggingface.co") or host.endswith(".hf.co"))


class PublicMirrorRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not permitted_host(newurl):
            raise ValueError("mirror redirect leaves permitted HTTPS hosts")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(client, entry):
    import certifi
    dataset, revision, path = entry["dataset"], entry["revision"], entry["path"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", dataset) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("invalid pinned dataset identity")
    if PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts:
        raise ValueError("invalid dataset path")
    expected = entry["sha256"]
    if not re.fullmatch(r"[0-9a-f]{64}", expected) or not 0 < entry["size"] <= 500_000_000:
        raise ValueError("missing source hash or excessive file size")
    url = f"https://huggingface.co/datasets/{dataset}/resolve/{revision}/" + quote(path, safe="/")
    receipt_path = client.root / "requests" / (sha(url.encode()) + ".json")
    if receipt_path.exists():
        receipt = strict_json(receipt_path.read_bytes())
        obj = client.root / "objects" / expected
        if receipt["sha256"] != expected or receipt["url"] != url or obj.stat().st_size != entry["size"] or sha(obj.read_bytes()) != expected:
            raise ValueError("mirror cache mismatch")
        return obj, receipt
    opener = build_opener(PublicMirrorRedirect(), HTTPSHandler(context=ssl.create_default_context(cafile=certifi.where())))
    temporary = client.root / "objects" / (expected + ".partial")
    digest, size = hashlib.sha256(), 0
    with opener.open(Request(url, headers={"User-Agent": "GQH-research-mirror-acquisition"}), timeout=90) as response:
        if response.status != 200:
            raise ValueError("incomplete mirror response")
        with temporary.open("wb") as f:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > entry["size"]:
                    raise ValueError("download exceeds declared byte bound")
                digest.update(chunk); f.write(chunk)
    if size != entry["size"] or digest.hexdigest() != expected:
        raise ValueError("download disagrees with pinned publisher SHA-256 or size")
    destination = client.root / "objects" / expected
    temporary.replace(destination)
    receipt = {"url": url, "sha256": expected, "size_bytes": size, "http_status": 200,
               "retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "content_type": "application/octet-stream",
               "last_modified": None, "dataset_revision": revision, "third_party_mirror": True}
    # Signed CDN redirect URLs are never retained.
    atomic_json(receipt_path, receipt)
    return destination, receipt


def acquire(plan, output):
    import pyarrow.parquet as pq
    if sum(e["size"] for e in plan["files"]) > 750_000_000:
        raise ValueError("plan exceeds bounded pilot limit")
    if (output / "complete.json").exists():
        raise ValueError("completed output exists")
    client = Retrieval(output)
    stored_plan = output / "plan.json"
    if stored_plan.exists() and strict_json(stored_plan.read_bytes()) != plan:
        raise ValueError("changed mirror plan")
    atomic_json(stored_plan, plan)
    quality = []
    def inventory():
        for entry in plan["files"]:
            path, receipt = download(client, entry)
            parquet = pq.ParquetFile(path)
            metadata = {"rows": parquet.metadata.num_rows, "row_groups": parquet.metadata.num_row_groups,
                        "schema": str(parquet.schema_arrow), "compressed_bytes": entry["size"]}
            quality.append({**entry, **metadata})
            yield record("hyperliquid_mirror_parquet", {"dataset": entry["dataset"], "revision": entry["revision"],
                         "path": entry["path"], "kind": entry["kind"]}, receipt, metadata,
                         quality_flags=["third_party_mirror", "venue_byte_equivalence_unverified", "coverage_unverified"])
            print(canonical({"file": entry["path"], "bytes": entry["size"], "rows": metadata["rows"]}), flush=True)
    result = records_file(output / "records.jsonl", inventory())
    result.update(kind="public_hyperliquid_mirror_pilot", strategy_ready=False, quality=quality)
    atomic_json(output / "complete.json", result)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan", type=Path); p.add_argument("output", type=Path)
    args = p.parse_args()
    try:
        acquire(strict_json(args.plan.read_bytes()), args.output)
    except Exception as exc:
        print(canonical({"status": "incomplete", "error_type": type(exc).__name__}), flush=True)
        raise SystemExit(1)
