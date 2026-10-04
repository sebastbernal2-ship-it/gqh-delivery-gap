#!/usr/bin/env bash
# Keep the research site serving on the shared alias.
#
# Another session deploys a different app to the same Vercel project, which replaces the production
# deployment and 404s our pages. This watchdog checks the alias on a fixed cadence, verifies the content
# is ours (not just a 200), and republishes docs/ when it is not. It backs off so it never fights a
# deploy loop: one republish per cycle at most.
#
# Usage:
#   scripts/watch_site.sh --minutes 240 --interval 120
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MINUTES=240
INTERVAL=120
while [ $# -gt 0 ]; do
  case "$1" in
    --minutes) MINUTES="$2"; shift 2 ;;
    --interval) INTERVAL="$2"; shift 2 ;;
    *) shift ;;
  esac
done
LOG="${TMPDIR:-/tmp}/gqh-site-watch.log"
MARKER="The field: forces, pushes, phases, chains"
DEADLINE=$(( $(date +%s) + MINUTES * 60 ))

check() {
  body=$(curl -s --max-time 25 https://docs-roan-seven.vercel.app/scan/field.html || true)
  case "$body" in
    *"$MARKER"*) return 0 ;;
    *) return 1 ;;
  esac
}

publish() {
  bash "$ROOT/scripts/deploy_docs.sh" >> "$LOG" 2>&1
}

echo "watchdog start $(date -u +%H:%M:%SZ), every ${INTERVAL}s for ${MINUTES} minutes" >> "$LOG"
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  if check; then
    echo "$(date -u +%H:%M:%SZ) ok" >> "$LOG"
  else
    echo "$(date -u +%H:%M:%SZ) alias does not serve the research site, republishing" >> "$LOG"
    publish
    if check; then
      echo "$(date -u +%H:%M:%SZ) restored" >> "$LOG"
    else
      echo "$(date -u +%H:%M:%SZ) still not serving after republish; mirror https://gqh-site.vercel.app" >> "$LOG"
    fi
  fi
  sleep "$INTERVAL"
done
echo "watchdog end $(date -u +%H:%M:%SZ)" >> "$LOG"
