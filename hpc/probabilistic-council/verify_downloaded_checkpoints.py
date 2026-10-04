"""Verify published checkpoint bytes and CPU predictions against HPG GPU references."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from execution_risk_predict import ExecutionRiskPredictor
from synchronized_tape import digest


def verify(root):
    root = Path(root)
    manifest = json.loads((root / 'manifest.json').read_text())
    if (manifest.get('schema_version') != 'jev-checkpoint-release-v1'
            or manifest.get('scope') != 'development_only'
            or manifest.get('calibrated') is not False):
        raise ValueError('checkpoint release contract mismatch')
    if digest(root / 'training-report.json') != manifest['report_sha256']:
        raise ValueError('training report hash mismatch')
    core = Path(__file__).parent
    for name, sha in manifest['runtime_code_sha256'].items():
        if digest(core / name) != sha:
            raise ValueError('runtime code changed: ' + name)
    fixture = json.loads((root / 'parity.json').read_text())
    if fixture['scope'] != 'synthetic_portability_only':
        raise ValueError('expected synthetic portability fixture')
    errors = {}
    for name, spec in manifest['checkpoints'].items():
        if Path(name).name != name or not name.endswith('.pt'):
            raise ValueError('invalid checkpoint name')
        checkpoint = root / name
        if checkpoint.stat().st_size != spec['bytes']:
            raise ValueError('checkpoint size mismatch: ' + name)
        predictor = ExecutionRiskPredictor(checkpoint, spec['sha256'], device='cpu')
        actual = predictor.risk(fixture['sequence'])
        expected = np.asarray(fixture['expected'][name])
        if expected.shape != (3, 2, 2, 3):
            raise ValueError('reference prediction shape mismatch')
        np.testing.assert_allclose(actual, expected, rtol=1e-5, atol=1e-5,
                                   err_msg='CPU/HPG parity: ' + name)
        errors[name] = float(np.max(np.abs(actual - expected)))
    return {'status': 'passed', 'checkpoints': len(errors), 'scope': 'synthetic_portability_only',
            'max_absolute_difference_bps': errors, 'torch': torch.__version__, 'numpy': np.__version__,
            'device': 'cpu', 'reference_gpu': fixture['gpu'], 'calibrated': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path,
                        default=Path(__file__).parent / 'checkpoints/hpg-44665003')
    args = parser.parse_args()
    print(json.dumps(verify(args.release), indent=2))
