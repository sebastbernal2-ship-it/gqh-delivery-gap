# Ownership

One writer per path. Two writers on one file is the only way this repo breaks.

## The four of us

| GitHub | Role |
|---|---|
| sebastbernal2-ship-it | repo owner, has push |
| aidanq06 | invited, write permission |
| vshnu1 | invited, write permission |
| lucyrunner | invited, write permission |

An invitation is not access until it is accepted. Each person accepts the GitHub invite, then runs
`make bootstrap` once and `make doctor` to confirm.

## Who owns what

One writer per path, and the paths get named when the direction lands. Until a row has a name,
nobody writes to that path.

| Path | Person |
|---|---|
| `docs/inbox/vishnu-2026-10-03/` | Vishnu, via his documentation agent; conversation handoff and proposals |
| `docs/thinking/vishnu-2026-10-03.md` | Vishnu, via his documentation agent; reconstructed conversation history |
| `docs/writing/style.md` | Vishnu, via his documentation agent; initial writing conventions |
| `.cursor/rules/gqh-context.mdc` | Vishnu, via his documentation agent; handoff routing |

Add a row per area of work as soon as it exists. Do not pre-create rows for work nobody has
started.

These assignments cover the documentation requested in Vishnu's chat. They do not assign
implementation, OOS access, or strategy approval to that agent. Claim a concrete component here
before starting it; do not assume a proposed architecture is already implemented.
