"""OFF-CLUSTER: package a validated risk cache and only its model dependencies."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from execution_risk_dataset import FILES, load_risk_cache
from synchronized_tape import digest

LAUNCH = '''#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
root="$PWD"
mkdir -p "$root/runs" "$root/logs"
module load pytorch/2.8.0
python - <<'VERIFY'
import hashlib
import json
from pathlib import Path
spec = json.loads(Path('bundle.json').read_text())
for name, expected in spec['files_sha256'].items():
    if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
        raise SystemExit(f'Bundle hash mismatch: {name}')
print('Risk bundle hashes verified')
VERIFY
export GQH_REPO_ROOT="$root"
export GQH_JEV_DATASET="$root/dataset"
export GQH_TAPE_RUN_DIR="$root/runs/risk-$(date -u +%Y%m%dT%H%M%SZ)"
export GQH_PYTHON="$(command -v python)"
export GQH_JEV_DEVICE=cuda
export GQH_JEV_ALLOW_DEVELOPMENT_SMOKE=1
sbatch --account="${GQH_SLURM_ACCOUNT:-ai-workshop}" --qos="${GQH_SLURM_QOS:-ai-workshop}" \\
  --partition=hpg-turin --gpus=l4:1 --chdir="$root/hpc/probabilistic-council" \\
  --output="$root/logs/risk-%j.out" --error="$root/logs/risk-%j.err" \\
  "$root/hpc/probabilistic-council/run-execution-risk.slurm"
'''


def package(dataset, output):
    dataset, output = Path(dataset), Path(output)
    if output.exists():
        raise ValueError("refuse existing risk package")
    spec, arrays = load_risk_cache(dataset)
    component = Path(__file__).parent
    files = {"dataset/manifest.json": (dataset / "manifest.json").read_bytes()}
    for name in FILES:
        files["dataset/" + name + ".npy"] = (dataset / (name + ".npy")).read_bytes()
    sources = ("execution_risk_train.py", "execution_risk_model.py", "execution_risk_dataset.py",
               "execution_risk_cost.py", "execution_risk_predict.py", "execution_action_model.py",
               "execution_model.py", "execution_dataset.py", "multisession_panel.py",
               "synchronized_tape.py", "runtime_provenance.py", "run-execution-risk.slurm")
    for name in sources:
        files["hpc/probabilistic-council/" + name] = (component / name).read_bytes()
    for path in sorted((component / "jevlike").glob("*.py")) + [component / "jevlike/LICENSE"]:
        files["hpc/probabilistic-council/jevlike/" + path.name] = path.read_bytes()
    files["submit.sh"] = LAUNCH.encode()
    files["README.txt"] = (
        "Development wiring only. These reused BTC cases do not establish trading edge.\n"
        "Run: cd jev-risk-training; bash submit.sh\n"
        "Model fitting is scratch A/B/AB, three epochs, seed 20261004. No pretraining.\n"
        "The empirical-quantile comparator is a count-based training-label diagnostic.\n"
        "Raw parsing/label construction run off-cluster; no PyArrow required on HPG.\n"
        "Verify the external ZIP SHA-256 and internal bundle hashes before submission.\n").encode()
    report = {"schema_version": "execution-movement-training-bundle-v1", "scope": "development_only",
              "dataset_manifest_sha256": digest(dataset / "manifest.json"),
              "parent_cases": len(arrays["features"]), "comparison_count": 4,
              "epochs": 3, "seed": 20261004,
              "files_sha256": {name: hashlib.sha256(value).hexdigest() for name, value in files.items()}}
    files["bundle.json"] = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in sorted(files.items()):
            archive.writestr("jev-risk-training/" + name, value)
    return {**report, "zip_sha256": digest(output), "zip_bytes": output.stat().st_size}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(package(args.dataset, args.output), indent=2))
