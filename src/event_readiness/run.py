"""Run source reconciliation or reviewed development features; outputs stay private by default."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from .archive import canonical_hash, digest_file, reconcile, SHA
from .collect import collect, reconcile_sources
from .features import build_features, publication_time, START, END


def read_json(path: Path):
    # Duplicate keys are input corruption, not last-writer-wins silently changing evidence.
    def unique(pairs):
        record = {}
        for key, value in pairs:
            if key in record:
                raise ValueError("duplicate JSON key")
            record[key] = value
        return record
    return json.loads(path.read_text(), object_pairs_hook=unique)


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents replacing a prior run receipt by accident.
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def expected_register(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return sorted({row["accession"] for row in csv.DictReader(stream)
                       if row["ticker"].upper() in {"PWR", "ETN", "EME", "DLR"}
                       and row["form"].upper().removesuffix("/A") in {"8-K", "10-Q", "10-K"}
                       and row["filed_date"] >= "2016-01-01"})


def fixture() -> tuple[list[dict], dict[str, bytes]]:
    """Fictional issuer, no real financial values, in the development date range."""
    facts, documents = [], {}
    for i, value in enumerate(("100.000000000001", "110.000000000002", "106.000000000003")):
        quote = f"SYNTHETIC: full-year demonstration guidance is {value} USD."
        content = quote.encode()
        digest = hashlib.sha256(content).hexdigest()
        documents[digest] = content
        facts.append({"fact_id": f"synthetic-{i}", "event_cluster_id": f"synthetic-shock-{i}",
            "issuer_cik": "0000000001", "ticker": "SYNTH", "security_id": "synthetic-common-1",
            "accession": f"0000000001-21-{i:06d}", "form": "8-K", "metric_name": "guidance",
            "fact_kind": "management_guidance", "unit": "USD", "currency": "USD",
            "scope": "synthetic segment", "definition_version": "synthetic-v1", "target_period": "FY2021",
            "comparability_group": "synthetic-fixed-perimeter", "value_text": value, "value_decimal": value,
            "source_document_url": f"https://example.invalid/synthetic-{i}", "document_sha256": digest,
            "source_span_start": 0, "source_span_end": len(content), "source_quote": quote,
            "input_batch_sha256": "a" * 64, "publication_basis": "verified_public_time",
            "published_at": f"2021-0{i+1}-05T21:05:00Z", "review_status": "reviewed",
            "reviewer_id": "synthetic-fixture-only", "reviewed_at": "2021-04-05T00:00:00Z",
            "exposure_status": "verified", "exposure_evidence_id": "synthetic-exposure",
            "extractor_version": "fixture-v1", "expectation_id": f"synthetic-{i-1}" if i else None})
    return facts, documents


def code_receipt() -> dict:
    root = Path(__file__).resolve().parents[2]
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True)
    return {"git_revision": revision.stdout.strip() if revision.returncode == 0 else "unavailable",
            "component_sha256": canonical_hash({p.name: digest_file(p) for p in sorted(Path(__file__).parent.glob("*.py"))}),
            "python_version": sys.version.split()[0]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    demo = sub.add_parser("demo")
    demo.add_argument("--out", type=Path, required=True)
    events = sub.add_parser("features")
    events.add_argument("--facts", type=Path, required=True)
    events.add_argument("--documents", type=Path, required=True)
    events.add_argument("--min-history", type=int, default=5)
    events.add_argument("--processing-seconds", type=int, default=60)
    events.add_argument("--out", type=Path, required=True)
    audit = sub.add_parser("reconcile")
    audit.add_argument("--snapshot", type=Path, required=True)
    audit.add_argument("--register", type=Path, required=True)
    audit.add_argument("--packages", type=Path)
    audit.add_argument("--out", type=Path, required=True)
    cloud = sub.add_parser("snapshot")
    cloud.add_argument("--connection-name", required=True)
    cloud.add_argument("--register", type=Path, required=True)
    cloud.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error("output exists; use a new run path")
    if args.mode == "snapshot":
        import snowflake.connector
        with snowflake.connector.connect(connection_name=args.connection_name) as connection:
            report = collect(connection, expected_register(args.register))
    elif args.mode == "reconcile":
        snapshot = read_json(args.snapshot)
        report = reconcile(snapshot, expected_register(args.register), args.packages)
        report["source_counts"] = reconcile_sources(snapshot)
    else:
        if args.mode == "demo":
            records, documents = fixture()
        else:
            package = read_json(args.facts)
            if set(package) != {"schema_version", "partition", "facts"} or package["schema_version"] != 1 or package["partition"] != "development":
                raise ValueError("explicit version-1 development fact package required")
            records = package["facts"]
            documents = {}
            for record in records:
                if not START <= publication_time(record["publication_basis"], record["published_at"]) < END:
                    continue
                digest = record.get("document_sha256", "")
                if not SHA.fullmatch(digest):
                    continue  # fact validation supplies the definitive error
                path = args.documents / digest
                if path.is_file():
                    documents[digest] = path.read_bytes()
        report = build_features(records, documents, min_history=getattr(args, "min_history", 5),
                                processing_seconds=getattr(args, "processing_seconds", 60))
        report["synthetic"] = args.mode == "demo"
        report["input_facts_sha256"] = canonical_hash(records)
    report["run"] = {**code_receipt(), "generated_at_utc": datetime.now(timezone.utc).isoformat()}
    write_json(args.out, report)
    print(json.dumps({"mode": args.mode, "artifact_sha256": digest_file(args.out),
                      "status": "artifact_created", "strategy_ready": False}, sort_keys=True))
    # A successful feature build is not a strategy gate; an unsuccessful reconciliation is a failure.
    if args.mode == "reconcile" and not report["archive_ready"]:
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Connector errors can expose account/connection details; no raw exception or traceback.
        print(f"event-readiness failed ({type(exc).__name__}); inspect inputs/connection privately", file=sys.stderr)
        raise SystemExit(1)
