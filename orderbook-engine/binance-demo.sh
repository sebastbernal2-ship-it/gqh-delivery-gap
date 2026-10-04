#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
usage() {
  echo "usage: $0 CAPTURE_OR_URL [SYMBOL] [PRICE_TICK] [QUANTITY_STEP]" >&2
  exit 2
}

capture="${1:-}"
symbol="${2:-BTCUSDT}"
price_tick="${3:-0.10}"
quantity_step="${4:-0.001}"
[[ -n "$capture" ]] || usage

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT
raw="$workdir/capture.jsonl.gz"
if [[ "$capture" == http://* || "$capture" == https://* ]]; then
  curl -fsSL "$capture" -o "$raw"
elif [[ -f "$capture" ]]; then
  case "$capture" in
    *.gz) cp "$capture" "$raw" ;;
    *) cp "$capture" "$workdir/capture.jsonl"; raw="$workdir/capture.jsonl" ;;
  esac
else
  echo "capture not found: $capture" >&2
  exit 1
fi

normalized="$workdir/normalized.jsonl"
python3 "$ROOT/collector/normalize_capture.py" "$raw" "$normalized"
opam exec -- dune exec "$ROOT/examples/binance_replay_benchmark.exe" -- \
  "$symbol" "$price_tick" "$quantity_step" "$normalized"
