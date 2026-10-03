#!/bin/bash
#SBATCH --job-name=gqh-kdb-bars
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=gqh-kdb-bars-%j.out
#SBATCH --error=gqh-kdb-bars-%j.err

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bash "$ROOT/scripts/build_hdb.sh"
