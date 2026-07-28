from __future__ import annotations

import re
from typing import Any

import click

from .output import emit_result
from .spec import classify_tags, is_excluded_op, operations_by_tag

_VERB = {"get_one": "get", "get_many": "list", "post": "create",
         "patch": "update", "put": "replace", "delete": "delete"}

_TYPE = {"integer": int, "number": float, "boolean": bool}


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _arg_dest(name: str) -> str:
    """Replicate Click's Argument destination normalization (lower + dash→underscore),
    so we can look up the kwarg for a path param like {projectId} (→ 'projectid')."""
    return name.lower().replace("-", "_")


def _body_dest(fname: str) -> str:
    """A valid Python identifier dest for a body field option, hyphen-safe."""
    return "_body_" + re.sub(r"[^0-9a-zA-Z_]", "_", fname)


def _op_command_name(op: dict, tag: str) -> str:
    """Name a command from its path action segment, falling back to a REST verb.

    `/ai-agents/{id}/run` → "run", `/ai-agents/seed-defaults` → "seed-defaults",
    `/projects` GET → "list", POST → "create", `/projects/{id}` GET → "get".
    """
    method, path = op["_method"], op["_path"]
    segs = path.replace("/api/v1/", "").strip("/").split("/")
    last = segs[-1] if segs else ""
    last_is_param = last.startswith("{")
    if not last_is_param:
        slugged = _slug(last)
        # A trailing literal that isn't just the resource/collection name is an action.
        if slugged and slugged != _slug(tag):
            return slugged
    if method == "get":
        return _VERB["get_one"] if last_is_param else _VERB["get_many"]
    if method == "post":
        return _VERB["post"]
    if method in ("patch", "put", "delete"):
        return _VERB[method]
    return _slug(op["operationId"])


def _qualified_name(op: dict, tag: str) -> str | None:
    """A path-derived name for disambiguating same-verb collisions within a tag,
    e.g. `/projects/{id}/cost/evm/trend` (tag cost) → "evm-trend"."""
    segs = [s for s in op["_path"].replace("/api/v1/", "").strip("/").split("/")
            if not s.startswith("{")]
    segs = [s for s in segs if _slug(s) != _slug(tag)]
    if not segs:
        return None
    name = _slug("-".join(segs[-2:]))
    if not name:
        return None
    # For write methods on a collection, suffix the verb to separate from a GET.
    if op["_method"] in ("post", "patch", "put", "delete"):
        return f"{name}-{_VERB.get(op['_method'], op['_method'])}"
    # A GET whose path ends in a parameter is a single-resource read colliding
    # with its own collection GET (`/strategic/kpis` vs `/strategic/kpis/{id}`).
    # Suffix the read verb rather than falling back to a meaningless `-2`.
    if op["_method"] == "get" and op["_path"].rstrip("/").split("/")[-1].startswith("{"):
        return f"{name}-{_VERB['get_one']}"
    return name


def _decorate(base: str, op: dict) -> str:
    """Attach the verb that distinguishes an operation from its siblings on the
    same resource: a write verb, or `-get` for a single-resource read."""
    if not base:
        return base
    if op["_method"] in ("post", "patch", "put", "delete"):
        return f"{base}-{_VERB.get(op['_method'], op['_method'])}"
    if op["_method"] == "get" and op["_path"].rstrip("/").split("/")[-1].startswith("{"):
        return f"{base}-{_VERB['get_one']}"
    return base


def _name_candidates(op: dict, tag: str):
    """Ordered command-name candidates; `build_api_group` takes the first unused
    one. The first two entries reproduce the historical names exactly, so a
    command that does not collide is never renamed by a spec refresh. Later
    entries widen the path window until the name is unique, which keeps
    genuinely contested names descriptive instead of falling back to `-2`."""
    yield _op_command_name(op, tag)
    qualified = _qualified_name(op, tag)
    if qualified:
        yield qualified

    raw = op["_path"].replace("/api/v1/", "").strip("/").split("/")
    norm: list[str] = []
    for seg in raw:
        if seg.startswith("{"):
            norm.append(_slug(seg.strip("{}")))
        elif seg == "*":
            norm.append("proxy")          # catch-all passthrough path
        else:
            norm.append(_slug(seg))
    pairs = [(n, r) for n, r in zip(norm, raw) if n]
    if not pairs:
        return
    norm = [n for n, _ in pairs]

    # Named resources carry the meaning; a `*` passthrough and `{param}` slots do
    # not, so prefer names built from real path segments before falling back to
    # the raw window. `/ai/reports/*` should read "ai-reports", never "proxy".
    named = [n for n, r in pairs if not r.startswith("{") and r != "*"]
    for width in (1, 2):
        if len(named) >= width:
            yield _decorate("-".join(named[-width:]), op)

    # Progressively wider windows over the full path, params included, so even
    # `/strategy/risks/{strategyId}/{riskId}` resolves to a descriptive name.
    for width in range(2, len(norm) + 1):
        yield _decorate("-".join(norm[-width:]), op)


def _path_params(op: dict) -> list[dict]:
    return [p for p in op.get("parameters", []) if p.get("in") == "path"]


def _query_params(op: dict) -> list[dict]:
    return [p for p in op.get("parameters", []) if p.get("in") == "query"]


def _body_schema(op: dict) -> dict | None:
    rb = op.get("requestBody") or {}
    return ((rb.get("content") or {}).get("application/json") or {}).get("schema")


def _click_type(schema: dict):
    return _TYPE.get((schema or {}).get("type", "string"), str)


def _build_command(op: dict, tag: str) -> click.Command:
    name = _op_command_name(op, tag)
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
            params.append(click.Option([f"--{_slug(fname)}", _body_dest(fname)],
                                        required=fname in required,
                                        type=_click_type(fschema),
                                        help=(fschema or {}).get("description", "")))
    writes = op["_method"] in ("post", "put", "patch")
    if body or writes:
        params.append(click.Option(["--data", "_raw_body"],
                                    help="Raw JSON body (overrides --field options)."))
    # Bodyless bare-verb CRUD shapes must not fire with an empty body: a
    # collection POST `create` would mint an untitled row, a resource PUT/PATCH
    # `replace`/`update` would blank fields. Both demand --data. Action endpoints
    # (trailing literal like /run, or trailing-param POST like gantt scheduling)
    # are untouched — `name` here is the pre-collision _op_command_name result.
    last_is_param = op["_path"].rstrip("/").split("/")[-1].startswith("{")
    requires_data = writes and not body and (
        (op["_method"] == "post" and not last_is_param and name == "create")
        or (op["_method"] in ("put", "patch") and last_is_param
            and name in ("replace", "update"))
    )

    def callback(**kwargs):
        ctx = click.get_current_context()
        obj = ctx.obj or {}
        client = obj["client"]
        path = op["_path"]
        for pp in _path_params(op):
            # Click normalized the Argument dest; look it up the same way.
            path = path.replace("{%s}" % pp["name"], str(kwargs.pop(_arg_dest(pp["name"]))))
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
            try:
                payload = _j.loads(raw)
            except _j.JSONDecodeError as e:
                raise click.UsageError(f"invalid JSON for --data: {e}")
        elif body_fields:
            payload = {f: kwargs[_body_dest(f)] for f in body_fields
                       if kwargs.get(_body_dest(f)) is not None}
        if requires_data and payload is None:
            raise click.UsageError(
                "this command writes a JSON body the API spec does not document; "
                "pass --data '<json>' (or use the curated equivalent command).")
        result = client.request(op["_method"].upper(), path, params=query or None, json=payload)
        emit_result(obj, result)

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
        # Deterministic order → stable command names across spec refreshes.
        # Within one path, reads claim a contested bare name before writes and
        # writes before DELETE — alphabetical order let `delete` win friendly
        # names (`pv-curve`, `push-subscribe`), handing agents destructive
        # commands where they meant to read/subscribe.
        rank = {"get": 0, "post": 1, "put": 2, "patch": 3, "delete": 4}
        for op in sorted(by_tag[tag], key=lambda o: (o["_path"], rank.get(o["_method"], 9))):
            if is_excluded_op(op):
                continue
            cmd = _build_command(op, tag)
            base = cmd.name
            for candidate in _name_candidates(op, tag):
                if candidate and candidate not in used:
                    cmd.name = candidate
                    break
            else:
                n = 2
                while cmd.name in used:       # last resort: numeric suffix
                    cmd.name = f"{base}-{n}"
                    n += 1
            used.add(cmd.name)
            sub.add_command(cmd)
        if sub.commands:
            root.add_command(sub)
    return root
