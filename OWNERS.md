# Ownership

One writer per path. Two writers on one file is the only way this repo breaks.

## The four of us

| GitHub | Role |
|---|---|
| sebastbernal2-ship-it | repo owner, maintains the shell (workflow, memory, gates) |
| aidanq06 | invited, write permission |
| vshnu1 | invited, write permission |
| lucyrunner | invited, write permission |

An invitation is not access until it is accepted. Each person accepts the GitHub invite, then runs
`make bootstrap` once and `make doctor` to confirm.

## Claimed paths

One table. A path appears once, with one person.

| Path | Person | What it is |
|---|---|---|
| `scripts/`, `tests/`, `Makefile`, `.githooks/`, `docs/workflow.md`, `docs/memory.md`, `docs/onboarding.md`, `docs/decisions.md` | sebastbernal2-ship-it | The collaboration shell: sync, memory bridge, gates |
| `docs/brief.md` | nobody | The track's own rules. Frozen, so it needs no owner |
| `docs/inbox/vishnu-2026-10-03/`, `docs/thinking/vishnu-2026-10-03.md`, `docs/writing/style.md`, `.cursor/rules/gqh-context.mdc` | vshnu1 | Equity-first research handoff, provider audit, data plan, writing conventions |
| `docs/inbox/aidan-2026-10-03/`, `docs/thinking/aidan-2026-10-03.md` | aidanq06 | Strategy specification, reasoning, implementation contracts, advanced-method research |
| `hpc/README.md`, `hpc/setup/` | lucyrunner | HiPerGator routing, account access and environment setup |

## Unclaimed

Empty until someone claims it. Do not build in an unclaimed path.

| Area | Waiting for |
|---|---|
| `src/<component>/` | Whoever implements the first component, after it is claimed here |
| `hpc/<approach>/` | Each compute approach, claimed before the job is written |
| `results/` | Whoever produces the first number the note quotes |
| A thesis in `docs/theses/` | Whoever promotes a proposal into a claim |

## Rules

1. **Claim before you build.** Add your row to the table above in the same commit that creates the
   path. A path with no owner is a path nobody should touch.
2. **Documentation ownership is not implementation authority.** Owning a handoff folder does not
   assign you the component it proposes, the out-of-sample split, or strategy approval.
3. **Open the out-of-sample window** only if your row explicitly says so. Nobody's does yet.
4. **Keep this file one table.** Do not append a second section with its own table. Add a row.
5. `make check` validates this file: one row per path, no duplicate claims, every person in the
   roster, and every claimed path that is not a future placeholder must exist.
