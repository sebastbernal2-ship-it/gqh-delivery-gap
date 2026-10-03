# Parallel work: how four people and their agents do not collide

Read this before you start editing. It exists because four people working at once is normal here,
and because a conflict found at merge time costs hours that nobody has.

## 1. The rule that actually prevents conflicts

**One writer per file. Decompose by concern, not by who wants to edit what.**

Branching does not fix concurrent edits. Git merges lines, not intentions. If two people edit one
file, a branch only postpones the collision.

So when three people are working on one feature, that is a signal to split the file, not to
schedule the edits. The same example, decomposed:

| Concern | Path | Writer |
|---|---|---|
| The logic: signals, rules, sizing | `src/strategy/` | one person |
| The contract between it and everything else | `src/strategy/INTERFACE.md` | shared, changes only by decision |
| The low-latency implementation of the same contract | `src/fast/` | a second person |
| Cluster integration, one directory per approach | `hpc/<approach>/` | a third person |

Nobody edits the same file. The only shared artifact is the interface, and it changes rarely, on
purpose, with a decision recorded in `docs/decisions.md`.

If a file genuinely cannot be split, then it needs **one owner** for the duration: that person
edits it, everyone else rebases onto their change and works around it, and ownership is written in
`OWNERS.md`.

## 2. Interfaces are the seam

Each component carries an `INTERFACE.md`: what goes in, what comes out, how it is called, what it
promises about latency or cost. That file is what lets two implementations proceed at the same time.

**Changing an interface is a decision.** It is the only change that breaks other people's in-flight
work, so it goes in `docs/decisions.md` with the date, and everyone rebases onto the new contract
rather than discovering it in a merge.

## 3. When to branch

| Situation | Do this |
|---|---|
| You own the paths, the change is small | Commit to `main` directly. This is the normal case |
| Your change is risky, or you want a review before it lands | Branch `feat/<handle>-<topic>` |
| A second person needs to touch the same file | Branch, and agree on one owner first |
| You want to try something that may be thrown away | Branch `try/<handle>-<topic>` |

Rules for a branch:

1. **Push it as soon as it exists.** `make claims` can only see pushed branches, and unpushed work
   is invisible work.
2. **Rebase onto main often**, at least every few hours: `git fetch && git rebase origin/main`.
3. **Merge the same day.** A branch that lives past a day becomes a rewrite, and the deadline here
   is measured in hours.
4. **Never leave a branch open overnight** without saying so in `docs/thinking/`.

## 4. Before you start, check

```
make claims      # every pushed branch: last commit, ahead, behind, files touched
make overlaps    # only the collisions, which is the part that costs hours
```

If your path collides with another branch, do not start typing. Pick one: split the file, wait, or
agree on a single owner for that file and let the other rebase after.

## 5. Two things at once on one machine

Agents must not share one checkout. Give each workstream its own directory:

```
make worktree NAME=vishnu-fast
```

That creates a sibling directory on its own branch off main. Work there, commit there, push from
there. Your main checkout stays usable for review and for other work.

## 6. How a change lands

1. `make sync` first. Always.
2. Work in the paths you own.
3. `git fetch && git rebase origin/main` before you commit, not after.
4. `make save M="what changed"` (add, commit, push).
5. If your change touched an interface, record it in `docs/decisions.md`.
6. If you learned something durable, it is already captured: the commit hook shares your memory.

Merging to `main` is a fast-forward after a rebase. There are no merge commits to untangle, because
nobody is asked to merge somebody else's long-lived branch.

## 7. The integration owner

One person is named in `OWNERS.md` as the integrator. They watch `make overlaps`, chase the branches
that have drifted, and decide the order changes land in when two of them are close.

When two branches genuinely must land together, the integrator rebases the second onto the first,
runs `make check`, and pushes. One person resolves it, once, instead of everyone resolving it
separately and differently.

## 8. If a conflict happens anyway

1. Rebase, do not merge: `git fetch && git rebase origin/main`.
2. Resolve in the file, keeping both intentions where both are real. A conflict is two people
   having a point.
3. Run `make check` and `make test` before you push.
4. Say in `docs/decisions.md` what the resolution chose, so the next person does not undo it.

Never force-push `main`. Never rewrite someone else's branch. Never resolve a conflict by deleting
the other person's work.

## 9. What a useful agent does with this file

- Before editing: check `make overlaps` and stay out of another branch's files.
- Before committing: rebase, then `make check`.
- If a task requires editing a file another writer owns, stop and report it instead of editing.
- If a task needs a new file, put it in the owning component's directory, not in the repo root.
