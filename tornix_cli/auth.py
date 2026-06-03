from __future__ import annotations

import click

from .config import Config
from .output import emit


@click.group(name="auth", help="Authentication and API keys.")
def auth_group() -> None:
    pass


@auth_group.command("login", help="Authenticate with an API key or email/password. "
                                  "Prefer TORNIX_API_KEY env over --api-key (which is "
                                  "visible in the process list and shell history).")
@click.option("--api-key", "api_key", default=None, help="Scoped API key (tk_…).")
@click.option("--email", default=None)
@click.option("--password", default=None,
              help="Password (prefer interactive entry; flags leak via ps/history).")
@click.pass_obj
def login(obj, api_key, email, password):
    cfg: Config = obj["config"]
    client = obj["client"]
    if api_key:
        cfg.api_key = api_key
        client.config.api_key = api_key
    elif email and password:
        tok = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        cfg.token = (tok or {}).get("access_token") or (tok or {}).get("token")
        client.config.token = cfg.token
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
