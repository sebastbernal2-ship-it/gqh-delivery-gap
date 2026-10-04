from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runtime_provenance import git_revision


class RuntimeProvenanceTests(unittest.TestCase):
    def test_zip_directory_without_git_is_explicitly_unknown(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertIsNone(git_revision(temp))

    def test_missing_git_executable_does_not_break_training_report(self):
        with patch('runtime_provenance.subprocess.run',side_effect=FileNotFoundError):
            self.assertIsNone(git_revision('.'))


if __name__=='__main__':unittest.main()
