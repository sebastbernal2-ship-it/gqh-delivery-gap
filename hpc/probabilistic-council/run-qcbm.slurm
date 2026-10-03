#!/bin/bash
#SBATCH --job-name=qcbm-fixture
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:10:00
#SBATCH --output=qcbm-fixture-%j.out
#SBATCH --error=qcbm-fixture-%j.err

set -euo pipefail
python3 qcbm_pilot.py --seed 20261003 --train-samples 5000 --steps 160
