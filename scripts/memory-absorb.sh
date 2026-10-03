#!/usr/bin/env bash
# Load the team's shared memory into this device's local store, so recall finds it.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

if [ ! -s memory/shared.json ]; then
  echo "memory/shared.json is empty or missing. Nothing to absorb."
  exit 0
fi

if ! command -v hippo >/dev/null; then
  echo "no hippo on this device. Read memory/SHARED.md instead."
  exit 0
fi

# A fresh clone has no store yet. Create one so this works on the first run.
if [ ! -d "$ROOT/.hippo" ]; then
  echo "no local store yet, initializing .hippo"
  hippo init --no-hooks --no-schedule >/dev/null 2>&1 || true
fi

python3 scripts/memory_absorb.py
