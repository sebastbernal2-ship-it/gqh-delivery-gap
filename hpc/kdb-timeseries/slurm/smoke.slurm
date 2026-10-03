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
: "${HPG_BLUE_DIR:?Set HPG_BLUE_DIR to the shared Blue allocation path}"
: "${GQH_REPO_ROOT:?Set GQH_REPO_ROOT to the absolute shared repository path}"
# Slurm runs a spooled copy. Submission/log directories need not contain the repo.
case "$GQH_REPO_ROOT" in /*) ;; *) echo "GQH_REPO_ROOT must be absolute" >&2; exit 2 ;; esac
ROOT="$GQH_REPO_ROOT/hpc/kdb-timeseries"
[[ -f "$ROOT/scripts/make_fixture.py" && -f "$ROOT/q/build_bars_hdb.q" && -f "$ROOT/q/smoke_check.q" ]] || {
    echo "GQH_REPO_ROOT does not contain the kdb-timeseries component" >&2; exit 2;
}
RUN_ROOT="$HPG_BLUE_DIR/gqh-kdb/smoke-${SLURM_JOB_ID:-local}"
mkdir -p "$RUN_ROOT/input" "$RUN_ROOT/hdb"
python3 "$ROOT/scripts/make_fixture.py" --output "$RUN_ROOT/input/bars.tsv"
"$Q_BIN" -q "$ROOT/q/build_bars_hdb.q" -input "$RUN_ROOT/input/bars.tsv" -out "$RUN_ROOT/hdb" -expected 3
"$Q_BIN" -q "$ROOT/q/smoke_check.q" -db "$RUN_ROOT/hdb/" -expected 3
printf 'KDB_SMOKE_OK path=%s\n' "$RUN_ROOT/hdb"
