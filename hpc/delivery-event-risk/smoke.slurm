#!/bin/bash
#SBATCH --job-name=gqh-event-risk-smoke
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=gqh-event-risk-smoke-%j.out
#SBATCH --error=gqh-event-risk-smoke-%j.err

set -euo pipefail
: "${GQH_REPO_ROOT:?Set GQH_REPO_ROOT to the absolute shared repository path}"
case "$GQH_REPO_ROOT" in /*) ;; *) echo "GQH_REPO_ROOT must be absolute" >&2; exit 2 ;; esac
ROOT="$GQH_REPO_ROOT/hpc/delivery-event-risk"
[[ -f "$ROOT/smoke.py" && -f "$ROOT/event_risk.cpp" ]] || {
    echo "GQH_REPO_ROOT does not contain hpc/delivery-event-risk" >&2; exit 2;
}
python3 "$ROOT/smoke.py" --compiler "${CXX:-g++}"
