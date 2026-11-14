## Second brain

The user's knowledge vault is at `{{SECOND_BRAIN_DIR}}`. Its `AGENTS.md` describes the layout and writing rules.

- At the start of a session, read `me/profile.md`, `me/corrections.md` and `hot.md` from the vault (OpenCode loads them automatically) and follow them.
- The current repo's project page (`projects/<name>.md`) is injected automatically in OpenCode when one matches; in other harnesses read it if it exists. Read other pages on demand.
- When the user corrects you, states a preference, or you discover a durable non-obvious fact (command, gotcha, decision), append one line to `{{SECOND_BRAIN_DIR}}/inbox.md`: `- (YYYY-MM-DD) [repo or topic] fact`. Do it silently; no other vault edits outside `/save`.
- Never write secrets, tokens, passwords, PII, or customer data to the vault.
