#!/usr/bin/env python3
"""Tests for the path checker.

Run: python3 tests/test_paths.py

The checker has one job: notice when a document points at a repo file that is gone. It must
not fire on prose that merely looks path-shaped, or on the path part of a URL, because a gate
that cries wolf gets switched off.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_paths import missing, references, strip_foreign_fences  # noqa: E402


def main() -> int:
    failures = []

    def check(name, got, want):
        if got != want:
            failures.append(name)
            print(f"FAIL {name}:\n  got  {got}\n  want {want}")
        else:
            print(f"ok   {name}")

    check("a real file reference is kept",
          references("see docs/workflow.md for the rules"), ["docs/workflow.md"])
    check("a directory reference with a trailing slash is kept",
          references("read everything in docs/thinking/"), ["docs/thinking/"])
    check("a URL path fragment is ignored",
          references("see https://example.com/docs/about-market-data-api for details"), [])
    check("bare prose that looks path-shaped is ignored",
          references("outputs implement the same declared data/result contracts"), [])
    # A placeholder is not a missing file. What is left of it is a real directory, and
    # verifying that directory exists is worth keeping, so that is the expected result.
    check("a placeholder leaves only its directory reference",
          references("write docs/theses/<id>.md"), ["docs/theses/"])
    check("two references on one line are both found",
          references("`docs/brief.md` and `docs/decisions.md`"),
          ["docs/brief.md", "docs/decisions.md"])

    # A fenced block tagged as belonging to another checkout is that repo's business, not ours.
    text = ("run these in the sibling checkout:\n"
            "```sh foreign-repo=algoterminal-data\n"
            "python scripts/validate_quant_graph.py\n"
            "```\n"
            "and this one is ours: `docs/brief.md`\n")
    check("a foreign repo fence is skipped, the rest is checked",
          references(strip_foreign_fences(text)), ["docs/brief.md"])
    check("an untagged fence is still checked",
          references(strip_foreign_fences("```sh\npython scripts/nope.py\n```")),
          ["scripts/nope.py"])

    tracked = ["results/README.md", "scripts/consumer.py"]
    contract = "generated-path: results/example.csv"
    check("declared output can be absent before generation",
          missing(tracked, {"results/README.md": contract, "scripts/consumer.py": "results/example.csv"}), [])
    check("undeclared output typos still fail",
          len(missing(tracked, {"results/README.md": contract, "scripts/consumer.py": "results/exmaple.csv"})), 1)
    check("output declarations cannot hide missing source files",
          len(missing(tracked, {"results/README.md": "generated-path: scripts/missing.py"})), 1)
    print(f"\n{11 - len(failures)}/11 passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
