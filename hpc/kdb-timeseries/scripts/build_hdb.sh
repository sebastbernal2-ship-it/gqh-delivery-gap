#!/bin/bash
set -euo pipefail
umask 002

: "${Q_BIN:?Set Q_BIN to the approved q executable}"
: "${HPG_BLUE_DIR:?Set HPG_BLUE_DIR to the shared Blue allocation path}"
: "${GQH_KDB_INPUT_TSV:?Set path to exported TSV staged under Blue}"
: "${GQH_KDB_OUTPUT_DIR:?Set a new, empty HDB version directory under Blue}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT/../.." && pwd)"
BLUE_REAL="$(cd "$HPG_BLUE_DIR" && pwd -P)"
INPUT_REAL="$(cd "$(dirname "$GQH_KDB_INPUT_TSV")" && pwd -P)/$(basename "$GQH_KDB_INPUT_TSV")"
OUTPUT_PARENT="$(dirname "$GQH_KDB_OUTPUT_DIR")"
mkdir -p "$OUTPUT_PARENT"
OUTPUT_PARENT_REAL="$(cd "$OUTPUT_PARENT" && pwd -P)"
OUTPUT="$OUTPUT_PARENT_REAL/$(basename "$GQH_KDB_OUTPUT_DIR")"
RECEIPT="$OUTPUT_PARENT_REAL/$(basename "$OUTPUT").receipt.json"

case "$INPUT_REAL" in "$BLUE_REAL"/*) ;; *) echo "input must be staged under HPG_BLUE_DIR" >&2; exit 2 ;; esac
case "$OUTPUT" in "$BLUE_REAL"/*) ;; *) echo "HDB destination must be under HPG_BLUE_DIR" >&2; exit 2 ;; esac
[[ -f "$INPUT_REAL" ]] || { echo "input TSV does not exist" >&2; exit 2; }
MANIFEST="$INPUT_REAL.manifest.json"
[[ -f "$MANIFEST" ]] || { echo "export manifest is missing beside TSV" >&2; exit 2; }
[[ ! -e "$OUTPUT" ]] || { echo "destination already exists; choose a new version directory" >&2; exit 2; }
[[ ! -e "$RECEIPT" ]] || { echo "receipt already exists; choose a new version directory" >&2; exit 2; }
mkdir "$OUTPUT"

EXPECTED_ROWS="$(python3 - "$INPUT_REAL" "$MANIFEST" <<'PY'
import hashlib, json, sys
path, manifest_path = sys.argv[1:]
with open(manifest_path, encoding="utf-8") as f:
    manifest = json.load(f)
digest = hashlib.sha256()
count = 0
with open(path, "rb") as f:
    header = f.readline()
    if not header:
        raise SystemExit("empty TSV")
    for line in f:
        digest.update(line)
        count += 1
if count != int(manifest["rows"]):
    raise SystemExit("TSV row count differs from manifest")
if digest.hexdigest() != manifest["sha256_tsv_body"]:
    raise SystemExit("TSV SHA-256 differs from manifest")
print(count)
PY
)"
[[ "$EXPECTED_ROWS" =~ ^[1-9][0-9]*$ ]] || { echo "manifest row count is invalid" >&2; exit 2; }
"$Q_BIN" -q "$ROOT/q/build_bars_hdb.q" -input "$INPUT_REAL" -out "$OUTPUT" -expected "$EXPECTED_ROWS"

python3 - "$MANIFEST" "$RECEIPT" "$OUTPUT" "$REPO_ROOT" <<'PY'
import json, os, subprocess, sys
manifest_path, receipt_path, output = sys.argv[1:]
with open(manifest_path, encoding="utf-8") as f:
    receipt = json.load(f)
try:
    commit = subprocess.check_output(["git", "-C", sys.argv[4], "rev-parse", "HEAD"], text=True).strip()
except Exception:
    commit = "unknown"
receipt.update({"hdb_path": output, "git_commit": commit,
                "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"),
                "build_status": "q-loader-completed; independent HDB restore validation still required"})
with open(receipt_path, "x", encoding="utf-8") as f:
    json.dump(receipt, f, indent=2, sort_keys=True)
    f.write("\n")
PY
echo "HDB_BUILD_RECEIPT=$RECEIPT"
