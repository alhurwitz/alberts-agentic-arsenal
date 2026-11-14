---
description: Health-check the second brain and propose cleanups (approval first)
---

Lint the user's second brain at `{{SECOND_BRAIN_DIR}}`. Extra focus from the user: $ARGUMENTS

Read the vault's `AGENTS.md` first for layout, budgets, and writing rules. Use shell tools (`wc`, `grep`, `rg`, `git log`) for mechanical checks; only read full pages where a check needs judgment.

## Checks

1. **Budgets**: line counts of `me/profile.md` (≤60), `me/corrections.md` (≤40 bullets), `hot.md` (≤25). Over budget → propose merges, promotions (correction → profile), or removals.
2. **Inbox backlog**: uncurated lines in `inbox.md`. If any, recommend `/save` rather than curating here.
3. **Stale**: `hot.md` threads and dated bullets older than 60 days; pages untouched for 180+ days (`git log -1 --format=%cs -- <file>`). Propose drop, archive to `knowledge/archive/`, or confirm still true.
4. **Dead references**: `projects/<repo>.md` whose repo no longer exists on disk; commands or paths in pages that no longer exist on disk.
5. **Duplicates and contradictions**: same fact in multiple pages, or pages that disagree (including profile vs corrections). Propose one canonical home plus links.
6. **Links**: broken `[[wikilinks]]`; orphan pages not in `index.md` and not linked from anywhere; `index.md` entries pointing at missing files.
7. **Safety**: anything resembling secrets, tokens, passwords, emails of others, customer data. Flag these first, as highest severity.
8. **Shape**: pages missing a title, vague bullets ("uses pytest") that should be concrete, pages over ~200 lines that should split.

## Output

Report findings as one line each, grouped by severity (safety → budget → stale/dead → duplicates → links → shape):
`path: problem → proposed fix`

If nothing is wrong, say so in one line and stop.

Otherwise ask the user which fixes to apply with the question tool (all, pick, none). Write nothing before approval. After applying: append one dated line to `log.md`, then `git -C {{SECOND_BRAIN_DIR}} add -A && git -C {{SECOND_BRAIN_DIR}} commit -m "lint: <short summary>" && git -C {{SECOND_BRAIN_DIR}} push`. If push fails, keep the local commit and say so.
