#!/usr/bin/env bash
# The daily capture job: one forward snapshot and one option snapshot, logged and idempotent.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/logs
today="$(date -u +%Y%m%d)"
log="data/logs/daily-${today}.log"
marker="data/logs/daily-${today}.done"

if [ -f "$marker" ]; then
  echo "$(date -u +%FT%TZ) already ran today; nothing to do" >> "$log"
  exit 0
fi
{
  echo "=== $(date -u +%FT%TZ) forward snapshot"
  python3 scripts/run_forward_snapshot.py --refresh || echo "snapshot failed with $?"
  echo "=== $(date -u +%FT%TZ) option snapshot"
  python3 scripts/collect_option_snapshots.py || echo "options failed with $?"
  echo "=== $(date -u +%FT%TZ) done"
} >> "$log" 2>&1
touch "$marker"
