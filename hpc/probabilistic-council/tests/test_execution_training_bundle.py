import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
import re

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from execution_linear_reference import prepare
from package_execution_training import package
from test_execution_jev import cache


class TrainingBundleTests(unittest.TestCase):
    def test_archived_real_trainer_runs_without_git_and_scores_prefit_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            dataset=cache(root)
            prepare(dataset,root/'reference')
            receipt=package(dataset,root/'reference',root/'training.zip')
            with zipfile.ZipFile(root/'training.zip') as archive:
                self.assertFalse(any('label_audit' in name for name in archive.namelist()))
                names=set(archive.namelist())
                pretrain_script='jev-training/hpc/probabilistic-council/run-execution-pretraining.slurm'
                self.assertIn(pretrain_script,names)
                self.assertEqual(receipt['masked_pretraining_epochs'],3)
                archive.extractall(root/'deployment')
            deployed=root/'deployment/jev-training'
            submit=deployed/'submit.sh'
            pretrain=deployed/'hpc/probabilistic-council/run-execution-pretraining.slurm'
            for script in (submit,pretrain):
                syntax=subprocess.run(['bash','-n',str(script)],capture_output=True,text=True)
                self.assertEqual(syntax.returncode,0,syntax.stderr)
            launch=submit.read_text()
            verifier=re.search(r"python - <<'VERIFY'\n(.*?)\nVERIFY",launch,re.S)
            self.assertIsNotNone(verifier)
            compile(verifier.group(1),str(submit),'exec')
            self.assertIn('run-execution-pretraining.slurm',launch)
            self.assertNotIn('run-execution-ablation.slurm',launch)
            pretrain_proc=subprocess.run([sys.executable,'execution_train.py','--dataset',str(deployed/'dataset'),
                '--output',str(root/'pretraining-run'),'--epochs','1','--pretraining-epochs','1','--device','cpu'],
                cwd=deployed/'hpc/probabilistic-council',capture_output=True,text=True,timeout=60)
            self.assertEqual(pretrain_proc.returncode,0,pretrain_proc.stderr)
            pretrain_report=json.loads((root/'pretraining-run/report.json').read_text())
            self.assertGreater(pretrain_report['pretraining_corpus']['windows'],0)
            self.assertGreater(len(pretrain_report['losses']['masked_pretrained']['pretraining_losses']),0)
            self.assertEqual(pretrain_report['pretraining_epochs'],1)
            proc=subprocess.run([sys.executable,'execution_ablation.py','--dataset',str(deployed/'dataset'),
                '--reference',str(deployed/'reference'),'--output',str(root/'run'),'--epochs','1'],
                cwd=deployed/'hpc/probabilistic-council',capture_output=True,text=True,timeout=60)
            self.assertEqual(proc.returncode,0,proc.stderr)
            report=json.loads((root/'run/report.json').read_text())
            self.assertIsNone(report['git_revision'])
            self.assertEqual(report['forecast_comparison_count'],6)
            self.assertIn('linear_latest_state',report['evaluation_metrics'])
            self.assertEqual(receipt['scope'],'development_only')
            with self.assertRaisesRegex(ValueError,'replace'):
                package(dataset,root/'reference',root/'training.zip')


if __name__=='__main__':unittest.main()
