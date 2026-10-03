#!/bin/bash
#SBATCH --job-name=council-modular
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:05:00
#SBATCH --output=council-modular-%j.out
#SBATCH --error=council-modular-%j.err

set -euo pipefail
python3 modular_pilot.py --seed 20261003 --rows 12000
