#!/usr/bin/env bash
# Start one BTC capture block if another whole UTC date is still needed, then exit.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/tape_block_due.py --root data/tape --target 5 | tee -a data/logs/tape.log
if ! python3 scripts/tape_block_due.py --root data/tape --target 5 | grep -q '"due": true'; then
  echo "block not due; nothing started" | tee -a data/logs/tape.log
  exit 0
fi
stamp="$(date -u +%Y%m%dT%H%MZ)"
out="data/tape/btc-${stamp}"
echo "starting block $out" | tee -a data/logs/tape.log
exec python3 hpc/probabilistic-council/record_execution_tape.py --output "$out" --seconds 21600 \
  --max-bytes 64000000 >> "$out.launch.log" 2>&1
