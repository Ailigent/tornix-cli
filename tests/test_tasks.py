import httpx
from click.testing import CliRunner
from tornix_cli.commands.tasks import tasks_group
from tornix_cli.client import TornixClient
from tornix_cli.config import Config


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
