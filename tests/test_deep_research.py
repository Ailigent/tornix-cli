import json
import httpx
from click.testing import CliRunner
from tornix_cli.commands.deep_research import deep_research_command, assemble_pmo_corpus
from tornix_cli.client import TornixClient
from tornix_cli.config import Config


def _client(routes):
    def handler(req):
        p = req.url.path
        if p in routes:
            return httpx.Response(200, json={"data": routes[p]})
        return httpx.Response(200, json={"data": []})
    cfg = Config(api_url="https://x.test", api_key="tk")
    return TornixClient(cfg, transport=httpx.MockTransport(handler))


def test_assemble_pmo_corpus_collects_sections():
    c = _client({
        "/api/v1/projects/p1": {"id": "p1", "name": "Villa"},
        "/api/v1/projects/p1/tasks": [{"id": "t1", "title": "Pour slab", "status": "late"}],
        "/api/v1/projects/p1/risks": [{"id": "r1", "title": "Rain delay"}],
    })
    corpus = assemble_pmo_corpus(c, project_id="p1")
    assert corpus["project"]["name"] == "Villa"
    kinds = {s["kind"] for s in corpus["sections"]}
    assert {"tasks", "risks"} <= kinds
    for s in corpus["sections"]:
        for item in s["items"]:
            assert "citation" in item


def test_agent_mode_emits_brief_json():
    c = _client({"/api/v1/projects/p1": {"id": "p1", "name": "Villa"}})
    obj = {"client": c, "json": True}
    r = CliRunner().invoke(deep_research_command,
                           ["Why is the project late?", "--source", "pmo", "--project", "p1"],
                           obj=obj)
    assert r.exit_code == 0, r.output
    out = json.loads(r.output)
    assert out["question"] == "Why is the project late?"
    assert out["mode"] == "agent"
    assert "corpus" in out and "sub_questions" in out
