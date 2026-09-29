"""Tornix CLI — agent-native interface for app.tornix.ai.

Backward-compat credential shim
--------------------------------
The sandbox provisioner writes a package-local ``.env`` using the legacy env
names ``API_URL``, ``API_KEY``, ``ORGANIZATION_ID`` (and ``USER_ID``).  The
upstream CLI reads ``TORNIX_API_URL`` / ``TORNIX_TOKEN`` / ``TORNIX_ORG``.  This
shim bridges the two naming schemes at import time so every existing sandbox
keeps working after a re-provision, without requiring any provisioner change.

Rules (evaluated on first import, never overwritten once set):
  * ``API_URL``     -> ``TORNIX_API_URL`` with a trailing ``/api/v1`` stripped
                       (the new client appends its own ``/api/v1/...`` prefix).
  * ``API_KEY``     -> ``TORNIX_TOKEN``   (the legacy value is a JWT bearer token).
  * ``ORGANIZATION_ID`` -> ``TORNIX_ORG``.

The shim is idempotent and safe: a ``TORNIX_*`` value that is already set is
NEVER overwritten, and the legacy names are left untouched.  The provisioner
may prepend its own ``.env`` loader to this same file; the shim sits in the
file body and runs on every import regardless.
"""
import os


def _apply_legacy_env_compat() -> None:
    """Bridge legacy env names (API_URL/API_KEY/ORGANIZATION_ID) to the new
    TORNIX_* names, only when the new name is not already set."""
    legacy_api_url = os.environ.get("API_URL")
    if legacy_api_url and not os.environ.get("TORNIX_API_URL"):
        # The new client appends its own /api/v1 path prefix, so strip a
        # trailing /api/v1 (and any trailing slash) from the legacy value.
        cleaned = legacy_api_url.rstrip("/")
        if cleaned.endswith("/api/v1"):
            cleaned = cleaned[: -len("/api/v1")]
        os.environ["TORNIX_API_URL"] = cleaned

    legacy_api_key = os.environ.get("API_KEY")
    if legacy_api_key and not os.environ.get("TORNIX_TOKEN"):
        os.environ["TORNIX_TOKEN"] = legacy_api_key

    legacy_org = os.environ.get("ORGANIZATION_ID")
    if legacy_org and not os.environ.get("TORNIX_ORG"):
        os.environ["TORNIX_ORG"] = legacy_org


_apply_legacy_env_compat()

__version__ = "0.1.0"
