#!/usr/bin/env bash
# Rerun the three tape studies once the collector has stopped writing, in the background.
#
# Used by the extended-window pass: the collector writes to data/tape, this waits for the file to stop
# growing, then refreshes the recorded-window results. Output goes to /tmp/tape-rerun.log.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
LOG="${TAPE_RERUN_LOG:-/tmp/tape-rerun.log}"
prev=-1
stable=0
while [ "$stable" -lt 2 ]; do
  sleep 120
  size=$(stat -c %s data/tape/tape-20261004T043744Z.jsonl 2>/dev/null || echo 0)
  if [ "$size" = "$prev" ]; then
    stable=$((stable + 1))
  else
    stable=0
  fi
  prev=$size
done
echo "collector idle at $(date -u +%H:%M:%SZ), rerunning tape studies" >> "$LOG"
python3 scripts/build_cascade_reversion_study.py >> "$LOG" 2>&1
python3 scripts/build_maker_entry_study.py >> "$LOG" 2>&1
python3 scripts/build_spillover_study.py >> "$LOG" 2>&1
echo "tape studies refreshed at $(date -u +%H:%M:%SZ)" >> "$LOG"
