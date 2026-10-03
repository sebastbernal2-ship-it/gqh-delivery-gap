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

if hippo import --file memory/shared.json >/dev/null 2>&1; then
  echo "absorbed $(python3 -c 'import json;print(len(json.load(open("memory/shared.json"))))') shared memories into the local store"
else
  echo "hippo import --file failed, trying markdown"
  if hippo import --markdown memory/SHARED.md >/dev/null 2>&1; then
    echo "absorbed shared memory from memory/SHARED.md"
  else
    echo "WARNING: could not absorb shared memory. Read memory/SHARED.md by hand."
    exit 0
  fi
fi
