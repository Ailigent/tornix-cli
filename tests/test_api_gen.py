import json

import click
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


def test_collision_names_prefer_reads_over_deletes():
    """When several methods on one path contest a bare action name, the GET/POST
    an agent intends must win it — never the DELETE. Before this rule,
    `api cost pv-curve` was the DELETE (wiping a client baseline) and
    `api notifications push-subscribe` was the UNsubscribe."""
    grp = build_api_group(load_spec())

    pv = grp.commands["cost"].commands["pv-curve"]._tornix_op
    assert pv["_method"] == "get"
    assert grp.commands["cost"].commands["baseline-pv-curve-delete"]._tornix_op["_method"] == "delete"

    sub = grp.commands["notifications"].commands["push-subscribe"]._tornix_op
    assert sub["_method"] == "post"
    assert "push-subscribe-delete" in grp.commands["notifications"].commands


# ── collision naming (2026-07 resync) ─────────────────────────────────────

def _mini_spec(paths):
    return {"openapi": "3.0.0", "paths": paths}


def _item_get(tag, param):
    return {"get": {"operationId": f"get_{param}", "tags": [tag],
                    "parameters": [{"name": param, "in": "path",
                                    "schema": {"type": "string"}}],
                    "responses": {}}}


def _list_get(tag, op_id):
    return {"get": {"operationId": op_id, "tags": [tag], "responses": {}}}


def test_a_lone_item_get_keeps_the_bare_read_verb():
    """With nothing to collide against, `/kpis/{id}` stays `get` — refreshing the
    spec must not rename commands that were never contested."""
    api = build_api_group(_mini_spec({
        "/api/v1/strategic/kpis": _list_get("strategic", "listKpis"),
        "/api/v1/strategic/kpis/{id}": _item_get("strategic", "id"),
    }))
    assert set(api.commands["strategic"].commands) == {"kpis", "get"}


def test_contested_item_gets_are_named_after_their_resource():
    """Two item reads in one tag: the first keeps `get`, the second becomes
    `kpis-get` rather than a meaningless `kpis-2`."""
    api = build_api_group(_mini_spec({
        "/api/v1/strategic/initiatives": _list_get("strategic", "listInitiatives"),
        "/api/v1/strategic/initiatives/{id}": _item_get("strategic", "id"),
        "/api/v1/strategic/kpis": _list_get("strategic", "listKpis"),
        "/api/v1/strategic/kpis/{id}": _item_get("strategic", "id"),
    }))
    names = set(api.commands["strategic"].commands)
    assert names == {"initiatives", "get", "kpis", "kpis-get"}


def test_candidates_widen_into_path_params_before_giving_up():
    """`_name_candidates` is the collision escape ladder: once the resource-scoped
    name is taken, it must keep offering descriptive names built from more of the
    path rather than leaving `build_api_group` to fall back to `-2`."""
    from tornix_cli.api_gen import _name_candidates

    op = {"_method": "get", "_path": "/api/v1/strategy/risks/{strategyId}/{riskId}",
          "operationId": "getRisk"}
    names = list(_name_candidates(op, "strategy"))
    assert "risks-get" in names
    assert any("riskid" in n for n in names), names
    assert not any(n.rsplit("-", 1)[-1].isdigit() for n in names)


def test_candidates_render_a_wildcard_segment_as_proxy():
    from tornix_cli.api_gen import _name_candidates

    op = {"_method": "get", "_path": "/api/v1/ai/reports/*", "operationId": "proxyReports"}
    names = list(_name_candidates(op, "ai-proxy"))
    assert any("proxy" in n for n in names), names
    assert not any("*" in n for n in names), names


def test_no_generated_command_uses_a_numeric_suffix():
    api = build_api_group(load_spec())
    bad = [f"{tag}.{name}"
           for tag, sub in api.commands.items()
           for name in sub.commands
           if name.rsplit("-", 1)[-1].isdigit()]
    assert bad == [], f"numeric-suffix fallback names remain: {bad}"


def test_bare_resource_name_belongs_to_the_collection_not_the_item():
    """Resyncing freed `cost-control invoices` from `/invoices/{id}` and gave it to
    the collection endpoint, matching the convention in every other tag: the bare
    name lists, `-get` reads one. Pinned so a future refactor cannot flip it back
    silently — callers passing an invoice id now hit a different endpoint."""
    cc = build_api_group(load_spec()).commands["cost-control"].commands
    assert cc["invoices"]._tornix_op["_path"] == "/api/v1/organizations/{orgId}/invoices"
    assert cc["invoices-get"]._tornix_op["_path"] == "/api/v1/invoices/{id}"


def test_generated_names_never_contain_a_raw_wildcard_or_brace():
    api = build_api_group(load_spec())
    bad = [f"{t}.{n}" for t, sub in api.commands.items() for n in sub.commands
           if "*" in n or "{" in n or "}" in n]
    assert bad == [], bad


# ── $ref request bodies (2026-07 resync) ──────────────────────────────────
# The backend documents most write bodies as `$ref: #/components/schemas/X`.
# Unresolved, such a body is truthy but exposes no properties: the command gets
# no --field options AND slips past the empty-body write guard, firing a POST
# with no payload. That is the untitled-row footgun, reintroduced.

REF_SPEC = {
    "openapi": "3.0.0",
    "components": {"schemas": {
        "CreateThingDto": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "size": {"type": "number"}},
            "required": ["title"],
        },
        "SelfRef": {"type": "object", "properties": {"child": {"$ref": "#/components/schemas/SelfRef"}}},
    }},
    "paths": {"/api/v1/things": {"post": {
        "operationId": "createThing", "tags": ["things"],
        "requestBody": {"required": True, "content": {"application/json": {
            "schema": {"$ref": "#/components/schemas/CreateThingDto"}}}},
        "responses": {},
    }}},
}


def test_ref_body_becomes_field_options():
    captured = {}

    def handler(req):
        captured["json"] = json.loads(req.content)
        return httpx.Response(201, json={"data": {"ok": True}})

    grp = build_api_group(REF_SPEC)
    r = CliRunner().invoke(grp, ["things", "create", "--title", "Villa", "--size", "5"],
                           obj=_ctx_obj(handler))
    assert r.exit_code == 0, r.output
    assert captured["json"] == {"title": "Villa", "size": 5.0}


def test_ref_body_required_field_is_enforced():
    grp = build_api_group(REF_SPEC)
    r = CliRunner().invoke(grp, ["things", "create"], obj=_ctx_obj(
        lambda req: httpx.Response(201, json={"data": {}})))
    assert r.exit_code != 0, "a required $ref body field must be required on the CLI"


def test_deref_survives_a_self_referential_schema():
    from tornix_cli.api_gen import _deref
    resolved = _deref({"$ref": "#/components/schemas/SelfRef"}, REF_SPEC)
    assert resolved["type"] == "object"


def test_every_documented_write_body_yields_options_or_demands_data():
    """No generated write command may be able to fire with an empty body."""
    from tornix_cli.spec import load_spec
    grp = build_api_group(load_spec())
    naked = []
    for tag, sub in grp.commands.items():
        for name, cmd in sub.commands.items():
            op = getattr(cmd, "_tornix_op", {})
            if op.get("_method") not in ("post", "put", "patch"):
                continue
            opts = {o for p in cmd.params if isinstance(p, click.Option) for o in p.opts}
            has_fields = any(o.startswith("--") and o not in ("--data", "--json", "--jsonl")
                             for o in opts)
            if not has_fields and "--data" not in opts:
                naked.append(f"{tag}.{name}")
    assert naked == [], f"write commands with no way to send a body: {naked}"
