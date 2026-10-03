#!/bin/bash
#SBATCH --job-name=council-smoke
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:05:00
#SBATCH --output=council-smoke-%j.out
#SBATCH --error=council-smoke-%j.err

set -euo pipefail
python3 pilot.py --seed 20261003 --rows 12000
