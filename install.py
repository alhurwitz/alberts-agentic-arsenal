#!/usr/bin/env python3
"""Install the arsenal into one or more agent harnesses.

Usage:
    ./install.py all
    ./install.py opencode claude
    ./install.py --dry-run codex

Every item (skill, agent, command, hook) is shared by default. A harness gets its own
variant only when the item has one: ``<item>/<harness>/`` for skills, ``<item>/<harness>.md``
for agents and commands, ``hooks/<hook>/<harness>/`` for hooks. Shared files are symlinked
so edits here apply everywhere; converted files are regenerated on every run. Anything an
install would replace is moved aside to ``<path>.bak-<timestamp>`` first.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
HOME = Path(os.environ.get("ARSENAL_HOME", Path.home()))
STAMP = time.strftime("%Y%m%d-%H%M%S")
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
ENV_REF = re.compile(r"\$\{(\w+)\}")
OPENCODE_ONLY_KEYS = ("model", "agent", "subtask", "subagent", "mode", "permissions")

if platform.system() == "Darwin":
    VSCODE_USER = HOME / "Library" / "Application Support" / "Code" / "User"
else:
    VSCODE_USER = HOME / ".config" / "Code" / "User"

HARNESSES = {
    "opencode": {
        "instructions": HOME / ".config/opencode/AGENTS.md",
        "skills": HOME / ".config/opencode/skills",
        "agents": HOME / ".config/opencode/agents",
        "commands": HOME / ".config/opencode/commands",
    },
    "claude": {
        "instructions": HOME / ".claude/CLAUDE.md",
        "skills": HOME / ".claude/skills",
        "agents": HOME / ".claude/agents",
        "commands": HOME / ".claude/commands",
    },
    "codex": {
        "instructions": HOME / ".codex/AGENTS.md",
        "skills": HOME / ".agents/skills",
        "agents": None,
        "commands": HOME / ".codex/prompts",
    },
    "copilot": {
        "instructions": HOME / ".copilot/copilot-instructions.md",
        "skills": HOME / ".copilot/skills",
        "agents": HOME / ".copilot/agents",
        "commands": VSCODE_USER / "prompts",
    },
}


class Installer:
    """Installs repo items into one harness."""

    def __init__(self, harness: str, dry_run: bool) -> None:
        self.harness = harness
        self.paths = HARNESSES[harness]
        self.dry_run = dry_run

    def log(self, action: str, path: Path) -> None:
        print(f"  {action:8} {path}")

    def clear(self, dest: Path) -> None:
        """Move aside whatever is at dest, unless it is already a link into this repo."""
        if dest.is_symlink() and REPO in Path(os.readlink(dest)).parents:
            if not self.dry_run:
                dest.unlink()
            return
        if dest.exists() or dest.is_symlink():
            backup = dest.with_name(f"{dest.name}.bak-{STAMP}")
            self.log("backup", backup)
            if not self.dry_run:
                dest.rename(backup)

    def link(self, src: Path, dest: Path) -> None:
        if dest.is_symlink() and Path(os.readlink(dest)) == src:
            return
        self.clear(dest)
        self.log("link", dest)
        if not self.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.symlink_to(src)

    def write(self, text: str, dest: Path) -> None:
        if dest.is_file() and not dest.is_symlink() and dest.read_text() == text:
            return
        self.clear(dest)
        self.log("write", dest)
        if not self.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text)

    def variant(self, item: Path, shared: str) -> tuple[Path | None, bool]:
        """Return (file, is_override) for a markdown item: <harness>.md beats the shared file."""
        own = item / f"{self.harness}.md"
        if own.exists():
            return own, True
        base = item / shared
        return (base, False) if base.exists() else (None, False)

    def portable(self, text: str) -> str:
        """Strip OpenCode-only frontmatter keys (model ids, agent routing, permissions)."""
        match = FRONTMATTER.match(text)
        if not match:
            return text
        kept, skipping = [], False
        for line in match.group(1).splitlines():
            key = line.split(":", 1)[0].strip()
            if not line.startswith((" ", "\t", "-")):
                skipping = key in OPENCODE_ONLY_KEYS
            if not skipping:
                kept.append(line)
        return "---\n" + "\n".join(kept) + "\n---\n" + text[match.end():]

    def install_instructions(self) -> None:
        self.link(REPO / "AGENTS.md", self.paths["instructions"])

    def install_skills(self) -> None:
        for skill in sorted(p for p in (REPO / "skills").iterdir() if p.is_dir()):
            own = skill / self.harness
            self.link(own if own.is_dir() else skill, self.paths["skills"] / skill.name)

    def install_markdown(self, kind: str, shared: str) -> None:
        target = self.paths[kind]
        if target is None:
            return
        for item in sorted(p for p in (REPO / kind).iterdir() if p.is_dir()):
            src, override = self.variant(item, shared)
            if src is None:
                continue
            dest = target / self.filename(kind, item.name)
            if override or self.harness == "opencode":
                self.link(src, dest)
            else:
                self.write(self.portable(src.read_text()), dest)

    def filename(self, kind: str, name: str) -> str:
        if self.harness == "copilot":
            return f"{name}.agent.md" if kind == "agents" else f"{name}.prompt.md"
        return f"{name}.md"

    def install_hooks(self) -> None:
        for hook in sorted(p for p in (REPO / "hooks").iterdir() if p.is_dir()):
            src = hook / self.harness
            if not src.is_dir():
                continue
            installer = getattr(self, f"hook_{self.harness}", None)
            if installer is None:
                print(f"  skip     hook {hook.name}: no installer for {self.harness}")
                continue
            installer(src)

    def hook_opencode(self, src: Path) -> None:
        plugins = HOME / ".config/opencode/plugins"
        for entry in sorted(src.iterdir()):
            self.link(entry, plugins / entry.name)

    def install_mcp(self) -> None:
        servers = json.loads((REPO / "mcp/servers.json").read_text())
        getattr(self, f"mcp_{self.harness}")(servers)

    def merge_json(self, path: Path, keys: list[str], entries: dict) -> None:
        """Set entries under nested keys in a JSON file, keeping everything else."""
        data = json.loads(path.read_text()) if path.exists() else {}
        node = data
        for key in keys:
            node = node.setdefault(key, {})
        if all(node.get(k) == v for k, v in entries.items()):
            return
        node.update(entries)
        self.log("merge", path)
        if not self.dry_run:
            if path.exists():
                shutil.copy2(path, path.with_name(f"{path.name}.bak-{STAMP}"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2) + "\n")

    def mcp_opencode(self, servers: dict) -> None:
        out = {}
        for name, spec in servers.items():
            spec = json.loads(ENV_REF.sub(lambda m: "{env:%s}" % m.group(1), json.dumps(spec)))
            out[name] = {**spec, "oauth": False} if spec["type"] == "remote" else spec
        out = json.loads(json.dumps(out).replace("{env:HOME}", str(HOME)))
        config = HOME / ".config/opencode/opencode.json"
        data = json.loads(config.read_text()) if config.exists() else {}
        keys = ["mcp", "servers"] if "servers" in data.get("mcp", {}) or not data.get("mcp") else ["mcp"]
        self.merge_json(config, keys, out)

    def mcp_claude(self, servers: dict) -> None:
        out = {}
        for name, spec in servers.items():
            if spec["type"] == "remote":
                out[name] = {"type": "http", "url": spec["url"], "headers": spec.get("headers", {})}
            else:
                out[name] = {"command": spec["command"][0], "args": spec["command"][1:]}
        self.merge_json(HOME / ".claude.json", ["mcpServers"], out)

    def mcp_copilot(self, servers: dict) -> None:
        cli, vscode = {}, {}
        for name, spec in servers.items():
            if spec["type"] == "remote":
                cli[name] = {"type": "http", "url": spec["url"], "headers": spec.get("headers", {}), "tools": ["*"]}
                vscode[name] = {"type": "http", "url": spec["url"], "headers": spec.get("headers", {})}
            else:
                local = {"command": spec["command"][0], "args": spec["command"][1:]}
                cli[name] = {"type": "local", **local, "tools": ["*"]}
                vscode[name] = {"type": "stdio", **local}
        self.merge_json(HOME / ".copilot/mcp-config.json", ["mcpServers"], cli)
        vscode = json.loads(ENV_REF.sub(lambda m: "${env:%s}" % m.group(1), json.dumps(vscode)))
        self.merge_json(VSCODE_USER / "mcp.json", ["servers"], vscode)

    def mcp_codex(self, servers: dict) -> None:
        config = HOME / ".codex/config.toml"
        text = config.read_text() if config.exists() else ""
        blocks = []
        for name, spec in servers.items():
            if f"[mcp_servers.{name}]" in text or f'[mcp_servers."{name}"]' in text:
                print(f"  keep     codex mcp {name} (already configured)")
                continue
            lines = [f'[mcp_servers."{name}"]']
            if spec["type"] == "remote":
                lines.append(f"url = {json.dumps(spec['url'])}")
                for header, value in spec.get("headers", {}).items():
                    bearer = re.fullmatch(r"Bearer \$\{(\w+)\}", value)
                    if header == "Authorization" and bearer:
                        lines.append(f"bearer_token_env_var = {json.dumps(bearer.group(1))}")
            else:
                command = [c.replace("${HOME}", str(HOME)) for c in spec["command"]]
                lines.append(f"command = {json.dumps(command[0])}")
                lines.append(f"args = {json.dumps(command[1:])}")
            blocks.append("\n".join(lines))
        if not blocks:
            return
        self.log("append", config)
        if not self.dry_run:
            config.parent.mkdir(parents=True, exist_ok=True)
            if config.exists():
                shutil.copy2(config, config.with_name(f"{config.name}.bak-{STAMP}"))
            config.write_text(text.rstrip() + ("\n\n" if text.strip() else "") + "\n\n".join(blocks) + "\n")

    def tui_opencode(self) -> None:
        plugins = HOME / ".config/opencode/plugins"
        cli = HOME / ".config/opencode/cli.json"
        data = json.loads(cli.read_text()) if cli.exists() else {}
        entries = data.setdefault("plugins", [])
        wanted = [str(plugins / "army-tui"), str(plugins / "find")]
        missing = [p for p in wanted if {"package": p} not in entries]
        if not missing:
            return
        entries.extend({"package": p} for p in missing)
        self.log("merge", cli)
        if not self.dry_run:
            if cli.exists():
                shutil.copy2(cli, cli.with_name(f"cli.json.bak-{STAMP}"))
            cli.write_text(json.dumps(data, indent=2) + "\n")

    def server_plugins_opencode(self) -> None:
        config = HOME / ".config/opencode/opencode.json"
        data = json.loads(config.read_text()) if config.exists() else {}
        entry = {"package": "./plugins/caveman"}
        if entry in data.get("plugins", []):
            return
        data.setdefault("plugins", []).append(entry)
        self.log("merge", config)
        if not self.dry_run:
            config.parent.mkdir(parents=True, exist_ok=True)
            config.write_text(json.dumps(data, indent=2) + "\n")

    def run(self) -> None:
        print(f"[{self.harness}]")
        self.install_instructions()
        self.install_skills()
        self.install_markdown("agents", "agent.md")
        self.install_markdown("commands", "command.md")
        self.install_hooks()
        self.install_mcp()
        if self.harness == "opencode":
            self.server_plugins_opencode()
            self.tui_opencode()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("harnesses", nargs="+", choices=[*HARNESSES, "all"])
    parser.add_argument("--dry-run", action="store_true", help="print actions without changing anything")
    args = parser.parse_args()
    names = list(HARNESSES) if "all" in args.harnesses else args.harnesses
    for name in names:
        Installer(name, args.dry_run).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
