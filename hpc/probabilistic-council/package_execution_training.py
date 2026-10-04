"""OFF-CLUSTER: package validated numerical arrays and pinned code for archived HPG deployment."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
from execution_dataset import load_cache
from synchronized_tape import digest


LAUNCH='''#!/bin/bash
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
    actual = hashlib.sha256(Path(name).read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f'Bundle hash mismatch: {name}')
print('Bundle file hashes verified')
VERIFY
export GQH_REPO_ROOT="$root"
export GQH_JEV_DATASET="$root/dataset"
export GQH_TAPE_RUN_DIR="$root/runs/pretraining-$(date -u +%Y%m%dT%H%M%SZ)"
export GQH_PYTHON="$(command -v python)"
export GQH_JEV_DEVICE=cuda
sbatch --account=ai-workshop --qos=ai-workshop --partition=hpg-turin \\
  --gpus=l4:1 --chdir="$root/hpc/probabilistic-council" \\
  --output="$root/logs/pretraining-%j.out" --error="$root/logs/pretraining-%j.err" \\
  "$root/hpc/probabilistic-council/run-execution-pretraining.slurm"
'''


def package(dataset,reference,output):
    dataset,reference,output=Path(dataset),Path(reference),Path(output)
    if output.exists():
        raise ValueError('refuse to replace a training package')
    spec,arrays=load_cache(dataset)
    ref=json.loads((reference/'manifest.json').read_text())
    if (ref.get('schema_version')!='execution-linear-reference-v1' or
        ref.get('dataset_manifest_sha256')!=digest(dataset/'manifest.json') or
        digest(reference/'probabilities.npy')!=ref.get('probabilities_sha256') or
        digest(reference/'parameters.json')!=ref.get('parameters_sha256')):
        raise ValueError('reference/dataset provenance mismatch')
    component=Path(__file__).parent
    files={}
    for name in ('manifest.json',*spec['array_sha256']):
        files['jev-training/dataset/'+name]=(dataset/name).read_bytes()
    for name in ('manifest.json','probabilities.npy'):
        files['jev-training/reference/'+name]=(reference/name).read_bytes()
    # Source only: no raw payloads, label audit, checkpoints or unrelated repo contents.
    for pattern in ('*.py','council/*.py','jevlike/*.py','jevlike/LICENSE'):
        for path in sorted(component.glob(pattern)):
            files['jev-training/hpc/probabilistic-council/'+path.relative_to(component).as_posix()]=path.read_bytes()
    files['jev-training/hpc/probabilistic-council/run-execution-ablation.slurm']=(component/'run-execution-ablation.slurm').read_bytes()
    files['jev-training/hpc/probabilistic-council/run-execution-pretraining.slurm']=(component/'run-execution-pretraining.slurm').read_bytes()
    files['jev-training/submit.sh']=LAUNCH.encode()
    files['jev-training/README.txt']=(
        'Development only. This package does not establish alpha or competition OOS.\n'
        'On HiPerGator: cd jev-training; bash submit.sh\n'
        'The job compares scratch fitting with masked reconstruction pretraining on the same real BTC pilot cache.\n'
        'Both models then receive equal supervised training and are scored on frozen development roles.\n'
        'Linear reference was fitted off-cluster. No acquisition/parsing runs on HPG.\n'
        'Verify bundle.json and the external ZIP SHA-256 before use.\n').encode()
    report={'schema_version':'execution-training-bundle-v1','scope':'development_only',
        'dataset_manifest_sha256':digest(dataset/'manifest.json'),
        'role_cases':{name:int((arrays['roles']==i).sum()) for i,name in enumerate(spec['partitions'])},
        'role_sessions':{name:sorted({spec['sessions'][j] for j in np.flatnonzero(arrays['roles']==i)})
                         for i,name in enumerate(spec['partitions'])},
        'pretraining_rows':spec['pretraining_rows'],'supervised_epochs':3,'seed':20261003,
        'masked_pretraining_epochs':3,'linear_reference_manifest':ref,
        'files_sha256':{name.removeprefix('jev-training/'):hashlib.sha256(value).hexdigest()
                        for name,value in files.items()},
        'limitations':['archive deployment may have null git revision; code hashes pin actual sources',
                       'market-data receipt proxy and completeness remain unverified',
                       'small previously inspected caches are wiring evidence only']}
    files['jev-training/bundle.json']=(json.dumps(report,indent=2,sort_keys=True)+'\n').encode()
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,value in files.items():
            archive.writestr(name,value)
    return {'zip_sha256':digest(output),'zip_bytes':output.stat().st_size,**report}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(package(a.dataset,a.reference,a.output),indent=2,sort_keys=True))
