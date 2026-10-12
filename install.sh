#!/bin/sh
# Installs the ecc-arena skill into ~/.claude/skills (or $CLAUDE_CONFIG_DIR/skills), with the
# vendored Everything-Claude-Code agents and skills beside it as a fallback. Nothing already in
# ~/.claude/agents or ~/.claude/skills is overwritten.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
NAME="ecc-arena"
DEST="$CLAUDE_DIR/skills/$NAME"

command -v python3 >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }

mkdir -p "$CLAUDE_DIR/skills"
rm -rf "$DEST"
cp -R "$HERE/skills/$NAME" "$DEST"
rm -rf "$DEST/tests" "$DEST/ecca/__pycache__"
mkdir -p "$DEST/ecc"
cp -R "$HERE/ecc/agents" "$HERE/ecc/skills" "$HERE/ecc/LICENSE" "$HERE/ecc/VENDORED.md" "$DEST/ecc/"
echo "installed skill into $DEST (vendored ECC agents and skills beside it)"

installed=$(ls "$CLAUDE_DIR"/agents/*.md 2>/dev/null | wc -l | tr -d ' ')
if [ "$installed" -gt 0 ]; then
  echo "found $installed ECC agents in $CLAUDE_DIR/agents: those take precedence over the vendored copy"
else
  echo "no ECC agents in $CLAUDE_DIR/agents: the vendored copy will be used"
fi

echo
echo "Done. Restart Claude Code, then try:"
echo "  /ecc-arena <describe the project>"
