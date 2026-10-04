"""Slurm spool paths, durable outputs and failure ordering; no cluster access implied."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

COMPONENT=Path(__file__).resolve().parents[1]
ROOT=COMPONENT.parents[1]
SCRIPT=COMPONENT/'run-multisession.slurm'


class MultisessionJobTests(unittest.TestCase):
    def environment(self,root):
        fake=root/'python';log=root/'calls'
        fake.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$GQH_TEST_CALLS"\nif [[ "$1" == "multisession_panel.py" && "${GQH_TEST_FAIL:-}" == "1" ]]; then exit 9; fi\n')
        fake.chmod(0o755)
        return {**os.environ,'GQH_REPO_ROOT':str(ROOT),'GQH_TAPE_OBJECTS':str(root),
                'GQH_TAPE_RUN_DIR':str(root/'run'),'GQH_PYTHON':str(fake),'GQH_TEST_CALLS':str(log)}

    def test_spooled_job_from_unrelated_submission_directory(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);spool=root/'spooled';spool.write_bytes(SCRIPT.read_bytes());env=self.environment(root)
            result=subprocess.run(['bash',str(spool)],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            calls=(root/'calls').read_text().splitlines()
            self.assertEqual(len(calls),3)
            self.assertTrue(calls[1].startswith('multisession_panel.py'))
            self.assertTrue(calls[2].startswith('information_views.py'))
            self.assertIn('--epochs 3 --seed 20261003',calls[2])

    def test_missing_relative_and_wrong_root_fail_before_work(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            for key,value in [('GQH_REPO_ROOT',None),('GQH_TAPE_OBJECTS','relative'),('GQH_REPO_ROOT',str(root))]:
                env=self.environment(root)
                if value is None:env.pop(key)
                else:env[key]=value
                result=subprocess.run(['bash',str(SCRIPT)],cwd=root,env=env,capture_output=True)
                self.assertNotEqual(result.returncode,0)
                self.assertFalse((root/'calls').exists());self.assertFalse((root/'run').exists())

    def test_existing_run_is_preserved_and_adapter_failure_stops_training(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);env=self.environment(root);(root/'run').mkdir();(root/'run/keep').write_text('keep')
            result=subprocess.run(['bash',str(SCRIPT)],env=env,capture_output=True)
            self.assertNotEqual(result.returncode,0);self.assertFalse((root/'calls').exists())
            self.assertEqual((root/'run/keep').read_text(),'keep')
            env['GQH_TAPE_RUN_DIR']=str(root/'failed');env['GQH_TEST_FAIL']='1'
            result=subprocess.run(['bash',str(SCRIPT)],env=env,capture_output=True)
            self.assertEqual(result.returncode,9)
            self.assertNotIn('information_views.py',(root/'calls').read_text())


if __name__=='__main__':unittest.main()
