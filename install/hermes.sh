#!/usr/bin/env bash
# Install the Tornix skill into Hermes.
set -euo pipefail
pip install --upgrade tornix-cli
DEST="${HERMES_SKILLS_DIR:-$HOME/.hermes/skills}/tornix"
mkdir -p "$DEST"
tornix skill generate --out "$DEST/SKILL.md"
echo "Installed Tornix skill to $DEST/SKILL.md"
