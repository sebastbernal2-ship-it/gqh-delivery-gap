"""Execute the actual job payload locally; no Slurm/modules/cluster access is claimed."""
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import tempfile
import unittest

COMPONENT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("g++"), "g++ required for native parity integration")
class JevLikeJobTests(unittest.TestCase):
    def test_spooled_job_trains_exports_and_verifies_native_probabilities(self):
        with tempfile.TemporaryDirectory(prefix="jevlike job ") as temp:
            root = Path(temp)
            stub = root / "bin"
            stub.mkdir()
            module = stub / "module"
            module.write_text("#!/bin/sh\nexit 0\n")
            module.chmod(0o755)
            # Use this test interpreter, without relying on a system `python` alias.
            python = stub / "python"
            python.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + ' "$@"\n')
            python.chmod(0o755)
            spool = root / "slurm_script"
            shutil.copyfile(COMPONENT / "run-jevlike.slurm", spool)
            env = dict(os.environ)
            env.pop("PYTHONPATH", None)
            env.update(PATH=str(stub) + os.pathsep + env["PATH"],
                       TMPDIR=str(root), SLURM_JOB_ID="regression", SLURM_CPUS_PER_TASK="2")
            result = subprocess.run(["bash", str(spool)], cwd=COMPONENT, env=env,
                                    text=True, capture_output=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            # Evaluation/export print multiline JSON; the final verifier emits one JSON line.
            parity = json.loads(result.stdout.strip().splitlines()[-1])
            self.assertEqual(parity["result"], "parity_ok")
            self.assertEqual(parity["synthetic_cases"], 4)
            self.assertLessEqual(parity["maximum_absolute_probability_error"], parity["tolerance"])
            for filename in ("tiny.pt", "tiny.jvlk", "jevlike-predict-cpp"):
                self.assertTrue((root / "jevlike-regression" / filename).is_file())


if __name__ == "__main__":
    unittest.main()
