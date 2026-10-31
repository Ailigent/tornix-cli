"""`tornix hse` — paths, filters, the photo upload + register pair, and the closure body. No network."""
import json

import httpx
from click.testing import CliRunner

from tornix_cli.__main__ import cli
from tornix_cli.client import TornixClient
from tornix_cli.commands.hse import hse_group
from tornix_cli.config import Config

PID = "11111111-1111-1111-1111-111111111111"
VID = "22222222-2222-2222-2222-222222222222"


def _run(args, tmp_path=None):
    calls = []

    def handler(req):
        calls.append({"m": req.method, "p": req.url.path, "q": dict(req.url.params), "b": req.content})
        p = req.url.path
        if p.endswith("/violations") and req.method == "GET":
            return httpx.Response(200, json={"data": [{"id": VID, "number": 12}], "total": 1, "counts": {"OPEN": 1}})
        if p == "/api/v1/storage/upload-direct":
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(200, json={"data": {"id": "x", "ok": True}})

    cfg = Config(api_url="https://x.test", api_key="tk", org_id="o")
    obj = {"config": cfg, "client": TornixClient(cfg, transport=httpx.MockTransport(handler)), "json": True}
    res = CliRunner().invoke(hse_group, args, obj=obj, catch_exceptions=False)
    return res, calls


def test_group_is_registered():
    assert "hse" in cli.commands


def test_violations_filters_and_counts():
    res, calls = _run(["violations", PID, "--status", "OPEN", "--severity", "HIGH", "--overdue"])
    q = calls[0]["q"]
    assert calls[0]["p"] == f"/api/v1/projects/{PID}/hse/violations"
    assert q["status"] == "OPEN" and q["severity"] == "HIGH" and q["overdue"] == "true"
    assert json.loads(res.output)["counts"] == {"OPEN": 1}


def test_violation_by_number_resolves_the_id():
    _, calls = _run(["violation", PID, "12"])
    assert calls[-1]["p"].endswith(f"/violations/{VID}")


def test_closure_needs_photo_ids_and_sends_them():
    res, calls = _run(["request-closure", PID, VID, "--photo-id", "33333333-3333-3333-3333-333333333333", "--note", "تم"])
    assert json.loads(calls[-1]["b"]) == {"photo_ids": ["33333333-3333-3333-3333-333333333333"], "note": "تم"}
    bad = CliRunner().invoke(hse_group, ["request-closure", PID, VID], obj={}, catch_exceptions=False)
    assert bad.exit_code == 2


def test_photo_add_uploads_then_registers(tmp_path):
    f = tmp_path / "a.jpg"
    f.write_bytes(b"\xff\xd8x")
    _, calls = _run(["photo-add", PID, VID, str(f), "--kind", "before"])
    up, reg = calls[-2], calls[-1]
    assert up["p"] == "/api/v1/storage/upload-direct" and up["q"]["bucket"] == "files"
    assert up["q"]["path"].startswith(f"hse/{PID}/violations/{VID}/before-")
    body = json.loads(reg["b"])
    assert body["kind"] == "before" and body["storage_path"] == up["q"]["path"] and body["mime_type"] == "image/jpeg"


def test_rejects_non_uuid_project():
    res = CliRunner().invoke(hse_group, ["kpis", "الواحة"], obj={"client": TornixClient(Config(api_url="https://x.test", api_key="t"), transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})))}, catch_exceptions=False)
    assert res.exit_code == 2
