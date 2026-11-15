#!/usr/bin/env bash
# Downloads the arsenal (no git needed) and runs install.py with your arguments.
#
#   curl -fsSL https://raw.githubusercontent.com/alhurwitz/alberts-agentic-arsenal/main/install.sh | bash -s -- all
#   curl -fsSL .../install.sh | bash -s -- claude --with army
#   curl -fsSL .../install.sh | bash -s -- --uninstall           # everything, then this download
#   curl -fsSL .../install.sh | bash -s -- --uninstall codex     # one harness
#
# The repo lives in $ARSENAL_DIR (default ~/.local/share/agentic-arsenal). Installed items are
# symlinks into it, so re-running this script updates everything in place. If $ARSENAL_DIR is
# a git checkout it is used as-is.
set -euo pipefail

TARBALL="https://codeload.github.com/alhurwitz/alberts-agentic-arsenal/tar.gz/refs/heads/main"
DIR="${ARSENAL_DIR:-$HOME/.local/share/agentic-arsenal}"

fail() { echo "error: $*" >&2; exit 1; }
command -v curl >/dev/null || fail "curl not found"
command -v python3 >/dev/null || fail "python3 not found"
# No arguments: install.py asks which harnesses, unless there is no terminal to ask on.
[ $# -gt 0 ] || { : </dev/tty; } 2>/dev/null || set -- all

uninstall=0 some=0
for arg in "$@"; do
  case "$arg" in
    --uninstall) uninstall=1 ;;
    opencode | claude | codex | copilot) some=1 ;;
  esac
done

if [ -d "$DIR/.git" ]; then
  echo "==> using git checkout at $DIR"
elif [ "$uninstall" = 1 ] && grep -q -- "--uninstall" "$DIR/install.py" 2>/dev/null; then
  echo "==> using installed copy at $DIR"
else
  echo "==> downloading arsenal to $DIR"
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  curl -fsSL "$TARBALL" | tar -xz -C "$tmp"
  mkdir -p "$(dirname "$DIR")"
  rm -rf "$DIR"
  mv "$tmp"/alberts-agentic-arsenal-main "$DIR"
fi

run() {
  # stdin is the piped script under `curl | bash`; read answers from the terminal instead.
  if { : </dev/tty; } 2>/dev/null; then python3 "$DIR/install.py" "$@" </dev/tty; else python3 "$DIR/install.py" "$@"; fi
}

if [ "$uninstall" = 0 ]; then
  run "$@"
  exit
fi
# Uninstall runs from the installed copy (its links point there), then deletes the download
# once every harness is gone. A git checkout is never deleted.
run "$@"
if [ "$some" = 0 ] && [ ! -d "$DIR/.git" ]; then
  echo "==> removing $DIR"
  rm -rf "$DIR"
fi
