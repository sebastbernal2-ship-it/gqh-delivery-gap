#!/bin/bash
#SBATCH --job-name=gqh-kdb-bars
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=gqh-kdb-bars-%j.out
#SBATCH --error=gqh-kdb-bars-%j.err

set -euo pipefail
: "${GQH_REPO_ROOT:?Set GQH_REPO_ROOT to the absolute shared repository path}"
# Slurm runs a spooled copy. Submission/log directories need not contain the repo.
case "$GQH_REPO_ROOT" in /*) ;; *) echo "GQH_REPO_ROOT must be absolute" >&2; exit 2 ;; esac
ROOT="$GQH_REPO_ROOT/hpc/kdb-timeseries"
[[ -f "$ROOT/scripts/build_hdb.sh" && -f "$ROOT/q/build_bars_hdb.q" ]] || {
    echo "GQH_REPO_ROOT does not contain the kdb-timeseries component" >&2; exit 2;
}
bash "$ROOT/scripts/build_hdb.sh"
