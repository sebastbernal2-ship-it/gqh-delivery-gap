#!/bin/bash
#SBATCH --job-name=qcbm-joint-gpu
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --partition=hpg-turin
#SBATCH --gpus=gpu:l4:1
#SBATCH --account=ai-workshop
#SBATCH --qos=ai-workshop
#SBATCH --output=qcbm-joint-gpu-%j.out
#SBATCH --error=qcbm-joint-gpu-%j.err

# Exact circuit Born machine on the L4 with the cuQuantum GPU device.
# Unverified on HiPerGator until a completed job and its receipt are recorded.
set -euo pipefail
module load pytorch/2.8.0
RUN_DIR="${RUN_DIR:-$PWD/runs/qcbm-gpu-$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$RUN_DIR"
python3 qcbm_joint.py --backend aer-gpu --steps 400 --shots 4000 --output "$RUN_DIR"
echo "receipt: $RUN_DIR/receipt.json"
