#!/usr/bin/env bash
# Copy Tornix slash commands into an OpenCode project (run from the project root).
set -euo pipefail
pip install --upgrade tornix-cli
DEST=".opencode/commands"
mkdir -p "$DEST"
PKG_PARENT="$(python -c 'import tornix_cli, os; print(os.path.dirname(os.path.dirname(tornix_cli.__file__)))')"
SRC="$PKG_PARENT/plugins/claude-code/commands"
if [ -d "$SRC" ]; then
  cp "$SRC"/*.md "$DEST/"
else
  # Wheel install without bundled plugins: synthesize a single command from the skill.
  tornix skill generate --out "$DEST/tornix.md"
fi
echo "Installed Tornix commands to $DEST"
