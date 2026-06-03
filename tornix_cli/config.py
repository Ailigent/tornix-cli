from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

import tomli_w

PROFILES = {
    "prod": "https://app.tornix.ai",
    "stage": "https://app-stage.tornix.ai",
}

CONFIG_PATH = Path(os.environ.get("TORNIX_CONFIG",
                   str(Path.home() / ".config" / "tornix" / "config.toml")))


@dataclass
class Config:
    profile: str = "prod"
    api_url: str | None = None       # explicit override; else derived from profile
    api_key: str | None = None
    token: str | None = None         # JWT (password-login fallback)
    org_id: str | None = None

    def __post_init__(self) -> None:
        if self.api_url is None:
            self.api_url = PROFILES.get(self.profile, PROFILES["prod"])

    @classmethod
    def load(cls) -> "Config":
        data: dict = {}
        if CONFIG_PATH.exists():
            data = tomllib.loads(CONFIG_PATH.read_text())
        profile = os.environ.get("TORNIX_PROFILE") or data.get("profile") or "prod"
        api_url = os.environ.get("TORNIX_API_URL") or data.get("api_url")
        api_key = os.environ.get("TORNIX_API_KEY") or data.get("api_key")
        token = os.environ.get("TORNIX_TOKEN") or data.get("token")
        org_id = os.environ.get("TORNIX_ORG") or data.get("org_id")
        return cls(profile=profile, api_url=api_url, api_key=api_key,
                   token=token, org_id=org_id)

    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        out = {k: v for k, v in {
            "profile": self.profile, "api_url": self.api_url,
            "api_key": self.api_key, "token": self.token, "org_id": self.org_id,
        }.items() if v is not None}
        CONFIG_PATH.write_text(tomli_w.dumps(out))
        os.chmod(CONFIG_PATH, 0o600)
