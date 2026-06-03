from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import tomli_w

PROFILES = {
    "prod": "https://app.tornix.ai",
    "stage": "https://app-stage.tornix.ai",
    "dev": "http://localhost:4000",
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
        # Restrict the parent dir (it holds a plaintext secret) to owner-only.
        parent = CONFIG_PATH.parent
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
        fd = os.open(CONFIG_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, tomli_w.dumps(out).encode("utf-8"))
        finally:
            os.close(fd)
        os.chmod(CONFIG_PATH, 0o600)  # ensure perms even if the file pre-existed
