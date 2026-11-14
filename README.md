# alberts-agentic-arsenal

One setup for every coding agent: skills, agents, commands, hooks and MCP, installed into OpenCode, Claude Code, Copilot and Codex.

Everything lives here once. `install.py` puts it where each harness looks. Items are shared by default; a harness gets its own variant only where it needs one.

## Install

```sh
git clone https://github.com/alhurwitz/alberts-agentic-arsenal ~/Code/alberts-agentic-arsenal
cd ~/Code/alberts-agentic-arsenal
./install.py --dry-run all     # preview
./install.py all               # or: ./install.py opencode claude
```

Shared files are symlinked, so editing them here updates every harness. Converted files (commands and agents for non-OpenCode harnesses) are regenerated, so re-run `./install.py` after editing those. Anything replaced is moved to `<path>.bak-<timestamp>`; config files are merged, not overwritten.

Needs Python 3.9+. Set `GITHUB_MCP_TOKEN` for the GitHub MCP server.

## Layout

```
AGENTS.md                  global instructions (CLAUDE.md, copilot-instructions.md, Codex AGENTS.md)
skills/<skill>/SKILL.md    shared skill
skills/<skill>/<harness>/  optional harness-specific copy of the skill
agents/<agent>/agent.md    shared agent
agents/<agent>/<harness>.md  harness-specific agent (only this harness gets it if no agent.md)
commands/<cmd>/command.md  shared slash command
commands/<cmd>/<harness>.md  harness-specific command
hooks/<hook>/<harness>/    plugin or hook code, per harness
mcp/servers.json           MCP servers, written once; ${VAR} for secrets
install.py                 installer
```

Harness names: `opencode`, `claude`, `codex`, `copilot`.

## Where things go

| | OpenCode | Claude Code | Codex | Copilot |
|---|---|---|---|---|
| Instructions | `~/.config/opencode/AGENTS.md` | `~/.claude/CLAUDE.md` | `~/.codex/AGENTS.md` | `~/.copilot/copilot-instructions.md` |
| Skills | `~/.config/opencode/skills/` | `~/.claude/skills/` | `~/.agents/skills/` | `~/.copilot/skills/` |
| Agents | `~/.config/opencode/agents/` | `~/.claude/agents/` | n/a | `~/.copilot/agents/*.agent.md` |
| Commands | `~/.config/opencode/commands/` | `~/.claude/commands/` | `~/.codex/prompts/` | VS Code user `prompts/*.prompt.md` |
| MCP | `opencode.json` | `~/.claude.json` | `~/.codex/config.toml` | `~/.copilot/mcp-config.json` + VS Code `mcp.json` |
| Hooks | `~/.config/opencode/plugins/` | not yet | not yet | not yet |

For non-OpenCode harnesses, OpenCode-only frontmatter (`model`, `agent`, `subtask`, `mode`, `permissions`) is stripped from commands and agents.

## What's in it

- **Caveman**: terse-output mode. Skills `caveman*`, commands `/caveman*`, OpenCode plugin.
- **Army**: hierarchical agent teams (`/alberts-army`, `army-officer`, `army-soldier`, plugin + TUI tree). OpenCode only: it depends on OpenCode's subagent tool.
- **Second brain**: injects the matching project page from an Obsidian vault (`SECOND_BRAIN_DIR`, default `~/Code/second-brain`). Commands `/save`, `/brain-lint`, `/brain-reindex`.
- **UI and design**: impeccable, frontend-design, design-system, ui-ux-pro-max, ui-styling, ui-verify, accessibility, animation-forge, browser-qa, dev-browser, computer-use, ui-demo, liquid-glass-design, frontend-slides.
- **Find**: OpenCode TUI search over the current session.
- **MCP**: GitHub, Playwright, open-computer-use.

## Adding a harness

Add an entry to `HARNESSES` in `install.py` and an `mcp_<harness>` method. Add `hook_<harness>` if it supports hooks.
