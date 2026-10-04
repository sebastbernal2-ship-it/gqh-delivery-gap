#!/usr/bin/env bash
# Normalize and load every window in a fetched slice into the Tiger store.
#
# usage: ingest_slice.sh SLICE_DIRECTORY
#
# Writes need a writable session, so the script switches the CLI to
# read_only=prod (PROD services stay protected, DEV stays writable) and always
# restores read_only=all on exit. Normalized JSONL is cached next to the
# windows, so a repeated run only reloads the store.
set -euo pipefail

SLICE=${1:?usage: ingest_slice.sh SLICE_DIRECTORY}
TIGER=${TIGER:-tiger}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
NORMALIZED="$SLICE/normalized"

mkdir -p "$NORMALIZED"
restore() { "$TIGER" config set read_only all >/dev/null 2>&1 || true; }
trap restore EXIT

# The slice manifest is the authority: only verified, replayable windows load.
while read -r entry; do
  name=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["name"])' "$entry")
  kind=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("kind","depth"))' "$entry")
  window="$SLICE/$name"
  [ -f "$window" ] || { echo "missing window $name" >&2; exit 1; }
  if [ "$kind" = "trades" ]; then
    output="$NORMALIZED/${name%.jsonl.gz}.trades.jsonl"
    [ -f "$output" ] || python3 "$ROOT/collector/normalize_trades.py" "$window" "$output"
  else
    output="$NORMALIZED/${name%.jsonl.gz}.depth.jsonl"
    [ -f "$output" ] || python3 "$ROOT/collector/normalize_capture.py" "$window" "$output"
  fi
done < <(python3 -c '
import json, sys
with open(sys.argv[1]) as handle:
    for line in handle:
        line = line.strip()
        if line:
            print(line)
' "$SLICE/slice-manifest.jsonl")

"$TIGER" config set read_only prod >/dev/null

for file in "$NORMALIZED"/*.depth.jsonl; do
  python3 "$ROOT/collector/tiger/ingest_normalized.py" "$file" --kind depth --tiger "$TIGER" \
    | sed -n '1p'
done
for file in "$NORMALIZED"/*.trades.jsonl; do
  python3 "$ROOT/collector/tiger/ingest_normalized.py" "$file" --kind trades --tiger "$TIGER" \
    | sed -n '1p'
done

echo "loaded slice $SLICE"
