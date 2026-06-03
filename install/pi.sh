#!/usr/bin/env bash
# Install the Tornix extension into Pi.
set -euo pipefail
pip install --upgrade tornix-cli
DEST="${PI_EXT_DIR:-$HOME/.pi/agent/extensions}/tornix"
mkdir -p "$DEST"
tornix skill generate --out "$DEST/SKILL.md"
echo "Installed Tornix extension to $DEST/SKILL.md"
