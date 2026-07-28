#!/usr/bin/env bash
# Install Tornix slash commands into an OpenCode project (run from the project root).
# Writes real OpenCode command files (not the skill) so it works after a PyPI install.
set -euo pipefail
pip install --upgrade tornix-cli || python3 -m pip install --upgrade tornix-cli
DEST=".opencode/commands"
mkdir -p "$DEST"

cat > "$DEST/tornix.md" <<'EOF'
---
description: Run a Tornix CLI command (agent-native, --json).
argument-hint: <tornix subcommand and args>
---

Run the Tornix CLI and return parsed results. Always pass `--json`.

1. Ensure auth: if a call returns exit code 3, run `tornix auth login --api-key tnx_…`
   or set `TORNIX_API_KEY`.
2. Run: `tornix --json $ARGUMENTS`
3. Parse the JSON output. On non-zero exit, read `{"error":{...}}` on stderr and act on `hint`.
4. Discover commands with `tornix catalog --json`; full backend under `tornix api <tag> <op>`.
EOF

cat > "$DEST/deep-research.md" <<'EOF'
---
description: Deep research over Tornix PMO data and/or the web, then synthesize a cited answer.
argument-hint: "<question>" [--project <id>] [--source pmo|web|both]
---

1. Run: `tornix --json deep-research $ARGUMENTS` (defaults to `--source pmo`).
2. The CLI returns `{question, sub_questions, corpus, web_brief, instructions}`.
3. If `web_brief` is present, execute its `search_queries` with your own web tools.
4. Synthesize a cited answer: cite PMO facts by `tornix://kind/id`, web facts by URL.
EOF

echo "Installed Tornix commands to $DEST"
