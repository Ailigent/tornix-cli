from __future__ import annotations

import re
from typing import Any

import click

from .output import emit
from .spec import classify_tags, is_excluded_path, operations_by_tag

_VERB = {"get_one": "get", "get_many": "list", "post": "create",
         "patch": "update", "put": "replace", "delete": "delete"}

_TYPE = {"integer": int, "number": float, "boolean": bool}


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _op_command_name(op: dict) -> str:
    """Derive a short verb from method + whether the path ends in a param."""
    method, path = op["_method"], op["_path"]
    last_is_param = path.rstrip("/").endswith("}")
    if method == "get":
        return _VERB["get_one"] if last_is_param else _VERB["get_many"]
    if method == "post":
        return _VERB["post"]
    if method in ("patch", "put", "delete"):
        return _VERB[method]
    return _slug(op["operationId"])


def _path_params(op: dict) -> list[dict]:
    return [p for p in op.get("parameters", []) if p.get("in") == "path"]


def _query_params(op: dict) -> list[dict]:
    return [p for p in op.get("parameters", []) if p.get("in") == "query"]


def _body_schema(op: dict) -> dict | None:
    rb = op.get("requestBody") or {}
    return ((rb.get("content") or {}).get("application/json") or {}).get("schema")


def _click_type(schema: dict):
    return _TYPE.get((schema or {}).get("type", "string"), str)


def _build_command(op: dict) -> click.Command:
    name = _op_command_name(op)
    params: list[click.Parameter] = []
    for p in _path_params(op):
        params.append(click.Argument([p["name"]], required=True,
                                     type=_click_type(p.get("schema", {}))))
    for q in _query_params(op):
        params.append(click.Option([f"--{_slug(q['name'])}"], required=q.get("required", False),
                                    type=_click_type(q.get("schema", {})),
                                    help=q.get("description", "")))
    body = _body_schema(op)
    body_fields: list[str] = []
    if body and body.get("type") == "object":
        required = set(body.get("required", []))
        for fname, fschema in (body.get("properties") or {}).items():
            body_fields.append(fname)
            params.append(click.Option([f"--{_slug(fname)}", "_body_" + fname],
                                        required=fname in required,
                                        type=_click_type(fschema),
                                        help=(fschema or {}).get("description", "")))
    if body:
        params.append(click.Option(["--data", "_raw_body"],
                                    help="Raw JSON body (overrides --field options)."))

    def callback(**kwargs):
        ctx = click.get_current_context()
        obj = ctx.obj or {}
        client = obj["client"]
        json_mode = obj.get("json", False)
        path = op["_path"]
        for pp in _path_params(op):
            path = path.replace("{%s}" % pp["name"], str(kwargs.pop(pp["name"])))
        query = {}
        for q in _query_params(op):
            key = _slug(q["name"]).replace("-", "_")
            v = kwargs.pop(key, None)
            if v is not None:
                query[q["name"]] = v
        payload: Any = None
        raw = kwargs.pop("_raw_body", None)
        if raw:
            import json as _j
            payload = _j.loads(raw)
        elif body_fields:
            payload = {f: kwargs[f"_body_{f}"] for f in body_fields
                       if kwargs.get(f"_body_{f}") is not None}
        result = client.request(op["_method"].upper(), path, params=query or None, json=payload)
        emit(result, json_mode=json_mode)

    cmd = click.Command(name=name, params=params, callback=callback,
                        help=op.get("summary") or op.get("description") or op["operationId"],
                        short_help=op.get("summary"))
    cmd._tornix_op = op  # for catalog introspection
    return cmd


def build_api_group(spec: dict) -> click.Group:
    cls = classify_tags(spec)
    by_tag = operations_by_tag(spec)
    root = click.Group(name="api", help="Full generated backbone (one subgroup per API tag).")
    for tag in sorted(cls["generate"]):
        sub = click.Group(name=_slug(tag), help=f"{tag} operations.")
        used: set[str] = set()
        for op in by_tag[tag]:
            if is_excluded_path(op["_path"]):
                continue
            cmd = _build_command(op)
            base = cmd.name
            n = 2
            while cmd.name in used:           # disambiguate duplicate verbs
                cmd.name = f"{base}-{n}"
                n += 1
            used.add(cmd.name)
            sub.add_command(cmd)
        if sub.commands:
            root.add_command(sub)
    return root
