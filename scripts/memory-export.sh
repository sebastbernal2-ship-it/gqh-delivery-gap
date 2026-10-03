#!/usr/bin/env bash
# Export this device's local memory store. Device to device transfer only.
#
# The repo is the shared memory: brief, idea, system, decisions, reviews.
# Local agent memory stays on the device, because this repo is public and a local
# store can hold paths, error notes, and credential references that must not ship.
set -euo pipefail

mkdir -p memory
DEVICE="$(hostname -s 2>/dev/null || echo device)"
OUT="memory/${DEVICE}.json"

if command -v hippo >/dev/null; then
  if hippo export "$OUT" >/dev/null 2>&1; then
    echo "exported local memory to $OUT (gitignored)"
    echo "copy it yourself if another device should import it, for example over scp."
  else
    echo "hippo export failed. Nothing written."
  fi
else
  echo "no hippo on this device. Nothing to export."
fi

cat <<'NOTE'

Reminder: if a fact matters to the team, it belongs in docs/, not in this export.
  brief and rubric     docs/00-brief.md
  the strategy         docs/01-idea.md
  the plan             docs/02-system.md
  a settled decision   docs/03-decisions.md
  a critique           docs/reviews/
NOTE
