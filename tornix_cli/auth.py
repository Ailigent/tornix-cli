from __future__ import annotations

import click

from .config import Config
from .output import emit


@click.group(name="auth", help="Authentication and API keys.")
def auth_group() -> None:
    pass


def _session_token(payload) -> str | None:
    p = payload or {}
    return p.get("access_token") or p.get("token")


def _complete_2fa(client, pending_token: str, code: str | None) -> str:
    """Exchange a short-lived 2FA-pending token for a real session token.

    A 2FA-enabled account gets `pending_token` back from /auth/login instead of
    a session; without this exchange the CLI would store None and leave a
    silently broken config."""
    client.post("/api/v1/auth/2fa/otp/send", json={"pending_token": pending_token})
    if not code:
        code = click.prompt("2FA code")
    verified = client.post("/api/v1/auth/2fa/verify",
                           json={"pending_token": pending_token, "code": code})
    token = _session_token(verified)
    if not token:
        raise click.ClickException("2FA verification did not return a session token.")
    return token


@auth_group.command("login", help="Authenticate with an API key or email/password. "
                                  "Prefer TORNIX_API_KEY env over --api-key (which is "
                                  "visible in the process list and shell history).")
@click.option("--api-key", "api_key", default=None, help="Scoped API key (tnx_…).")
@click.option("--email", default=None)
@click.option("--password", default=None,
              help="Password (prefer interactive entry; flags leak via ps/history).")
@click.option("--code", default=None,
              help="2FA code, for headless login on a 2FA-enabled account. "
                   "Omit it and you'll be prompted.")
@click.pass_obj
def login(obj, api_key, email, password, code):
    cfg: Config = obj["config"]
    client = obj["client"]
    if api_key:
        cfg.api_key = api_key
        client.config.api_key = api_key
    elif email and password:
        resp = client.post("/api/v1/auth/login",
                           json={"email": email, "password": password})
        token = _session_token(resp)
        if not token:
            pending = (resp or {}).get("pending_token")
            if not pending:
                raise click.ClickException(
                    "login returned neither a session token nor a 2FA pending_token.")
            token = _complete_2fa(client, pending, code)
        cfg.token = token
        client.config.token = token
    else:
        raise click.UsageError("Provide --api-key or --email/--password.")
    me = client.get("/api/v1/auth/me")
    cfg.save()
    emit({"logged_in": True, "user": me}, json_mode=obj.get("json"))


@auth_group.command("logout", help="Clear the stored API key / token.")
@click.pass_obj
def logout(obj):
    cfg: Config = obj["config"]
    cfg.api_key = None
    cfg.token = None
    cfg.save()
    emit({"logged_out": True}, json_mode=obj.get("json"))


@auth_group.command("whoami", help="Show the authenticated user.")
@click.pass_obj
def whoami(obj):
    emit(obj["client"].get("/api/v1/auth/me"), json_mode=obj.get("json"))


@auth_group.group("keys", help="Manage API keys.")
def keys():
    pass


@keys.command("list", help="List your API keys.")
@click.pass_obj
def keys_list(obj):
    emit(obj["client"].get("/api/v1/api-keys"), json_mode=obj.get("json"))


@keys.command("scopes", help="List available permission scopes.")
@click.pass_obj
def keys_scopes(obj):
    emit(obj["client"].get("/api/v1/api-keys/scopes"), json_mode=obj.get("json"))


@keys.command("create", help="Create a new API key (raw key shown once).")
@click.option("--name", required=True)
@click.option("--scope", "scopes", multiple=True, help="Permission scope (repeatable).")
@click.pass_obj
def keys_create(obj, name, scopes):
    body = {"name": name, "scopes": list(scopes)}
    emit(obj["client"].post("/api/v1/api-keys", json=body), json_mode=obj.get("json"))


@keys.command("revoke", help="Revoke an API key by id.")
@click.argument("key_id")
@click.pass_obj
def keys_revoke(obj, key_id):
    emit(obj["client"].post(f"/api/v1/api-keys/{key_id}/revoke"), json_mode=obj.get("json"))


@keys.command("get", help="Show one API key by id.")
@click.argument("key_id")
@click.pass_obj
def keys_get(obj, key_id):
    emit(obj["client"].get(f"/api/v1/api-keys/{key_id}"), json_mode=obj.get("json"))


@keys.command("update", help="Update an API key (PATCH) with a JSON body.")
@click.argument("key_id")
@click.option("--data", "raw", required=True, help="JSON body (PATCH).")
@click.pass_obj
def keys_update(obj, key_id, raw):
    import json as _j
    try:
        payload = _j.loads(raw)
    except _j.JSONDecodeError as e:
        raise click.UsageError(f"invalid JSON for --data: {e}")
    emit(obj["client"].patch(f"/api/v1/api-keys/{key_id}", json=payload),
         json_mode=obj.get("json"))


@keys.command("delete", help="Delete an API key by id.")
@click.argument("key_id")
@click.pass_obj
def keys_delete(obj, key_id):
    emit(obj["client"].delete(f"/api/v1/api-keys/{key_id}"), json_mode=obj.get("json"))


@keys.command("usage", help="Show usage statistics for an API key.")
@click.argument("key_id")
@click.pass_obj
def keys_usage(obj, key_id):
    emit(obj["client"].get(f"/api/v1/api-keys/{key_id}/usage"), json_mode=obj.get("json"))
