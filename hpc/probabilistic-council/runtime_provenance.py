"""Source provenance for Git checkouts and archived deployments; never invent a revision."""
from pathlib import Path
import subprocess


def git_revision(directory):
    try:
        result=subprocess.run(['git','rev-parse','HEAD'],cwd=Path(directory),
                              capture_output=True,text=True,timeout=5,check=False)
    except (OSError,subprocess.TimeoutExpired):
        return None
    value=result.stdout.strip()
    return value if result.returncode==0 and len(value)==40 and all(c in '0123456789abcdef' for c in value) else None
