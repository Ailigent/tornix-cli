import json
import httpx
from click.testing import CliRunner
from tornix_cli.data import data_group, rpc_command
from tornix_cli.client import TornixClient
from tornix_cli.config import Config


def _obj(handler):
    cfg = Config(api_url="https://x.test", api_key="tk")
    return {"client": TornixClient(cfg, transport=httpx.MockTransport(handler)), "json": True}


def test_data_select_builds_query():
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        return httpx.Response(200, json={"data": [{"id": 1}]})

    r = CliRunner().invoke(data_group, ["select", "organization_projects",
                                        "--eq", "status=active", "--limit", "5"],
                           obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert "/api/v1/data/organization_projects" in seen["url"]
    assert "status=eq.active" in seen["url"] or "status=active" in seen["url"]


def test_rpc_posts_args():
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"data": {"ok": True}})

    r = CliRunner().invoke(rpc_command, ["pmo_overview", "--arg", "org_id=9"], obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert seen["body"] == {"org_id": "9"}


# ── New tests: --count, --offset, --filter ────────────────────────────────────

def test_count_returns_count_from_envelope():
    """--count should return {"count": N} using the full envelope, not raw rows."""
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        return httpx.Response(200, json={"data": [{"id": 1}], "count": 42})

    r = CliRunner().invoke(data_group, ["select", "project_tasks", "--count"],
                           obj=_obj(handler))
    assert r.exit_code == 0, r.output
    out = json.loads(r.output)
    assert out == {"count": 42}
    # backend should receive count=exact and limit=1
    assert "count=exact" in seen["url"]
    assert "limit=1" in seen["url"]


def test_count_falls_back_to_meta_count():
    """--count should also read count from body['meta']['count'] when top-level missing."""

    def handler(req):
        return httpx.Response(200, json={"data": [], "meta": {"count": 7}})

    r = CliRunner().invoke(data_group, ["select", "project_tasks", "--count"],
                           obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert json.loads(r.output) == {"count": 7}


def test_count_falls_back_to_data_len():
    """--count should fall back to len(data) when no explicit count field."""

    def handler(req):
        return httpx.Response(200, json={"data": [{"id": 1}, {"id": 2}]})

    r = CliRunner().invoke(data_group, ["select", "project_tasks", "--count"],
                           obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert json.loads(r.output) == {"count": 2}


def test_offset_sent_as_query_param():
    """--offset N should include offset=N in the request URL."""
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        return httpx.Response(200, json={"data": [{"id": 5}]})

    r = CliRunner().invoke(data_group, ["select", "project_tasks",
                                        "--offset", "20", "--limit", "10"],
                           obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert "offset=20" in seen["url"]
    assert "limit=10" in seen["url"]


def test_filter_raw_passthrough():
    """--filter col=op.value should be forwarded verbatim (no eq. wrapping)."""
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        return httpx.Response(200, json={"data": []})

    r = CliRunner().invoke(data_group, ["select", "project_tasks",
                                        "--filter", "status=in.(done,closed)"],
                           obj=_obj(handler))
    assert r.exit_code == 0, r.output
    # The raw value must be passed without additional eq. wrapping
    assert "status=in.%28done%2Cclosed%29" in seen["url"] or "status=in.(done,closed)" in seen["url"]


def test_filter_multiple_operators():
    """Multiple --filter flags should all appear in the request."""
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        return httpx.Response(200, json={"data": []})

    r = CliRunner().invoke(data_group, ["select", "project_tasks",
                                        "--filter", "percent_complete=gte.100",
                                        "--filter", "priority=eq.high"],
                           obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert "percent_complete=gte.100" in seen["url"] or "percent_complete=gte.100" in seen["url"]
    assert "priority=eq.high" in seen["url"]


# ── New test: client envelope=True ────────────────────────────────────────────

def test_client_envelope_true_returns_full_body():
    """client.request(..., envelope=True) must return the raw {data, meta, count} dict."""
    full_body = {"data": [{"id": 1}], "count": 99, "meta": {"page": 1}}

    def handler(req):
        return httpx.Response(200, json=full_body)

    cfg = Config(api_url="https://x.test", api_key="tk")
    client = TornixClient(cfg, transport=httpx.MockTransport(handler))
    result = client.get("/api/v1/data/tasks", envelope=True)
    assert result == full_body


def test_client_envelope_false_unwraps_as_before():
    """Default envelope=False must still unwrap data as before."""
    full_body = {"data": [{"id": 1}], "count": 99}

    def handler(req):
        return httpx.Response(200, json=full_body)

    cfg = Config(api_url="https://x.test", api_key="tk")
    client = TornixClient(cfg, transport=httpx.MockTransport(handler))
    result = client.get("/api/v1/data/tasks")
    assert result == [{"id": 1}]
