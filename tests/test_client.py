import httpx
import pytest
from tornix_cli.client import TornixClient
from tornix_cli.config import Config
from tornix_cli.errors import TornixError


def make_client(handler):
    cfg = Config(api_url="https://x.test", api_key="tk_1", org_id="org-9")
    return TornixClient(cfg, transport=httpx.MockTransport(handler))


def test_injects_auth_and_org_headers():
    seen = {}

    def handler(req):
        seen["auth"] = req.headers.get("authorization")
        seen["org"] = req.headers.get("x-organization-id")
        return httpx.Response(200, json={"data": {"ok": True}})

    out = make_client(handler).get("/api/v1/projects")
    assert seen["auth"] == "Bearer tk_1"
    assert seen["org"] == "org-9"
    assert out == {"ok": True}            # envelope unwrapped


def test_unwraps_only_when_enveloped():
    c = make_client(lambda r: httpx.Response(200, json=[1, 2, 3]))
    assert c.get("/x") == [1, 2, 3]


def test_error_mapping():
    def handler(req):
        return httpx.Response(403, json={"message": "no scope"})
    with pytest.raises(TornixError) as ei:
        make_client(handler).get("/x")
    assert ei.value.status == 403
    assert "no scope" in ei.value.message
