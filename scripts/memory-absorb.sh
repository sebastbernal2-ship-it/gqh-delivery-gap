#!/usr/bin/env bash
# Load the team's shared memory into this device's local store, so recall finds it.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

if [ ! -s memory/shared.json ]; then
  echo "memory/shared.json is empty or missing. Nothing to absorb."
  exit 0
fi

if ! command -v hippo >/dev/null; then
  echo "no hippo on this device. Read memory/SHARED.md instead."
  exit 0
fi

python3 scripts/memory_absorb.py
