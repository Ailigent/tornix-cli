# Tornix CLI Backend Resync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resync the Tornix CLI with the updated backend — re-pin the prod OpenAPI spec (816 → 1037 ops), fix collision naming, support the new 2FA login, repair the drifted curated overlay, and add a drift guard so this cannot silently rot again.

**Architecture:** The CLI generates its `tornix api` backbone from a pinned OpenAPI snapshot at `tornix_cli/generated/_spec.json`. A hand-written "curated overlay" (`tornix_cli/commands/*.py`) provides ergonomic commands for daily-driver domains. The resync fixes the generator's naming rules first (so re-pinning yields clean names), then re-pins, then repairs the overlay and auth, then adds validation that ties the overlay back to the spec.

**Tech Stack:** Python 3.11+, `click` (command tree), `httpx` (HTTP + `MockTransport` in tests), `rich` (tables), `pytest`.

## Global Constraints

- Pin target is **prod**: `https://app.tornix.ai`. Never pin stage.
- Unit tests must run **offline**. Use `httpx.MockTransport`; never hit the network in `tests/`.
- Do not alter `FOLD_TAGS` / `EXCLUDE_TAGS` / `SUPERSEDED_OPS` policy in `tornix_cli/spec.py`.
- Do not rename any generated command that does not currently collide. Agent scripts depend on existing names.
- Every command keeps working with `--json` before or after the subcommand.
- Test pattern (match the existing suite): build a ctx `obj` dict wired to a `TornixClient` over `httpx.MockTransport`, drive with `CliRunner().invoke(group, [...], obj=obj)`.
- Baseline before any change: `84 passed, 8 skipped`.

---

### Task 1: Fix generated-command collision naming

Twenty-eight generated commands fall back to meaningless numeric suffixes (`kpis-2`, `requests-2`, `workflows-2`). Every case is a collection GET colliding with a single-resource GET. Fix the naming rule before re-pinning, so the re-pin produces clean names.

**Files:**
- Modify: `tornix_cli/api_gen.py` (`_qualified_name`, ~lines 55-70)
- Test: `tests/test_api_gen.py`

**Interfaces:**
- Consumes: `_slug(s) -> str`, `_VERB` dict, both already in `tornix_cli/api_gen.py`.
- Produces: `_qualified_name(op: dict, tag: str) -> str | None` — unchanged signature. New behavior: for a GET whose `_path` ends in a path parameter, returns `"<resource>-get"`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_api_gen.py`:

```python
def _mini_spec(paths):
    return {"openapi": "3.0.0", "paths": paths}


def test_collection_and_item_get_do_not_collide_numerically():
    spec = _mini_spec({
        "/api/v1/strategic/kpis": {
            "get": {"operationId": "listKpis", "tags": ["strategic"], "responses": {}},
        },
        "/api/v1/strategic/kpis/{id}": {
            "get": {"operationId": "getKpi", "tags": ["strategic"],
                    "parameters": [{"name": "id", "in": "path",
                                    "schema": {"type": "string"}}],
                    "responses": {}},
        },
    })
    api = build_api_group(spec)
    names = set(api.commands["strategic"].commands)
    assert names == {"kpis", "kpis-get"}


def test_no_generated_command_uses_a_numeric_suffix():
    api = build_api_group(load_spec())
    bad = [f"{tag}.{name}"
           for tag, sub in api.commands.items()
           for name in sub.commands
           if name.rsplit("-", 1)[-1].isdigit()]
    assert bad == [], f"numeric-suffix fallback names remain: {bad}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_api_gen.py -k "collide or numeric" -v`
Expected: FAIL — first test gets `{"kpis", "kpis-2"}`; second lists ~28 names.

- [ ] **Step 3: Implement the naming fix**

In `tornix_cli/api_gen.py`, replace the tail of `_qualified_name`:

```python
    name = _slug("-".join(segs[-2:]))
    # For write methods on a collection, suffix the verb to separate from a GET.
    if op["_method"] in ("post", "patch", "put", "delete"):
        name = f"{name}-{_VERB.get(op['_method'], op['_method'])}" if name else None
    return name or None
```

with:

```python
    name = _slug("-".join(segs[-2:]))
    if not name:
        return None
    # For write methods on a collection, suffix the verb to separate from a GET.
    if op["_method"] in ("post", "patch", "put", "delete"):
        return f"{name}-{_VERB.get(op['_method'], op['_method'])}"
    # A GET whose path ends in a parameter is a single-resource read colliding
    # with its own collection GET (`/strategic/kpis` vs `/strategic/kpis/{id}`).
    # Suffix the read verb rather than falling back to a meaningless `-2`.
    if op["_method"] == "get" and op["_path"].rstrip("/").split("/")[-1].startswith("{"):
        return f"{name}-{_VERB['get_one']}"
    return name
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_api_gen.py -v`
Expected: PASS. Then `python3 -m pytest -q` → no regressions (84 passed baseline).

- [ ] **Step 5: Commit**

```bash
git add tornix_cli/api_gen.py tests/test_api_gen.py
git commit -m "fix(api-gen): name item-GET collisions '<resource>-get' instead of '-2'"
```

---

### Task 2: Re-pin the prod OpenAPI spec

**Files:**
- Modify: `tornix_cli/generated/_spec.json` (regenerated, not hand-edited)
- Test: `tests/test_spec.py`

**Interfaces:**
- Consumes: `load_spec() -> dict` and `fetch_spec(base_url: str, timeout: float = 30.0) -> dict` from `tornix_cli/spec.py`; `build_api_group(spec: dict) -> click.Group` from Task 1.
- Produces: a pinned spec with 777 paths / 1037 operations / 72 tags.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_spec.py`:

```python
def test_pinned_spec_is_current_prod_surface():
    spec = load_spec()
    ops = [(m, p) for p, ms in spec["paths"].items() for m in ms
           if m in ("get", "post", "put", "patch", "delete")]
    assert len(spec["paths"]) == 777
    assert len(ops) == 1037


def test_pinned_spec_covers_the_new_backend_tags():
    tags = {(op.get("tags") or ["misc"])[0]
            for ms in load_spec()["paths"].values() for op in ms.values()
            if isinstance(op, dict)}
    for new in ("agile", "governance", "templates", "memory", "twin",
                "request-board", "search", "bim", "pre-project",
                "access-requests", "app-versions", "link-preview", "data"):
        assert new in tags, f"missing new backend tag: {new}"


def test_dead_super_agent_proxy_ops_are_gone():
    assert "/api/v1/ai/super-agent/*" not in load_spec()["paths"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_spec.py -k "current_prod or new_backend or super_agent" -v`
Expected: FAIL — 587 paths / 816 ops, new tags absent, `super-agent` path present.

- [ ] **Step 3: Re-pin from prod**

```bash
tornix gen --from https://app.tornix.ai
```

If the installed `tornix` binary is stale, run the module directly instead:

```bash
python3 -c "
import json, pathlib
from tornix_cli.spec import fetch_spec
spec = fetch_spec('https://app.tornix.ai')
pathlib.Path('tornix_cli/generated/_spec.json').write_text(json.dumps(spec))
print('paths', len(spec['paths']))
"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest -q`
Expected: PASS, including Task 1's `test_no_generated_command_uses_a_numeric_suffix` now
running against the full 1037-op spec.

Then confirm the surface built as designed:

```bash
python3 -c "
from tornix_cli.api_gen import build_api_group
from tornix_cli.spec import load_spec
g = build_api_group(load_spec())
print('groups', len(g.commands), 'commands', sum(len(s.commands) for s in g.commands.values()))
"
```
Expected: `groups 66 commands 1002` (±small drift if the backend moved since; the numeric-suffix test is the real gate).

- [ ] **Step 5: Commit**

```bash
git add tornix_cli/generated/_spec.json tests/test_spec.py
git commit -m "feat(spec): re-pin prod OpenAPI snapshot (816 -> 1037 ops, 13 new tags)"
```

---

### Task 3: Make table columns resilient to backend field renames

`projects list` renders empty `id` and `progress` columns because the payload now uses
`project_id` and `success_rate`. Requested columns that do not exist must not render as a
grid of blanks.

**Files:**
- Modify: `tornix_cli/output.py` (`_render_human`, ~lines 68-80)
- Test: `tests/test_output.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `_render_human(data, columns)` — unchanged signature. New behavior: keeps only
  requested columns present in at least one row; if none survive, falls back to the first 8
  keys of the first row.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_output.py`:

```python
from tornix_cli.output import emit


def test_missing_requested_columns_are_dropped(capsys):
    rows = [{"project_id": "p1", "name": "TaskFlow", "success_rate": 42}]
    emit(rows, columns=["id", "name", "progress"])
    out = capsys.readouterr().out
    assert "name" in out and "TaskFlow" in out
    assert "progress" not in out
    assert "id" not in out


def test_all_columns_missing_falls_back_to_payload_keys(capsys):
    rows = [{"project_id": "p1", "success_rate": 42}]
    emit(rows, columns=["id", "progress"])
    out = capsys.readouterr().out
    assert "project_id" in out and "p1" in out


def test_present_columns_are_still_honored_in_order(capsys):
    rows = [{"b": 2, "a": 1}]
    emit(rows, columns=["a", "b"])
    out = capsys.readouterr().out
    assert out.index("a") < out.index("b")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_output.py -k "missing or fallback or honored" -v`
Expected: FAIL — `progress`/`id` headers render as empty columns.

- [ ] **Step 3: Implement resilient column selection**

In `tornix_cli/output.py`, replace this line in `_render_human`:

```python
        cols = columns or list(data[0].keys())[:8]
```

with:

```python
        cols = _resolve_columns(data, columns)
```

and add above `_fmt`:

```python
def _resolve_columns(rows: list, columns: list[str] | None) -> list[str]:
    """Keep only requested columns the payload actually has, so a backend field
    rename degrades to different columns instead of a grid of blanks."""
    fallback = list(rows[0].keys())[:8]
    if not columns:
        return fallback
    present = {k for row in rows if isinstance(row, dict) for k in row}
    kept = [c for c in columns if c in present]
    return kept or fallback
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_output.py -v && python3 -m pytest -q`
Expected: PASS, no regressions.

- [ ] **Step 5: Commit**

```bash
git add tornix_cli/output.py tests/test_output.py
git commit -m "fix(output): drop requested columns absent from the payload"
```

---

### Task 4: Repair the curated overlay against the re-pinned spec

**Files:**
- Modify: `tornix_cli/commands/projects.py` (columns in `projects_list`, `projects_members`)
- Modify: `tornix_cli/commands/tasks.py` (`tasks_list` — add `--limit`, fix columns)
- Modify: `tornix_cli/commands/approvals.py`, `tornix_cli/commands/meetings.py` (columns)
- Test: `tests/test_projects.py`, `tests/test_tasks.py`

**Interfaces:**
- Consumes: `client(obj)` and `show(obj, data, columns=None)` from `tornix_cli/commands/_helpers.py`.
- Produces: no new symbols; command flags change only additively.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_tasks.py`:

```python
def test_tasks_list_supports_limit():
    seen = {}

    def handler(req):
        seen["params"] = dict(req.url.params)
        return httpx.Response(200, json={"data": []})

    r = CliRunner().invoke(tasks_group,
                           ["list", "--project", "p1", "--limit", "5"],
                           obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert seen["params"]["limit"] == "5"
```

Add to `tests/test_projects.py`:

```python
def test_projects_list_columns_match_the_live_payload():
    from tornix_cli.commands import projects as projects_mod
    src = inspect.getsource(projects_mod.projects_list)
    assert "project_id" in src
    assert "success_rate" in src
```

(Add `import inspect` at the top of `tests/test_projects.py` if absent.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_tasks.py tests/test_projects.py -k "limit or columns_match" -v`
Expected: FAIL — `No such option '--limit'`; `project_id` absent from the source.

- [ ] **Step 3: Implement the repairs**

In `tornix_cli/commands/projects.py`, change `projects_list`'s `show(...)` call to:

```python
    show(obj, client(obj).get("/api/v1/projects", params=params or None),
         columns=["project_id", "name", "status", "success_rate"])
```

In `tornix_cli/commands/tasks.py`, replace the `tasks_list` command with:

```python
@tasks_group.command("list", help="List tasks in a project.")
@click.option("--project", "project_id", required=True, help="Project id (tasks are nested).")
@click.option("--status", default=None)
@click.option("--limit", type=int, default=None, help="Maximum number of tasks to return.")
@click.pass_obj
def tasks_list(obj, project_id, status, limit):
    params = {}
    if status:
        params["status"] = status
    if limit is not None:
        params["limit"] = limit
    show(obj, client(obj).get(f"/api/v1/projects/{project_id}/tasks", params=params or None),
         columns=["id", "title", "status", "assignee_id", "due_date"])
```

Task 3 makes any stale column in `approvals.py` / `meetings.py` / `projects_members`
degrade gracefully, so leave those column lists alone unless the drift-guard test in Task 6
flags their **paths**.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_tasks.py tests/test_projects.py -v && python3 -m pytest -q`
Expected: PASS.

Verify against the real backend:

```bash
tornix projects list --limit 3
tornix --json tasks list --project <a real project id> --limit 2
```
Expected: `projects list` shows populated `project_id` and `success_rate` columns; `tasks list --limit` no longer errors.

- [ ] **Step 5: Commit**

```bash
git add tornix_cli/commands/projects.py tornix_cli/commands/tasks.py tests/test_projects.py tests/test_tasks.py
git commit -m "fix(curated): correct project columns and add 'tasks list --limit'"
```

---

### Task 5: Support the backend's new 2FA login flow

`auth login --email --password` reads only `access_token`/`token`. On a 2FA-enabled account
the backend returns a `pending_token` instead, so the CLI stores `None` and silently writes a
broken config.

**Files:**
- Modify: `tornix_cli/auth.py` (`login`, plus new `keys` subcommands)
- Test: `tests/test_auth.py`

**Interfaces:**
- Consumes: `client.post(path, json=...)`, `client.get(path)`, `Config.save()`.
- Produces: `login` gains `--code TEXT`. New commands `auth keys get <key_id>`,
  `auth keys update <key_id> --data <json>`, `auth keys delete <key_id>`,
  `auth keys usage <key_id>`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_auth.py`:

```python
def test_login_completes_the_2fa_challenge():
    calls = []

    def handler(req):
        calls.append(req.url.path)
        if req.url.path == "/api/v1/auth/login":
            return httpx.Response(200, json={"data": {"pending_token": "pt-1"}})
        if req.url.path == "/api/v1/auth/2fa/otp/send":
            return httpx.Response(200, json={"data": {"sent": True}})
        if req.url.path == "/api/v1/auth/2fa/verify":
            body = json.loads(req.content)
            assert body == {"pending_token": "pt-1", "code": "123456"}
            return httpx.Response(200, json={"data": {"access_token": "real-token"}})
        return httpx.Response(200, json={"data": {"id": "u1"}})

    obj = _obj(handler)
    r = CliRunner().invoke(
        auth_group,
        ["login", "--email", "a@b.c", "--password", "pw", "--code", "123456"],
        obj=obj)
    assert r.exit_code == 0, r.output
    assert "/api/v1/auth/2fa/otp/send" in calls
    assert "/api/v1/auth/2fa/verify" in calls
    assert obj["config"].token == "real-token"


def test_login_never_stores_a_null_token():
    def handler(req):
        if req.url.path == "/api/v1/auth/login":
            return httpx.Response(200, json={"data": {"unexpected": True}})
        return httpx.Response(200, json={"data": {"id": "u1"}})

    obj = _obj(handler)
    r = CliRunner().invoke(
        auth_group, ["login", "--email", "a@b.c", "--password", "pw"], obj=obj)
    assert r.exit_code != 0
    assert obj["config"].token is None


def test_keys_usage_hits_the_usage_endpoint():
    seen = {}

    def handler(req):
        seen["path"] = req.url.path
        return httpx.Response(200, json={"data": {"calls": 7}})

    r = CliRunner().invoke(auth_group, ["keys", "usage", "k1"], obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert seen["path"] == "/api/v1/api-keys/k1/usage"
```

The `_obj` helper in `tests/test_auth.py` must expose the `Config` it builds so the
assertions above can read `obj["config"]`. If it does not already, update it to:

```python
def _obj(handler):
    cfg = Config(api_url="https://x.test")
    return {"config": cfg,
            "client": TornixClient(cfg, transport=httpx.MockTransport(handler)),
            "json": True}
```

Ensure `tests/test_auth.py` imports `json`, `httpx`, `CliRunner`, `TornixClient`, `Config`,
and `auth_group`.

To keep the test from writing to the developer's real config file, add this fixture to
`tests/conftest.py`:

```python
import pytest


@pytest.fixture(autouse=True)
def _isolate_config(tmp_path, monkeypatch):
    """Never touch the developer's real ~/.config/tornix/config.toml during tests."""
    monkeypatch.setattr("tornix_cli.config.CONFIG_PATH", tmp_path / "config.toml")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_auth.py -k "2fa or null_token or usage" -v`
Expected: FAIL — no `--code` option, no 2FA calls, no `keys usage` command.

- [ ] **Step 3: Implement 2FA login and the new key commands**

In `tornix_cli/auth.py`, add a helper above `login`:

```python
def _session_token(payload) -> str | None:
    p = payload or {}
    return p.get("access_token") or p.get("token")


def _complete_2fa(client, pending_token: str, code: str | None) -> str:
    """Exchange a 2FA-pending token for a real session token."""
    client.post("/api/v1/auth/2fa/otp/send", json={"pending_token": pending_token})
    if not code:
        code = click.prompt("2FA code", hide_input=False)
    verified = client.post("/api/v1/auth/2fa/verify",
                           json={"pending_token": pending_token, "code": code})
    token = _session_token(verified)
    if not token:
        raise click.ClickException("2FA verification did not return a session token.")
    return token
```

Add the option to the `login` command:

```python
@click.option("--code", default=None,
              help="2FA code (for headless login on a 2FA-enabled account).")
```

and change its signature to `def login(obj, api_key, email, password, code):`, replacing the
`elif email and password:` branch with:

```python
    elif email and password:
        resp = client.post("/api/v1/auth/login",
                           json={"email": email, "password": password})
        token = _session_token(resp)
        if not token:
            pending = (resp or {}).get("pending_token")
            if not pending:
                raise click.ClickException(
                    "login returned neither a session token nor a 2FA pending_token.")
            token = _complete_2fa(client, pending, code)
        cfg.token = token
        client.config.token = token
```

Append the new key commands to `tornix_cli/auth.py`:

```python
@keys.command("get", help="Show one API key by id.")
@click.argument("key_id")
@click.pass_obj
def keys_get(obj, key_id):
    emit(obj["client"].get(f"/api/v1/api-keys/{key_id}"), json_mode=obj.get("json"))


@keys.command("update", help="Update an API key (PATCH) with a JSON body.")
@click.argument("key_id")
@click.option("--data", "raw", required=True, help="JSON body (PATCH).")
@click.pass_obj
def keys_update(obj, key_id, raw):
    import json as _j
    try:
        payload = _j.loads(raw)
    except _j.JSONDecodeError as e:
        raise click.UsageError(f"invalid JSON for --data: {e}")
    emit(obj["client"].patch(f"/api/v1/api-keys/{key_id}", json=payload),
         json_mode=obj.get("json"))


@keys.command("delete", help="Delete an API key by id.")
@click.argument("key_id")
@click.pass_obj
def keys_delete(obj, key_id):
    emit(obj["client"].delete(f"/api/v1/api-keys/{key_id}"), json_mode=obj.get("json"))


@keys.command("usage", help="Show usage statistics for an API key.")
@click.argument("key_id")
@click.pass_obj
def keys_usage(obj, key_id):
    emit(obj["client"].get(f"/api/v1/api-keys/{key_id}/usage"), json_mode=obj.get("json"))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_auth.py -v && python3 -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tornix_cli/auth.py tests/test_auth.py tests/conftest.py
git commit -m "feat(auth): complete the backend's 2FA login challenge; add api-key {id} commands"
```

---

### Task 6: Add the drift guard

The root cause is that nothing ties the hand-written curated overlay back to the spec. Two
mechanisms: a test that fails when a curated path leaves the spec, and a `tornix doctor`
command that diffs pinned against live.

**Files:**
- Create: `tornix_cli/doctor.py`
- Create: `tests/test_doctor.py`
- Create: `tests/test_drift.py`
- Modify: `tornix_cli/__main__.py` (register `doctor`)

**Interfaces:**
- Consumes: `load_spec()`, `fetch_spec(base_url)` from `tornix_cli/spec.py`; `emit` from `tornix_cli/output.py`.
- Produces:
  - `spec_operations(spec: dict) -> set[tuple[str, str]]` — `{(method, path)}`, method lowercase.
  - `diff_specs(pinned: dict, live: dict) -> dict` — `{"added": [...], "removed": [...], "pinned_ops": int, "live_ops": int, "in_sync": bool}` where `added`/`removed` are sorted `[method, path]` lists.
  - `doctor_command` — a `click.Command` named `doctor`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_drift.py`:

```python
"""The curated overlay is hand-written; nothing else ties it back to the spec.
This test is the guard that would have caught the June 2026 drift."""
import re
from pathlib import Path

import pytest

from tornix_cli.spec import load_spec

CURATED = Path(__file__).resolve().parent.parent / "tornix_cli" / "commands"

# Paths the curated overlay calls, as (method, path) with {param} placeholders.
CALL = re.compile(r"""\.(get|post|put|patch|delete)\(\s*f?["']([^"']+)["']""")


def _spec_paths():
    return set(load_spec()["paths"])


def _normalize(path: str) -> str:
    """f-string interpolations -> spec-style placeholders: {project_id} stays a
    placeholder, and any placeholder name matches any spec placeholder name."""
    return re.sub(r"\{[^}]+\}", "{}", path)


@pytest.mark.parametrize("source", sorted(CURATED.glob("*.py")))
def test_curated_commands_only_call_paths_the_spec_defines(source):
    spec_norm = {_normalize(p): p for p in _spec_paths()}
    missing = []
    for method, path in CALL.findall(source.read_text()):
        if not path.startswith("/api/"):
            continue
        if _normalize(path) not in spec_norm:
            missing.append(f"{method.upper()} {path}")
    assert not missing, f"{source.name} calls paths absent from the pinned spec: {missing}"
```

Create `tests/test_doctor.py`:

```python
from tornix_cli.doctor import diff_specs, spec_operations

PINNED = {"paths": {
    "/api/v1/a": {"get": {}},
    "/api/v1/gone": {"post": {}},
}}
LIVE = {"paths": {
    "/api/v1/a": {"get": {}},
    "/api/v1/new": {"put": {}},
}}


def test_spec_operations_extracts_method_path_pairs():
    assert spec_operations(PINNED) == {("get", "/api/v1/a"), ("post", "/api/v1/gone")}


def test_spec_operations_ignores_non_http_keys():
    spec = {"paths": {"/x": {"get": {}, "parameters": [], "summary": "n/a"}}}
    assert spec_operations(spec) == {("get", "/x")}


def test_diff_specs_reports_added_and_removed():
    d = diff_specs(PINNED, LIVE)
    assert d["added"] == [["put", "/api/v1/new"]]
    assert d["removed"] == [["post", "/api/v1/gone"]]
    assert d["pinned_ops"] == 2 and d["live_ops"] == 2
    assert d["in_sync"] is False


def test_diff_specs_in_sync_when_identical():
    d = diff_specs(PINNED, PINNED)
    assert d["added"] == [] and d["removed"] == [] and d["in_sync"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_doctor.py tests/test_drift.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tornix_cli.doctor'`. `test_drift.py`
should already PASS after Task 4; if it fails, it has found a genuinely stale curated path —
fix the path before continuing.

- [ ] **Step 3: Implement the doctor module**

Create `tornix_cli/doctor.py`:

```python
from __future__ import annotations

import click

from .output import emit
from .spec import fetch_spec, load_spec

_HTTP = ("get", "post", "put", "patch", "delete")


def spec_operations(spec: dict) -> set[tuple[str, str]]:
    """Every (method, path) pair an OpenAPI document defines."""
    return {(m.lower(), p)
            for p, methods in (spec.get("paths") or {}).items()
            for m in methods if m.lower() in _HTTP}


def diff_specs(pinned: dict, live: dict) -> dict:
    """Compare the pinned snapshot against a live spec."""
    p, l = spec_operations(pinned), spec_operations(live)
    added = sorted([m, path] for m, path in l - p)
    removed = sorted([m, path] for m, path in p - l)
    return {"pinned_ops": len(p), "live_ops": len(l),
            "added": added, "removed": removed,
            "in_sync": not added and not removed}


@click.command("doctor", help="Diff the pinned OpenAPI snapshot against a live backend.")
@click.option("--from", "src", default=None,
              help="Base URL to check against (defaults to the active profile).")
@click.pass_obj
def doctor_command(obj, src):
    base = src or obj["config"].api_url
    try:
        live = fetch_spec(base)
    except ValueError as e:
        raise click.UsageError(str(e))
    report = diff_specs(load_spec(), live)
    report["checked"] = base
    emit(report, json_mode=obj.get("json"))
    if not report["in_sync"]:
        raise SystemExit(1)
```

In `tornix_cli/__main__.py`, add the import beside the other `from .` imports:

```python
from .doctor import doctor_command
```

and register it in the "Assemble layers" block, before `add_json_option(cli)`:

```python
cli.add_command(doctor_command)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_doctor.py tests/test_drift.py -v && python3 -m pytest -q`
Expected: PASS.

Verify the command against the real backend:

```bash
tornix --json doctor --from https://app.tornix.ai
```
Expected: `"in_sync": true` and exit 0 immediately after Task 2's re-pin.

- [ ] **Step 5: Commit**

```bash
git add tornix_cli/doctor.py tornix_cli/__main__.py tests/test_doctor.py tests/test_drift.py
git commit -m "feat(doctor): add spec drift guard command and curated-path test"
```

---

### Task 7: Regenerate the agent-facing surface

`SKILL.md`, the Claude Code plugin, and the README all describe the June command surface.

The `install/*.sh` scripts and the Claude Code plugin do **not** embed a command list —
the installers call `tornix skill generate` and the plugin delegates to `tornix catalog
--json`, so both self-update once the spec is re-pinned. They do carry one stale fact: they
document API keys as `tk_…`, but real keys are `tnx_…` (verified against a live key).

**Files:**
- Modify: `skills/tornix/SKILL.md` (regenerated, not hand-edited)
- Modify: `README.md` (op/tag counts, key prefix, 2FA login, `doctor`)
- Modify: `tornix_cli/skillgen.py` (key prefix in the `HEADER` constant)
- Modify: `plugins/claude-code/README.md`, `plugins/claude-code/commands/tornix.md`, `install/opencode.sh` (key prefix)
- Test: `tests/test_skillgen.py`

**Interfaces:**
- Consumes: `render_skill(catalog: dict) -> str` from `tornix_cli/skillgen.py`; `_describe` from `tornix_cli/catalog.py`.
- Produces: no new symbols.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_skillgen.py`:

```python
def test_generated_skill_covers_the_new_backend_domains():
    from tornix_cli.__main__ import cli
    from tornix_cli.catalog import _describe
    from tornix_cli.skillgen import render_skill

    content = render_skill(_describe(cli, "tornix"))
    for domain in ("agile", "governance", "templates", "memory"):
        assert f"tornix api {domain} " in content, f"SKILL.md missing {domain}"
    assert "-2 " not in content, "SKILL.md still advertises numeric-suffix command names"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_skillgen.py -k new_backend_domains -v`
Expected: PASS if Tasks 1-2 landed (the catalog is built live from the pinned spec). If it
FAILS, the re-pin did not take — re-check Task 2 before continuing.

- [ ] **Step 3: Regenerate SKILL.md and update the README**

```bash
tornix skill generate
```

If the installed binary is stale, reinstall first: `pip install --user -e .`

Fix the stale key prefix everywhere it appears (SKILL.md's copy comes from `skillgen.py`'s
`HEADER`, so change the source and regenerate — do not hand-edit `skills/tornix/SKILL.md`):

```bash
sed -i 's/tk_…/tnx_…/g' README.md plugins/claude-code/README.md \
    plugins/claude-code/commands/tornix.md install/opencode.sh tornix_cli/skillgen.py
tornix skill generate      # re-render SKILL.md from the corrected HEADER
grep -rn 'tk_' README.md plugins install skills tornix_cli   # expect no matches
```

Then update `README.md`:
- Replace "587 paths / 816 operations / 59 tags" with "777 paths / 1037 operations / 72 tags".
- In the Quickstart auth block, document the 2FA path:
  ```bash
  # 2FA-enabled accounts: pass --code for headless login (otherwise you're prompted).
  tornix auth login --email you@example.com --password … --code 123456
  ```
- Add to the Development section:
  ```bash
  tornix doctor                   # diff the pinned spec against the live backend
  ```

- [ ] **Step 4: Verify**

Run: `python3 -m pytest -q`
Expected: PASS.

```bash
grep -c '^- `tornix ' skills/tornix/SKILL.md
```
Expected: roughly 1000+ command lines (up from the June ~800).

- [ ] **Step 5: Commit**

```bash
git add skills/tornix/SKILL.md README.md tornix_cli/skillgen.py plugins install tests/test_skillgen.py
git commit -m "docs: regenerate SKILL.md for the 1002-command surface; fix tk_ -> tnx_ key prefix; document 2FA and doctor"
```

---

## Final Verification

- [ ] `python3 -m pytest -q` — all green, count strictly above the 84-passed baseline.
- [ ] `tornix --json doctor` — `"in_sync": true`.
- [ ] `tornix projects list --limit 3` — populated `project_id` / `success_rate` columns.
- [ ] `tornix --json tasks list --project <id> --limit 2` — succeeds.
- [ ] `tornix api strategic kpis-get --help` — exists; no `kpis-2` anywhere in `tornix catalog`.
- [ ] `tornix api agile --help` — the new domain is reachable.
