#!/usr/bin/env python3
"""Filter tests for the shared memory bridge.

Run: python3 tests/test_memory_filter.py

The shared file is committed to a PUBLIC repo. Default deny: an entry is shared only
when it carries the share tag, and it must survive redaction.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from memory_filter import filter_entries, redact  # noqa: E402

SHARE = "gqh"

CASES = []


def case(name):
    def wrap(fn):
        CASES.append((name, fn))
        return fn
    return wrap


def entry(content, tags=(SHARE,), **extra):
    item = {"id": extra.pop("id", "mem_test"), "content": content, "tags": list(tags)}
    item.update(extra)
    return item


@case("untagged entry is dropped")
def _():
    out = filter_entries([entry("a fact", tags=["random"])], SHARE)
    assert out == [], out


@case("share-tagged entry is kept")
def _():
    out = filter_entries([entry("the mechanism is the delivery gap")], SHARE)
    assert len(out) == 1, out
    assert out[0]["content"] == "the mechanism is the delivery gap"


@case("project tag is accepted")
def _():
    out = filter_entries([entry("x", tags=["quanthacks"])], SHARE)
    assert len(out) == 1, out


# Credential shapes are assembled at runtime, never written literally. A public repo
# should not carry key-shaped strings, and both our scanner and GitHub's push protection
# flag them. Coverage is unchanged: the assembled string is realistic.
def fake(prefix: str, body: str = "a1b2c3d4e5f6g7h8i9j0") -> str:
    return prefix + body


def assign(name: str, value: str, sep: str = " = ") -> str:
    return name + sep + value


@case("api key assignments are dropped")
def _():
    for text in [
        assign("OPENAI_API_KEY", fake("sk-proj-"), "="),
        assign("client_secret", "abc12345"),
        assign("GITHUB_TOKEN", fake("ghp_", "abcdefghijklmnopqrstuvwxyz"), "="),
        fake("AIzaSy", "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6"),
        "-----BEGIN " + "OPENSSH PRIVATE KEY-----",
    ]:
        out = filter_entries([entry(text)], SHARE)
        assert out == [], (text, out)


@case("phrase mentions of secrets are kept, raw values are not")
def _():
    kept = filter_entries([entry("never commit api keys to a public repo")], SHARE)
    assert len(kept) == 1, kept
    dropped = filter_entries([entry(assign("api_key", "9f8e7d6c5b4a39281706", ": "))], SHARE)
    assert dropped == [], dropped


@case("home paths are rewritten")
def _():
    out = redact("data lives in /home/sebas/kun-agent-workspace/projects/quanthacks/data")
    assert "/home/sebas" not in out, out
    assert "<repo>/data" in out, out


@case("windows paths are rewritten")
def _():
    out = redact(r"cache at /mnt/c/Users/ortal/Downloads/imc4")
    assert "/mnt/c/Users" not in out, out
    assert "<win-home>" in out, out


@case("path tags are stripped from shared entries")
def _():
    out = filter_entries([entry("x", tags=[SHARE, "path:sebas", "path:projects"])], SHARE)
    assert out[0]["tags"] == [SHARE], out[0]["tags"]


@case("store scoped mode shares untagged entries")
def _():
    # When the store lives inside the repo, every entry in it is project scope by
    # construction, so capture does not need a human to tag anything.
    out = filter_entries([entry("untagged but in the project store", tags=[])],
                         SHARE, store_scoped=True)
    assert len(out) == 1, out
    assert out[0]["tags"] == [SHARE], out[0]["tags"]


@case("store scoped mode still drops secrets and still redacts")
def _():
    out = filter_entries([entry("token: " + "a1b2c3d4e5f6g7h8", tags=[])],
                         SHARE, store_scoped=True)
    assert out == [], out
    ok = filter_entries([entry("see /home/someone/thing", tags=[])], SHARE, store_scoped=True)
    assert "/home/someone" not in ok[0]["content"], ok


@case("output is stable and sorted by id")
def _():
    items = [entry("b", id="mem_2"), entry("a", id="mem_1")]
    first = [e["id"] for e in filter_entries(items, SHARE)]
    second = [e["id"] for e in filter_entries(list(reversed(items)), SHARE)]
    assert first == ["mem_1", "mem_2"], first
    assert first == second, (first, second)


def main() -> int:
    failures = []
    for name, fn in CASES:
        try:
            fn()
            print(f"ok   {name}")
        except AssertionError as exc:
            failures.append(name)
            print(f"FAIL {name}: {exc}")
    print(f"\n{len(CASES) - len(failures)}/{len(CASES)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
