"""Wrapper regression tests; the q stub is NOT an HDB/runtime validation."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

COMPONENT = Path(__file__).resolve().parents[1]
REPO = COMPONENT.parents[1]


class JobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="kdb jobs ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.blue = self.root / "blue"
        self.blue.mkdir()
        self.input = self.blue / "bars.tsv"
        subprocess.run([sys.executable, str(COMPONENT / "scripts/make_fixture.py"),
                        "--output", str(self.input)], check=True)
        body = self.input.read_bytes().split(b"\n", 1)[1]
        self.manifest = {"rows": 3, "sha256_tsv_body": hashlib.sha256(body).hexdigest()}
        self.manifest_path = Path(str(self.input) + ".manifest.json")
        self.manifest_path.write_text(json.dumps(self.manifest))
        self.output = self.blue / "hdb" / "v001"
        self.receipt = self.output.with_suffix(".receipt.json")
        self.calls = self.root / "q-calls.jsonl"
        self.q = self.root / "fake q"
        self.q.write_text("#!/usr/bin/env python3\n"
                          "import json, os, sys\n"
                          "from pathlib import Path\n"
                          "assert Path(sys.argv[2]).is_file(), sys.argv\n"
                          "with open(os.environ['TEST_Q_CALLS'], 'a') as f:\n"
                          "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                          "sys.exit(int(os.environ.get('TEST_Q_EXIT', '0')))\n")
        self.q.chmod(0o755)
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(("GQH_", "HPG_", "SLURM_", "TEST_Q_"))}
        self.env.update(Q_BIN=str(self.q), HPG_BLUE_DIR=str(self.blue),
                        GQH_REPO_ROOT=str(REPO), GQH_KDB_INPUT_TSV=str(self.input),
                        GQH_KDB_OUTPUT_DIR=str(self.output), TEST_Q_CALLS=str(self.calls),
                        SLURM_JOB_ID="12345", SLURM_SUBMIT_DIR=str(self.root))

    def run_script(self, path, spool=False):
        if spool:
            dest = self.root / "spool" / "job12345" / "slurm_script"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)
            path = dest
        return subprocess.run(["bash", str(path)], env=self.env, cwd=self.root,
                              text=True, capture_output=True)

    def build(self):
        return self.run_script(COMPONENT / "scripts/build_hdb.sh")

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_receipt_records_success_and_provenance(self):
        self.assert_success(self.build())
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual(receipt["rows"], 3)
        self.assertEqual(receipt["sha256_tsv_body"], self.manifest["sha256_tsv_body"])
        self.assertEqual(receipt["hdb_path"], str(self.output))
        self.assertEqual(receipt["slurm_job_id"], "12345")
        commit = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
        self.assertEqual(receipt["git_commit"], commit)
        self.assertIn("independent HDB restore validation still required", receipt["build_status"])
        args = json.loads(self.calls.read_text())
        self.assertEqual(args[-2:], ["-expected", "3"])

    def test_spooled_build_from_unrelated_submission_directory(self):
        self.assert_success(self.run_script(COMPONENT / "slurm/build-bars.slurm", spool=True))
        self.assertTrue(self.receipt.exists())

    def test_spooled_smoke_calls_loader_then_validator(self):
        self.assert_success(self.run_script(COMPONENT / "slurm/smoke.slurm", spool=True))
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual([Path(call[1]).name for call in calls],
                         ["build_bars_hdb.q", "smoke_check.q"])

    def test_wrappers_reject_missing_relative_or_wrong_repo(self):
        for script in ("build-bars.slurm", "smoke.slurm"):
            for value in (None, "relative/repo", str(self.blue)):
                with self.subTest(script=script, root=value):
                    self.env.pop("GQH_REPO_ROOT", None)
                    if value is not None:
                        self.env["GQH_REPO_ROOT"] = value
                    result = self.run_script(COMPONENT / "slurm" / script, spool=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("GQH_REPO_ROOT", result.stderr)
                    self.assertFalse(self.calls.exists())

    def test_checksum_failure_has_no_output_or_q_call(self):
        self.input.write_bytes(self.input.read_bytes().replace(b"1200", b"1201"))
        result = self.build()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SHA-256", result.stderr)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.calls.exists())

    def test_row_count_failure_has_no_output(self):
        self.manifest["rows"] = 4
        self.manifest_path.write_text(json.dumps(self.manifest))
        self.assertNotEqual(self.build().returncode, 0)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.calls.exists())

    def test_missing_manifest_has_no_output(self):
        self.manifest_path.unlink()
        self.assertNotEqual(self.build().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_loader_failure_never_writes_success_receipt(self):
        self.env["TEST_Q_EXIT"] = "17"
        result = self.build()
        self.assertEqual(result.returncode, 17, result.stderr)
        self.assertFalse(self.receipt.exists())
        # Preserve partial output for investigation; retries require a new version.
        self.assertTrue(self.output.is_dir())
        self.env.pop("TEST_Q_EXIT")
        self.assertNotEqual(self.build().returncode, 0)
        self.assertEqual(len(self.calls.read_text().splitlines()), 1)

    def test_existing_output_and_receipt_are_preserved(self):
        self.assert_success(self.build())
        before = self.receipt.read_bytes()
        self.assertNotEqual(self.build().returncode, 0)
        self.assertEqual(self.receipt.read_bytes(), before)
        self.assertEqual(len(self.calls.read_text().splitlines()), 1)

    def test_receipt_alone_blocks_reuse(self):
        self.receipt.parent.mkdir(parents=True)
        self.receipt.write_text("existing receipt")
        self.assertNotEqual(self.build().returncode, 0)
        self.assertEqual(self.receipt.read_text(), "existing receipt")
        self.assertFalse(self.output.exists())

    def test_individual_shell_syntax(self):
        for script in sorted((REPO / "hpc").rglob("*.slurm")):
            with self.subTest(script=script.name):
                result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
                self.assert_success(result)


if __name__ == "__main__":
    unittest.main()
