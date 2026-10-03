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

Then read, in order: `memory/SHARED.md`, `docs/CURRENT.md`, `docs/brief.md`,
`docs/decisions.md`, `OWNERS.md`.

The idea is expected to move, often. `docs/CURRENT.md` is regenerated from the thesis ledger, so
it is always the live position and it is never out of date. Do not rewrite a snapshot in
`docs/history/`: write a new thesis and supersede it.

## 4. Where things go

One table answers this. It is in the root `README.md`, section "Where does my thing go". The short
version: drafts and thinking have no rules, claims go in `docs/theses/`, code goes in `src/<component>/`
with its own README, cluster jobs go in `hpc/<approach>/` with its own README.

`make check` enforces the parts that matter: the root stays a short list, and every area of code or
compute has a README.

## 5. Work

- Stay inside the paths your workstream owns. `OWNERS.md` is the authority.
- Durable facts go in `docs/`, at their owner, never in chat. One owner per fact.
- Every number the note quotes comes from `results/`. Regenerate, never hand-edit.
- The out-of-sample window is opened once, by its owner, and reported as it lands.

Capture is automatic. You do not need to remember a memory command:

- `make remember M="what you learned"` if you want to write one down deliberately.
- `.githooks/pre-commit` refreshes and stages the shared memory on every commit.
- `make share` refreshes it now; `make save M="..."` commits and pushes.

## 6. Before you edit anything

```
make sync        # pull, and load the team's memory
make claims      # who else is in flight, and on which files
```

If a pushed branch already touches the file you are about to edit, stop and read
`docs/workflow.md`. That file is short and it is the difference between parallel work and four
people rewriting each other. If you need your own checkout: `make worktree NAME=<your-name>`.

## 7. Check the plumbing

```
make doctor
```

Reports three things: whether this project's memory is isolated to this repo or bleeding into a
shared store, whether every harness file carries the protocol, and whether capture and the shared
memory are wired. Healthy output ends with `result: healthy`.

If your machine has several projects, keep each one's memory in its own store. A project's store
lives at its repo root. Writing memories from a parent directory puts them somewhere other
projects read, which is how one project's notes show up in another project's session.

## 8. Where to ask

Draft first, formalise later. `docs/inbox/` takes anything with no rules. When a claim is real
enough to trade on, it becomes `docs/theses/<id>.md` plus one line in the ledger, and `make current`
publishes it to everyone. `docs/reviews/TEMPLATE.md` is for a critique, `docs/decisions.md` for
anything settled.
