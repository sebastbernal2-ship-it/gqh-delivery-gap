#!/bin/bash
#SBATCH --job-name=gqh-kdb-smoke
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:10:00
#SBATCH --output=gqh-kdb-smoke-%j.out
#SBATCH --error=gqh-kdb-smoke-%j.err

set -euo pipefail
umask 002
: "${Q_BIN:?Set Q_BIN to the approved q executable}"
: "${HPG_BLUE_DIR:?Set HPG_BLUE_DIR to the team's shared Blue directory}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_ROOT="$HPG_BLUE_DIR/gqh-kdb/smoke-${SLURM_JOB_ID:-local}"
mkdir -p "$RUN_ROOT/input" "$RUN_ROOT/hdb"
python3 "$ROOT/scripts/make_fixture.py" --output "$RUN_ROOT/input/bars.tsv"
"$Q_BIN" -q "$ROOT/q/build_bars_hdb.q" -input "$RUN_ROOT/input/bars.tsv" -out "$RUN_ROOT/hdb" -expected 3
"$Q_BIN" -q "$ROOT/q/smoke_check.q" -db "$RUN_ROOT/hdb/" -expected 3
printf 'KDB_SMOKE_OK path=%s\n' "$RUN_ROOT/hdb"
