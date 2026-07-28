"""Characterization + contract tests for the `projects` command scope.

These cover the curated `tornix projects ...` commands in
tornix_cli/commands/projects.py, plus one regression guard for the
duplicate-/untitled-project bug Karem reported.

Pattern (matches the rest of the suite): build a shared ctx obj wired to a
TornixClient over an httpx.MockTransport, then drive the command with
CliRunner().invoke(projects_group, [...], obj=obj). The transport handler
inspects the httpx.Request and returns an httpx.Response.
"""
import json

import httpx
from click.testing import CliRunner

from tornix_cli.api_gen import build_api_group
from tornix_cli.client import TornixClient
from tornix_cli.commands.projects import projects_group
from tornix_cli.config import Config
from tornix_cli.errors import TornixError
from tornix_cli.spec import load_spec


def _obj(handler, *, org_id=None):
    cfg = Config(api_url="https://x.test", api_key="tk", org_id=org_id)
    return {"client": TornixClient(cfg, transport=httpx.MockTransport(handler)), "json": True}


# ── list ──────────────────────────────────────────────────────────────────

def test_projects_list_hits_endpoint():
    seen = {}

    def handler(req):
        seen["path"] = req.url.path
        seen["params"] = dict(req.url.params)
        return httpx.Response(200, json={"data": [{"id": "p1", "name": "A"}]})

    r = CliRunner().invoke(projects_group, ["list"], obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert seen["path"] == "/api/v1/projects"
    # No --limit / --status → no query params sent at all.
    assert seen["params"] == {}


def test_projects_list_limit_param():
    seen = {}

    def handler(req):
        seen["params"] = dict(req.url.params)
        return httpx.Response(200, json={"data": []})

    r = CliRunner().invoke(projects_group, ["list", "--limit", "5"], obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert seen["params"] == {"limit": "5"}


def test_projects_list_status_param():
    seen = {}

    def handler(req):
        seen["params"] = dict(req.url.params)
        return httpx.Response(200, json={"data": []})

    r = CliRunner().invoke(projects_group, ["list", "--status", "active"], obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert seen["params"] == {"status": "active"}


def test_projects_list_limit_and_status_params():
    seen = {}

    def handler(req):
        seen["params"] = dict(req.url.params)
        return httpx.Response(200, json={"data": []})

    r = CliRunner().invoke(
        projects_group, ["list", "--limit", "10", "--status", "active"], obj=_obj(handler)
    )
    assert r.exit_code == 0, r.output
    assert seen["params"] == {"limit": "10", "status": "active"}


# ── get / health / members ─────────────────────────────────────────────────

def test_projects_get():
    def handler(req):
        assert req.url.path == "/api/v1/projects/p1"
        assert req.method == "GET"
        return httpx.Response(200, json={"data": {"id": "p1"}})

    r = CliRunner().invoke(projects_group, ["get", "p1"], obj=_obj(handler))
    assert r.exit_code == 0, r.output
    # Envelope is unwrapped: emitted object is the inner data, not {"data": ...}.
    assert json.loads(r.output) == {"id": "p1"}


def test_projects_health():
    seen = {}

    def handler(req):
        seen["path"] = req.url.path
        return httpx.Response(200, json={"data": {"score": 0.9}})

    r = CliRunner().invoke(projects_group, ["health", "p1"], obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert seen["path"] == "/api/v1/projects/p1/health"


def test_projects_members():
    seen = {}

    def handler(req):
        seen["path"] = req.url.path
        return httpx.Response(200, json={"data": [{"id": "u1", "name": "Sam", "role": "owner"}]})

    r = CliRunner().invoke(projects_group, ["members", "p1"], obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert seen["path"] == "/api/v1/projects/p1/members"


# ── create ─────────────────────────────────────────────────────────────────

def test_projects_create_sends_exactly_one_request():
    """Pin: the curated create issues EXACTLY ONE POST (rules out client-side
    duplication; httpx transport retries only re-establish connections, never
    re-send a dispatched request). The untitled-project fix itself is guarded by
    test_generated_api_projects_create_is_removed, and server-side duplication
    by tests/test_projects_e2e.py."""
    count = {"n": 0}
    seen = {}

    def handler(req):
        count["n"] += 1
        seen["method"] = req.method
        seen["path"] = req.url.path
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"data": {"id": "p9", "name": "Alpha"}})

    r = CliRunner().invoke(projects_group, ["create", "--name", "Alpha"], obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert count["n"] == 1, f"expected exactly 1 request, got {count['n']}"
    assert seen["method"] == "POST"
    assert seen["path"] == "/api/v1/projects"


def test_projects_create_body_is_name_only_when_no_description():
    """Body must be EXACTLY {"name": X} — no stray null/"description" key."""
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"data": {"id": "p9", "name": "Alpha"}})

    r = CliRunner().invoke(projects_group, ["create", "--name", "Alpha"], obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert seen["body"] == {"name": "Alpha"}
    assert "description" not in seen["body"]


def test_projects_create_includes_description_when_given():
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"data": {"id": "p9"}})

    r = CliRunner().invoke(
        projects_group,
        ["create", "--name", "Alpha", "--description", "A villa"],
        obj=_obj(handler),
    )
    assert r.exit_code == 0, r.output
    assert seen["body"] == {"name": "Alpha", "description": "A villa"}


def test_projects_create_unwraps_envelope_and_emits_created_object():
    def handler(req):
        return httpx.Response(200, json={"data": {"id": "p9", "name": "Alpha"}})

    r = CliRunner().invoke(projects_group, ["create", "--name", "Alpha"], obj=_obj(handler))
    assert r.exit_code == 0, r.output
    # {"data": {...}} envelope is unwrapped to the bare created object.
    assert json.loads(r.output) == {"id": "p9", "name": "Alpha"}


def test_projects_create_sends_org_header_when_configured():
    seen = {}

    def handler(req):
        seen["org"] = req.headers.get("X-Organization-ID")
        return httpx.Response(200, json={"data": {"id": "p9"}})

    r = CliRunner().invoke(
        projects_group, ["create", "--name", "Alpha"], obj=_obj(handler, org_id="org-42")
    )
    assert r.exit_code == 0, r.output
    assert seen["org"] == "org-42"


def test_projects_create_trims_padded_name():
    """Names are normalized: leading/trailing whitespace is stripped before the
    request (intentional for an agent-driven CLI; documented in --name help)."""
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"data": {"id": "p9"}})

    r = CliRunner().invoke(projects_group, ["create", "--name", "  Alpha  "], obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert seen["body"] == {"name": "Alpha"}


def test_projects_create_requires_name():
    """--name is required; omitting it is a usage error (and sends NO request)."""
    count = {"n": 0}

    def handler(req):
        count["n"] += 1
        return httpx.Response(200, json={"data": {}})

    r = CliRunner().invoke(projects_group, ["create"], obj=_obj(handler))
    assert r.exit_code != 0
    assert count["n"] == 0


# ── update ─────────────────────────────────────────────────────────────────

def test_projects_update_puts_parsed_body():
    seen = {}

    def handler(req):
        seen["method"] = req.method
        seen["path"] = req.url.path
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"data": {"id": "p1", "name": "New"}})

    r = CliRunner().invoke(
        projects_group, ["update", "p1", "--data", '{"name": "New"}'], obj=_obj(handler)
    )
    assert r.exit_code == 0, r.output
    assert seen["method"] == "PUT"
    assert seen["path"] == "/api/v1/projects/p1"
    assert seen["body"] == {"name": "New"}


def test_projects_update_invalid_json_is_usage_error():
    """Bad --data raises click.UsageError → non-zero exit, and no request fires."""
    count = {"n": 0}

    def handler(req):
        count["n"] += 1
        return httpx.Response(200, json={"data": {}})

    r = CliRunner().invoke(
        projects_group, ["update", "p1", "--data", "{not json"], obj=_obj(handler)
    )
    assert r.exit_code != 0
    assert count["n"] == 0


# ── error mapping ───────────────────────────────────────────────────────────

def test_projects_create_400_surfaces_as_nonzero_without_crashing():
    """A 400 backend response becomes a TornixError (handled), not a raw crash."""
    def handler(req):
        return httpx.Response(400, json={"error": {"message": "bad name", "code": "VALIDATION"}})

    r = CliRunner().invoke(projects_group, ["create", "--name", "Alpha"], obj=_obj(handler))
    assert r.exit_code != 0
    # It must be a domain error, not an accidental KeyError/TypeError/etc.
    assert isinstance(r.exception, TornixError)
    assert r.exception.status == 400


def test_projects_get_404_surfaces_as_nonzero_without_crashing():
    def handler(req):
        return httpx.Response(404, json={"error": {"message": "no such project"}})

    r = CliRunner().invoke(projects_group, ["get", "nope"], obj=_obj(handler))
    assert r.exit_code != 0
    assert isinstance(r.exception, TornixError)
    assert r.exception.status == 404


# ── GENERATED escape hatch removed (the untitled-project footgun fix) ─────────

def test_generated_api_projects_create_is_removed():
    """The empty-body footgun is GONE from the generated `api` group.

    The pinned OpenAPI spec carries `requestBody: null` for POST /api/v1/projects,
    so the generated `api projects create` used to emit a create command with NO
    --name option and send an EMPTY body — creating an untitled project. That op
    (operationId ProjectsController_create) is now excluded from the generated
    group because the curated, name-required `tornix projects create --name` fully
    covers it. The agent can no longer reach the empty-body create.
    """
    root = build_api_group(load_spec())

    # The projects subgroup still exists and keeps its safe generated commands…
    proj = root.commands["projects"]
    assert "list" in proj.commands
    assert "delete" in proj.commands
    # …but the footgun create is gone.
    assert "create" not in proj.commands


def test_projects_create_rejects_blank_name():
    """Defense-in-depth: the curated create refuses a blank/whitespace name so an
    agent passing --name "" cannot mint an untitled project. No request fires."""
    count = {"n": 0}

    def handler(req):
        count["n"] += 1
        return httpx.Response(200, json={"data": {"id": "p9"}})

    r = CliRunner().invoke(projects_group, ["create", "--name", "   "], obj=_obj(handler))
    assert r.exit_code != 0
    assert count["n"] == 0


def test_projects_list_table_shows_live_field_names(capsys):
    """The backend renamed these fields; the columns must follow or the table
    renders blanks (the reported symptom)."""
    row = {"project_id": "p1", "name": "TaskFlow", "status": "ACTIVE",
           "budget": 42}

    def handler(req):
        return httpx.Response(200, json={"data": [row]})

    obj = _obj(handler)
    obj["json"] = False
    r = CliRunner().invoke(projects_group, ["list"], obj=obj)
    assert r.exit_code == 0, r.output
    assert "TaskFlow" in r.output and "p1" in r.output
    assert "42" in r.output, r.output
