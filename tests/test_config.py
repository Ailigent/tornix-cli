import tornix_cli.config as cfgmod
from tornix_cli.config import Config, PROFILES
import tomli_w


def test_profile_default_url():
    c = Config(profile="prod")
    assert c.api_url == PROFILES["prod"]
    assert Config(profile="stage").api_url == PROFILES["stage"]


def test_explicit_url_overrides_profile():
    assert Config(profile="prod", api_url="http://localhost:4000").api_url == "http://localhost:4000"


def test_env_precedence(monkeypatch, tmp_path):
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.delenv("TORNIX_CONFIG", raising=False)
    monkeypatch.setenv("TORNIX_API_KEY", "tnx_env")
    monkeypatch.setenv("TORNIX_ORG", "org-env")
    monkeypatch.setattr(cfgmod, "CONFIG_PATH", tmp_path / "config.toml")
    c = Config.load()
    assert c.api_key == "tnx_env"
    assert c.org_id == "org-env"


def test_legacy_env_compatibility_is_limited_to_tornix_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.delenv("TORNIX_CONFIG", raising=False)
    monkeypatch.setattr(cfgmod, "CONFIG_PATH", tmp_path / "config.toml")
    monkeypatch.delenv("TORNIX_API_KEY", raising=False)
    monkeypatch.delenv("TORNIX_API_URL", raising=False)
    monkeypatch.delenv("API_URL", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    monkeypatch.setenv("API_KEY", "tnx_test_legacy")
    monkeypatch.setenv("API_URL", "https://app-stage.tornix.ai")
    c = Config.load()
    assert c.api_key == "tnx_test_legacy"
    assert c.api_url == PROFILES["stage"]

    monkeypatch.setenv("API_KEY", "not-a-tnx-value")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "not-a-tnx-value")
    monkeypatch.setenv("API_URL", "https://untrusted.example")
    c = Config.load()
    assert c.api_key is None
    assert c.api_url == PROFILES["prod"]


def test_non_tornix_key_material_is_ignored_even_with_saved_key(monkeypatch, tmp_path):
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.delenv("TORNIX_CONFIG", raising=False)
    path = tmp_path / "config.toml"
    monkeypatch.setattr(cfgmod, "CONFIG_PATH", path)
    Config(api_key="tnx_" + "saved_test").save()
    monkeypatch.setenv("TORNIX_API_KEY", "service-role-shape")
    monkeypatch.setenv("API_KEY", "tnx_legacy_test")

    assert Config.load().api_key is None


def test_profile_home_uses_an_isolated_config_path(monkeypatch, tmp_path):
    shared = tmp_path / "shared" / "config.toml"
    shared.parent.mkdir()
    shared.write_text(tomli_w.dumps({"api_key": "tnx_shared_test", "org_id": "org-shared"}))
    profile_home = tmp_path / "profile-a"
    profile_config = profile_home / ".config" / "tornix" / "config.toml"
    profile_config.parent.mkdir(parents=True)
    profile_config.write_text(tomli_w.dumps({"api_key": "tnx_profile_test", "org_id": "org-profile"}))

    monkeypatch.setattr(cfgmod, "CONFIG_PATH", shared)
    monkeypatch.delenv("TORNIX_CONFIG", raising=False)
    monkeypatch.setenv("HERMES_HOME", str(profile_home))
    monkeypatch.delenv("TORNIX_API_KEY", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("TORNIX_ORG", raising=False)

    c = Config.load()
    assert c.api_key == "tnx_profile_test"
    assert c.org_id == "org-profile"
    Config(api_key="tnx_" + "written_test", org_id="org-profile").save()
    assert Config.load().api_key == "tnx_written_test"
    assert "tnx_shared_test" in shared.read_text()


def test_save_then_load_roundtrip(monkeypatch, tmp_path):
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.delenv("TORNIX_CONFIG", raising=False)
    monkeypatch.setattr(cfgmod, "CONFIG_PATH", tmp_path / "config.toml")
    monkeypatch.delenv("TORNIX_API_KEY", raising=False)
    monkeypatch.delenv("TORNIX_ORG", raising=False)
    monkeypatch.delenv("TORNIX_PROFILE", raising=False)
    file_key = "tnx_" + "file"
    Config(api_key=file_key, org_id="org-file", profile="stage").save()
    c = Config.load()
    assert c.api_key == file_key
    assert c.org_id == "org-file"
    assert c.profile == "stage"
