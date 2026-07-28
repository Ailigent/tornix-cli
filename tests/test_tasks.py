import httpx
from click.testing import CliRunner
from tornix_cli.api_gen import build_api_group
from tornix_cli.commands.tasks import tasks_group
from tornix_cli.client import TornixClient
from tornix_cli.config import Config
from tornix_cli.spec import load_spec


def _obj(handler):
    cfg = Config(api_url="https://x.test", api_key="tk")
    return {"client": TornixClient(cfg, transport=httpx.MockTransport(handler)), "json": True}


def test_tasks_list_filters_by_project():
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        return httpx.Response(200, json={"data": [{"id": "t1"}]})

    r = CliRunner().invoke(tasks_group, ["list", "--project", "p1"], obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert "/projects/p1/tasks" in seen["url"]


def test_tasks_create_rejects_blank_title():
    """Same untitled-row guard as projects create: a blank/whitespace --title is a
    usage error and no request fires."""
    count = {"n": 0}

    def handler(req):
        count["n"] += 1
        return httpx.Response(200, json={"data": {"id": "t1"}})

    r = CliRunner().invoke(tasks_group, ["create", "--project", "p1", "--title", "  "],
                           obj=_obj(handler))
    assert r.exit_code != 0
    assert count["n"] == 0


def test_generated_api_tasks_create_is_removed():
    """Sibling of the projects-create exclusion: POST /projects/{projectId}/tasks
    has no requestBody in the spec, so the generated `api tasks create` could only
    ever mint untitled tasks. The curated `tasks create --title` supersedes it."""
    root = build_api_group(load_spec())
    tasks = root.commands["tasks"]
    assert "create" not in tasks.commands
    # Safe generated siblings remain.
    assert "list" in tasks.commands
    assert "delete" in tasks.commands


# ── curated overlay resync (2026-07) ──────────────────────────────────────
# The backend names the task title field `name`, not `title`. `tasks create`
# was posting {"title": ...}, which the API rejects (name is required) — the
# curated create command was simply broken.

def test_tasks_create_sends_the_field_the_backend_requires():
    seen = {}

    def handler(req):
        import json as _j
        seen["json"] = _j.loads(req.content)
        return httpx.Response(201, json={"data": {"id": "t1"}})

    r = CliRunner().invoke(tasks_group,
                           ["create", "--project", "p1", "--title", "Pour slab"],
                           obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert seen["json"]["name"] == "Pour slab"
    assert "title" not in seen["json"], "backend has no `title` field on tasks"


def test_tasks_create_body_matches_the_spec_schema():
    """Whatever the curated command sends must be a documented body field."""
    from tornix_cli.api_gen import _body_schema
    spec = load_spec()
    op = dict(spec["paths"]["/api/v1/projects/{projectId}/tasks"]["post"])
    op["_method"], op["_path"] = "post", "/api/v1/projects/{projectId}/tasks"
    props = set((_body_schema(op, spec) or {}).get("properties") or {})

    seen = {}

    def handler(req):
        import json as _j
        seen["json"] = _j.loads(req.content)
        return httpx.Response(201, json={"data": {}})

    CliRunner().invoke(tasks_group,
                       ["create", "--project", "p1", "--title", "X", "--assignee", "u1"],
                       obj=_obj(handler))
    assert set(seen["json"]) <= props, f"undocumented fields: {set(seen['json']) - props}"


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


def test_tasks_list_table_shows_the_task_name():
    """Column names must match the payload or the table renders blanks. Driven in
    human (non-json) mode so the actual rendered table is what gets asserted."""
    task = {"id": "t1", "name": "Pour slab", "status": "ACTIVE",
            "assignee_id": "u1", "due_date": "2026-08-01"}

    def handler(req):
        return httpx.Response(200, json={"data": [task]})

    obj = _obj(handler)
    obj["json"] = False
    r = CliRunner().invoke(tasks_group, ["list", "--project", "p1"], obj=obj)
    assert r.exit_code == 0, r.output
    assert "Pour slab" in r.output, r.output
    assert "name" in r.output
