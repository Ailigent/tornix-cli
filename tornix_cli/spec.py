from __future__ import annotations

import json
from pathlib import Path

import httpx

PINNED_SPEC = Path(__file__).parent / "generated" / "_spec.json"

# Tags re-exposing the same backend via proxy/compat layers → fold into `data`/`rpc`.
FOLD_TAGS = {"PostgREST Compatibility", "data-proxy", "rpc-proxy"}
# Tags that are internal/webhook/meta/duplicate → never generate commands.
EXCLUDE_TAGS = {
    "mcp", "api-docs", "API Documentation", "storage-compat",
    "odoo-sync", "odoo-sync-admin",
}
# Inbound webhooks / OAuth+integration callbacks are not first-class commands
# (spec §3 non-goal). Matches e.g. .../livekit/webhook, .../odoo-*-callback, auth OAuth callbacks.
EXCLUDE_PATH_SUBSTRINGS = ("webhook", "callback")

# Operations a curated command already covers AND whose generated form is unsafe.
# These ops have no requestBody in the spec, so their generated commands would
# send an EMPTY body and mint untitled rows (the duplicate/untitled-project bug).
# Keyed on (method, path) wire coordinates — NOT operationId — so a `tornix gen`
# spec refresh that renames controllers cannot silently resurrect them.
SUPERSEDED_OPS = {
    ("post", "/api/v1/projects"),                     # → tornix projects create --name
    ("post", "/api/v1/projects/{projectId}/tasks"),   # → tornix tasks create --title
}


def load_spec() -> dict:
    return json.loads(Path(PINNED_SPEC).read_text())


def _allowed_base(base: str) -> bool:
    """Allow https anywhere; http only for localhost/dev (SSRF guard)."""
    if base.startswith("https://"):
        return True
    if base.startswith("http://"):
        host = base[len("http://"):].split("/")[0].split(":")[0]
        return host in ("localhost", "127.0.0.1", "0.0.0.0") or host.endswith(".local")
    return False


_API_PREFIX = "/api/v1"
_COMPAT_PREFIXES = ("/rest/v1", "/storage/v1", "/api/credits")


def normalize_spec_paths(spec: dict) -> dict:
    """Apply NestJS's omitted global prefix while preserving legacy API roots.

    The backend OpenAPI exporter omits the global `/api/v1` prefix from ordinary
    controller routes. The CLI snapshot and request paths use that prefix, but
    `/rest/v1`, `/storage/v1`, and `/api/credits` are compatibility roots and
    must remain unchanged. The operation is idempotent and rejects collisions
    rather than silently dropping routes.
    """
    raw_paths = spec.get("paths")
    if not isinstance(raw_paths, dict):
        raise ValueError("OpenAPI paths must be an object")

    normalized_paths: dict[str, dict] = {}
    for path, path_item in raw_paths.items():
        if not isinstance(path, str) or not path.startswith("/"):
            raise ValueError(f"OpenAPI path must start with '/': {path!r}")
        prefixed = (path == _API_PREFIX or path.startswith(_API_PREFIX + "/")
                    or any(path == root or path.startswith(root + "/")
                           for root in _COMPAT_PREFIXES))
        normalized = path if prefixed else _API_PREFIX + path
        if not isinstance(path_item, dict):
            raise ValueError(f"OpenAPI path item must be an object: {path!r}")
        target = normalized_paths.setdefault(normalized, {})
        for key, value in path_item.items():
            if key in target and target[key] != value:
                raise ValueError(f"conflicting OpenAPI paths normalize to {normalized!r}")
            target[key] = value

    result = dict(spec)
    result["paths"] = normalized_paths
    return result


def fetch_spec(base_url: str, timeout: float = 30.0) -> dict:
    base = base_url.rstrip("/")
    if not _allowed_base(base):
        raise ValueError(f"refusing to fetch spec from non-https/non-local URL: {base_url}")
    url = base + "/api/v1/api-docs/openapi.json"
    body = httpx.get(url, timeout=timeout).json()
    spec = body.get("data", body) if isinstance(body, dict) else body
    if not (isinstance(spec, dict) and (spec.get("openapi") or spec.get("swagger"))
            and spec.get("paths")):
        raise ValueError("fetched document is not a valid OpenAPI spec (missing openapi/paths)")
    return normalize_spec_paths(spec)


def operations_by_tag(spec: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for path, methods in (spec.get("paths") or {}).items():
        for method, op in methods.items():
            if method.lower() not in ("get", "post", "put", "patch", "delete"):
                continue
            tag = (op.get("tags") or ["misc"])[0]
            entry = dict(op)
            entry["_method"] = method.lower()
            entry["_path"] = path
            entry.setdefault("operationId", _fallback_op_id(method, path))
            out.setdefault(tag, []).append(entry)
    return out


def classify_tags(spec: dict) -> dict[str, set[str]]:
    tags = set(operations_by_tag(spec).keys())
    fold = tags & FOLD_TAGS
    exclude = tags & EXCLUDE_TAGS
    generate = tags - fold - exclude
    return {"generate": generate, "fold": fold, "exclude": exclude}


def is_excluded_path(path: str) -> bool:
    return any(sub in path for sub in EXCLUDE_PATH_SUBSTRINGS)


def is_excluded_op(op: dict) -> bool:
    """An operation is excluded from the generated api group when its path is a
    webhook/callback OR it is superseded by a safer curated command."""
    return (is_excluded_path(op.get("_path", ""))
            or (op.get("_method"), op.get("_path")) in SUPERSEDED_OPS)


def _fallback_op_id(method: str, path: str) -> str:
    slug = path.strip("/").replace("/api/v1/", "").replace("{", "").replace("}", "")
    slug = slug.replace("/", "_").replace("-", "_")
    return f"{method.lower()}_{slug}"
