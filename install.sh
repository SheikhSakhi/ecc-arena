#!/bin/sh
# Installs the ecc-arena skill into ~/.claude/skills (or $CLAUDE_CONFIG_DIR/skills).
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
NAME="ecc-arena"

command -v python3 >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }

mkdir -p "$CLAUDE_DIR/skills"
rm -rf "$CLAUDE_DIR/skills/$NAME"
cp -R "$HERE/skills/$NAME" "$CLAUDE_DIR/skills/"
rm -rf "$CLAUDE_DIR/skills/$NAME/tests" "$CLAUDE_DIR/skills/$NAME/ecca/__pycache__"
echo "installed skill into $CLAUDE_DIR/skills/$NAME"

if [ -d "$CLAUDE_DIR/agents" ] && ls "$CLAUDE_DIR"/agents/*.md >/dev/null 2>&1; then
  echo "ECC agents found in $CLAUDE_DIR/agents: competitors will work in those roles"
else
  echo "no ECC agents in $CLAUDE_DIR/agents: competitors will work from the chain descriptions (install everything-claude-code to change that)"
fi

echo
echo "Done. Restart Claude Code, then try:"
echo "  /ecc-arena --quick <describe the project>"
