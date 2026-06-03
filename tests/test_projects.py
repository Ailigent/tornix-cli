import httpx
from click.testing import CliRunner
from tornix_cli.commands.projects import projects_group
from tornix_cli.client import TornixClient
from tornix_cli.config import Config


def _obj(handler):
    cfg = Config(api_url="https://x.test", api_key="tk")
    return {"client": TornixClient(cfg, transport=httpx.MockTransport(handler)), "json": True}


def test_projects_list_hits_endpoint():
    seen = {}

    def handler(req):
        seen["path"] = req.url.path
        return httpx.Response(200, json={"data": [{"id": "p1", "name": "A"}]})

    r = CliRunner().invoke(projects_group, ["list"], obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert seen["path"] == "/api/v1/projects"


def test_projects_get():
    def handler(req):
        assert req.url.path == "/api/v1/projects/p1"
        return httpx.Response(200, json={"data": {"id": "p1"}})

    r = CliRunner().invoke(projects_group, ["get", "p1"], obj=_obj(handler))
    assert r.exit_code == 0, r.output
