"""Regression tests for issues found in the adversarial review."""
import json
from pathlib import Path

import click
import httpx
from click.testing import CliRunner

from tornix_cli.api_gen import build_api_group
from tornix_cli.client import TornixClient
from tornix_cli.config import Config
from tornix_cli.output import add_json_option, emit_result
from tornix_cli.spec import is_excluded_path

EDGE = json.loads((Path(__file__).parent / "fixtures" / "spec_edge.json").read_text())


def _obj(handler, **extra):
    cfg = Config(api_url="https://x.test", api_key="tk")
    o = {"client": TornixClient(cfg, transport=httpx.MockTransport(handler)), "json": True}
    o.update(extra)
    return o


# ── #1 critical: camelCase path params must not KeyError ──
def test_camelcase_path_param_substitutes():
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        return httpx.Response(200, json={"data": []})

    grp = build_api_group(EDGE)
    r = CliRunner().invoke(grp, ["projects", "items", "P1"], obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert "/api/v1/projects/P1/items" in seen["url"]


# ── #9: hyphenated body fields must reach the payload ──
def test_hyphenated_body_field_sent():
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        return httpx.Response(201, json={"data": {"ok": True}})

    grp = build_api_group(EDGE)
    r = CliRunner().invoke(grp, ["widgets", "create", "--content-type", "app/json", "--size", "3"],
                           obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert seen["body"] == {"content-type": "app/json", "size": 3}


# ── #8: invalid JSON → clean UsageError (exit 2), not a traceback ──
def test_invalid_json_data_is_usage_error():
    grp = build_api_group(EDGE)
    r = CliRunner().invoke(grp, ["widgets", "create", "--content-type", "x", "--data", "not-json"],
                           obj=_obj(lambda q: None))
    assert r.exit_code == 2
    assert "invalid JSON" in r.output


# ── #10: inbound webhooks/callbacks are not generated ──
def test_webhook_path_excluded():
    assert is_excluded_path("/api/v1/meetings/livekit/webhook")
    assert is_excluded_path("/api/v1/odoo/cost-callback")
    grp = build_api_group(EDGE)
    meetings = grp.commands["meetings"]
    assert set(meetings.commands) == {"list"}   # webhook POST excluded


# ── #12: --json / --jsonl flags are injected on every subcommand ──
def test_add_json_option_injects_jsonl():
    grp = build_api_group(EDGE)
    add_json_option(grp)
    items = grp.commands["projects"].commands["items"]
    opts = {o for p in items.params if isinstance(p, click.Option) for o in p.opts}
    assert "--json" in opts and "--jsonl" in opts


def test_emit_result_jsonl(capsys):
    emit_result({"json": True, "jsonl": True}, [{"a": 1}, {"a": 2}])
    lines = capsys.readouterr().out.strip().splitlines()
    assert [json.loads(x) for x in lines] == [{"a": 1}, {"a": 2}]


# ── #3: an explicit api_url must beat a --profile ──
def test_profile_does_not_override_explicit_url(monkeypatch):
    from tornix_cli.__main__ import cli
    monkeypatch.setenv("TORNIX_API_URL", "https://custom.example.com")
    monkeypatch.delenv("TORNIX_PROFILE", raising=False)
    monkeypatch.delenv("TORNIX_API_KEY", raising=False)
    r = CliRunner().invoke(cli, ["--profile", "prod", "--json", "config", "show"], obj=None)
    assert r.exit_code == 0, r.output
    assert json.loads(r.output)["api_url"] == "https://custom.example.com"


# ── #2: a passed-in obj (REPL) is preserved, client not rebuilt ──
def test_passed_obj_preserved():
    from tornix_cli.__main__ import cli
    cfg = Config(api_url="https://sentinel.test")
    client = TornixClient(cfg)
    obj = {"config": cfg, "client": client, "json": True}
    r = CliRunner().invoke(cli, ["config", "show"], obj=obj)
    assert r.exit_code == 0, r.output
    assert json.loads(r.output)["api_url"] == "https://sentinel.test"
    assert obj["client"] is client


# ── #4/#13: config file + dir are owner-only ──
def test_config_perms(monkeypatch, tmp_path):
    import os
    import tornix_cli.config as cfgmod
    monkeypatch.setattr(cfgmod, "CONFIG_PATH", tmp_path / "sub" / "config.toml")
    monkeypatch.delenv("TORNIX_API_KEY", raising=False)
    Config(api_key="tk_secret").save()
    assert oct(os.stat(cfgmod.CONFIG_PATH).st_mode & 0o777) == "0o600"
    assert oct(os.stat(cfgmod.CONFIG_PATH.parent).st_mode & 0o777) == "0o700"


# ── #19: SSRF guard on spec fetch base URL ──
def test_fetch_spec_rejects_bad_scheme():
    import pytest
    from tornix_cli.spec import fetch_spec
    with pytest.raises(ValueError):
        fetch_spec("ftp://evil.example.com")
    with pytest.raises(ValueError):
        fetch_spec("http://evil.example.com")   # http only allowed for localhost
