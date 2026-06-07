from __future__ import annotations

import json

import click

from .output import emit_result


def _load_json(raw: str, label: str = "--data"):
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise click.UsageError(f"invalid JSON for {label}: {e}")


@click.group(name="data", help="Generic PostgREST-style table access (escape hatch).")
def data_group() -> None:
    pass


def _kv(pairs: tuple[str, ...]) -> dict[str, str]:
    out = {}
    for p in pairs:
        k, _, v = p.partition("=")
        out[k] = v
    return out


@data_group.command("select", help="Read rows from a table with optional filters.")
@click.argument("table")
@click.option("--eq", "eq", multiple=True, help="Equality filter col=value (repeatable).")
@click.option("--filter", "filters", multiple=True,
              help="Raw PostgREST filter col=op.value (repeatable), e.g. status=in.(done,closed) "
                   "or percent_complete=gte.100. Operators: eq,neq,gt,gte,lt,lte,like,ilike,in,is,not.")
@click.option("--select", "select_", default=None, help="Comma-separated columns (project only what you need).")
@click.option("--order", default=None, help="col.asc / col.desc")
@click.option("--limit", type=int, default=None)
@click.option("--offset", type=int, default=None, help="Skip N rows (pagination).")
@click.option("--count", is_flag=True, default=False,
              help="Return ONLY the total row count (matching the filters), not the rows. "
                   "Use this for 'how many' questions instead of pulling rows.")
@click.pass_obj
def data_select(obj, table, eq, filters, select_, order, limit, offset, count):
    params = {}
    for k, v in _kv(eq).items():
        params[k] = f"eq.{v}"          # PostgREST operator form
    for f in filters:
        k, _, v = f.partition("=")
        if k:
            params[k] = v              # raw op.value passthrough (backend parses col=op.value)
    if select_:
        params["select"] = select_
    if order:
        params["order"] = order
    if count:
        # count-only: ask the backend for an exact count, minimise rows returned
        params["count"] = "exact"
        params["limit"] = 1
        body = obj["client"].get(f"/api/v1/data/{table}", params=params, envelope=True)
        n = None
        if isinstance(body, dict):
            n = body.get("count")
            if n is None and isinstance(body.get("meta"), dict):
                n = body["meta"].get("count")
            if n is None and isinstance(body.get("data"), list):
                n = len(body["data"])
        emit_result(obj, {"count": n})
        return
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset
    emit_result(obj, obj["client"].get(f"/api/v1/data/{table}", params=params))


@data_group.command("insert", help="Insert a row (or array of rows) into a table.")
@click.argument("table")
@click.option("--data", "raw", required=True, help="JSON row or array.")
@click.pass_obj
def data_insert(obj, table, raw):
    emit_result(obj, obj["client"].post(f"/api/v1/data/{table}", json=_load_json(raw)))


@data_group.command("update", help="Update rows matching --eq filters.")
@click.argument("table")
@click.option("--eq", "eq", multiple=True, required=True)
@click.option("--data", "raw", required=True)
@click.pass_obj
def data_update(obj, table, eq, raw):
    params = {k: f"eq.{v}" for k, v in _kv(eq).items()}
    emit_result(obj, obj["client"].patch(f"/api/v1/data/{table}", params=params, json=_load_json(raw)))


@data_group.command("delete", help="Delete rows matching --eq filters.")
@click.argument("table")
@click.option("--eq", "eq", multiple=True, required=True)
@click.pass_obj
def data_delete(obj, table, eq):
    params = {k: f"eq.{v}" for k, v in _kv(eq).items()}
    emit_result(obj, obj["client"].delete(f"/api/v1/data/{table}", params=params))


@click.command(name="rpc", help="Call a backend RPC function.")
@click.argument("function")
@click.option("--arg", "args", multiple=True, help="key=value (repeatable).")
@click.option("--data", "raw", default=None, help="Raw JSON body (overrides --arg).")
@click.pass_obj
def rpc_command(obj, function, args, raw):
    body = _load_json(raw) if raw else _kv(args)
    emit_result(obj, obj["client"].post(f"/api/v1/rpc/{function}", json=body))
