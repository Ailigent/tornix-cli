"""Multi-organization helpers: list the caller's orgs, resolve `--org <name>`,
and the `--org all` fan-out for read commands.

Tornix honours `X-Organization-ID` per request for a verified member, so one
token reaches every org the user belongs to; nothing here needs another secret.
"""
from __future__ import annotations

import base64
import dataclasses
import json
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import click

from .errors import EXIT, TornixError
from .output import capture_emit, emit

ALL = "all"
MAX_WORKERS = 6
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)

# Commands that run once per org under `--org all`. Collection reads only: a
# read of ONE id (`projects get`, `tasks list --project p`, `hse …`) belongs to a
# single org, so fanning it out would only produce N-1 "not found" errors.
READ_ALL: frozenset[tuple[str, str]] = frozenset({
    ("projects", "list"),
    ("approvals", "list"),
    ("meetings", "list"),
    ("meetings", "room-list"),
    ("calendar", "list"),
    ("calendar", "members"),
    ("workload", "team"),
    ("workload", "suggestions"),
    ("workload", "calendar"),
    ("workload", "requests"),
    ("data", "select"),
})
# Top-level commands that never touch org data: `--org all` is simply ignored.
PASSTHROUGH = frozenset({"orgs", "config", "auth", "catalog", "doctor", "skill", "gen"})


def is_uuid(value: str | None) -> bool:
    return bool(value and _UUID_RE.match(value))


# ── listing ──
def _normalize(raw: Any) -> list[dict]:
    if isinstance(raw, dict):
        raw = next((raw[k] for k in ("organizations", "items", "data") if isinstance(raw.get(k), list)), [])
    out = []
    for o in raw or []:
        if not isinstance(o, dict) or not o.get("id"):
            continue
        out.append({"id": str(o["id"]), "name": o.get("name"),
                    "role": o.get("role") or o.get("member_role") or o.get("membership_role")})
    return out


def fetch_orgs(client) -> list[dict]:
    """The caller's orgs as [{id, name, role}], cached on the client for the process.

    Asks `?for=talon` (only orgs the user enabled for Talon, MO-04) and falls back to
    the plain list when an older Tornix rejects the query (400) or lacks it (404)."""
    cached = getattr(client, "_orgs_cache", None)
    if cached is not None:
        return cached
    no_org = {"X-Organization-ID": None}   # the list is per user; never scope it to an org
    try:
        raw = client.get("/api/v1/organizations", params={"for": "talon"}, headers=no_org)
    except TornixError as e:
        if e.status not in (400, 404):
            raise
        raw = client.get("/api/v1/organizations", headers=no_org)
    orgs = _normalize(raw)
    client._orgs_cache = orgs
    return orgs


def token_org_claim(token: str | None) -> str | None:
    """`organization_id` from a JWT payload (unverified; display only)."""
    try:
        payload = (token or "").split(".")[1]
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data.get("organization_id") or data.get("org_id") or data.get("organizationId")


# ── name resolution ──
def resolve_org(orgs: list[dict], value: str) -> str:
    """Org id for an id or a name: exact id, exact name (case-insensitive), then a
    unique prefix, then a unique substring. Ambiguity is a clear usage error."""
    v = value.strip()
    for o in orgs:
        if o["id"] == v:
            return o["id"]
    low = v.casefold()
    for test in (lambda n: n == low, lambda n: n.startswith(low), lambda n: low in n):
        hits = [o for o in orgs if test((o.get("name") or "").casefold())]
        if len(hits) == 1:
            return hits[0]["id"]
        if len(hits) > 1:
            names = "; ".join(f'"{o["name"]}" ({o["id"]})' for o in hits)
            raise click.UsageError(
                f'--org "{value}" matches more than one organization: {names}. '
                "Use the full name or the id.")
    names = ", ".join(f'"{o["name"]}"' for o in orgs) or "none"
    raise click.UsageError(f'--org "{value}" matches no organization of yours (yours: {names}).')


# ── --org all ──
def _walk(root: click.Group, tokens: list[str]) -> tuple[list[str], click.Command]:
    cmd: click.Command = root
    path: list[str] = []
    for tok in tokens:
        if not isinstance(cmd, click.Group):
            break
        if tok.startswith("-"):
            continue
        sub = cmd.commands.get(tok)
        if sub is None:
            break
        path.append(tok)
        cmd = sub
    return path, cmd


def is_read_all(path: list[str], cmd: click.Command) -> bool:
    if tuple(path) in READ_ALL:
        return True
    op = getattr(cmd, "_tornix_op", None)       # generated `api …` command
    return bool(op and op.get("_method") == "get" and "{" not in op.get("_path", "{"))


def run_all_orgs(ctx: click.Context, root: click.Group, tokens: list[str]) -> None:
    """Handle `--org all`: run a read command once per org (parallel), print the merged
    result and exit. Commands that touch no org data just run normally (returns)."""
    from .client import TornixClient

    path, cmd = _walk(root, tokens)
    if not path or path[0] in PASSTHROUGH:
        return
    if not is_read_all(path, cmd):
        raise click.UsageError(
            f'`--org all` only works for list-style reads; "tornix {" ".join(path)}" needs ONE '
            'organization. Re-run with --org "<name>" (see `tornix orgs list`).')
    obj, cfg = ctx.obj, ctx.obj["config"]
    parent = obj["client"]
    orgs = fetch_orgs(parent)
    if not orgs:
        raise TornixError("this account belongs to no organization", status=404)

    def one(org: dict):
        cl = TornixClient(dataclasses.replace(cfg, org_id=org["id"]),
                          transport=getattr(parent, "_transport", None))
        sink: list = []
        try:
            with capture_emit(sink):
                with root.make_context("tornix", ["--org", org["id"], *tokens],
                                       obj={"config": cl.config, "client": cl, "json": True}) as c2:
                    root.invoke(c2)
            return sink, None
        except click.exceptions.Exit as e:
            return sink, (None if e.exit_code == 0 else TornixError(f"exit {e.exit_code}"))
        except Exception as e:                    # one org failing must not sink the rest
            return sink, e
        finally:
            cl.close()

    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(orgs))) as pool:
        results = list(pool.map(one, orgs))

    rows: list[dict] = []
    errors: list[dict] = []
    columns: list[str] | None = None
    for org, (sink, err) in zip(orgs, results):
        tag = {"id": org["id"], "name": org["name"]}
        if err is not None:
            e = err if isinstance(err, TornixError) else TornixError(str(getattr(err, "message", err)))
            errors.append({"org": tag, "error": {"message": e.message, "status": e.status, "code": e.code}})
        for data, cols in sink:
            columns = columns or cols
            items = data if isinstance(data, list) else ([] if data is None else [data])
            for it in items:
                row = dict(it) if isinstance(it, dict) else {"value": it}
                if "org" in row:
                    row["org_raw"] = row.pop("org")
                row["org"] = tag
                rows.append(row)

    jsonl = "--jsonl" in tokens
    if jsonl or "--json" in tokens or obj.get("json"):
        if jsonl:
            emit(rows, json_mode=True, jsonl=True)
            for er in errors:
                click.echo(json.dumps(er, ensure_ascii=False), err=True)
        else:
            emit({"data": rows, "errors": errors}, json_mode=True)
    else:
        flat = [{**r, "org": r["org"]["name"]} for r in rows]
        emit(flat, columns=[*columns, "org"] if columns else None)
        for er in errors:
            click.echo(f'warning: {er["org"]["name"]}: {er["error"]["message"]}', err=True)
    if errors and len(errors) == len(orgs):
        raise TornixError("every organization failed: " + errors[0]["error"]["message"],
                          status=errors[0]["error"]["status"])
    ctx.exit(EXIT.OK)
