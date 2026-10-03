# Claude Code: read AGENTS.md first

`AGENTS.md` is the single owner of the working rules for this repo. Read it at the start of
every session, before writing anything.

The parts that decide whether this repo works for four people:

1. `make sync` before you start. It pulls the team's work and loads their shared memory.
2. `memory/SHARED.md` is the team's memory. Read it.
3. Then read `docs/CURRENT.md`, `docs/brief.md`, `docs/decisions.md`, `OWNERS.md`.
4. Stay inside the paths your workstream owns. See `OWNERS.md`.
5. Every number the note quotes comes from `results/`. Regenerate, never hand-edit.
6. The out-of-sample window is opened once, by its owner, and reported as it lands.
7. Never commit credentials, absolute local paths, or anything under `data/`.

Capture is mechanical in this repo. `hippo hook install claude-code` wires the per-machine
wrapper for this harness, and `.githooks/pre-commit` refreshes and stages the shared memory on
every commit. See `docs/memory.md`.

<!-- hippo:start -->
## Project Memory (Hippo)

Pinned rules and recent writes auto-inject at every prompt via the installed
UserPromptSubmit hook; never re-run that part manually. At the START of a
task (not per prompt), additionally load task-specific context: git-aware
recall over the full store that per-prompt injection does not cover. Also
run it if the hook is not installed:
```bash
hippo context --auto --budget 1500
```

When you learn something important:
```bash
hippo remember "<lesson>"
```

When you hit an error or discover a gotcha:
```bash
hippo remember "<what went wrong and why>" --error
```

After completing work successfully:
```bash
hippo outcome --good
```

When the user ends the session, capture a brief summary:
```bash
hippo capture --stdin <<< '<decisions, errors, lessons — 2-5 bullets>'
```
<!-- hippo:end -->
