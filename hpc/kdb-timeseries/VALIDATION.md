# kdb job-wrapper correctness audit — 2026-10-03

Scope: repair the reviewed shell/Slurm failures on main `85c3f31`. This is a local
correctness record, not a HiPerGator job receipt or a q/HDB certification. The Python exporter
and q storage model retain their existing interfaces. The submission environment gains the
explicit repository-root contract recorded in `docs/decisions.md`.

## Root causes and fixes

### A submitted script has a different location from the repository

Both Slurm scripts formerly derived the component directory from `BASH_SOURCE[0]`.
Slurm executes a copied batch script; locating sibling repository files from that copy resolves
into the spool tree. The documented workflow also submits from a Blue logs directory, so simply
substituting `SLURM_SUBMIT_DIR` would still be wrong: it denotes the submission directory, not
the checkout. This distinction follows the [official sbatch documentation](https://slurm.schedmd.com/sbatch.html).

Both wrappers now require an exported, absolute `GQH_REPO_ROOT` and check for their required
component files. No fallback silently chooses another checkout. See the [README](README.md)
for the updated commands. The path must be visible on compute nodes, not merely the login node.
UF recommends a Blue working directory when submitting computation;
see [UF computation guidance](https://docs.rc.ufl.edu/quickstart/computation/).

### Successful loader invocation still produced a failed job

`build_hdb.sh` passes manifest, receipt, output and repository paths to its receipt writer.
The Python snippet unpacked only three variables. A successful q invocation therefore led to
`ValueError` instead of a receipt. The writer now unpacks four named variables and uses the
named repository root for commit provenance. The receipt still explicitly says independent
restore validation is required. It is never evidence of reconciliation by itself.

### Input rejection consumed an unused version

The output directory was created before input-body checksum and row-count verification.
Correctly rejecting a bad input left a version directory that prevented a subsequent build.
Creation now follows successful preflight. Once q starts, failed/partial output remains in place
for investigation. Reruns must use a new version; no automatic deletion or overwrite was added.
Parent-directory creation is unchanged; the guarantee concerns the claimed HDB version itself.

### Local shell portability

The apostrophe in the smoke script's parameter-expansion error message caused an unmatched
quote on the validation host's Bash 3.2. It was removed without changing the environment contract.
This was observed locally; no claim is made that the original also failed under the cluster's
different Bash version. Every `.slurm` file is now syntax-checked individually by the regression
suite. Passing multiple filenames to one `bash -n` invocation does not check them all.

## Tests and evidence

Run from the repository root:

```sh
python3 -m unittest discover -s hpc/kdb-timeseries/tests -v
```

Local result: **17 passing tests**: six existing exporter tests and eleven new wrapper tests.
The new tests use private temporary directories, including paths containing spaces, and launch
real Bash/Python subprocesses. Their q executable is a deliberately simple stub that records
arguments and returns a configured status. It does not interpret q or create real database files.

| Contract | Regression evidence |
|---|---|
| A successful loader writes an accurate receipt | Checks input hash/count, output path, Git revision, job ID and qualified status |
| Spooling cannot relocate repository lookup | Copies both scripts into a fake spool tree and runs from an unrelated logs directory |
| Bad repository configuration fails early | Missing, relative and wrong-component paths fail before q |
| Input integrity rejection does not consume a version | Checksum and row-count mismatches create no output version and never call q |
| Missing input manifest fails early | No version created |
| Loader failure propagates | Exit status 17 preserved; no receipt; partial version protected from retry |
| Published/claimed versions are immutable to this wrapper | Existing output or receipt prevents reuse; original receipt bytes unchanged |
| Smoke executes validation after loading | Stub records loader then smoke validator |
| Shell scripts parse | Each HPC Slurm script checked independently |

Before applying the fixes, the tests reproduced the wrong spool path, receipt unpacking failure,
premature output creation and Bash syntax failure. After the fixes, all seventeen pass.
Validation host: macOS arm64, Bash 3.2.57, Python 3.12.0. Linux/Slurm was simulated only at the
script-location and environment boundary; no scheduler was installed or contacted.

## Remaining acceptance gate

The approved q runtime and an authenticated HiPerGator session were unavailable for this run.
The q scripts remain unmodified and runtime-unverified. Stub success cannot establish whether
TSV parsing, q expression evaluation, symbol enumeration, partition writing or reload works.
KX's [partitioned-database documentation](https://code.kx.com/kdb-x/learn/q4m/14_Introduction_to_kdb%2B.html)
describes the `.Q.dpft` persistence contract; it does not validate this implementation.

The owner should complete these stages in order:

1. Set the approved `Q_BIN`, team `HPG_BLUE_DIR` and shared `GQH_REPO_ROOT` as in the README.
   Submit the synthetic smoke job from a separate Blue logs directory.
2. Retain job ID, Git revision, q version, stdout/stderr and scheduler exit status. Require the
   actual q loader and reload validator to finish successfully. Diagnose any q errors before
   using real data; a shell test cannot resolve those.
3. Stage a checksummed 100-row canary plus manifest, build a new version, then independently
   reload and compare counts by date/symbol, scaled integer values, row hashes and provenance.
4. Only after that evidence passes, build the full selected batch and test the durable restore
   path. No automatic TigerData deletion or production cutover is part of this change.

The [JevLike validation record](../probabilistic-council/VALIDATION.md) owns the model-side
audit and the repository-wide check results for this combined repair.
