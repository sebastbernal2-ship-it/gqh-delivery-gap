# C++ probabilistic council

This is a dependency-free C++17 implementation of the council runtime under the same
`council-distribution-0.2.0` forecast contract as the Python API.

## Included

- Validated categorical forecasts with ordered classes, model/data versions, contexts, validity
  windows, optional epistemic uncertainty, abstention, and explicitly enumerated joint states.
- Multiclass temperature calibration selected by calibration-set log loss.
- Inverse-Brier global and supported context reliability weights, with a nonzero minimum weight.
- Linear and logarithmic opinion pools, final pool calibration, entropy, disagreement, and weighted
  input-uncertainty diagnostics.
- Separate chronological specialist-calibration, gate-fit, and pool-calibration partitions. Case IDs
  cannot overlap and predictions must be later than all fitting data.
- Bounded `std::thread` specialist inference and joint-distribution marginalization.

Forecast timestamps are UTC Unix seconds. The caller must parse source timestamps correctly and
preserve the information cutoff; the library checks `cutoff <= forecast < valid_until`. It does not
assume independent specialists. Temperature scaling, inverse-Brier weights, and opinion pools are
transparent baselines, not production defaults.

## Build and run

Locally with CMake:

```sh
cmake -S cpp -B build-cpp
cmake --build build-cpp --parallel
./build-cpp/council_synthetic_pilot
```

On HiPerGator, copy this approach directory to writable scratch or Blue storage, then submit
`sbatch run-cpp.slurm`. The Slurm job builds with the system C++17 compiler and runs a seeded
synthetic example. It does not use financial observations or Laya weights. No C++ Laya inference
adapter, GPU path, data loader, model registry, or execution policy is included yet.

## HiPerGator run record

Verified 2026-10-03: Slurm job `44557427` compiled the C++17 library and synthetic pilot on
HiPerGator, then completed in three seconds with exit code `0` and empty stderr. Stdout reported 120
synthetic evaluation rows and the parallel fused distribution. This is a software smoke result only;
it contains no market observations, Laya weights, or financial forecast.
