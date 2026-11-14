#!/usr/bin/env python3
"""Install the arsenal into one or more agent harnesses.

Usage:
    ./install.py all
    ./install.py opencode claude
    ./install.py --dry-run codex
    ./install.py all --with second-brain --without caveman
    ./install.py all --reconfigure        # ask the optional-module questions again

Every item (skill, agent, command, hook) is shared by default. A harness gets its own
variant only when the item has one: ``<item>/<harness>/`` for skills, ``<item>/<harness>.md``
for agents and commands, ``hooks/<hook>/<harness>/`` for hooks. Shared files are symlinked
so edits here apply everywhere; converted or templated files are regenerated on every run.
Anything an install would replace is moved to ``~/.config/agentic-arsenal/backups/<timestamp>/`` first.

Optional modules are listed in ``modules.json``. The installer asks about each one the first
time and remembers the answers in ``~/.config/agentic-arsenal/config.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent
HOME = Path(os.environ.get("ARSENAL_HOME", Path.home()))
ARMY = Path(os.environ.get("AGENTIC_ARMY_DIR", REPO.parent / "agentic-army"))
CONFIG = HOME / ".config/agentic-arsenal/config.json"
MODULES = json.loads((REPO / "modules.json").read_text())
STAMP = time.strftime("%Y%m%d-%H%M%S")
BACKUPS = HOME / ".config/agentic-arsenal/backups" / STAMP
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
ENV_REF = re.compile(r"\$\{(\w+)\}")
OPENCODE_ONLY_KEYS = ("model", "agent", "subtask", "subagent", "mode", "permissions")
BLOCK_BEGIN = "<!-- agentic-arsenal-begin -->"
BLOCK_END = "<!-- agentic-arsenal-end -->"
BLOCK = re.compile(re.escape(BLOCK_BEGIN) + r".*?" + re.escape(BLOCK_END) + r"\n?", re.S)
SECOND_BRAIN_DEFAULT = "~/Code/second-brain"
SECOND_BRAIN_SESSION_PAGES = ("me/profile.md", "me/corrections.md", "hot.md")
OCU_VERSION = "v0.1.0"
OCU_URL = (
    "https://github.com/nogu66/open-computer-use/releases/download/"
    f"{OCU_VERSION}/ocu-{OCU_VERSION}-macos-universal.tar.gz"
)
OCU_SHA256 = "3626bfc7ee43108a5079c873e3ecdd42f6a7bd7f955a319a2bc4ea249ec67ee4"

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


def backup_path(path: Path) -> Path:
    """Where a replaced file goes: outside every harness folder, so harnesses never load it."""
    try:
        relative = path.relative_to(HOME)
    except ValueError:
        relative = Path(*path.parts[1:])
    return BACKUPS / relative


def expand(path: str) -> Path:
    return Path(re.sub(r"^~(?=$|/)", str(HOME), path)).resolve()


def ask_yes_no(question: str, default: bool) -> bool:
    hint = "Y/n" if default else "y/N"
    while True:
        answer = input(f"{question}? [{hint}] ").strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes", "n", "no"):
            return answer.startswith("y")


class Settings:
    """Optional-module choices, asked once and remembered in CONFIG."""

    def __init__(self, args: argparse.Namespace) -> None:
        saved = json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
        interactive = sys.stdin.isatty() and not args.dry_run
        self.modules: dict[str, bool] = {}
        self.second_brain_dir = saved.get("secondBrainDir", SECOND_BRAIN_DEFAULT)
        for name, module in MODULES.items():
            if platform.system() not in module.get("platforms", [platform.system()]):
                self.modules[name] = False
            elif name in args.with_modules or name in args.without_modules:
                self.modules[name] = name in args.with_modules
            elif name in saved.get("modules", {}) and not args.reconfigure:
                self.modules[name] = saved["modules"][name]
            elif interactive:
                self.modules[name] = ask_yes_no(module["prompt"], module["default"])
                if name == "second-brain" and self.modules[name]:
                    answer = input(f"  Vault folder (created if missing) [{self.second_brain_dir}]: ").strip()
                    self.second_brain_dir = answer or self.second_brain_dir
            else:
                self.modules[name] = module["default"]
        self.dry_run = args.dry_run

    def excluded(self, kind: str) -> set[str]:
        """Names of items of this kind that belong only to disabled modules."""
        return {
            item
            for name, module in MODULES.items()
            if not self.modules[name]
            for item in module.get(kind, [])
        }

    def render(self, text: str) -> str:
        return text.replace("{{SECOND_BRAIN_DIR}}", self.second_brain_dir)

    def save(self) -> None:
        if self.dry_run:
            return
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        data = {"modules": self.modules, "secondBrainDir": self.second_brain_dir}
        CONFIG.write_text(json.dumps(data, indent=2) + "\n")

    def prepare(self) -> None:
        """One-time setup that does not depend on a harness."""
        print("[setup]")
        enabled = [name for name, on in self.modules.items() if on]
        print(f"  modules  {', '.join(enabled) or 'none'}")
        if self.modules["second-brain"]:
            self.create_vault()
        if self.modules["computer-use"]:
            self.install_ocu()

    def create_vault(self) -> None:
        vault = expand(self.second_brain_dir)
        if vault.exists():
            return
        print(f"  create   {vault} (from templates/second-brain)")
        if self.dry_run:
            return
        shutil.copytree(REPO / "templates/second-brain", vault)
        subprocess.run(["git", "init", "-q", str(vault)], check=False)

    def ocu_path(self) -> Path:
        default = HOME / ".local/bin/ocu"
        found = shutil.which("ocu")
        return Path(found) if found and not default.exists() else default

    def install_ocu(self) -> None:
        dest = self.ocu_path()
        if dest.exists():
            return
        print(f"  download ocu {OCU_VERSION} -> {dest}")
        if self.dry_run:
            return
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "ocu.tar.gz"
            urllib.request.urlretrieve(OCU_URL, archive)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            if digest != OCU_SHA256:
                raise SystemExit(f"ocu download checksum mismatch: {digest}")
            with tarfile.open(archive) as tar:
                member = tar.getmember(f"ocu-{OCU_VERSION}-macos-universal/ocu")
                extracted = tar.extractfile(member)
                assert extracted is not None
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(extracted.read())
        dest.chmod(0o755)
        print("  note     grant Accessibility (and Screen Recording for screenshots) to your terminal/agent app")


class Installer:
    """Installs repo items into one harness."""

    def __init__(self, harness: str, settings: Settings) -> None:
        self.harness = harness
        self.paths = HARNESSES[harness]
        self.settings = settings
        self.dry_run = settings.dry_run

    def log(self, action: str, path: Path) -> None:
        print(f"  {action:8} {path}")

    def ours(self, dest: Path) -> bool:
        return dest.is_symlink() and REPO in Path(os.readlink(dest)).parents

    def clear(self, dest: Path) -> None:
        """Move aside whatever is at dest, unless it is already a link into this repo."""
        if self.ours(dest):
            if not self.dry_run:
                dest.unlink()
            return
        if dest.exists() or dest.is_symlink():
            backup = backup_path(dest)
            self.log("backup", backup)
            if not self.dry_run:
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dest), str(backup))

    def remove_ours(self, dest: Path, generated: str | None = None) -> None:
        """Remove what this repo installed for an item whose module is now disabled."""
        is_generated = generated is not None and dest.is_file() and not dest.is_symlink() and dest.read_text() == generated
        if self.ours(dest) or is_generated:
            self.log("remove", dest)
            if not self.dry_run:
                dest.unlink()

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

    def save_json(self, path: Path, data: dict) -> None:
        self.log("merge", path)
        if not self.dry_run:
            if path.exists():
                backup_path(path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup_path(path))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2) + "\n")

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
        """Keep a managed block in the harness's global instructions file; the rest is the user's."""
        dest = self.paths["instructions"]
        snippets = [
            self.settings.render((REPO / "instructions" / module["instructions"]).read_text()).strip()
            for name, module in MODULES.items()
            if self.settings.modules[name] and "instructions" in module
        ]
        current = dest.read_text() if dest.exists() else ""
        rest = BLOCK.sub("", current).strip()
        block = f"{BLOCK_BEGIN}\n" + "\n\n".join(snippets) + f"\n{BLOCK_END}\n" if snippets else ""
        updated = (block + ("\n" + rest + "\n" if rest else "")) if block else (rest + "\n" if rest else "")
        if updated == current or (not current and not updated):
            return
        self.log("update", dest)
        if not self.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(updated)

    def install_skills(self) -> None:
        skipped = self.settings.excluded("skills")
        for skill in sorted(p for p in (REPO / "skills").iterdir() if p.is_dir()):
            dest = self.paths["skills"] / skill.name
            if skill.name in skipped:
                self.remove_ours(dest)
                continue
            own = skill / self.harness
            self.link(own if own.is_dir() else skill, dest)

    def install_markdown(self, kind: str, shared: str) -> None:
        target = self.paths[kind]
        if target is None or not (REPO / kind).is_dir():
            return
        skipped = self.settings.excluded(kind)
        for item in sorted(p for p in (REPO / kind).iterdir() if p.is_dir()):
            dest = target / self.filename(kind, item.name)
            src, override = self.variant(item, shared)
            if src is None:
                continue
            text = src.read_text()
            rendered = self.settings.render(text)
            native = override or self.harness == "opencode"
            if item.name in skipped:
                self.remove_ours(dest, rendered if native else self.portable(rendered))
                continue
            if rendered == text and native:
                self.link(src, dest)
            elif native:
                self.write(rendered, dest)
            else:
                self.write(self.portable(rendered), dest)

    def filename(self, kind: str, name: str) -> str:
        if self.harness == "copilot":
            return f"{name}.agent.md" if kind == "agents" else f"{name}.prompt.md"
        return f"{name}.md"

    def install_hooks(self) -> None:
        skipped = self.settings.excluded("hooks")
        for hook in sorted(p for p in (REPO / "hooks").iterdir() if p.is_dir()):
            src = hook / self.harness
            if not src.is_dir():
                continue
            installer = getattr(self, f"hook_{self.harness}", None)
            if installer is None:
                print(f"  skip     hook {hook.name}: no installer for {self.harness}")
                continue
            installer(src, hook.name in skipped)

    def hook_opencode(self, src: Path, skip: bool) -> None:
        plugins = HOME / ".config/opencode/plugins"
        for entry in sorted(src.iterdir()):
            if skip:
                self.remove_ours(plugins / entry.name)
            else:
                self.link(entry, plugins / entry.name)

    def install_mcp(self) -> None:
        skipped = self.settings.excluded("mcp")
        servers = json.loads((REPO / "mcp/servers.json").read_text())
        servers = {name: spec for name, spec in servers.items() if name not in skipped}
        if "open-computer-use" in servers:
            servers["open-computer-use"]["command"] = [str(self.settings.ocu_path())]
        if servers:
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
        self.save_json(path, data)

    def mcp_opencode(self, servers: dict) -> None:
        out = {}
        for name, spec in servers.items():
            spec = json.loads(ENV_REF.sub(lambda m: "{env:%s}" % m.group(1), json.dumps(spec)))
            out[name] = {**spec, "oauth": False} if spec["type"] == "remote" else spec
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
                continue
            lines = [f'[mcp_servers."{name}"]']
            if spec["type"] == "remote":
                lines.append(f"url = {json.dumps(spec['url'])}")
                for header, value in spec.get("headers", {}).items():
                    bearer = re.fullmatch(r"Bearer \$\{(\w+)\}", value)
                    if header == "Authorization" and bearer:
                        lines.append(f"bearer_token_env_var = {json.dumps(bearer.group(1))}")
            else:
                lines.append(f"command = {json.dumps(spec['command'][0])}")
                lines.append(f"args = {json.dumps(spec['command'][1:])}")
            blocks.append("\n".join(lines))
        if not blocks:
            return
        self.log("append", config)
        if not self.dry_run:
            config.parent.mkdir(parents=True, exist_ok=True)
            if config.exists():
                backup_path(config).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(config, backup_path(config))
            config.write_text(text.rstrip() + ("\n\n" if text.strip() else "") + "\n\n".join(blocks) + "\n")

    def config_opencode(self) -> None:
        """Register plugins and second-brain session pages in OpenCode's JSON configs."""
        config = HOME / ".config/opencode/opencode.json"
        data = json.loads(config.read_text()) if config.exists() else {}
        changed = False
        caveman = {"package": "./plugins/caveman"}
        plugins = data.setdefault("plugins", [])
        if self.settings.modules["caveman"] and caveman not in plugins:
            plugins.append(caveman)
            changed = True
        if not self.settings.modules["caveman"] and caveman in plugins:
            plugins.remove(caveman)
            changed = True
        instructions = data.setdefault("instructions", [])
        pages = [f"{self.settings.second_brain_dir.rstrip('/')}/{page}" for page in SECOND_BRAIN_SESSION_PAGES]
        wanted = {expand(p) for p in pages}
        if self.settings.modules["second-brain"]:
            present = {expand(p) for p in instructions}
            for path in pages:
                if expand(path) not in present:
                    instructions.append(path)
                    changed = True
        elif any(expand(p) in wanted for p in instructions):
            instructions[:] = [p for p in instructions if expand(p) not in wanted]
            changed = True
        if changed:
            self.save_json(config, data)

        cli = HOME / ".config/opencode/cli.json"
        data = json.loads(cli.read_text()) if cli.exists() else {}
        entries = data.setdefault("plugins", [])
        find = {"package": str(HOME / ".config/opencode/plugins/find")}
        if find not in entries:
            entries.append(find)
            self.save_json(cli, data)

    def army_opencode(self) -> None:
        """Delegate to agentic-army's own installer when it is cloned alongside this repo."""
        script = ARMY / "install.sh"
        if not script.exists():
            print(f"  skip     agentic-army not found at {ARMY} (clone alhurwitz/agentic-army there)")
            return
        self.log("run", script)
        if not self.dry_run:
            subprocess.run([str(script)], check=True)

    def run(self) -> None:
        print(f"[{self.harness}]")
        self.install_instructions()
        self.install_skills()
        self.install_markdown("agents", "agent.md")
        self.install_markdown("commands", "command.md")
        self.install_hooks()
        self.install_mcp()
        if self.harness == "opencode":
            self.config_opencode()
            self.army_opencode()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("harnesses", nargs="+", choices=[*HARNESSES, "all"])
    parser.add_argument("--dry-run", action="store_true", help="print actions without changing anything")
    parser.add_argument("--with", dest="with_modules", action="append", default=[], choices=list(MODULES))
    parser.add_argument("--without", dest="without_modules", action="append", default=[], choices=list(MODULES))
    parser.add_argument("--reconfigure", action="store_true", help="ask the optional-module questions again")
    args = parser.parse_args()
    settings = Settings(args)
    settings.prepare()
    names = list(HARNESSES) if "all" in args.harnesses else args.harnesses
    for name in names:
        Installer(name, settings).run()
    settings.save()
    return 0


if __name__ == "__main__":
    sys.exit(main())
