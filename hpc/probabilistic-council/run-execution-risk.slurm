#!/bin/bash
#SBATCH --job-name=jev-risk-views
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
set -euo pipefail
: "${GQH_REPO_ROOT:?absolute checkout or bundle root required}"
: "${GQH_JEV_DATASET:?absolute prepared risk cache required}"
: "${GQH_TAPE_RUN_DIR:?absolute new output directory required}"
for path in "$GQH_REPO_ROOT" "$GQH_JEV_DATASET" "$GQH_TAPE_RUN_DIR"; do
  [[ "$path" = /* ]] || { echo "Absolute paths required" >&2; exit 2; }
done
component="$GQH_REPO_ROOT/hpc/probabilistic-council"
[[ -f "$component/execution_risk_train.py" && -f "$GQH_JEV_DATASET/manifest.json" ]] || exit 2
[[ ! -e "$GQH_TAPE_RUN_DIR" ]] || { echo "Refuse existing output" >&2; exit 2; }
if [[ -z "${GQH_PYTHON:-}" ]]; then
  source /etc/profile.d/modules.sh
  module load pytorch/2.8.0
  GQH_PYTHON=python3
fi
export PYTHONUNBUFFERED=1
export PYTHONPATH="$component${PYTHONPATH:+:$PYTHONPATH}"
"$GQH_PYTHON" -c 'import sys; from execution_risk_dataset import load_risk_cache; load_risk_cache(sys.argv[1])' "$GQH_JEV_DATASET"
args=()
if [[ "${GQH_JEV_ALLOW_DEVELOPMENT_SMOKE:-0}" = 1 ]]; then args+=(--allow-development-smoke); fi
"$GQH_PYTHON" "$component/execution_risk_train.py" \
  --dataset "$GQH_JEV_DATASET" --output "$GQH_TAPE_RUN_DIR" \
  --device "${GQH_JEV_DEVICE:-cpu}" "${args[@]}"
