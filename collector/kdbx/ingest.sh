#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/ubuntu/collector}"
DATA_DIR="$ROOT/data"
KDB_DIR="$ROOT/kdbx/db"
MANIFEST="$DATA_DIR/manifest.jsonl"
SEEN="$KDB_DIR/loaded.sha256"
NORMALIZED="$(mktemp /tmp/binance-kdbx.XXXXXX.jsonl)"
LOCK="$KDB_DIR/.ingest.lock"

mkdir -p "$KDB_DIR"
exec 9>"$LOCK"
flock -n 9 || exit 0
trap 'rm -f "$NORMALIZED"' EXIT

if [[ ! -f "$MANIFEST" ]]; then
  exit 0
fi

tail -n +1 "$MANIFEST" | while IFS= read -r manifest_row; do
  [[ -n "$manifest_row" ]] || continue
  path="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["path"])' "$manifest_row")"
  kind="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("kind","depth"))' "$manifest_row")"
  digest="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["sha256"])' "$manifest_row" 2>/dev/null || true)"
  if [[ ! -f "$path" && "$path" == /data/binance/* ]]; then
    path="$DATA_DIR/${path#/data/binance/}"
  fi
  [[ -f "$path" ]] || continue
  gzip -t "$path" 2>/dev/null || continue
  actual_digest="$(sha256sum "$path" | awk '{print $1}')"
  if [[ -n "$digest" && "$digest" != "$actual_digest" ]]; then
    continue
  fi
  digest="$actual_digest"
  grep -Fqx "$digest" "$SEEN" 2>/dev/null && continue
  if [[ "$kind" == "trades" ]]; then
    if ! python3 "$ROOT/normalize_trades.py" "$path" "$NORMALIZED"; then
      printf 'skip invalid trade capture: %s\n' "$path" >&2
      continue
    fi
    (cd "$ROOT/kdbx" && /home/ubuntu/.kx/bin/q trade_load.q "$NORMALIZED" "$KDB_DIR")
  else
    if ! python3 "$ROOT/normalize_capture.py" "$path" "$NORMALIZED"; then
      printf 'skip invalid depth capture: %s\n' "$path" >&2
      continue
    fi
    (cd "$ROOT/kdbx" && /home/ubuntu/.kx/bin/q load.q "$NORMALIZED" "$KDB_DIR")
  fi
  printf '%s\n' "$digest" >> "$SEEN"
done
