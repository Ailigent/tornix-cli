import base64
import json

import click
import httpx
import pytest
from click.testing import CliRunner

from tornix_cli.__main__ import cli
from tornix_cli.client import TornixClient
from tornix_cli.config import Config
from tornix_cli.orgs import fetch_orgs, resolve_org

A = "aaaaaaaa-0000-0000-0000-000000000001"
B = "bbbbbbbb-0000-0000-0000-000000000002"
ORGS = [{"id": A, "name": "Acme Builders", "role": "admin"},
        {"id": B, "name": "Acme Labs", "role": "member"}]


def _obj(handler, **cfg_kw):
    cfg = Config(api_url="https://x.test", api_key="tnx_k", **cfg_kw)
    return {"config": cfg, "client": TornixClient(cfg, transport=httpx.MockTransport(handler))}


def _run(args, handler, **cfg_kw):
    return CliRunner().invoke(cli, args, obj=_obj(handler, **cfg_kw))


def _router(per_org, seen=None, fail=()):
    """/organizations lists ORGS; every other GET answers per X-Organization-ID."""
    def handler(req):
        if seen is not None:
            seen.append((req.method, req.url.path, dict(req.url.params), req.headers.get("x-organization-id")))
        if req.url.path == "/api/v1/organizations":
            return httpx.Response(200, json={"data": ORGS})
        org = req.headers.get("x-organization-id")
        if org in fail:
            return httpx.Response(403, json={"message": "ORG_MEMBERSHIP_REQUIRED"})
        return httpx.Response(200, json={"data": per_org[org]})
    return handler


# ── MO-07 orgs list ──
def test_orgs_list_marks_current_and_asks_for_talon_first():
    seen = []
    r = _run(["--json", "--org", B, "orgs", "list"], _router({}, seen))
    assert r.exit_code == 0, r.output
    rows = json.loads(r.output)
    assert [(o["id"], o["role"], o["current"]) for o in rows] == [(A, "admin", False), (B, "member", True)]
    assert seen[0][2] == {"for": "talon"} and seen[0][3] is None   # unscoped list, ?for=talon first


def test_orgs_list_falls_back_to_plain_list_on_400_and_unwraps():
    calls = []

    def handler(req):
        calls.append(dict(req.url.params))
        if req.url.params.get("for"):
            return httpx.Response(400, json={"message": "property for should not exist"})
        return httpx.Response(200, json=ORGS)       # bare array, no {data}

    r = _run(["--json", "orgs", "list"], handler)
    assert r.exit_code == 0, r.output
    assert len(json.loads(r.output)) == 2
    assert calls == [{"for": "talon"}, {}]


def test_orgs_list_current_defaults_to_token_claim():
    payload = base64.urlsafe_b64encode(json.dumps({"organization_id": A}).encode()).decode().rstrip("=")
    jwt = f"h.{payload}.s"
    cfg = Config(api_url="https://x.test", token=jwt)
    obj = {"config": cfg, "client": TornixClient(cfg, transport=httpx.MockTransport(_router({})))}
    r = CliRunner().invoke(cli, ["--json", "orgs", "list"], obj=obj)
    assert [o["current"] for o in json.loads(r.output)] == [True, False]


# ── name resolution ──
def test_resolve_exact_prefix_contains_and_ambiguous():
    orgs = ORGS + [{"id": "c", "name": "Zeta Group", "role": None}]
    assert resolve_org(orgs, "acme labs") == B                 # exact, case-insensitive
    assert resolve_org(orgs, "acme b") == A                    # unique prefix
    assert resolve_org(orgs, "group") == "c"                   # unique substring
    assert resolve_org(orgs, A) == A                           # id
    with pytest.raises(click.UsageError) as e:
        resolve_org(orgs, "acme")
    assert "Acme Builders" in e.value.message and "Acme Labs" in e.value.message
    with pytest.raises(click.UsageError):
        resolve_org(orgs, "nope")


def test_org_name_sent_as_resolved_id_and_list_fetched_once():
    seen = []
    handler = _router({A: [{"id": "p1"}], B: [{"id": "p2"}]}, seen)
    obj = _obj(handler, org_id="acme labs")
    cl = obj["client"]
    cl.get("/api/v1/projects")
    cl.get("/api/v1/projects")
    heads = [h for _, path, _, h in seen if path == "/api/v1/projects"]
    assert heads == [B, B]
    assert sum(1 for _, path, _, _ in seen if path == "/api/v1/organizations") == 1


def test_ambiguous_name_is_a_usage_error_via_cli():
    r = _run(["--org", "acme", "--json", "projects", "list", "--all"], _router({}))
    assert r.exit_code != 0
    assert "more than one organization" in r.output


# ── MO-08 --org all ──
def test_org_all_merges_rows_and_tags_org():
    seen = []
    per = {A: [{"id": "p1", "name": "Tower"}], B: [{"id": "p2", "name": "Lab"}]}
    r = _run(["--org", "all", "--json", "projects", "list", "--all"], _router(per, seen))
    assert r.exit_code == 0, r.output
    out = json.loads(r.output)
    assert out["errors"] == []
    assert {(x["id"], x["org"]["name"]) for x in out["data"]} == {("p1", "Acme Builders"), ("p2", "Acme Labs")}
    assert {h for _, p, _, h in seen if p == "/api/v1/projects"} == {A, B}


def test_org_all_one_failing_org_is_reported_not_fatal():
    per = {A: [{"id": "p1"}], B: []}
    r = _run(["--org", "all", "--json", "projects", "list", "--all"], _router(per, fail=(B,)))
    assert r.exit_code == 0, r.output
    out = json.loads(r.output)
    assert [x["id"] for x in out["data"]] == ["p1"]
    assert out["errors"][0]["org"]["id"] == B
    assert out["errors"][0]["error"]["status"] == 403


def test_org_all_human_output_warns_on_stderr():
    per = {A: [{"id": "p1"}], B: []}
    r = _run(["--org", "all", "projects", "list", "--all"], _router(per, fail=(B,)))
    assert r.exit_code == 0
    assert "Acme Builders" in r.output and "warning: Acme Labs" in r.output


def test_org_all_every_org_failing_exits_nonzero():
    r = _run(["--org", "all", "--json", "projects", "list", "--all"], _router({}, fail=(A, B)))
    assert r.exit_code != 0


def test_org_all_works_for_generated_get_list_commands():
    per = {A: [{"id": "x"}], B: [{"id": "y"}]}
    r = _run(["--org", "all", "--json", "api", "projects", "list"], _router(per))
    assert r.exit_code == 0, r.output
    assert len(json.loads(r.output)["data"]) == 2


@pytest.mark.parametrize("args", [
    ["tasks", "create", "--project", "p1", "--title", "x"],
    ["approvals", "approve", "step1"],
    ["projects", "update", "p1", "--data", "{}"],
    ["tasks", "list", "--project", "p1"],       # one project belongs to one org
    ["projects", "get", "p1"],
])
def test_org_all_refuses_writes_and_single_id_reads(args):
    seen = []
    r = _run(["--org", "all", "--json", *args], _router({}, seen))
    assert r.exit_code != 0
    assert "ONE organization" in r.output
    assert not [s for s in seen if s[0] != "GET" or s[1] != "/api/v1/organizations"]


def test_org_all_does_not_block_orgs_list():
    r = _run(["--org", "all", "--json", "orgs", "list"], _router({}))
    assert r.exit_code == 0, r.output
    assert [o["current"] for o in json.loads(r.output)] == [False, False]
