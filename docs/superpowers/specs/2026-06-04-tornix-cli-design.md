# Tornix CLI — Design Spec

**Date:** 2026-06-04
**Status:** Approved in principle (pending spec review)
**Author:** Karem + Claude
**Repo:** `~/projects/tornix-cli` (new standalone repo, target remote `Ailigent/tornix-cli`)

---

## 1. Summary

`tornix` is an **agent-native command-line interface** for the Tornix PMO platform
(`app.tornix.ai`). It lets AI agents (Claude Code, Hermes, Pi, OpenCode, …) and humans
drive the full Tornix backend from the terminal: projects, tasks, procurement, approvals,
risks, cost, meetings, AI features, and more.

It follows the **CLI-Anything** methodology (HKUDS): authentic integration against the real
backend, dual REPL/subcommand modes, `--json` on every command for machine consumption, and
a generated `SKILL.md` plus per-platform agent installers. Unlike a hand-reverse-engineered
client, it is **generated from the backend's public OpenAPI spec** and kept in sync, with a
thin curated overlay for ergonomics.

A flagship `tornix deep-research` command performs multi-source research over PMO data and/or
the web and returns a cited report (or a structured corpus for the driving agent to synthesize).

## 2. Goals

- **Full backend coverage** of the Tornix NestJS core API (816 operations across 59 tags),
  minus duplicate/proxy/compat surfaces.
- **Agent-native UX**: every command supports `--json`; stable exit codes; predictable,
  parseable errors; a self-describing `tornix catalog` and generated `SKILL.md`.
- **Human-friendly UX**: ergonomic curated commands for daily-driver domains; pretty tables;
  an interactive REPL.
- **Stay in sync**: regenerate the command surface from the live/pinned OpenAPI spec.
- **Drop-in agent integration**: Claude Code plugin (`/tornix`, `/deep-research`), Hermes/Pi/
  OpenCode installers, optional `cli-hub` publish.
- **Secure headless auth** via scoped API keys.

## 3. Non-goals

- Re-implementing or replacing the existing Tornix **MCP server** (the CLI is a complementary
  agent surface; we do not re-wrap MCP tools).
- Re-exposing the FastAPI AI microservices directly (they are reached through the credit-metered
  NestJS `ai-proxy`; covering them directly would duplicate that surface).
- A GUI, a long-running daemon, or offline mode.
- Write access to internal/webhook/proxy endpoints (Odoo callbacks, LiveKit webhooks, PostgREST
  compat) as first-class commands.

## 4. Target system (verified 2026-06-04 against prod `app.tornix.ai`)

- **Base URL / prefix:** `https://app.tornix.ai`, global prefix `api/v1`. Configurable
  (prod / stage `app-stage.tornix.ai` / LAN dev).
- **Public OpenAPI:** `GET /api/v1/api-docs/openapi.json` is `@Public()`, returns the full
  NestJS spec (587 paths, 816 ops, 59 tags). Responses are wrapped in a `{ "data": … }` envelope.
- **Service manifest:** `GET /api/v1/api-docs/aggregate` lists all services; `GET
  /api/v1/api-docs/spec/:id` returns each spec. Services: `nestjs` (core, 587p) + 14 AI
  microservices (`strategic-navigator` 67p, `ai-planning-engine` 58p, `super-agent`,
  `monte-carlo`, `budget`, `status-reports`, `meeting-analysis`, `project-insights`,
  `document-classifier`, `vendor-offers`, `email-processor`, `contract-extraction`,
  `contract-generation`, `ai-dependency-suggester`, `credit-manager`) + `mcp` (53 tools).
- **Auth:** JWT bearer. Headless path = **scoped API keys** (`/api/v1/api-keys`: create returns
  the raw key once; `GET /scopes` lists permission scopes). Tenant scoping via the
  `X-Organization-ID` header. Password login (`/api/v1/auth/...`) is a fallback to mint a token.
- **Generic data layer:** PostgREST-compat (`/api/v1/data/{table}`) and `rpc` (`/api/v1/rpc/{fn}`)
  exist as escape hatches.

### Coverage & dedup policy

| Surface | Decision |
|---|---|
| NestJS core tags (real domains: projects, tasks, procurement, approvals, risks, cost, cost-control, meetings, gantt, strategy, strategic, notifications, email, credits, time-tracking, users, chat, documents, gis, dashboards, program, portfolio, hr-requests, benefits, organizations, invitations, payments, plan-generation, ai-agents, ai-chat, ai-widgets, …) | **Generate** command groups |
| `PostgREST Compatibility`, `data-proxy`, `rpc-proxy` | **Fold** into generic `tornix data` / `tornix rpc`; do not generate per-op commands |
| `ai-proxy` (credit-metered gateway to AI microservices) | **Keep** as the path to AI features; **do not** also generate the FastAPI microservices directly (duplicate) |
| `mcp` service (53 tools re-wrapping the backend) | **Exclude** (duplicate of the same backend via a different protocol) |
| `storage` vs `storage-compat`, `api-docs`, Odoo `*-callback`, `livekit-webhook` | **Exclude / internal-only** (webhooks, proxies, meta) |
| `(untagged)` ops (29) | Grouped under `misc`, or by URL prefix during codegen |

## 5. Architecture

**Hybrid: generated backbone + curated overlay**, over a shared HTTP client.

```
              ┌─────────────────────────────────────────────┐
  agent / human│                  tornix (Click)             │
              └─────────────────────────────────────────────┘
                 │            │              │            │
          curated overlay  generated     generic      deep-research
        (projects, tasks,  groups (one   data/rpc     (--source pmo|web|both)
         approvals, …)     per OpenAPI    escape
                           tag)           hatch
                 └──────────────┴──────────────┴────────────┘
                                 │
                        client.py (httpx)
            base URL · API-key/JWT auth · X-Organization-ID ·
            {data:…} envelope unwrap · retries · pagination · errors
                                 │
                        Tornix backend (api/v1)
```

- **`client.py`** — single HTTP client: resolves base URL + auth, injects `Authorization` and
  `X-Organization-ID`, unwraps the `{data:…}` envelope, normalizes errors into a stable shape,
  handles retries/timeouts and PostgREST pagination (`Range`/`count`).
- **`generated/`** — codegen output: one module per OpenAPI tag, one Click command per operation.
  Options are derived from path/query/body JSON Schema. A pinned `_spec.json` snapshot is vendored
  so the CLI is reproducible offline; `tornix gen` refreshes it from a URL/file.
- **`commands/`** — curated overlay: small, hand-written, high-ergonomics commands for the
  daily-driver domains, delegating to the generated client functions. Houses `deep_research.py`.
- **`repl.py`** — `repl_skin`-style interactive shell (branded banner, history, persistent
  session/org context, command completion).
- **`output.py`** — rendering contract: human tables by default, `--json` for machine output,
  `--quiet`, consistent exit codes.
- **`config.py` / `auth.py`** — `~/.config/tornix/config.toml`, env overrides, profiles
  (prod/stage), `login`/`logout`/`whoami`.

### Design principles
- The **generated layer guarantees completeness**; the **curated layer guarantees ergonomics**.
- Curated commands never bypass the client — they compose generated client calls.
- Generation is deterministic and re-runnable; no manual edits to `generated/`.

## 6. Command surface

```
tornix
├── auth        login --api-key / --email --password · logout · whoami · keys (list/create/scopes)
├── config      get/set · profiles (prod|stage|dev) · org use <id>
├── catalog     list every command + JSON schema (self-describing; powers SKILL.md)
├── data        <table> select|insert|update|delete           # generic PostgREST escape hatch
├── rpc         <fn> --arg k=v                                  # generic RPC escape hatch
├── gen         refresh generated surface from OpenAPI (url|file)
│
├── projects    list · get · create · update · members · ...    # curated
├── tasks       list · get · create · update · move · comment · ...
├── approvals   list · get · approve · reject · ...
├── procurement requests · plans · pmo · supplier-evaluations · ...
├── risks · cost · cost-control · meetings · gantt · documents · notifications ·
│   credits · time-tracking · users · chat · strategy · portfolio · program · ...   # curated subset
│
├── api         <tag> <operation> [--opts]                      # generated backbone (full coverage)
│
└── deep-research  --source pmo|web|both  [--project/--portfolio] [--synthesize]
```

- **Curated** groups: the ~15 daily-driver domains get friendly verbs/flags.
- **`tornix api <tag> <op>`**: every remaining operation, generated, full coverage.
- **`tornix catalog --json`**: emits the full command tree + parameter schemas so agents (and
  the `SKILL.md` generator) discover capabilities programmatically.

## 7. Output & error contract

- Default: human-readable tables / summaries.
- `--json`: single JSON object/array on stdout, nothing else. `--jsonl` for streamed lists.
- Errors: non-zero exit + a JSON error on stderr when `--json` (`{ "error": { "code", "message",
  "status", "hint" } }`). Exit codes: `0` ok · `1` generic · `2` usage · `3` auth · `4` not-found
  · `5` validation · `6` rate-limit/credits.
- Never print secrets; redact tokens in verbose logs.

## 8. Auth & config

- **Primary:** API key — `tornix auth login --api-key tk_…` (or `TORNIX_API_KEY`). Stored in
  `~/.config/tornix/config.toml` (0600). `tornix auth keys create --scope … --name …` mints one
  via the API and prints the raw key once.
- **Fallback:** `tornix auth login --email … --password …` mints a JWT.
- **Org scoping:** `tornix config org use <id>` or `TORNIX_ORG`; sent as `X-Organization-ID`.
- **Profiles:** prod (default), stage, dev — switch base URL without re-login.
- Precedence: CLI flag > env > config file.

## 9. `deep-research` design

`tornix deep-research "<question>" --source pmo|web|both [--project <id> | --portfolio <id>] [--synthesize]`

- **`--source pmo`**: fan out across the target project/portfolio's tasks, comments, documents,
  meetings (analysis/transcripts), risks, cost/budget, approvals via the API; assemble a
  **structured, citation-tagged corpus** (each fact linked to its Tornix record).
- **`--source web`**: produce a research brief (decomposed sub-questions + search queries). Web
  execution is **delegated to the driving agent's own tools** in agent mode; in `--synthesize`
  mode it uses a configured web provider or the Tornix `super-agent`/`project-insights` endpoint.
- **`--source both`**: merge PMO + web into one corpus/report.
- **Run modes:**
  - **Agent mode (default):** emit structured JSON (corpus + citations + open sub-questions +
    suggested next calls) for the driving agent to synthesize. No LLM calls, no credit use —
    *true agent-native*.
  - **`--synthesize` (standalone):** the CLI calls a Tornix AI endpoint (credit-metered) to write
    a finished, cited Markdown report and prints it.
- Output honors the global `--json` contract; citations reference Tornix record IDs and/or URLs.

## 10. Agent integration

- **`skills/tornix/SKILL.md`** — generated from `tornix catalog`: YAML frontmatter, command
  groups, JSON-parsing guidance, error handling, examples. Canonical + package-local copy.
- **Claude Code plugin** (`plugins/claude-code/`): `/tornix` (run any command) and
  `/deep-research` slash commands; marketplace-installable.
- **Installers** (`install/`): Hermes (skill), Pi (`~/.pi/agent/extensions/`), OpenCode
  (`.opencode/commands/`), OpenClaw (`~/.openclaw/skills/`) — mirroring CLI-Anything's
  per-platform entry points.
- **`cli-hub`** (optional): publish so agents can `cli-hub install tornix`.

## 11. Repo layout

```
tornix-cli/
├── tornix_cli/
│   ├── __main__.py · client.py · config.py · auth.py · output.py · repl.py · catalog.py
│   ├── codegen/            # spec → Click generator
│   ├── generated/          # generated groups + _spec.json (pinned snapshot)
│   └── commands/           # curated overlay incl. deep_research.py
├── skills/tornix/SKILL.md
├── plugins/claude-code/
├── install/                # hermes / pi / opencode / openclaw installers
├── tests/                  # unit (mocked) + e2e (live stage)
├── docs/                   # this spec + generated command reference
├── pyproject.toml          # entry_point: tornix ; pip + cli-hub
└── README.md
```

## 12. Testing

- **Unit** (default, no network): client behavior (auth headers, envelope unwrap, error mapping,
  pagination), output formatting, codegen against fixture specs, config/profile resolution.
- **E2E** (`TORNIX_E2E=1`, against **stage** with a test API key): real auth, `catalog`,
  representative read commands per generated group, a safe write+cleanup cycle, deep-research
  `--source pmo` corpus shape. Hard-fail (not skip) when the env is configured, per CLI-Anything.
- CI runs unit always; e2e gated on secrets.

## 13. Build / release

- `pip install tornix-cli` → `tornix` on PATH (`pyproject.toml`, console_scripts).
- Versioned; `tornix gen` refreshes the pinned spec for a release.
- Optional `cli-hub` registry publish + GitHub repo `Ailigent/tornix-cli` with CI.

## 14. Implementation phases (CLI-Anything 7-phase, to be expanded by writing-plans)

1. **Analysis** — fetch/pin OpenAPI, classify tags (generate vs fold vs exclude), map schemas.
2. **Design** — finalize curated overlay command names/flags; output contract; config schema.
3. **Implementation** — client, config/auth, output, codegen, generated groups, curated overlay,
   `data`/`rpc`, REPL, `catalog`, `deep-research`.
4. **Test planning** — `TEST.md` (unit + e2e matrix).
5. **Test implementation** — unit + e2e suites; run against stage.
6. **Documentation** — generate `SKILL.md`, command reference, README.
7. **Publishing** — `pyproject.toml`, installers, plugin, (optional) cli-hub; validate `tornix` on PATH.

Under ultracode, phases 1/3/5 are orchestrated as workflows (fan out over tags to generate +
adversarially verify each group; verify e2e against live stage).

## 15. Risks & mitigations

- **Spec drift / inaccuracy** → pin `_spec.json`; `tornix gen` to refresh; e2e smoke per group.
- **Untagged / inconsistent operations** → deterministic fallback grouping by URL prefix.
- **AI/credit-metered endpoints in tests** → e2e avoids credit-consuming calls except an explicit,
  opt-in deep-research `--synthesize` smoke.
- **Auth scopes** → respect API-key scopes; surface `403` as exit `3` with a clear hint.
- **Large surface (816 ops)** → generation is the backbone; curated layer stays intentionally small.

## 16. Success criteria

- `tornix catalog --json` lists the full surface; `SKILL.md` generated from it.
- Every generated command supports `--json` and maps 1:1 to a real backend operation.
- Curated overlay covers the ~15 daily-driver domains ergonomically.
- `tornix deep-research --source both` returns a valid corpus (agent mode) and a cited report
  (`--synthesize`).
- An agent (Claude Code) can install the plugin and complete a real PMO task end-to-end via `/tornix`.
- Unit tests green; e2e green against stage.
