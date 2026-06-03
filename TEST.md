# Tornix CLI — Test Plan

## Layers

| Layer | Network | When | Command |
|---|---|---|---|
| Unit | None (httpx MockTransport / fixtures) | Always (CI) | `pytest -q` |
| E2E | Live **stage** backend, real API key | Opt-in | `TORNIX_E2E=1 TORNIX_API_KEY=tk_… pytest tests/test_e2e.py -v` |

Unit tests never touch the network — `tornix_cli.client.TornixClient` accepts an
`httpx.MockTransport`, and the spec layer uses `tests/fixtures/spec_min.json`.

## Unit coverage

- `test_errors` — exit-code mapping + error dict shape.
- `test_config` — file/env/profile precedence, save/load round-trip.
- `test_client` — auth + `X-Organization-ID` headers, `{data:…}` envelope unwrap, error mapping.
- `test_output` — `--json` / `--jsonl` / error rendering.
- `test_spec` — tag classification (generate/fold/exclude), `operations_by_tag`, pinned load.
- `test_api_gen` — generated subgroups, path-arg + query-option + body-field invocation.
- `test_data` — `data select` query building, `rpc` arg posting.
- `test_auth` — API-key login persistence, `whoami`.
- `test_catalog` — self-describing tree includes every layer.
- `test_repl` — line parsing.
- `test_main` — root help lists all layers, global `--json`.
- `test_projects` / `test_tasks` / `test_approvals` — curated endpoint shapes
  (projects flat; tasks project-nested; approvals on `/requests` + step decisions).
- `test_deep_research` — PMO corpus assembly (project-nested tasks/risks, citations),
  agent-mode brief JSON.
- `test_skillgen` — SKILL.md frontmatter + command listing.

## E2E (stage) procedure

Requires a stage API key with read scopes. With `TORNIX_E2E=1`:

1. `tornix --json auth whoami` → returns the authenticated user.
2. `tornix --json catalog` → full command tree.
3. `tornix --json projects list --limit 1` → succeeds (read).
4. `tornix --json deep-research "status?" --source pmo` → agent-mode corpus.

### Per-tag smoke (manual / extended)

For broader confidence on the generated backbone, for each tag in
`tornix catalog --json` under `api`, run `tornix api <tag> <list-op> --help` to confirm the
command builds, and one safe **read** per tag (`list`/`get`) against stage. Avoid
credit-consuming AI endpoints except an explicit, opt-in
`tornix deep-research … --synthesize` smoke.

## Notes

- Write operations in E2E should create + immediately clean up (delete) test records, and
  run only against **stage**, never prod.
- The pinned spec (`tornix_cli/generated/_spec.json`) is refreshed with `tornix gen`.
