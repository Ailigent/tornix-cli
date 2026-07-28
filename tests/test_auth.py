import httpx
from click.testing import CliRunner
from tornix_cli.auth import auth_group
from tornix_cli.client import TornixClient
from tornix_cli.config import Config
import tornix_cli.config as cfgmod


def _obj(handler):
    cfg = Config(api_url="https://x.test")
    return {"client": TornixClient(cfg, transport=httpx.MockTransport(handler)),
            "config": cfg, "json": True}


def test_login_api_key_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(cfgmod, "CONFIG_PATH", tmp_path / "c.toml")
    monkeypatch.delenv("TORNIX_API_KEY", raising=False)

    def handler(req):                # whoami after login
        return httpx.Response(200, json={"data": {"email": "k@t.ai"}})

    r = CliRunner().invoke(auth_group, ["login", "--api-key", "tk_abc"], obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert Config.load().api_key == "tk_abc"


def test_whoami(tmp_path, monkeypatch):
    monkeypatch.setattr(cfgmod, "CONFIG_PATH", tmp_path / "c.toml")

    def handler(req):
        return httpx.Response(200, json={"data": {"email": "k@t.ai", "id": "u1"}})

    r = CliRunner().invoke(auth_group, ["whoami"], obj=_obj(handler))
    assert r.exit_code == 0
    assert "k@t.ai" in r.output


# ── 2FA login (2026-07 backend resync) ────────────────────────────────────
# The backend added POST /auth/2fa/otp/send and POST /auth/2fa/verify. On a
# 2FA-enabled account, /auth/login returns a short-lived `pending_token`
# instead of a session, which the old code read as None and saved silently.

def test_login_completes_the_2fa_challenge():
    import json as _j
    calls = []

    def handler(req):
        calls.append(req.url.path)
        if req.url.path == "/api/v1/auth/login":
            return httpx.Response(200, json={"data": {"pending_token": "pt-1"}})
        if req.url.path == "/api/v1/auth/2fa/otp/send":
            return httpx.Response(200, json={"data": {"sent": True}})
        if req.url.path == "/api/v1/auth/2fa/verify":
            assert _j.loads(req.content) == {"pending_token": "pt-1", "code": "123456"}
            return httpx.Response(200, json={"data": {"access_token": "real-token"}})
        return httpx.Response(200, json={"data": {"id": "u1"}})

    obj = _obj(handler)
    r = CliRunner().invoke(
        auth_group,
        ["login", "--email", "a@b.c", "--password", "pw", "--code", "123456"],
        obj=obj)
    assert r.exit_code == 0, r.output
    assert "/api/v1/auth/2fa/otp/send" in calls
    assert "/api/v1/auth/2fa/verify" in calls
    assert obj["config"].token == "real-token"


def test_login_prompts_for_the_code_when_not_supplied():
    def handler(req):
        if req.url.path == "/api/v1/auth/login":
            return httpx.Response(200, json={"data": {"pending_token": "pt-9"}})
        if req.url.path == "/api/v1/auth/2fa/verify":
            return httpx.Response(200, json={"data": {"access_token": "tok-9"}})
        return httpx.Response(200, json={"data": {"id": "u1"}})

    obj = _obj(handler)
    r = CliRunner().invoke(
        auth_group, ["login", "--email", "a@b.c", "--password", "pw"],
        obj=obj, input="654321\n")
    assert r.exit_code == 0, r.output
    assert obj["config"].token == "tok-9"


def test_login_never_stores_a_null_token():
    """A login response with neither a session nor a pending_token must fail
    loudly instead of persisting None and leaving a silently broken config."""
    def handler(req):
        if req.url.path == "/api/v1/auth/login":
            return httpx.Response(200, json={"data": {"unexpected": True}})
        return httpx.Response(200, json={"data": {"id": "u1"}})

    obj = _obj(handler)
    r = CliRunner().invoke(
        auth_group, ["login", "--email", "a@b.c", "--password", "pw"], obj=obj)
    assert r.exit_code != 0
    assert obj["config"].token is None


def test_2fa_verify_without_a_token_fails_loudly():
    def handler(req):
        if req.url.path == "/api/v1/auth/login":
            return httpx.Response(200, json={"data": {"pending_token": "pt-2"}})
        if req.url.path == "/api/v1/auth/2fa/verify":
            return httpx.Response(200, json={"data": {"still": "nothing"}})
        return httpx.Response(200, json={"data": {"id": "u1"}})

    obj = _obj(handler)
    r = CliRunner().invoke(
        auth_group,
        ["login", "--email", "a@b.c", "--password", "pw", "--code", "000000"],
        obj=obj)
    assert r.exit_code != 0
    assert obj["config"].token is None


def test_plain_login_still_works_without_2fa():
    def handler(req):
        if req.url.path == "/api/v1/auth/login":
            return httpx.Response(200, json={"data": {"access_token": "plain"}})
        return httpx.Response(200, json={"data": {"id": "u1"}})

    obj = _obj(handler)
    r = CliRunner().invoke(
        auth_group, ["login", "--email", "a@b.c", "--password", "pw"], obj=obj)
    assert r.exit_code == 0, r.output
    assert obj["config"].token == "plain"


# ── api-key {id} commands added by the backend ────────────────────────────

def test_keys_usage_hits_the_usage_endpoint():
    seen = {}

    def handler(req):
        seen["path"] = req.url.path
        return httpx.Response(200, json={"data": {"calls": 7}})

    r = CliRunner().invoke(auth_group, ["keys", "usage", "k1"], obj=_obj(handler))
    assert r.exit_code == 0, r.output
    assert seen["path"] == "/api/v1/api-keys/k1/usage"


def test_keys_get_update_delete_hit_the_right_verbs():
    seen = []

    def handler(req):
        seen.append((req.method, req.url.path))
        return httpx.Response(200, json={"data": {}})

    runner = CliRunner()
    assert runner.invoke(auth_group, ["keys", "get", "k1"], obj=_obj(handler)).exit_code == 0
    assert runner.invoke(auth_group, ["keys", "update", "k1", "--data", '{"name":"n"}'],
                         obj=_obj(handler)).exit_code == 0
    assert runner.invoke(auth_group, ["keys", "delete", "k1"], obj=_obj(handler)).exit_code == 0
    assert seen == [("GET", "/api/v1/api-keys/k1"),
                    ("PATCH", "/api/v1/api-keys/k1"),
                    ("DELETE", "/api/v1/api-keys/k1")]
