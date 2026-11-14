---
description: Curate this session's learnings into the second brain (approval first)
---

Curate learnings into Albert's second brain at `~/Code/second-brain`. Extra focus from Albert: $ARGUMENTS

1. Read the vault's `AGENTS.md` (rules and budgets), `inbox.md`, `hot.md`, `me/profile.md`, `me/corrections.md`, and `projects/<current-repo>.md` if it exists.
2. Gather candidates from this session and from `inbox.md`:
   - Corrections or preferences Albert stated → `me/corrections.md` (or `me/profile.md` if stable and general).
   - Repo facts: purpose, stack, commands, gotchas, decisions → `projects/<repo>.md` (create from scratch if missing, add to `index.md`).
   - Cross-repo learnings, runbooks, snippets → `knowledge/<topic>.md`.
   - Where work stands now and next steps → rewrite `hot.md`.
3. Drop anything already captured, trivial, one-off, or sensitive (secrets, PII, claim/customer data).
4. Present the plan as a short list grouped by file: `+ add`, `~ update`, `- remove`. Ask Albert to approve all, some, or none with the question tool. Write nothing before approval.
5. Apply approved changes, respecting budgets. Remove curated lines from `inbox.md`.
6. Append one dated line to `log.md`, then commit and push in the vault: `git -C ~/Code/second-brain add -A && git -C ~/Code/second-brain commit -m "save: <short summary>" && git -C ~/Code/second-brain push`. If the push fails (offline, auth), keep the local commit and tell Albert.
7. Report what changed in one short list.
