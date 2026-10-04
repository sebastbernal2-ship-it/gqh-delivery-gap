#!/bin/bash
#SBATCH --job-name=jev-multisession-dev
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=jev-multisession-%j.out
#SBATCH --error=jev-multisession-%j.err

set -euo pipefail
: "${GQH_REPO_ROOT:?export the absolute shared repository root}"
: "${GQH_TAPE_OBJECTS:?export the absolute pinned-object directory}"
: "${GQH_TAPE_RUN_DIR:?export a new absolute durable run directory}"
for path in "$GQH_REPO_ROOT" "$GQH_TAPE_OBJECTS" "$GQH_TAPE_RUN_DIR"; do
    [[ "$path" = /* ]] || { echo 'absolute paths required' >&2; exit 2; }
done
component="$GQH_REPO_ROOT/hpc/probabilistic-council"
[[ -f "$component/multisession_panel.py" && -f "$component/multisession_plan.json" ]] || { echo 'wrong repository root' >&2; exit 2; }
[[ -d "$GQH_TAPE_OBJECTS" ]] || { echo 'source objects missing' >&2; exit 2; }
[[ ! -e "$GQH_TAPE_RUN_DIR" ]] || { echo 'run directory already exists' >&2; exit 2; }
if [[ -z "${GQH_PYTHON:-}" ]]; then
    module load pytorch
    GQH_PYTHON=python3
fi
"$GQH_PYTHON" -c 'import torch, pyarrow'
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-2}"
mkdir -p "$GQH_TAPE_RUN_DIR"
cd "$component"
"$GQH_PYTHON" multisession_panel.py --plan multisession_plan.json \
    --objects "$GQH_TAPE_OBJECTS" --output "$GQH_TAPE_RUN_DIR/panel"
"$GQH_PYTHON" information_views.py --panel "$GQH_TAPE_RUN_DIR/panel/panel.jsonl" \
    --manifest "$GQH_TAPE_RUN_DIR/panel/manifest.json" --output "$GQH_TAPE_RUN_DIR/models" \
    --epochs 3 --seed 20261003
