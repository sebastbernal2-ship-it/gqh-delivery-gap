#!/usr/bin/env bash
# Daily capture-to-report job. Runs on the box that collects, needs no database.
#
#   normalize new capture windows -> build canonical fixtures -> replay -> report
#
# Everything it writes lands under collector/data, which is ignored by git.
set -euo pipefail

REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
DATA_DIR="${DATA_DIR:-$REPO_DIR/collector/data}"
DAY="${1:-$(date -u +%Y%m%d)}"
DAY_START="${DAY:0:4}-${DAY:4:2}-${DAY:6:2}T00:00:00Z"
DAY_END="$(date -u -d "$DAY_START +1 day" +%Y-%m-%dT00:00:00Z)"
STATE_DIR="$DATA_DIR/state"
NORMALIZED="$DATA_DIR/normalized"
FIXTURES="$DATA_DIR/fixtures"
REPORTS="$DATA_DIR/reports"
SYMBOL="${SYMBOL:-BTCUSDT}"

mkdir -p "$STATE_DIR" "$NORMALIZED" "$FIXTURES" "$REPORTS"

say() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

# 1. Normalize every capture window that has no normalized output yet. Selection
# is by missing output, never by the label in the file name: a five-minute
# window that starts before midnight carries the previous day's label, and a
# UTC day of data spans both.
normalized_count=0
skipped_count=0
for capture in "$DATA_DIR"/*.jsonl.gz; do
  [ -e "$capture" ] || continue
  base="$(basename "$capture" .jsonl.gz)"
  case "$base" in
    *trades*) target="$NORMALIZED/$base.trades.jsonl"; mode=trades;;
    *)        target="$NORMALIZED/$base.depth.jsonl"; mode=depth;;
  esac
  [ -s "$target" ] && continue
  # Write beside the target and move it in, so a rejected or interrupted run
  # never leaves a partially normalized file that the next run would trust.
  partial="$target.part"
  rm -f "$partial"
  if [ "$mode" = trades ]; then
    runner="python3 $REPO_DIR/collector/normalize_trades.py"
  else
    runner="python3 $REPO_DIR/collector/normalize_capture.py"
  fi
  if $runner "$capture" "$partial" >/dev/null 2>&1 && [ -s "$partial" ]; then
    mv "$partial" "$target"
    normalized_count=$((normalized_count + 1))
  else
    # Expected for the window still being written: it has no snapshot yet, so
    # it is not replayable. It is retried on the next run.
    rm -f "$partial"
    skipped_count=$((skipped_count + 1))
  fi
done
say "normalized=$normalized_count skipped=$skipped_count"

# 2. Build the fixtures for the day from whatever is normalized.
depth_fixture="$FIXTURES/depth-$DAY.jsonl"
trades_fixture="$FIXTURES/trades-$DAY.jsonl"
built=0
if compgen -G "$NORMALIZED/*.depth.jsonl" >/dev/null; then
  python3 "$REPO_DIR/collector/build_fixture.py" --kind depth --symbol "$SYMBOL" \
    --start "$DAY_START" --end "$DAY_END" \
    --input "$NORMALIZED" --output "$depth_fixture" --manifest "$depth_fixture.manifest.json" >/dev/null
  built=$((built + 1))
fi
if compgen -G "$NORMALIZED/*.trades.jsonl" >/dev/null; then
  python3 "$REPO_DIR/collector/build_fixture.py" --kind trades --symbol "$SYMBOL" \
    --start "$DAY_START" --end "$DAY_END" \
    --input "$NORMALIZED" --output "$trades_fixture" --manifest "$trades_fixture.manifest.json" >/dev/null
  built=$((built + 1))
fi
if [ "$built" -eq 0 ]; then
  say "no fixtures built: nothing normalized for $DAY yet"
  exit 0
fi

# 3. Replay through the engine and write the report.
if [ ! -s "$trades_fixture" ]; then
  : > "$trades_fixture"
fi
report="$REPORTS/report-$DAY.json"
( cd "$REPO_DIR" && opam exec -- dune exec examples/fixture_report.exe -- --deterministic \
    "$depth_fixture" "$trades_fixture" "$depth_fixture.manifest.json" 25 10 ) > "$report" 2>/dev/null
python3 - "$report" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
print(
    "replayed events={events} snapshots={snapshots} gaps={chain_gaps} "
    "mismatch={book_mismatch} checksum={book_checksum}".format(**data)
)
for mode in data.get("modes", []):
    print(
        "  mode={mode} fills={fills} filled_units={filled_units} fees={fees} "
        "realized_pnl={realized_pnl} liquidations={liquidations}".format(**mode)
    )
PY
say "report=$report"
