# Second Brain: Vault Rules

Personal knowledge vault for your coding agents. Plain Markdown, Obsidian-compatible, git-tracked.
Agents read it to know who you are and where work left off, and write back what they learn.

## Layout

| Path | Purpose | Loaded |
|---|---|---|
| `me/profile.md` | Who you are, stack, preferences, how he likes to work | Every session |
| `me/corrections.md` | Things you told an agent to do or stop doing | Every session |
| `hot.md` | Where work left off, open threads | Every session |
| `inbox.md` | Raw append-only captures awaiting `/save` | On demand |
| `projects/<repo>.md` | One page per repo: purpose, stack, commands, gotchas, decisions | Auto, when the session's directory matches (OpenCode `second-brain.ts` plugin) |
| `knowledge/<topic>.md` | Durable learnings, runbooks, snippets not tied to one repo | On demand |
| `index.md` | Map of every page | On demand |
| `log.md` | Dated change log of the vault | On demand |

## Budgets

Files loaded every session cost tokens on every request. Keep them tight:

- `me/profile.md`: under 60 lines.
- `me/corrections.md`: under 40 bullets. Merge or promote into profile when it grows.
- `hot.md`: under 25 lines. Overwrite, don't append. Drop finished threads.

## Writing rules

- One fact per bullet. Concrete over vague: "uses `uv run pytest -x`" not "uses pytest".
- Update an existing bullet instead of adding a near-duplicate.
- Date corrections and decisions: `(YYYY-MM-DD)`.
- Link pages with `[[projects/my-repo]]`-style wikilinks.
- New page: add it to `index.md`.
- New project page: start it with `paths:` frontmatter listing its workspace folders (e.g. `- ~/Code/my-repo`) so it is injected automatically. Without it, a page only matches a folder of the same name.
- Project pages are loaded every request in their repo: keep each under ~5k characters.
- Every curation pass: add one dated line to `log.md`.
- Never store secrets, tokens, passwords, PII, or customer data. Reference where a secret lives, never its value.
