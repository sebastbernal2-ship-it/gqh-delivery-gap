#!/usr/bin/env bash
# Export this device's memory, filter it, and write the shared files for the team.
#
# Default deny: only entries tagged with the share tag (gqh), quanthacks, or
# gator-quant-hacks are shared, and only after redaction. See scripts/memory_filter.py.
set -euo pipefail

SHARE_TAG="${SHARE_TAG:-gqh}"
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

if ! command -v hippo >/dev/null; then
  echo "no hippo on this device. Nothing to share."
  exit 0
fi

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

if ! hippo export "$TMP" >/dev/null 2>&1; then
  echo "hippo export failed. Nothing shared."
  exit 0
fi

python3 scripts/memory_filter.py "$TMP" memory

echo
echo "wrote memory/SHARED.md and memory/shared.json"
echo "review the diff, then: make save M=\"memory: share from $(hostname -s)\""
