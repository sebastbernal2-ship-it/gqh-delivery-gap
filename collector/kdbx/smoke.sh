#!/usr/bin/env bash
set -euo pipefail

DEPTH_JSONL="${1:?usage: smoke.sh DEPTH_JSONL [TRADE_JSONL]}"
TRADE_JSONL="${2:-}"
Q_BIN="${Q_BIN:-$HOME/.kx/bin/q}"
if [[ ! -x "$Q_BIN" ]]; then
  Q_BIN="q"
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_DIR="$(mktemp -d)"
trap 'rm -rf "$DB_DIR"' EXIT

"$Q_BIN" "$SCRIPT_DIR/load.q" "$DEPTH_JSONL" "$DB_DIR"
"$Q_BIN" "$SCRIPT_DIR/export.q" "$DB_DIR" > "$DB_DIR/depth-export.jsonl"
python3 - "$DEPTH_JSONL" "$DB_DIR/depth-export.jsonl" <<'PY'
import json
import sys

def count(path):
    return sum(
        1
        for line in open(path, encoding="utf-8")
        if line.lstrip().startswith("{") and json.loads(line)
    )

source, exported = map(count, sys.argv[1:])
if source != exported:
    raise SystemExit(f"depth row count mismatch: source={source} exported={exported}")
print(f"depth rows verified: {source}")
PY

if [[ -n "$TRADE_JSONL" ]]; then
  "$Q_BIN" "$SCRIPT_DIR/trade_load.q" "$TRADE_JSONL" "$DB_DIR"
  "$Q_BIN" "$SCRIPT_DIR/trade_export.q" "$DB_DIR" > "$DB_DIR/trade-export.jsonl"
  python3 - "$TRADE_JSONL" "$DB_DIR/trade-export.jsonl" <<'PY'
import json
import sys

def count(path):
    return sum(
        1
        for line in open(path, encoding="utf-8")
        if line.lstrip().startswith("{") and json.loads(line)
    )

source, exported = map(count, sys.argv[1:])
if source != exported:
    raise SystemExit(f"trade row count mismatch: source={source} exported={exported}")
print(f"trade rows verified: {source}")
PY
fi
