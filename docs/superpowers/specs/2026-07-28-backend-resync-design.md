# Tornix CLI — Backend Resync (2026-07-28)

## Problem

The CLI's command surface is generated from a pinned OpenAPI snapshot taken 2026-06-04.
The backend has shipped substantially since then, and the CLI has drifted out of sync.

Measured against live `https://app.tornix.ai/api/v1/api-docs/openapi.json`:

| | pinned (2026-06-04) | live (2026-07-28) |
|---|---|---|
| paths | 587 | 777 |
| operations | 816 | 1037 |
| tags | 59 | 72 |

226 operations added, 5 removed, 13 new tags: `access-requests`, `agile` (53 ops),
`app-versions`, `bim`, `data`, `governance`, `link-preview`, `memory`, `pre-project`,
`request-board`, `search`, `templates`, `twin`. Existing tags grew too — `approvals` +22,
`meetings` +15, `risks` +4, `documents` +4.

The 5 removed operations are all `/api/v1/ai/super-agent/*` proxy wildcards (`ai-proxy`).

### Confirmed symptoms

1. **Missing features.** 226 operations have no command.
2. **Command errors.** The curated overlay was hand-written against the June spec and
   never revisited: `tornix tasks list --limit 2` fails with `No such option '--limit'`.
3. **Wrong output shape.** Curated commands hardcode `columns=[...]` that no longer match
   the payload. `projects list` renders empty `id` and `progress` columns because the live
   object uses `project_id` and `success_rate`:

   ```
   ┃ id ┃ name                              ┃ status ┃ progress ┃
   │    │ TaskFlow                          │ ACTIVE │          │
   ```

4. **Stale agent integration.** `SKILL.md`, the Claude Code plugin, and the installers are
   generated from `tornix catalog`, which is built from the June spec — agents are handed a
   surface missing a third of the backend.
5. **New endpoint authentication.** The backend added a 2FA login flow:
   `POST /api/v1/auth/2fa/otp/send` and `POST /api/v1/auth/2fa/verify`. `Verify2faPendingDto`
   requires `{pending_token, code}`, where `pending_token` is documented as *"Short-lived
   2FA-pending token returned by login/callback"*. Today `auth login --email --password`
   reads only `access_token`/`token` from the login response, so on a 2FA-enabled account it
   stores `None` and silently writes a broken config. `api-keys` also gained
   `{id}` GET/PATCH/DELETE and `{id}/usage`.

### Root cause

The curated overlay hardcodes paths, flags, and field names that nothing validates against
the spec. Backend changes therefore surface as silently wrong output rather than as errors.
Re-pinning alone fixes today's drift but not the mechanism, so the same rot recurs on the
next release.

## Scope

Full regeneration across the live spec's 72 tags via the generated backbone. Of those, 66
become `tornix api <tag>` groups; 3 fold into `data`/`rpc` (`PostgREST Compatibility`,
`data-proxy`, `rpc-proxy`) and 3 are excluded (`API Documentation`, `odoo-sync`,
`odoo-sync-admin`) under the existing `FOLD_TAGS`/`EXCLUDE_TAGS` policy, which this change
does not alter.

**Out of scope:** curated ergonomic commands for the new domains (`agile`, `governance`,
`templates`, …). They remain reachable as `tornix api <tag> <op>`. This was considered and
explicitly declined.

## Pin target: prod

Stage (`app-stage.tornix.ai`, 1041 ops) is a strict superset of prod (1037 ops) by four
operations: `DELETE /api/v1/agile/tasks/{taskId}`, `POST /api/v1/agile/tasks/bulk-delete`,
`PUT /api/v1/agile/projects/{projectId}/sprint-cadence`, `GET /api/v1/time-entries/logged-hours`.

Pin **prod**. It matches the CLI's default `prod` profile and the README, and guarantees
every generated command exists in production. Pinning stage would generate four commands
that 404 for anyone on the default profile.

## Design

### 1. Re-pin the spec

`tornix gen --from https://app.tornix.ai` overwrites `tornix_cli/generated/_spec.json`.
The existing `fetch_spec` already validates the scheme (SSRF guard) and that the document is
a real OpenAPI spec. The 5 dead `super-agent` wildcards disappear as a consequence of the
refresh; no exclusion list change is needed.

Verified by dry run: `build_api_group(live_spec)` builds cleanly, producing **1002 commands
across 66 groups** (up from 782/53). No existing command is renamed except the 5 removed
`super-agent` operations, so agent scripts calling current names keep working.

### 2. Fix collision naming

The dry run produced 28 numeric-suffix fallbacks (`kpis-2`, `requests-2`, `workflows-2`,
`get-2`, …). Every one is the same shape — a collection GET colliding with a
single-resource GET:

```
kpis          GET /api/v1/strategic/kpis          ← list
kpis-2        GET /api/v1/strategic/kpis/{id}     ← get one
```

`-2` carries no meaning for an agent, and the count grows with every backend release.

**Fix:** in `_qualified_name`, when a GET's path ends in a path parameter, suffix the
resource name with the read verb — `kpis` (list) and `kpis-get <id>`. This is deterministic,
self-describing, and eliminates all 28 numeric names. It renames no command that does not
currently collide.

Nesting (`api strategic kpis get <id>`) was considered and rejected: it reads better but
renames existing flat commands, breaking agent scripts.

### 3. 2FA login

`auth login --email --password` inspects the login response. When it carries `pending_token`
rather than a session:

1. `POST /api/v1/auth/2fa/otp/send` to dispatch the code.
2. Obtain the code from `--code` when supplied (headless), otherwise prompt interactively.
3. `POST /api/v1/auth/2fa/verify` with `{pending_token, code}` and store the returned token.

A login response that yields neither a session nor a `pending_token` must fail loudly rather
than persist `None` — the current silent-broken-config behaviour is itself a bug.

Add `auth keys get`, `update`, `delete`, and `usage` for the new `api-keys/{id}` operations.

Note: `x-api-key` is declared in the spec only for the five PostgREST-compat operations,
which are folded into `data`/`rpc`. API keys continue to travel as `Authorization: Bearer`
— confirmed working against live.

### 4. Repair the curated overlay

Reconcile every curated command's path, flags, and columns against the re-pinned spec:

- `projects list` — columns → `project_id`, `name`, `status`, `success_rate`.
- `tasks list` — add `--limit`; audit remaining flags against the spec's query parameters.
- `approvals`, `meetings` — same audit for paths, flags, and columns.

### 5. Resilient columns

`show()` (via `emit_result`) drops requested columns absent from the payload and falls back
to the response's own leading keys. A future field rename then degrades to different columns
rather than a silent grid of blanks.

### 6. Drift guard

Two mechanisms, so drift fails loudly instead of rotting:

- **Test:** every curated command's `(method, path)` must exist in the pinned spec. This
  check alone would have caught the June breakage.
- **`tornix doctor`:** fetches the live spec, diffs it against the pinned snapshot, and
  reports added / removed / renamed operations with a non-zero exit on drift.

### 7. Regenerate the agent surface

`tornix skill generate` rewrites `SKILL.md` from the 1002-command catalog; refresh the Claude
Code plugin under `plugins/claude-code/` and the `install/*.sh` installers to match.

## Testing

- Unit tests stay offline, driven by spec fixtures (existing `tests/` convention).
- Collision naming: assert no generated command name ends in a numeric suffix, and that
  `strategic kpis` / `strategic kpis-get` both exist and map to the right paths.
- 2FA: mock a `pending_token` login response and assert the otp/send → verify exchange, plus
  that a response with neither session nor `pending_token` raises instead of storing `None`.
- Columns: assert a payload missing a requested column falls back rather than rendering blanks.
- Drift guard: assert the curated-path test fails against a spec fixture with a renamed path.
- Regression: the 5 `super-agent` commands are gone; previously working command names are
  unchanged.

## Success criteria

- `tornix api` exposes 66 tag groups / ~1002 commands from the prod spec.
- No command name ends in a numeric collision suffix.
- `tornix projects list` renders populated columns.
- `tornix tasks list --limit N` works.
- Login succeeds on a 2FA-enabled account and never persists a null token.
- `SKILL.md` and the plugin describe the current surface.
- The drift guard fails when a curated path leaves the spec.
