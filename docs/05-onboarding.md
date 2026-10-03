# Onboarding: a teammate on a new machine

Ten minutes. The repo does most of it.

## 1. Clone and bootstrap

```
git clone https://github.com/sebastbernal2-ship-it/gqh-delivery-gap.git
cd gqh-delivery-gap
make bootstrap
```

`bootstrap` checks tooling, builds the virtual environment, enables the commit hook, wires the
harness wrappers it can safely wire, loads the team's shared memory, and prints the protocol.

## 2. Know which file your agent reads

| Harness | File it reads | Notes |
|---|---|---|
| pi, Codex, OpenCode, OpenClaw | `AGENTS.md` | the single owner of the working rules |
| Claude Code | `CLAUDE.md` | points at `AGENTS.md` |
| Cursor | `.cursorrules` | points at `AGENTS.md` |

All three are committed. If your agent does not mention the repo rules at the start of a session,
open your harness file and read it yourself, then tell me, because that is a bug.

## 3. Start a session

```
make sync        # pulls the team's work and loads their shared memory
```

Then read, in order: `memory/SHARED.md`, `docs/00-brief.md`, `docs/01-idea.md`,
`docs/02-system.md`, `docs/03-decisions.md`, `OWNERS.md`.

## 4. Work

- Stay inside the paths your workstream owns. `OWNERS.md` is the authority.
- Durable facts go in `docs/`, at their owner, never in chat. One owner per fact.
- Every number the note quotes comes from `results/`. Regenerate, never hand-edit.
- The out-of-sample window is opened once, by its owner, and reported as it lands.

Capture is automatic. You do not need to remember a memory command:

- `make remember M="what you learned"` if you want to write one down deliberately.
- `.githooks/pre-commit` refreshes and stages the shared memory on every commit.
- `make share` refreshes it now; `make save M="..."` commits and pushes.
- `make schedule` adds an unattended share every 15 minutes, if you want belt and braces.

## 5. Check the plumbing

```
make doctor
```

Reports three things: whether this project's memory is isolated to this repo or bleeding into a
shared store, whether every harness file carries the protocol, and whether capture and the shared
memory are wired. Healthy output ends with `result: healthy`.

If your machine has several projects, keep each one's memory in its own store. A project's store
lives at its repo root. Writing memories from a parent directory puts them somewhere other
projects read, which is how one project's notes show up in another project's session.

## 6. Where to ask

Write your question in the repo, do not keep it in chat: `docs/reviews/TEMPLATE.md` for a critique
of the idea or the plan, and `docs/03-decisions.md` for anything settled.
