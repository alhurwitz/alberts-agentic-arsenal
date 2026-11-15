# alberts-agentic-arsenal

One setup for every coding agent: skills, agents, commands, hooks and MCP, installed into OpenCode, Claude Code, Copilot and Codex.

Everything lives here once. `install.py` puts it where each harness looks. Items are shared by default; a harness gets its own variant only where it needs one.

## Quick start

You need Python 3.9+ and curl. Nothing else is required; optional pieces download what they need.

```sh
curl -fsSL https://raw.githubusercontent.com/alhurwitz/alberts-agentic-arsenal/main/install.sh | bash
# or skip the questions:
curl -fsSL https://raw.githubusercontent.com/alhurwitz/alberts-agentic-arsenal/main/install.sh | bash -s -- claude --with army
```

This downloads the repo to `~/.local/share/agentic-arsenal` (set `ARSENAL_DIR` to change it) and runs `install.py` from there. Run the same command again to update.

To hack on the arsenal, clone it instead and run `./install.py all` from the checkout. `install.sh` also uses an existing git checkout at `ARSENAL_DIR` as-is.

With no harness named, the installer shows a checklist of harnesses (the ones it finds are pre-checked; arrow keys, space, enter). The first run also shows a checklist of the optional modules (below), asks for paths with tab completion, and remembers your answers in `~/.config/agentic-arsenal/config.json`. Output is colored on a terminal; set `NO_COLOR=1` to turn that off. Change them later with `./install.py all --reconfigure`, or per run with `--with <module>` / `--without <module>`. Preview any run with `--dry-run`.

Then restart your agent.

To update: re-run the curl command (or `git pull && ./install.py all` in a clone).

### Uninstall

```sh
curl -fsSL https://raw.githubusercontent.com/alhurwitz/alberts-agentic-arsenal/main/install.sh | bash -s -- --uninstall
# or just some harnesses:
curl -fsSL https://raw.githubusercontent.com/alhurwitz/alberts-agentic-arsenal/main/install.sh | bash -s -- --uninstall codex copilot
```

From a clone: `./install.py --uninstall [harness...]`. Add `--dry-run` to preview.

Uninstall removes only what the installer put there:
- links into the repo
- generated files that still match what it would write (a file you edited is left alone)
- the instructions block (your own text in the same file stays)
- the MCP servers and OpenCode plugin entries it added, if they are unchanged
- empty folders it leaves behind

With the `army` module on, it also runs agentic-army's `uninstall.sh` for the same harnesses. Uninstalling every harness also deletes `~/.config/agentic-arsenal/`, the downloaded copy in `~/.local/share/agentic-arsenal`, and a downloaded agentic-army. A git checkout is never deleted, and neither is your second-brain vault. Config files are backed up to `.bak-<timestamp>` before each change.

### Optional modules

| Module | What you get | Asks |
|---|---|---|
| `caveman` | Terse replies that cut output tokens: `/caveman` commands, skills, OpenCode plugin, and an instructions block | yes/no |
| `second-brain` | A Markdown (Obsidian-compatible) vault your agents read for context and write learnings to: `/save`, `/brain-lint`, `/brain-reindex`, an OpenCode plugin that injects the current repo's page, and an instructions block | yes/no, then the vault folder. A starter vault is created there if the folder doesn't exist |
| `computer-use` | macOS only. Agents drive native app windows through [open-computer-use](https://github.com/nogu66/open-computer-use): MCP server, `computer-use` skill, `/computer` | yes/no. Downloads the pinned `ocu` release to `~/.local/bin/ocu` (checksum verified) if it isn't installed. Grant Accessibility (and Screen Recording for screenshots) to your terminal or agent app |
| `army` | Hierarchical agent teams from [agentic-army](https://github.com/alhurwitz/agentic-army): `/army`, officer and soldier agents, hooks and MCP server, for every harness you install | yes/no. Downloads the latest agentic-army next to this repo on every run (a git checkout there, or at `AGENTIC_ARMY_DIR`, is used as-is), then runs its `install.sh` for the same harnesses |

Everything else always installs: the UI/design skills and commands, the GitHub and Playwright MCP servers, and the OpenCode find plugin.

### GitHub MCP token

The GitHub MCP server reads `GITHUB_MCP_TOKEN`. Create a fine-grained token on GitHub and export it in your shell profile:

```sh
export GITHUB_MCP_TOKEN=github_pat_...
```

## What the installer touches

- **Skills, commands, agents, plugins**: symlinks into this repo, so updating the repo updates them. Commands that are converted for a harness or contain your settings are written as files and refreshed on each run.
- **Global instructions** (`AGENTS.md`, `CLAUDE.md`, `copilot-instructions.md`): only a block between `<!-- agentic-arsenal-begin -->` and `<!-- agentic-arsenal-end -->`. Your own text outside it is kept.
- **Config files** (`opencode.json`, `~/.claude.json`, Codex `config.toml`, Copilot `mcp-config.json`, VS Code `mcp.json`): entries merged in, with a backup copy first.
- Anything else it would replace is moved to `~/.config/agentic-arsenal/backups/<timestamp>/`, outside every harness folder so agents never load backups.
- Turning a module off removes the links and generated files it installed. MCP entries are left in place.

| | OpenCode | Claude Code | Codex | Copilot |
|---|---|---|---|---|
| Instructions | `~/.config/opencode/AGENTS.md` | `~/.claude/CLAUDE.md` | `~/.codex/AGENTS.md` | `~/.copilot/copilot-instructions.md` |
| Skills | `~/.config/opencode/skills/` | `~/.claude/skills/` | `~/.agents/skills/` | `~/.copilot/skills/` |
| Agents | `~/.config/opencode/agents/` | `~/.claude/agents/` | n/a | `~/.copilot/agents/*.agent.md` |
| Commands | `~/.config/opencode/commands/` | `~/.claude/commands/` | `~/.codex/prompts/` | VS Code user `prompts/*.prompt.md` |
| MCP | `opencode.json` | `~/.claude.json` | `~/.codex/config.toml` | `~/.copilot/mcp-config.json` + VS Code `mcp.json` |
| Hooks | `~/.config/opencode/plugins/` | not yet | not yet | not yet |

For non-OpenCode harnesses, OpenCode-only frontmatter (`model`, `agent`, `subtask`, `mode`, `permissions`) is stripped from commands and agents.

## Layout

```
modules.json                 optional modules and the items each one owns
instructions/<module>.md     instruction blocks added for enabled modules
templates/second-brain/      starter vault
skills/<skill>/SKILL.md      shared skill
skills/<skill>/<harness>/    optional harness-specific copy of the skill
agents/<agent>/agent.md      shared agent
agents/<agent>/<harness>.md  harness-specific agent
commands/<cmd>/command.md    shared slash command
commands/<cmd>/<harness>.md  harness-specific command
hooks/<hook>/<harness>/      plugin or hook code, per harness
mcp/servers.json             MCP servers, written once; ${VAR} for secrets
install.sh                   curl bootstrap: downloads the repo, runs install.py
install.py                   installer
```

Harness names: `opencode`, `claude`, `codex`, `copilot`. `{{SECOND_BRAIN_DIR}}` in a command or instruction file is replaced with the configured vault folder.

## Contributing

Open a pull request. To add a harness, add an entry to `HARNESSES` in `install.py` and an `mcp_<harness>` method, plus `hook_<harness>` if it supports hooks. To add an optional module, add it to `modules.json`.
