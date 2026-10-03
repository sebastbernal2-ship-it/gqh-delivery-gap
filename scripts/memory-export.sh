#!/usr/bin/env bash
# Export this device's local memory store so every other device converges.
# The repo remains the source of truth. This is a convenience cache.
set -euo pipefail

mkdir -p memory
DEVICE="$(hostname -s 2>/dev/null || echo device)"

if command -v hippo >/dev/null; then
  if hippo export "memory/${DEVICE}.json" >/dev/null 2>&1; then
    echo "exported local memory to memory/${DEVICE}.json"
  else
    echo "hippo export failed. Nothing written."
  fi
else
  echo "no hippo on this device. Nothing to export."
fi

echo "Commit it if it changed: make save M=\"memory: export from ${DEVICE}\""
