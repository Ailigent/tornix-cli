import httpx
from click.testing import CliRunner
from tornix_cli.api_gen import build_api_group
from tornix_cli.commands.tasks import tasks_group
from tornix_cli.client import TornixClient
from tornix_cli.config import Config
from tornix_cli.spec import load_spec


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


def test_tasks_create_rejects_blank_title():
    """Same untitled-row guard as projects create: a blank/whitespace --title is a
    usage error and no request fires."""
    count = {"n": 0}

    def handler(req):
        count["n"] += 1
        return httpx.Response(200, json={"data": {"id": "t1"}})

    r = CliRunner().invoke(tasks_group, ["create", "--project", "p1", "--title", "  "],
                           obj=_obj(handler))
    assert r.exit_code != 0
    assert count["n"] == 0


def test_generated_api_tasks_create_is_removed():
    """Sibling of the projects-create exclusion: POST /projects/{projectId}/tasks
    has no requestBody in the spec, so the generated `api tasks create` could only
    ever mint untitled tasks. The curated `tasks create --title` supersedes it."""
    root = build_api_group(load_spec())
    tasks = root.commands["tasks"]
    assert "create" not in tasks.commands
    # Safe generated siblings remain.
    assert "list" in tasks.commands
    assert "delete" in tasks.commands
