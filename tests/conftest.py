import pytest


@pytest.fixture(autouse=True)
def _isolate_config(tmp_path, monkeypatch):
    """Never touch the developer's real ~/.config/tornix/config.toml during tests.
    `auth login` calls Config.save(), which would otherwise overwrite it."""
    monkeypatch.setattr("tornix_cli.config.CONFIG_PATH", tmp_path / "config.toml")
