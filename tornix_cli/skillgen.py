from __future__ import annotations

FRONTMATTER = """---
name: tornix
description: Drive the Tornix PMO platform (app.tornix.ai) from the CLI — projects, tasks, procurement, approvals, risks, cost, meetings, AI, and deep-research. Every command supports --json.
---
"""

HEADER = """
# Tornix CLI Skill

`tornix` is an agent-native CLI for the Tornix PMO backend. **Always pass `--json`**
for machine-readable output (it works before or after any subcommand). Authentication is
AUTOMATIC: the platform injects the signed-in user's token as `TORNIX_TOKEN` in your
environment — never run `tornix auth login`, and NEVER ask the user for an API key,
token, password, or any other credential. If a command fails with an auth error (exit
code 3 / `Invalid or expired token`), do NOT retry, re-authenticate, or show login
steps: tell the user the platform session needs a refresh — refresh the page (web) or
fully close and reopen the app (mobile), or start a new conversation. Never invoke any
`tornix auth …` or `tornix api auth …` command (login/logout/keys): those exist for the
platform's own flows, not for you. Scope a request to an org with `--org <id>` or
`TORNIX_ORG`.

Discover the full surface programmatically: `tornix catalog --json`.

## Conventions
- Output: add `--json` to any command. Errors go to stderr as `{"error": {...}}` with
  non-zero exit codes (3=auth, 4=not-found, 5=validation, 6=rate-limit/credits).
- Full backbone: `tornix api <tag> <operation> [--opts] --json` covers every backend operation.
- Escape hatches: `tornix data select <table> --eq col=val --json`, `tornix rpc <fn> --arg k=v --json`.
- Deep research: `tornix deep-research "<question>" --source pmo|web|both --project <id> --json`.
  Default returns a structured cited corpus for you to synthesize; add `--synthesize`
  to have Tornix AI write the report.

## Commands
"""


def _walk(node: dict, prefix: str, lines: list[str]) -> None:
    children = node.get("commands")
    if children:
        for c in children:
            _walk(c, f"{prefix} {c['name']}".strip(), lines)
    else:
        help_ = node.get("help", "")
        lines.append(f"- `tornix {prefix} --json` — {help_}")


def render_skill(catalog: dict) -> str:
    lines: list[str] = []
    for c in catalog.get("commands", []):
        _walk(c, c["name"], lines)
    body = "\n".join(lines)
    return FRONTMATTER + HEADER + body + "\n"
