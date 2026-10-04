"""Retired mixed workload must never run raw preprocessing or classical baselines on HPG."""
from pathlib import Path
import subprocess
import tempfile
import unittest

class RetiredJobTests(unittest.TestCase):
    def test_old_job_fails_closed_from_spooled_directory(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'spool';p.write_bytes((Path(__file__).resolve().parents[1]/'run-multisession.slurm').read_bytes())
            result=subprocess.run(['bash',str(p)],cwd=t,capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertIn('retired',result.stderr)
            self.assertEqual(list(Path(t).iterdir()),[p])

if __name__=='__main__':unittest.main()
