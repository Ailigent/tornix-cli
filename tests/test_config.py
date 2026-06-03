import tornix_cli.config as cfgmod
from tornix_cli.config import Config, PROFILES


def test_profile_default_url():
    c = Config(profile="prod")
    assert c.api_url == PROFILES["prod"]
    assert Config(profile="stage").api_url == PROFILES["stage"]


def test_explicit_url_overrides_profile():
    assert Config(profile="prod", api_url="http://localhost:4000").api_url == "http://localhost:4000"


def test_env_precedence(monkeypatch, tmp_path):
    monkeypatch.setenv("TORNIX_API_KEY", "tk_env")
    monkeypatch.setenv("TORNIX_ORG", "org-env")
    monkeypatch.setattr(cfgmod, "CONFIG_PATH", tmp_path / "config.toml")
    c = Config.load()
    assert c.api_key == "tk_env"
    assert c.org_id == "org-env"


def test_save_then_load_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr(cfgmod, "CONFIG_PATH", tmp_path / "config.toml")
    monkeypatch.delenv("TORNIX_API_KEY", raising=False)
    monkeypatch.delenv("TORNIX_ORG", raising=False)
    monkeypatch.delenv("TORNIX_PROFILE", raising=False)
    Config(api_key="tk_file", org_id="org-file", profile="stage").save()
    c = Config.load()
    assert c.api_key == "tk_file"
    assert c.org_id == "org-file"
    assert c.profile == "stage"
