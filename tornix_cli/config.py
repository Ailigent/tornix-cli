from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

import tomli_w

PROFILES = {
    "prod": "https://app.tornix.ai",
    "stage": "https://app-stage.tornix.ai",
    "dev": "http://localhost:4000",
}

CONFIG_PATH = Path(os.environ.get("TORNIX_CONFIG",
                   str(Path.home() / ".config" / "tornix" / "config.toml")))


def _effective_config_path() -> Path:
    """Prefer an explicit path, then isolate each Hermes profile from shared HOME."""
    explicit = os.environ.get("TORNIX_CONFIG")
    if explicit:
        return Path(explicit)
    hermes_home = os.environ.get("HERMES_HOME")
    if hermes_home:
        return Path(hermes_home) / ".config" / "tornix" / "config.toml"
    return CONFIG_PATH


@dataclass
class Config:
    profile: str = "prod"
    api_url: str | None = None       # explicit override; else derived from profile
    api_key: str | None = None
    token: str | None = None         # JWT (password-login fallback)
    org_id: str | None = None
    # True when api_url came from an explicit source (env/file/flag), so a later
    # --profile must NOT silently replace it.
    url_pinned: bool = field(default=False)

    def __post_init__(self) -> None:
        if self.api_url is None:
            self.api_url = PROFILES.get(self.profile, PROFILES["prod"])
        else:
            self.url_pinned = True

    @classmethod
    def load(cls) -> "Config":
        config_path = _effective_config_path()
        data: dict = {}
        if config_path.exists():
            data = tomllib.loads(config_path.read_text())
        profile = os.environ.get("TORNIX_PROFILE") or data.get("profile") or "prod"
        api_url = os.environ.get("TORNIX_API_URL") or data.get("api_url")
        if api_url is None:
            legacy_url = os.environ.get("API_URL")
            if legacy_url:
                parsed = urlsplit(legacy_url)
                allowed_hosts = {"app.tornix.ai", "app-stage.tornix.ai"}
                if (
                    parsed.scheme == "https"
                    and parsed.hostname in allowed_hosts
                    and parsed.username is None
                    and parsed.password is None
                    and not parsed.query
                    and not parsed.fragment
                ):
                    api_url = legacy_url.rstrip("/")
        primary_key = os.environ.get("TORNIX_API_KEY")
        if primary_key:
            # Refuse wrong-provider secrets rather than forwarding them to Tornix.
            api_key = primary_key if primary_key.startswith("tnx_") else None
        else:
            legacy_key = os.environ.get("API_KEY")
            saved_key = data.get("api_key")
            api_key = (
                legacy_key if legacy_key and legacy_key.startswith("tnx_")
                else saved_key if saved_key and saved_key.startswith("tnx_")
                else None
            )
        token = os.environ.get("TORNIX_TOKEN") or data.get("token")
        org_id = os.environ.get("TORNIX_ORG") or data.get("org_id")
        return cls(profile=profile, api_url=api_url, api_key=api_key,
                   token=token, org_id=org_id)

    def save(self) -> None:
        # Restrict the parent dir (it holds a plaintext secret) to owner-only.
        config_path = _effective_config_path()
        parent = config_path.parent
        parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(parent, 0o700)
        except OSError:
            pass
        out = {k: v for k, v in {
            "profile": self.profile, "api_url": self.api_url,
            "api_key": self.api_key, "token": self.token, "org_id": self.org_id,
        }.items() if v is not None}
        # Create the file 0600 atomically (no world-readable window before chmod).
        fd = os.open(config_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, tomli_w.dumps(out).encode("utf-8"))
        finally:
            os.close(fd)
        os.chmod(config_path, 0o600)  # ensure perms even if the file pre-existed
