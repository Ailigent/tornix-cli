from __future__ import annotations

import json

import click

from .output import emit


@click.group(name="data", help="Generic PostgREST-style table access (escape hatch).")
def data_group() -> None:
    pass


def _kv(pairs: tuple[str, ...]) -> dict[str, str]:
    out = {}
    for p in pairs:
        k, _, v = p.partition("=")
        out[k] = v
    return out


@data_group.command("select")
@click.argument("table")
@click.option("--eq", "eq", multiple=True, help="Filter col=value (repeatable).")
@click.option("--select", "select_", default=None, help="Comma-separated columns.")
@click.option("--order", default=None, help="col.asc / col.desc")
@click.option("--limit", type=int, default=None)
@click.pass_obj
def data_select(obj, table, eq, select_, order, limit):
    params = {}
    for k, v in _kv(eq).items():
        params[k] = f"eq.{v}"          # PostgREST operator form
    if select_:
        params["select"] = select_
    if order:
        params["order"] = order
    if limit is not None:
        params["limit"] = limit
    emit(obj["client"].get(f"/api/v1/data/{table}", params=params), json_mode=obj.get("json"))


@data_group.command("insert")
@click.argument("table")
@click.option("--data", "raw", required=True, help="JSON row or array.")
@click.pass_obj
def data_insert(obj, table, raw):
    emit(obj["client"].post(f"/api/v1/data/{table}", json=json.loads(raw)),
         json_mode=obj.get("json"))


@data_group.command("update")
@click.argument("table")
@click.option("--eq", "eq", multiple=True, required=True)
@click.option("--data", "raw", required=True)
@click.pass_obj
def data_update(obj, table, eq, raw):
    params = {k: f"eq.{v}" for k, v in _kv(eq).items()}
    emit(obj["client"].patch(f"/api/v1/data/{table}", params=params, json=json.loads(raw)),
         json_mode=obj.get("json"))


@data_group.command("delete")
@click.argument("table")
@click.option("--eq", "eq", multiple=True, required=True)
@click.pass_obj
def data_delete(obj, table, eq):
    params = {k: f"eq.{v}" for k, v in _kv(eq).items()}
    emit(obj["client"].delete(f"/api/v1/data/{table}", params=params), json_mode=obj.get("json"))


@click.command(name="rpc", help="Call a backend RPC function.")
@click.argument("function")
@click.option("--arg", "args", multiple=True, help="key=value (repeatable).")
@click.option("--data", "raw", default=None, help="Raw JSON body (overrides --arg).")
@click.pass_obj
def rpc_command(obj, function, args, raw):
    body = json.loads(raw) if raw else _kv(args)
    emit(obj["client"].post(f"/api/v1/rpc/{function}", json=body), json_mode=obj.get("json"))
