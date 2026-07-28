# Tornix CLI

`tornix` is an **agent-native command-line interface** for the Tornix PMO platform
(`app.tornix.ai`). It lets AI agents (Claude Code, Hermes, Pi, OpenCode, OpenClaw, …) and
humans drive the full Tornix backend from the terminal — projects, tasks, procurement,
approvals, risks, cost, meetings, AI features, and multi-source **deep research**.

Built following the [CLI-Anything](https://github.com/HKUDS/CLI-Anything) methodology:
authentic integration against the real backend, dual REPL/subcommand modes, `--json` on
every command, and a generated `SKILL.md` plus per-platform agent installers.

## How it works

The command surface is **generated from the backend's public OpenAPI spec**
(777 paths / 1037 operations / 72 tags), so it covers the whole API and stays in sync:

- **Generated backbone** — `tornix api <tag> <operation>` covers every backend operation.
- **Curated overlay** — ergonomic commands for daily-driver domains: `projects`, `tasks`,
  `approvals`, `meetings`, plus `deep-research`.
- **Escape hatches** — `tornix data select <table> …` and `tornix rpc <fn> …`.

Duplicate/proxy surfaces (PostgREST-compat, the MCP re-wrap, internal FastAPI services
reached via the credit-metered AI proxy) are excluded.

## Install

```bash
pip install tornix-cli          # or: pipx install tornix-cli
```

> Not yet published to PyPI? Install from source: `git clone … && cd tornix-cli && pip install .`
> (use `pip install --break-system-packages .` on Debian/Ubuntu system Python).

## Quickstart

```bash
# Authenticate with a scoped API key (created in the Tornix web app, or via the CLI).
tornix auth login --api-key tnx_…           # or: export TORNIX_API_KEY=tnx_…
tornix --json auth whoami

# Email/password login. On a 2FA-enabled account the CLI sends the OTP and
# prompts for the code; pass --code to stay headless.
tornix auth login --email you@example.com --password … [--code 123456]

# Discover the whole surface (great for agents).
tornix --json catalog

# Curated commands.
tornix --json projects list --limit 5
tornix --json tasks list --project <project-id>
tornix --json approvals list --status pending

# Full backbone (anything the backend can do).
tornix --json api cost evm <project-id>

# Generic escape hatches.
tornix --json data select organization_projects --eq status=active --limit 5
tornix --json rpc pmo_overview --arg org_id=<id>

# Deep research.
tornix --json deep-research "Why is the project late?" --project <id> --source both
```

`--json` works **before or after** any subcommand. Without it you get human-readable tables.

## Configuration

Resolution order: **CLI flag > environment > config file** (`~/.config/tornix/config.toml`).

| Setting | Flag | Env | Notes |
|---|---|---|---|
| API key | `auth login --api-key` | `TORNIX_API_KEY` | Primary, headless auth |
| Base URL / profile | `--profile prod\|stage` | `TORNIX_PROFILE`, `TORNIX_API_URL` | `prod` default |
| Organization | `--org <id>`, `config org <id>` | `TORNIX_ORG` | Sent as `X-Organization-ID` |
| JWT (fallback) | `auth login --email --password` | `TORNIX_TOKEN` | Mints a token |

## Exit codes

`0` ok · `1` generic · `2` usage · `3` auth (401/403) · `4` not-found · `5` validation · `6` rate-limit/credits.
Errors print to stderr as `{"error": {"code","message","status","hint"}}` under `--json`.

## Deep research

`tornix deep-research "<question>" --source pmo|web|both [--project <id>|--portfolio <id>] [--synthesize]`

- Default (**agent mode**): emits a structured, citation-tagged corpus (PMO records and/or a
  web research brief) plus sub-questions and instructions, for the *driving agent* to
  synthesize. No LLM calls, no credit use.
- `--synthesize` (**standalone**): calls the Tornix AI endpoint to write a finished, cited
  report and prints it (uses credits).

PMO facts are cited as `tornix://<kind>/<id>`; web facts by URL.

## Agent integration

- **Claude Code** — `plugins/claude-code/` exposes `/tornix` and `/deep-research`.
- **Installers** — `install/{hermes,pi,opencode,openclaw}.sh` drop a generated `SKILL.md`
  (or slash commands) into each platform.
- **SKILL.md** — regenerate any time with `tornix skill generate` (built from
  `tornix catalog`).

## Development

```bash
pip install -e ".[dev]"
pytest -q                       # unit tests (no network)
tornix doctor                   # diff the pinned snapshot against a live backend
tornix gen                      # refresh the pinned OpenAPI snapshot
```

See `TEST.md` for the full test plan and `docs/superpowers/` for the design spec and plan.
