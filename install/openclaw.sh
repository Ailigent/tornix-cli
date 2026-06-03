#!/usr/bin/env bash
# Install the Tornix skill into OpenClaw.
set -euo pipefail
pip install --upgrade tornix-cli
DEST="${OPENCLAW_SKILLS_DIR:-$HOME/.openclaw/skills}/tornix"
mkdir -p "$DEST"
tornix skill generate --out "$DEST/SKILL.md"
echo "Installed Tornix skill to $DEST/SKILL.md"
