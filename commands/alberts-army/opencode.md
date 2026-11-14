---
description: Run a task with a chain of command: Albert's general commands officers and soldiers, up to 5 ranks deep
---

Run this task as an army. You are the General.

1. Size the task and pick a depth: 1 for a few parallel pieces, more only when units split again (max 5).
2. Call `army_mobilize` with that `maxDepth` (and `maxAgents` only if the task sets a budget; default 50).
3. Create your base worktree with an ABSOLUTE path from the current branch (add `.army/` to `.git/info/exclude`):
   `git -C <repo abs> worktree add -b <task-slug> <repo abs>/.army/<task-slug>`
4. Follow the `army-officer` playbook (the `army-officer` agent definition): set per-team budgets (`TROOPS: <n>` as first line of each officer prompt), dispatch, then `army_wait` instead of ending your turn.
5. Merge, clean up, and run `army_check` until empty.
6. Report final branch, summary, files, checks, blockers, plus `army_status` totals (agents, elapsed, budget used). Albert can run `alberts-army-status` in a terminal (or `!alberts-army-status`) to see the tree without a model call.

Task: $ARGUMENTS
