# Tornix CLI — Claude Code plugin

Exposes two slash commands backed by the `tornix` CLI:

- `/tornix <subcommand …>` — run any Tornix command (agent-native, `--json`).
- `/deep-research "<question>" [--project <id>] [--source pmo|web|both]` — research over
  PMO data and/or the web, then synthesize a cited answer.

## Install

1. Install the CLI: `pip install tornix-cli` (or `pipx install tornix-cli`).
2. Authenticate: `tornix auth login --api-key tnx_…` (or set `TORNIX_API_KEY`).
3. Add this plugin to Claude Code (marketplace install, or point Claude Code at this
   `plugins/claude-code` directory).

## Notes

- All output is JSON; errors are `{"error":{...}}` on stderr with exit codes
  (3=auth, 4=not-found, 5=validation, 6=rate-limit/credits).
- Discover the full surface with `tornix catalog --json`.
