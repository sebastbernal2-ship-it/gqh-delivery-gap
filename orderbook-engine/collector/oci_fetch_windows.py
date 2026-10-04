#!/usr/bin/env python3
"""Copy capture windows from the OCI VM with verified provenance.

The VM collector writes five-minute windows plus a manifest line per file that
carries its SHA-256. This tool copies the windows in a label range, verifies
every local copy against the remote manifest, and writes a slice manifest that
the Tiger ingest and fixture export can cite.

usage: oci_fetch_windows.py START_LABEL END_LABEL DESTINATION
       oci_fetch_windows.py --latest N DESTINATION

Labels look like 20261004T0015. The range is inclusive and compared as text.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

# Window labels look like 20261004T0015 in every file name, for both the depth
# and the trades prefix, so they are extracted by pattern rather than by field
# position.
LABEL_PATTERN = re.compile(r"(\d{8}T\d{4})")

DEFAULT_HOST = "ubuntu@132.145.171.74"
DEFAULT_KEY = "~/.ssh/oci-binance-capture.key"
DEFAULT_REMOTE_DIR = "/home/ubuntu/collector/data"


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    completed = subprocess.run(command, text=True, capture_output=True, check=False, **kwargs)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return completed


def remote_files(host: str, key: str, remote_dir: str, start, end, latest):
    listing = run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            "-o",
            "IdentitiesOnly=yes",
            "-i",
            key,
            host,
            f"ls {remote_dir}/btcusdt-*.jsonl.gz {remote_dir}/manifest.jsonl",
        ]
    ).stdout.splitlines()
    windows = []
    for path in listing:
        name = path.rsplit("/", 1)[-1]
        if name == "manifest.jsonl":
            continue
        match = LABEL_PATTERN.search(name)
        if match is None:
            continue
        label = match.group(1)
        if latest is not None:
            windows.append((label, path))
        elif start <= label <= end:
            windows.append((label, path))
    windows.sort()
    if latest is not None:
        windows = windows[-latest:]
    return windows


def manifest_records(host: str, key: str, remote_dir: str, label: str):
    contents = run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            "-o",
            "IdentitiesOnly=yes",
            "-i",
            key,
            host,
            f"grep -h '{label}' {remote_dir}/manifest.jsonl || true",
        ]
    ).stdout
    records = []
    for line in contents.splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def has_snapshot(path: Path) -> bool:
    """A depth window is replayable only when it carries a REST snapshot.

    The collector writes the snapshot as the first record of each window after
    the periodic-refresh fix, and the normalizer rejects a window without one.
    """
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if "lastUpdateId" in line:
                return True
    return False


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("start", nargs="?")
    parser.add_argument("end", nargs="?")
    parser.add_argument(
        "--latest",
        type=int,
        help="Fetch the newest N windows instead of a label range",
    )
    parser.add_argument("destination", type=Path)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--key", default=DEFAULT_KEY)
    parser.add_argument("--remote-dir", default=DEFAULT_REMOTE_DIR)
    args = parser.parse_args()
    key = str(Path(args.key).expanduser())
    args.destination.mkdir(parents=True, exist_ok=True)
    try:
        if args.latest is None and (args.start is None or args.end is None):
            raise RuntimeError("give a label range or --latest N")
        windows = remote_files(
            args.host,
            key,
            args.remote_dir,
            args.start or "",
            args.end or "",
            args.latest,
        )
        if not windows:
            raise RuntimeError("no capture windows matched")
        slice_manifest = []
        skipped = []
        for label, remote_path in windows:
            records = manifest_records(args.host, key, args.remote_dir, label)
            if not records:
                skipped.append({"label": label, "reason": "open window without a manifest record"})
                print(f"skipped {label}: open window without a manifest record")
                continue
            # Two collectors can cover the same label while a fix rolls out.
            # Keep only the newest capture per label and kind, so a slice never
            # mixes two streams of the same window.
            newest = {}
            for record in records:
                key_pair = (label, record.get("kind", "depth"))
                started = record.get("started") or ""
                if key_pair not in newest or started > (newest[key_pair].get("started") or ""):
                    newest[key_pair] = record
            records = list(newest.values())
            for record in records:
                name = record["path"].rsplit("/", 1)[-1]
                # A label appears once per kind in the listing, so the same
                # record set can be visited twice; take each file once.
                if any(entry["name"] == name for entry in slice_manifest):
                    continue
                target = args.destination / name
                if not target.exists():
                    run(
                        [
                            "scp",
                            "-q",
                            "-o",
                            "BatchMode=yes",
                            "-o",
                            "ConnectTimeout=10",
                            "-o",
                            "IdentitiesOnly=yes",
                            "-i",
                            key,
                            # Manifest paths are container paths; the host copy
                            # lives in the data directory under the same name.
                            f"{args.host}:{args.remote_dir}/{name}",
                            str(target),
                        ]
                    )
                digest = sha256_of(target)
                if digest != record["sha256"]:
                    raise RuntimeError(f"{name}: hash mismatch against the remote manifest")
                if record.get("kind", "depth") == "depth" and not has_snapshot(target):
                    skipped.append({"label": label, "name": name, "reason": "no snapshot record"})
                    print(f"skipped {name}: no snapshot record")
                    target.unlink()
                    continue
                slice_manifest.append(
                    {
                        "label": label,
                        "kind": record.get("kind", "depth"),
                        "name": name,
                        "sha256": digest,
                        "bytes": record.get("bytes"),
                        "records": record.get("records"),
                        "started": record.get("started"),
                        "ended": record.get("ended"),
                    }
                )
                print(f"verified {name} bytes={record.get('bytes')}")
        if not slice_manifest:
            raise RuntimeError("no replayable windows in that label range")
        manifest_path = args.destination / "slice-manifest.jsonl"
        manifest_path.write_text(
            "".join(json.dumps(entry, sort_keys=True) + "\n" for entry in slice_manifest),
            encoding="utf-8",
        )
        if skipped:
            (args.destination / "slice-skipped.jsonl").write_text(
                "".join(json.dumps(entry, sort_keys=True) + "\n" for entry in skipped),
                encoding="utf-8",
            )
        print(
            f"windows={len(slice_manifest)} skipped={len(skipped)} manifest={manifest_path}"
        )
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        print(f"slice fetch failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
