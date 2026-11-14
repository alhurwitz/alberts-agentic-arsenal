---
description: Rebuild the second brain index.md from disk and fix link problems
---

Re-index Albert's second brain at `~/Code/second-brain`. Extra focus from Albert: $ARGUMENTS

Read the vault's `AGENTS.md` first for layout and writing rules.

## Steps

1. List every page: `git -C ~/Code/second-brain ls-files '*.md'` plus untracked `*.md` under `me/`, `projects/`, `knowledge/` (skip `AGENTS.md`, `index.md`, `log.md`).
2. Rebuild `index.md` keeping its existing sections (`## Me`, `## Working state`, `## Projects`, `## Knowledge`, plus any others already there). Add missing pages to the right section, drop entries whose file is gone, sort each section alphabetically. Keep the entry format `- [[path/without-ext]]`.
3. Fix links across all pages:
   - Broken `[[wikilinks]]` (target missing): repoint to the renamed/moved page if one obviously matches, otherwise remove the brackets and keep the text.
   - Ignore `[[` inside backticks or code (e.g. JSON in `knowledge/nebula.md`).
4. Project pages: any `projects/*.md` missing `paths:` frontmatter gets it, using `~/Code/<name>` if that folder exists; otherwise list it for Albert.
5. Mechanical fixes only. Do not rewrite content, merge pages, or delete pages; report those as suggestions for `/brain-lint`.
6. Compute changes first and present them as one line per change (`path: problem → fix`). Ask Albert to approve all, some, or none with the question tool. Write nothing before approval.
7. After applying: append one dated line to `log.md`, then `git -C ~/Code/second-brain add -A && git -C ~/Code/second-brain commit -m "reindex: <short summary>" && git -C ~/Code/second-brain push`. If push fails, keep the local commit and say so.

If nothing needs changing, say so in one line and stop.
