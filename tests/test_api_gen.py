import json
from pathlib import Path
import httpx
from click.testing import CliRunner
from tornix_cli.api_gen import build_api_group
from tornix_cli.client import TornixClient
from tornix_cli.config import Config
from tornix_cli.spec import load_spec

FIX = Path(__file__).parent / "fixtures" / "spec_min.json"


def _ctx_obj(handler):
    cfg = Config(api_url="https://x.test", api_key="tk")
    return {"client": TornixClient(cfg, transport=httpx.MockTransport(handler)),
            "json": True}


def test_group_has_tag_subgroups_and_ops():
    grp = build_api_group(json.loads(FIX.read_text()))
    assert "projects" in grp.commands           # folded/excluded tags absent
    assert "postgrest-compatibility" not in grp.commands
    assert "mcp" not in grp.commands
    assert set(grp.commands["projects"].commands) >= {"list", "get"}
    assert set(grp.commands["widgets"].commands) >= {"create"}


def test_path_param_and_query_option_invocation():
    captured = {}

    def handler(req):
        captured["url"] = str(req.url)
        return httpx.Response(200, json={"data": {"id": "p1"}})

    grp = build_api_group(json.loads(FIX.read_text()))
    r = CliRunner().invoke(grp, ["projects", "get", "p1"], obj=_ctx_obj(handler))
    assert r.exit_code == 0, r.output
    assert "/api/v1/projects/p1" in captured["url"]


def test_body_field_invocation():
    captured = {}

    def handler(req):
        captured["json"] = json.loads(req.content)
        return httpx.Response(201, json={"data": {"ok": True}})

    grp = build_api_group(json.loads(FIX.read_text()))
    r = CliRunner().invoke(grp, ["widgets", "create", "--name", "Villa", "--budget", "5"],
                           obj=_ctx_obj(handler))
    assert r.exit_code == 0, r.output
    assert captured["json"] == {"name": "Villa", "budget": 5.0}


# ── empty-body write guard (untitled-row / field-blanking footgun class) ──────
# The pinned NestJS spec under-annotates requestBody on most write ops. The
# generator must not let bare-verb CRUD commands fire with an empty body:
#  - bodyless COLLECTION POST named `create`  → would mint an untitled row
#  - bodyless RESOURCE PUT/PATCH `replace`/`update` → would blank fields
# Both now require --data. Action endpoints (trailing literal or trailing-param
# POST like gantt scheduling) keep working bodyless.

def test_bodyless_collection_create_requires_data():
    """`api risks create p1` (POST /projects/{projectId}/risks, no requestBody)
    must refuse to fire without --data instead of minting an untitled risk."""
    count = {"n": 0}

    def handler(req):
        count["n"] += 1
        return httpx.Response(201, json={"data": {"ok": True}})

    grp = build_api_group(load_spec())
    r = CliRunner().invoke(grp, ["risks", "create", "p1"], obj=_ctx_obj(handler))
    assert r.exit_code != 0
    assert count["n"] == 0

    captured = {}

    def handler2(req):
        captured["json"] = json.loads(req.content)
        captured["path"] = req.url.path
        return httpx.Response(201, json={"data": {"ok": True}})

    r = CliRunner().invoke(grp, ["risks", "create", "p1",
                                 "--data", '{"title": "flood"}'],
                           obj=_ctx_obj(handler2))
    assert r.exit_code == 0, r.output
    assert captured["path"] == "/api/v1/projects/p1/risks"
    assert captured["json"] == {"title": "flood"}


def test_bodyless_resource_replace_requires_data():
    """`api projects replace <id>` (PUT /projects/{id}, no requestBody) used to
    send an empty PUT body — a field-blanking hazard that could not carry a
    payload at all. It must demand --data, and forward it when given."""
    count = {"n": 0}

    def handler(req):
        count["n"] += 1
        return httpx.Response(200, json={"data": {"ok": True}})

    grp = build_api_group(load_spec())
    r = CliRunner().invoke(grp, ["projects", "replace", "p1"], obj=_ctx_obj(handler))
    assert r.exit_code != 0
    assert count["n"] == 0

    captured = {}

    def handler2(req):
        captured["method"] = req.method
        captured["json"] = json.loads(req.content)
        return httpx.Response(200, json={"data": {"ok": True}})

    r = CliRunner().invoke(grp, ["projects", "replace", "p1",
                                 "--data", '{"name": "New"}'],
                           obj=_ctx_obj(handler2))
    assert r.exit_code == 0, r.output
    assert captured["method"] == "PUT"
    assert captured["json"] == {"name": "New"}


def test_bodyless_action_endpoint_still_fires_without_data():
    """Trailing-param POST actions (e.g. gantt schedule) are NOT CRUD creates and
    must keep working with no body, exactly as before the guard."""
    captured = {}

    def handler(req):
        captured["path"] = req.url.path
        captured["content"] = req.content
        return httpx.Response(200, json={"data": {"ok": True}})

    grp = build_api_group(load_spec())
    r = CliRunner().invoke(grp, ["gantt", "schedule-create", "p1"], obj=_ctx_obj(handler))
    assert r.exit_code == 0, r.output
    assert captured["path"] == "/api/v1/gantt/schedule/p1"
    assert captured["content"] in (b"", None)
