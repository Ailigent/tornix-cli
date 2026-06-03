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
