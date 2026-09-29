# Tornix CLI

`tornix` is an **agent-native command-line interface** for the Tornix PMO platform
(`app.tornix.ai`). It lets AI agents (Claude Code, Hermes, Pi, OpenCode, OpenClaw, …) and
humans drive the supported Tornix backend surface from the terminal — projects, tasks, procurement,
approvals, risks, cost, meetings, AI features, and multi-source **deep research**.

Built following the [CLI-Anything](https://github.com/HKUDS/CLI-Anything) methodology:
authentic integration against the real backend, dual REPL/subcommand modes, `--json` on
every command, and a generated `SKILL.md` plus per-platform agent installers.

## How it works

The command surface is **generated from the backend's public OpenAPI spec**
(1,290 paths / 1,701 method entries / 93 tags) from the backend GitHub `tal` branch
(`3958c62f`, 102 commits ahead of `main` at sync time). The method-entry total includes
1,658 GET/POST/PUT/PATCH/DELETE entries, 15 HEAD, 14 OPTIONS, and 14 SEARCH entries.
The NestJS exporter omits its global `/api/v1` prefix, so `gen` and `doctor` normalize
routes consistently while preserving `/rest/v1`, `/storage/v1`, and `/api/credits`
compatibility paths. This tracks Talon's GitHub source; routes may be ahead of the
deployed service.

- **Generated backbone** — `tornix api <tag> <operation>` exposes 1,614 generated
  commands; this is not a one-to-one mapping of method entries. Webhook/callback and
  superseded routes are omitted, while compatibility/proxy groups fold into `data`/`rpc`.
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
# Verify the already configured identity; credential setup is not part of the agent workflow.
tornix --json auth whoami

# Discover the generated CLI command catalog.
tornix --json catalog

# Curated commands.
tornix --json projects list --limit 5
tornix --json tasks list --project <project-id>
tornix --json approvals list --status pending

# Generated API routes (supported subset; not every backend method).
tornix --json api cost evm <project-id>

# Generic escape hatches.
tornix --json data select organization_projects --eq status=active --limit 5
tornix --json rpc pmo_overview --arg org_id=<id>

# Deep research.
tornix --json deep-research "Why is the project late?" --project <id> --source both
```

`--json` works **before or after** any subcommand. Without it you get human-readable tables.

## Credential handling

Credential setup is human-operator-only. Do not pass API keys, passwords, or OTPs as command-line arguments; they can appear in shell history or process listings. Agents may verify the configured identity with `tornix auth whoami` but must not run login/logout/key-management commands or handle credentials.

## Configuration

Resolution order: **CLI flag > profile environment > profile config file**. On multi-profile Hermes hosts, config is isolated under `HERMES_HOME/.config/tornix/config.toml`; otherwise set `TORNIX_CONFIG` to a profile-specific file. The single-user fallback is `~/.config/tornix/config.toml`.

| Setting | Flag | Env | Notes |
|---|---|---|---|
| API key | secure profile setup only | `TORNIX_API_KEY` | Never pass the secret as a CLI argument |
| Base URL / profile | `--profile prod\|stage` | `TORNIX_PROFILE`, `TORNIX_API_URL` | `prod` default |
| Organization | `--org <id>`, `config org <id>` | `TORNIX_ORG` | Sent as `X-Organization-ID`; verify membership first |
| JWT (fallback) | secure profile setup only | `TORNIX_TOKEN` | Never pass passwords or OTPs as CLI arguments |
| Config path | — | `HERMES_HOME`, `TORNIX_CONFIG` | Keep profile configs separate |

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
