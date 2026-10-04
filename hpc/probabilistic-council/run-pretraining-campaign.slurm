#!/bin/bash
# Submit from this directory with --account and --qos for your allocation.
# Set JEV_RISK_DATASET and JEV_CAMPAIGN_OUTPUT to staged validated arrays and a new run directory.
#SBATCH --job-name=jev-pretrain-control
#SBATCH --partition=hpg-turin
#SBATCH --gpus=l4:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load pytorch/2.8.0
: "${JEV_RISK_DATASET:?set JEV_RISK_DATASET}"
: "${JEV_CAMPAIGN_OUTPUT:?set JEV_CAMPAIGN_OUTPUT}"
export PYTHONUNBUFFERED=1
args=()
if [[ "${JEV_REUSED_DEVELOPMENT_SMOKE:-0}" == "1" ]]; then
    args+=(--allow-reused-development-smoke)
fi
python execution_pretraining_campaign.py --dataset "$JEV_RISK_DATASET" \
    --output "$JEV_CAMPAIGN_OUTPUT" --device cuda "${args[@]}"
