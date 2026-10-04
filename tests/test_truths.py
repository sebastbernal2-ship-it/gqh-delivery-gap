#!/usr/bin/env python3
"""Tests for the truth ledger validator.

Run: python3 tests/test_truths.py

The ledger records what we know about the world, with the evidence and the scope. The validator
enforces the rules that keep it auditable:

  structure    every entry carries a title, a statement, evidence, a scope and a consequence
  sequence     ids run T1..Tn with no gap and no repeat, because the ledger grows at the tail
  links        every path an entry cites resolves, and a glob matches at least once
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_truths import problems  # noqa: E402

FILES = {"results/a.csv", "docs/plan/x.md"}


def exists(token):
    if "*" in token:
        prefix, suffix = token.split("*", 1)
        return any(name.startswith(prefix) and name.endswith(suffix) for name in FILES)
    return token in FILES


def truth(number=1, title="A truth", statement="the statement", evidence="`results/a.csv`",
          scope="the scope", consequence="the consequence"):
    return (f"## T{number}. {title}\n\n"
            f"**Statement**: {statement}.\n"
            f"**Evidence**: {evidence}.\n"
            f"**Scope**: {scope}.\n"
            f"**Consequence**: {consequence}.\n\n")


def ledger(*entries):
    return "# The truth ledger\n\n" + "".join(entries) + "# Where the truths point\n\nprose\n"


def main() -> int:
    failures = []

    def check(name, got, expect_empty=True):
        if (len(got) == 0) != expect_empty:
            failures.append(name)
            print(f"FAIL {name}: {got}")
        else:
            print(f"ok   {name}")

    check("a well formed entry passes", problems(ledger(truth()), exists=exists))
    check("two sequential entries pass",
          problems(ledger(truth(), truth(number=2)), exists=exists))
    check("an empty ledger fails",
          problems("# The truth ledger\n\nprose only\n", exists=exists), expect_empty=False)

    check("a missing field fails",
          problems(ledger(truth().replace("**Scope**: the scope.\n", "**Scope**:\n")),
                  exists=exists), expect_empty=False)
    check("an empty field fails",
          problems(ledger(truth().replace("**Consequence**: the consequence.\n", "**Consequence**:\n")),
                  exists=exists), expect_empty=False)
    check("fields out of order fail",
          problems(ledger(truth().replace("**Scope**: the scope.\n**Consequence**: the consequence.",
                                          "**Consequence**: the consequence.\n**Scope**: the scope.")),
          exists=exists), expect_empty=False)

    check("a repeated id fails",
          problems(ledger(truth(), truth(number=1)), exists=exists), expect_empty=False)
    check("a gap in the ids fails",
          problems(ledger(truth(number=1), truth(number=3)), exists=exists), expect_empty=False)

    check("a broken link fails",
          problems(ledger(truth(evidence="`results/missing.csv`")), exists=exists),
          expect_empty=False)
    check("a matching glob passes",
          problems(ledger(truth(evidence="`results/a*.csv`")), exists=exists))
    check("an unmatched glob fails",
          problems(ledger(truth(evidence="`results/z*.csv`")), exists=exists), expect_empty=False)
    check("a backticked command is not a link",
          problems(ledger(truth(evidence="`make check` says so")), exists=exists))
    check("a brace shorthand is not a link",
          problems(ledger(truth(evidence="`results/a-{one,two}.csv`")), exists=exists))

    if failures:
        print(f"\n{len(failures)} failures")
        return 1
    print("\ntruth ledger validator: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
