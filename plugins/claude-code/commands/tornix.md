---
description: Run a Tornix CLI command (agent-native, --json).
argument-hint: <tornix subcommand and args>
---

Run the Tornix CLI and return parsed results. Always pass `--json`.

Steps:
1. If `tornix` is not installed, install it: `pip install tornix-cli` (or `pipx install tornix-cli`).
2. Ensure auth: if a call returns exit code 3, tell the user to run
   `tornix auth login --api-key tk_…` or set `TORNIX_API_KEY`.
3. Run: `tornix --json $ARGUMENTS`
4. Parse the JSON output. On non-zero exit, read the `{"error":{...}}` on stderr and act on `hint`.
5. To discover commands, run `tornix catalog --json` first. The full backend is under
   `tornix api <tag> <operation>`; generic access via `tornix data` / `tornix rpc`.
