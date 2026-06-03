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
