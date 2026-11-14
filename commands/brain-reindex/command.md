---
description: Rebuild the second brain index.md from disk and fix link problems
---

Re-index the user's second brain at `{{SECOND_BRAIN_DIR}}`. Extra focus from the user: $ARGUMENTS

Read the vault's `AGENTS.md` first for layout and writing rules.

## Steps

1. List every page: `git -C {{SECOND_BRAIN_DIR}} ls-files '*.md'` plus untracked `*.md` under `me/`, `projects/`, `knowledge/` (skip `AGENTS.md`, `index.md`, `log.md`).
2. Rebuild `index.md` keeping its existing sections (`## Me`, `## Working state`, `## Projects`, `## Knowledge`, plus any others already there). Add missing pages to the right section, drop entries whose file is gone, sort each section alphabetically. Keep the entry format `- [[path/without-ext]]`.
3. Fix links across all pages:
   - Broken `[[wikilinks]]` (target missing): repoint to the renamed/moved page if one obviously matches, otherwise remove the brackets and keep the text.
   - Ignore `[[` inside backticks or code.
4. Project pages: any `projects/*.md` missing `paths:` frontmatter gets it, using the repo's folder if one obviously matches; otherwise list it for the user.
5. Mechanical fixes only. Do not rewrite content, merge pages, or delete pages; report those as suggestions for `/brain-lint`.
6. Compute changes first and present them as one line per change (`path: problem → fix`). Ask the user to approve all, some, or none with the question tool. Write nothing before approval.
7. After applying: append one dated line to `log.md`, then `git -C {{SECOND_BRAIN_DIR}} add -A && git -C {{SECOND_BRAIN_DIR}} commit -m "reindex: <short summary>" && git -C {{SECOND_BRAIN_DIR}} push`. If push fails, keep the local commit and say so.

If nothing needs changing, say so in one line and stop.
