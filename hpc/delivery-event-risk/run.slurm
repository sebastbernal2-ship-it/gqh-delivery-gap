#!/bin/bash
#SBATCH --job-name=gqh-event-risk
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --output=gqh-event-risk-%j.out
#SBATCH --error=gqh-event-risk-%j.err

set -euo pipefail
: "${GQH_REPO_ROOT:?Set GQH_REPO_ROOT to the absolute shared repository path}"
: "${GQH_EVENT_CSV:?Set GQH_EVENT_CSV to the frozen development event CSV}"
: "${GQH_EVENT_MANIFEST:?Set GQH_EVENT_MANIFEST to the event manifest}"
: "${GQH_BARS_TSV:?Set GQH_BARS_TSV to the development-only daily bars TSV}"
: "${GQH_BARS_MANIFEST:?Set GQH_BARS_MANIFEST to the KDB exporter manifest}"
: "${GQH_DEVELOPMENT_START:?Set GQH_DEVELOPMENT_START from the frozen study protocol}"
: "${GQH_SEALED_START:?Set GQH_SEALED_START from the frozen study protocol}"
: "${GQH_OUTPUT_DIR:?Set GQH_OUTPUT_DIR to a new directory outside Git}"

case "$GQH_REPO_ROOT" in /*) ;; *) echo "GQH_REPO_ROOT must be absolute" >&2; exit 2 ;; esac
for path in "$GQH_EVENT_CSV" "$GQH_EVENT_MANIFEST" "$GQH_BARS_TSV" "$GQH_BARS_MANIFEST" "$GQH_OUTPUT_DIR"; do
    case "$path" in /*) ;; *) echo "input and output paths must be absolute: $path" >&2; exit 2 ;; esac
done
case "$GQH_OUTPUT_DIR" in "$GQH_REPO_ROOT"/*) echo "outputs must be outside the repository" >&2; exit 2 ;; esac
ROOT="$GQH_REPO_ROOT/hpc/delivery-event-risk"
[[ -f "$ROOT/event_risk.cpp" && -f "$ROOT/verify_inputs.py" ]] || {
    echo "GQH_REPO_ROOT does not contain hpc/delivery-event-risk" >&2; exit 2;
}
[[ -f "$GQH_EVENT_CSV" && -f "$GQH_EVENT_MANIFEST" && -f "$GQH_BARS_TSV" && -f "$GQH_BARS_MANIFEST" ]] || {
    echo "one or more declared input files are missing" >&2; exit 2;
}
[[ ! -e "$GQH_OUTPUT_DIR" ]] || { echo "refusing to overwrite output directory" >&2; exit 2; }

CXX_BIN="${CXX:-g++}"
command -v "$CXX_BIN" >/dev/null || { echo "C++17 compiler not found: $CXX_BIN" >&2; exit 2; }
SCRATCH="${SLURM_TMPDIR:-/tmp}/gqh-event-risk-${SLURM_JOB_ID:-manual}"
mkdir "$SCRATCH"
"$CXX_BIN" -std=c++17 -O2 -Wall -Wextra -Wpedantic -Werror \
    "$ROOT/event_risk.cpp" -o "$SCRATCH/event_risk"
python3 "$ROOT/verify_inputs.py" \
    --events "$GQH_EVENT_CSV" --event-manifest "$GQH_EVENT_MANIFEST" \
    --bars "$GQH_BARS_TSV" --bars-manifest "$GQH_BARS_MANIFEST" \
    --development-start "$GQH_DEVELOPMENT_START" --sealed-start "$GQH_SEALED_START" \
    --receipt "$SCRATCH/input-receipt.json"
"$SCRATCH/event_risk" --events "$GQH_EVENT_CSV" --bars "$GQH_BARS_TSV" \
    --development-start "$GQH_DEVELOPMENT_START" --sealed-start "$GQH_SEALED_START" \
    --cost-bps-per-side "${GQH_COST_BPS_PER_SIDE:-10}" --output "$GQH_OUTPUT_DIR"
cp "$SCRATCH/input-receipt.json" "$GQH_OUTPUT_DIR/input-receipt.json"
echo "event-risk run complete: $GQH_OUTPUT_DIR"
