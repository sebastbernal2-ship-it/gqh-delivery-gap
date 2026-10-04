#!/bin/bash
#SBATCH --job-name=jev-execution
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=jev-execution-%j.out
#SBATCH --error=jev-execution-%j.err
set -euo pipefail
: "${GQH_REPO_ROOT:?export an absolute shared repository root}"
: "${GQH_JEV_DATASET:?export an absolute prepared numerical cache}"
: "${GQH_TAPE_RUN_DIR:?export a new absolute model output directory}"
for path in "$GQH_REPO_ROOT" "$GQH_JEV_DATASET" "$GQH_TAPE_RUN_DIR"; do
    [[ "$path" = /* ]] || { echo 'absolute paths required' >&2; exit 2; }
done
component="$GQH_REPO_ROOT/hpc/probabilistic-council"
[[ -f "$component/execution_train.py" ]] || { echo 'wrong repository root' >&2; exit 2; }
[[ -f "$GQH_JEV_DATASET/manifest.json" ]] || { echo 'prepared cache missing' >&2; exit 2; }
[[ ! -e "$GQH_TAPE_RUN_DIR" ]] || { echo 'run directory already exists' >&2; exit 2; }
if [[ -z "${GQH_PYTHON:-}" ]]; then module load pytorch; GQH_PYTHON=python3; fi
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-2}"
cd "$component"
"$GQH_PYTHON" -c 'import torch, numpy; from execution_dataset import load_cache; import sys; load_cache(sys.argv[1])' "$GQH_JEV_DATASET"
"$GQH_PYTHON" execution_train.py --dataset "$GQH_JEV_DATASET" --output "$GQH_TAPE_RUN_DIR" \
    --epochs 3 --pretraining-epochs 3 --device "${GQH_JEV_DEVICE:-cpu}"
