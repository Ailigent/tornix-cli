import httpx
from click.testing import CliRunner
from tornix_cli.commands.approvals import approvals_group
from tornix_cli.client import TornixClient
from tornix_cli.config import Config


def _obj(handler):
    cfg = Config(api_url="https://x.test", api_key="tk")
    return {"client": TornixClient(cfg, transport=httpx.MockTransport(handler)), "json": True}


def test_approve_posts_decision():
    seen = {}

    def handler(req):
        seen["path"] = req.url.path
        return httpx.Response(200, json={"data": {"status": "approved"}})

    r = CliRunner().invoke(approvals_group, ["approve", "a1"], obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert seen["path"] == "/api/v1/approvals/steps/a1/approve"
