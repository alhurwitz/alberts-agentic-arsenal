# alberts-agentic-arsenal

One setup for every coding agent: skills, agents, commands, hooks and MCP, installed into OpenCode, Claude Code, Copilot and Codex.

Everything lives here once. `install.py` puts it where each harness looks. Items are shared by default; a harness gets its own variant only where it needs one.

## Quick start

You need Python 3.9+ and git. Nothing else is required; optional pieces download what they need.

```sh
git clone https://github.com/alhurwitz/alberts-agentic-arsenal ~/Code/alberts-agentic-arsenal
cd ~/Code/alberts-agentic-arsenal
./install.py all                 # or pick harnesses: ./install.py opencode claude
```

The first run asks about each optional module (below) and remembers your answers in `~/.config/agentic-arsenal/config.json`. Change them later with `./install.py all --reconfigure`, or per run with `--with <module>` / `--without <module>`. Preview any run with `--dry-run`.

Then restart your agent.

To update: `git pull && ./install.py all`.

### Optional modules

| Module | What you get | Asks |
|---|---|---|
| `caveman` | Terse replies that cut output tokens: `/caveman` commands, skills, OpenCode plugin, and an instructions block | yes/no |
| `second-brain` | A Markdown (Obsidian-compatible) vault your agents read for context and write learnings to: `/save`, `/brain-lint`, `/brain-reindex`, an OpenCode plugin that injects the current repo's page, and an instructions block | yes/no, then the vault folder. A starter vault is created there if the folder doesn't exist |
| `computer-use` | macOS only. Agents drive native app windows through [open-computer-use](https://github.com/nogu66/open-computer-use): MCP server, `computer-use` skill, `/computer` | yes/no. Downloads the pinned `ocu` release to `~/.local/bin/ocu` (checksum verified) if it isn't installed. Grant Accessibility (and Screen Recording for screenshots) to your terminal or agent app |

Everything else always installs: the UI/design skills and commands, the GitHub and Playwright MCP servers, and the OpenCode find plugin.

### GitHub MCP token

The GitHub MCP server reads `GITHUB_MCP_TOKEN`. Create a fine-grained token on GitHub and export it in your shell profile:

```sh
export GITHUB_MCP_TOKEN=github_pat_...
```

### Agent teams

The army (hierarchical agent teams) lives in its own repo, [agentic-army](https://github.com/alhurwitz/agentic-army). Clone it next to this one (`~/Code/agentic-army`, or set `AGENTIC_ARMY_DIR`) and `./install.py opencode` runs its installer too.

## What the installer touches

- **Skills, commands, agents, plugins**: symlinks into this repo, so `git pull` updates them. Commands that are converted for a harness or contain your settings are written as files and refreshed on each run.
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
install.py                   installer
```

Harness names: `opencode`, `claude`, `codex`, `copilot`. `{{SECOND_BRAIN_DIR}}` in a command or instruction file is replaced with the configured vault folder.

## Contributing

Open a pull request. To add a harness, add an entry to `HARNESSES` in `install.py` and an `mcp_<harness>` method, plus `hook_<harness>` if it supports hooks. To add an optional module, add it to `modules.json`.
