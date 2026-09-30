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
profile-scoped and preconfigured — never inspect raw config files or `.env`, and NEVER ask the user
for an API key, token, password, or any other credential. If a command fails with an auth
error (exit code 3 / `Invalid or expired token`), do NOT re-authenticate or show login
steps: tell the user the current profile session needs a refresh and stop.

## Profile-scoped configuration
On multi-profile Hermes deployments, the CLI isolates config under `HERMES_HOME`.
If `HERMES_HOME` is not set, set a profile-specific `TORNIX_CONFIG` to a file inside the active profile;
never use a shared/default config. If neither is available, stop before running the CLI.

## Caller and organization safety
Before the first Tornix data request in each user session, run `tornix auth whoami --json`
and `tornix config show --json`. Match the returned caller to the active Hermes/Tornix
profile or another explicit user-to-organization mapping. List memberships with the
read-only `tornix api organizations list --json`. If `org_id` is configured, verify it
is in that caller's memberships. If it is absent, use only a single explicit
user-to-organization mapping for this profile and verify that membership; if none or
ambiguous, stop and ask. Never guess from a shared/default config or choose the first
item in the list. If caller, profile, or organization cannot be matched, stop before any
further org-scoped data read or write and ask the user.

`whoami` is the only allowed `tornix auth` command. Never invoke `tornix auth login/logout/keys …`,
`tornix api auth …`, or `tornix api api-keys …`. API-key creation can reveal a raw key only once;
key lifecycle is user-controlled in the authenticated Tornix web app. Never
copy, print, store, or transmit key secrets. Password-bearing user creation, reset, account and connected-mailbox deletion, and bulk-import
operations are human-operator-only and withheld from agent command references;
never provide credentials via command options or `--data`. After caller/org verification, scope requests
with `--org <id>` or `TORNIX_ORG` as needed.

Discover additional command names with `tornix catalog --json`; its output may include human-only
auth, API-key, password-bearing, and account/mailbox deletion operations above, which remain forbidden to the agent.

## Conventions
- Output: add `--json` to any command. Errors go to stderr as `{"error": {...}}` with
  non-zero exit codes (3=auth, 4=not-found, 5=validation, 6=rate-limit/credits).
- Generated backbone: `tornix api <tag> <operation> [--opts] --json` exposes the CLI's
  generated route set, not every backend method. Some webhook/callback and superseded
  operations are omitted; compatibility/proxy groups fold into `data`/`rpc`.
- Escape hatches: `tornix data select <table> --eq col=val --json`, `tornix rpc <fn> --arg k=v --json`.
- Deep research: `tornix deep-research "<question>" --source pmo|web|both --project <id> --json`.
  Default returns a structured cited corpus for you to synthesize; add `--synthesize`
  to have Tornix AI write the report.

## Meetings and video rooms
- For anything with a time or an attendee, use `tornix calendar create`.
- `tornix meetings room-create --name "<name>"` creates an UNSCHEDULED room only
  (for example, "open a room now and send me the link"). Never use it instead of
  booking a calendar event.
- Video rooms live in `video_rooms`, not `chat_rooms`; a team chat is not a meeting room.

## Commands
"""


AGENT_WITHHELD_API_COMMANDS = frozenset({
    ("company-admin", "members-create"),
    ("company-admin", "password"),
    ("company-admin-excel", "apply"),
    ("company-admin-excel", "send-credentials"),
    ("company-admin-talon", "talon-users-create"),
    ("company-admin-talon", "update"),
    ("company-admin-talon", "import"),
    ("users", "change-password"),
    ("users", "delete"),
    ("users", "delete-user"),
    ("users", "delete-google"),
    ("users", "delete-apple"),
    ("company-admin", "delete"),
    ("company-admin-talon", "delete"),
    ("email", "delete"),
    ("email", "connect"),
    ("email", "imap-connect"),
})


def agent_command_allowed(command: str) -> bool:
    """Whether a command path belongs in agent-facing generated references.

    Authentication/session endpoints, API-key lifecycle operations, password-bearing
    routes, and account deletions (including connected mailboxes) remain available to human CLI operators
    but must not be advertised as agent actions.
    """
    parts = command.strip().split()
    if parts[:1] == ["tornix"]:
        parts = parts[1:]
    if not parts:
        return True
    if parts[0] == "auth":
        return len(parts) == 1 or parts == ["auth", "whoami"]
    if parts[0] == "api-keys":
        return False
    if parts[0] == "api" and len(parts) > 1:
        if parts[1] in {"auth", "api-keys"}:
            return False
        if len(parts) > 2 and tuple(parts[1:3]) in AGENT_WITHHELD_API_COMMANDS:
            return False
    return True


def _walk(node: dict, prefix: str, lines: list[str]) -> None:
    if not agent_command_allowed(f"tornix {prefix}"):
        return
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
