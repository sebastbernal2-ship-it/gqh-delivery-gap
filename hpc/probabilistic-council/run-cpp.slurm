#!/bin/bash
#SBATCH --job-name=council-cpp
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=1G
#SBATCH --time=00:05:00
#SBATCH --output=council-cpp-%j.out
#SBATCH --error=council-cpp-%j.err

set -euo pipefail
g++ -std=c++17 -O2 -Wall -Wextra -Wpedantic -pthread \
    -I cpp/include cpp/src/council.cpp cpp/src/jevlike_tiny.cpp \
    cpp/examples/synthetic_pilot.cpp \
    -o council-cpp-pilot
./council-cpp-pilot
