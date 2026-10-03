"""Reconcile SEC metadata and retained bytes without fetching, writing or repairing a warehouse."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from zipfile import ZipFile, BadZipFile

STAGE = "VECTOR_RESEARCH.RAW.SEC_FILING_ARCHIVE"
SHA = re.compile(r"[0-9a-f]{64}\Z")
ACCESSION = re.compile(r"\d{10}-\d{2}-\d{6}\Z")


def digest_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical_hash(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                     allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def stage_key(path: str) -> str:
    """Normalize only known LIST output and fully-qualified archive references, never basename match."""
    path = path.lstrip("@")
    if path.startswith(STAGE + "/"):
        path = path[len(STAGE) + 1:]
    elif path.lower().startswith("sec_filing_archive/"):
        path = path.split("/", 1)[1]
    parts = PurePosixPath(path).parts
    if not parts or parts[0] == "/" or any(p in ("..", ".") for p in path.split("/")):
        raise ValueError("invalid archive object path")
    if not re.fullmatch(r"accession=\d{18}/(?:sha256=[0-9a-f]{64}/)?[A-Za-z0-9_.-]+\.zip", path):
        raise ValueError("unrecognized archive object path")
    return path


def verify_package(path: Path, manifest: dict, max_uncompressed: int = 2_000_000_000) -> list[str]:
    """Verify ZIP and individual document SHA256, length, membership; never extract files."""
    failures = []
    if path.stat().st_size != int(manifest["package_size_bytes"]):
        failures.append("package_size_mismatch")
    if digest_file(path) != manifest["package_sha256"]:
        failures.append("package_hash_mismatch")
    if failures:
        return failures
    try:
        with ZipFile(path) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                failures.append("duplicate_zip_member")
            if sum(info.file_size for info in infos) > max_uncompressed:
                return failures + ["package_uncompressed_limit"]
            expected = {"index.json"} | {"documents/" + d["name"] for d in manifest["documents"]}
            if set(names) != expected:
                failures.append("zip_membership_mismatch")
            for doc in manifest["documents"]:
                member = "documents/" + doc["name"]
                if member not in names:
                    continue
                h = hashlib.sha256()
                length = 0
                with archive.open(member) as stream:
                    while chunk := stream.read(1024 * 1024):
                        length += len(chunk)
                        h.update(chunk)
                if h.hexdigest() != doc["sha256"] or length != int(doc["size_bytes"]):
                    failures.append("document_bytes_mismatch:" + doc["name"])
    except (BadZipFile, RuntimeError, OSError, KeyError):
        failures.append("unreadable_package")
    return failures


def reconcile(snapshot: dict, expected_accessions: list[str], package_dir: Path | None = None) -> dict:
    """Full selected-accession metadata audit; readiness requires local package byte verification.

    Snapshot fields are normalized lowercase exports from the read-only collector. Multiple versions
    are retained and ALL must reconcile: newest timestamp is never an implicit version choice.
    """
    expected = set(expected_accessions)
    if not expected or not all(ACCESSION.fullmatch(a) for a in expected):
        raise ValueError("expected accession set must be nonempty and well formed")
    manifests = snapshot["manifests"]
    documents = snapshot["documents"]
    stage_objects = snapshot["stage_objects"]
    problems = []
    def issue(code, accession=None, package_sha256=None):
        problems.append({"code": code, "accession": accession, "package_sha256": package_sha256})

    indexed = defaultdict(list)
    paths = defaultdict(set)
    by_document = defaultdict(list)
    objects = defaultdict(list)
    for obj in stage_objects:
        objects[stage_key(obj["name"])].append(obj)
    for doc in documents:
        if doc["accession"] in expected:
            by_document[(doc["accession"], doc["package_sha256"])].append(doc)
    for source in manifests:
        if source["accession"] not in expected:
            continue
        m = dict(source)
        if "documents" not in m:
            m["documents"] = json.loads(m["documents_json"])
        accession, sha = m["accession"], m["package_sha256"]
        if not SHA.fullmatch(sha):
            raise ValueError("invalid package SHA256")
        key = stage_key(m["package_stage_path"])
        if not key.startswith("accession=" + accession.replace("-", "") + "/"):
            issue("path_accession_mismatch", accession, sha)
        indexed[(accession, sha)].append(m)
        paths[key].add(sha)
    for key, hashes in paths.items():
        if len(hashes) > 1:
            issue("mutable_stage_path_multiple_versions")
    results = []
    for (accession, sha), group in sorted(indexed.items()):
        failures = []
        if len(group) != 1:
            failures.append("duplicate_manifest_key")
        m = group[0]
        docs = m["documents"]
        names = [d["name"] for d in docs]
        if not docs or len(docs) != int(m["document_count"]):
            failures.append("manifest_document_count_mismatch")
        if len(names) != len(set(names)):
            failures.append("duplicate_manifest_document")
        for d in docs:
            if not d["name"] or "/" in d["name"] or "\\" in d["name"] or d["name"] in (".", ".."):
                raise ValueError("unsafe document name")
            if not SHA.fullmatch(d["sha256"]) or int(d["size_bytes"]) < 0:
                raise ValueError("invalid document hash or size")
        actual = by_document[(accession, sha)]
        if len(actual) != len(docs):
            failures.append("document_table_count_mismatch")
        expected_docs = Counter((d["name"], d["sha256"], int(d["size_bytes"])) for d in docs)
        actual_docs = Counter((d["document_name"], d["document_sha256"], int(d["document_size_bytes"])) for d in actual)
        if expected_docs != actual_docs:
            failures.append("document_table_content_mismatch")
        key = stage_key(m["package_stage_path"])
        if any(stage_key(d["package_stage_path"]) != key for d in actual):
            failures.append("document_table_stage_mismatch")
        objects_for_key = objects[key]
        if len(objects_for_key) != 1:
            failures.append("stage_missing_or_duplicate")
        # Snowflake LIST size/MD5 can describe encrypted stored bytes. Do not equate either to
        # source SHA256 or unencrypted ZIP size. The downloaded package is the verification.
        local = package_dir / (sha + ".zip") if package_dir else None
        byte_status = "not_checked"
        if local is not None and local.is_file():
            byte_failures = verify_package(local, m)
            failures.extend(byte_failures)
            byte_status = "verified" if not byte_failures else "failed"
        elif package_dir:
            failures.append("local_package_missing")
        for code in failures:
            issue(code, accession, sha)
        results.append({"accession": accession, "package_sha256": sha,
                        "document_count": len(docs), "byte_status": byte_status,
                        "metadata_ok": not failures, "failures": failures})
    for (accession, sha) in by_document.keys() - indexed.keys():
        issue("orphan_document_version", accession, sha)
    missing = sorted(expected - {key[0] for key in indexed})
    for accession in missing:
        issue("missing_accession", accession)
    verified = {r["accession"] for r in results if r["byte_status"] == "verified" and r["metadata_ok"]}
    return {"schema_version": 1, "snapshot_sha256": canonical_hash(snapshot),
            "expected_accessions_sha256": canonical_hash(sorted(expected)),
            "expected_accession_count": len(expected), "package_version_count": len(results),
            "byte_verified_accession_count": len(verified), "missing_accessions": missing,
            "problems": problems, "packages": results,
            "archive_ready": not problems and bool(results) and all(r["byte_status"] == "verified" for r in results),
            "retry_policy": "Missing accessions are candidates only; check the other operator before fetching. Existing unverified versions require investigation, not overwrite."}
