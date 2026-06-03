import json
from pathlib import Path
import httpx
from click.testing import CliRunner
from tornix_cli.api_gen import build_api_group
from tornix_cli.client import TornixClient
from tornix_cli.config import Config

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
    proj = grp.commands["projects"]
    assert set(proj.commands) >= {"list", "get", "create"}


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
    r = CliRunner().invoke(grp, ["projects", "create", "--name", "Villa", "--budget", "5"],
                           obj=_ctx_obj(handler))
    assert r.exit_code == 0, r.output
    assert captured["json"] == {"name": "Villa", "budget": 5.0}
