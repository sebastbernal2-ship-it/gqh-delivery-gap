#!/bin/bash
#SBATCH --job-name=jevlike-cpp-smoke
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --output=jevlike-cpp-%j.out
#SBATCH --error=jevlike-cpp-%j.err

set -euo pipefail
module load pytorch

RUN_DIR="${TMPDIR:-/tmp}/jevlike-${SLURM_JOB_ID}"
mkdir -p "$RUN_DIR"
python -m jevlike.data synthetic --output "$RUN_DIR/data" \
    --train 256 --validation 64 --test 64 --seed 20261003
python -m jevlike.train "$RUN_DIR/data/train.jsonl" \
    --validation "$RUN_DIR/data/validation.jsonl" \
    --output "$RUN_DIR/tiny.pt" --encoder tiny --width 32 --rank 32 \
    --context-tokens 192 --option-tokens 32 --epochs 2 --batch-size 32 \
    --device cpu --seed 20261003
python -m jevlike.eval "$RUN_DIR/tiny.pt" "$RUN_DIR/data/test.jsonl" \
    --batch-size 32 --device cpu
python jevlike/export_tiny_cpp.py "$RUN_DIR/tiny.pt" \
    --output "$RUN_DIR/tiny.jvlk" --data-version synthetic-20261003
g++ -std=c++17 -O2 -Wall -Wextra -Wpedantic -pthread \
    -I cpp/include cpp/src/council.cpp cpp/src/jevlike_tiny.cpp \
    cpp/examples/jevlike_predict.cpp -o "$RUN_DIR/jevlike-predict-cpp"
python -m jevlike.verify_cpp_parity --checkpoint "$RUN_DIR/tiny.pt" \
    --weights "$RUN_DIR/tiny.jvlk" --cpp-binary "$RUN_DIR/jevlike-predict-cpp"
