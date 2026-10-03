#!/usr/bin/env bash
# Export this device's memory, filter it, and write the shared files for the team.
#
# Capture is mechanical: if the memory store lives inside this repo, every entry in it
# is project scope by construction, so nothing needs a human tag. If the store lives
# outside the repo, the default is deny and only project-tagged entries are shared.
# Redaction and the credential rules apply in both modes.
set -uo pipefail

SHARE_TAG="${SHARE_TAG:-gqh}"
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

if ! command -v hippo >/dev/null; then
  echo "no hippo on this device. Nothing to share."
  exit 0
fi

# Resolve the store the way hippo does: nearest .hippo/hippo.db walking up.
resolve_store() {
  local d="$1"
  while [ "$d" != "/" ] && [ -n "$d" ]; do
    if [ -f "$d/.hippo/hippo.db" ]; then printf '%s' "$d"; return 0; fi
    d="$(dirname "$d")"
  done
  printf ''
}

STORE="$(resolve_store "$ROOT")"
MODE=""
case "$STORE" in
  "$ROOT"|"$ROOT"/*) MODE="--store-scoped" ;;
  "") MODE="" ;;
  *)  MODE="" ;;
esac

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

if ! hippo export "$TMP" >/dev/null 2>&1; then
  echo "hippo export failed. Nothing shared."
  exit 0
fi

python3 scripts/memory_filter.py $MODE "$TMP" memory
echo "(store: ${STORE:-none}, mode: ${MODE:-tagged})"
echo "review the diff, then: make save M=\"memory: share from $(hostname -s)\""
