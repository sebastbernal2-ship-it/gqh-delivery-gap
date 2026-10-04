import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from execution_risk_dataset import prepare
from package_execution_risk_training import package
from test_execution_jev import cache


class RiskBundleTests(unittest.TestCase):
    def test_staged_bundle_runs_from_slurm_spool_and_rejects_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare(cache(root), root / 'dataset')
            receipt = package(root / 'dataset', root / 'bundle.zip')
            self.assertEqual(receipt['comparison_count'], 4)
            with zipfile.ZipFile(root / 'bundle.zip') as archive:
                self.assertFalse(any('audit.jsonl' in name for name in archive.namelist()))
                archive.extractall(root / 'staged')
            bundle = root / 'staged/jev-risk-training'
            hashes = json.loads((bundle / 'bundle.json').read_text())['files_sha256']
            for name, expected in hashes.items():
                self.assertEqual(hashlib.sha256((bundle / name).read_bytes()).hexdigest(), expected)
            subprocess.run(['bash', '-n', str(bundle / 'submit.sh')], check=True)
            job = bundle / 'hpc/probabilistic-council/run-execution-risk.slurm'
            spool = root / 'slurm-spool'
            spool.mkdir()
            environment = dict(os.environ, GQH_REPO_ROOT=str(bundle),
                               GQH_JEV_DATASET=str(bundle / 'dataset'),
                               GQH_TAPE_RUN_DIR=str(bundle / 'runs/check'),
                               GQH_PYTHON=sys.executable, GQH_JEV_DEVICE='cpu',
                               GQH_JEV_ALLOW_DEVELOPMENT_SMOKE='1')
            result = subprocess.run(['bash', str(job)], cwd=spool, env=environment,
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((bundle / 'runs/check/report.json').read_text())
            self.assertEqual(report['epochs'], 3)
            self.assertFalse(report['pretraining'])
            repeated = subprocess.run(['bash', str(job)], cwd=spool, env=environment,
                                      text=True, capture_output=True)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertIn('Refuse existing output', repeated.stderr)
            with (bundle / 'dataset/features.npy').open('ab') as handle:
                handle.write(b'corrupt')
            environment['GQH_TAPE_RUN_DIR'] = str(bundle / 'runs/bad')
            rejected = subprocess.run(['bash', str(job)], cwd=spool, env=environment,
                                      text=True, capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn('risk array hash mismatch', rejected.stderr)
            self.assertFalse((bundle / 'runs/bad').exists())


if __name__ == '__main__':
    unittest.main()
