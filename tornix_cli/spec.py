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
    "livekit-webhook", "odoo-sync-callback",
}
# Path-prefix exclusions for untagged/internal operations.
EXCLUDE_PATH_PREFIXES = ("/api/v1/odoo-", "/api/v1/livekit", "/api/v1/webhooks")


def load_spec() -> dict:
    return json.loads(Path(PINNED_SPEC).read_text())


def fetch_spec(base_url: str, timeout: float = 30.0) -> dict:
    url = base_url.rstrip("/") + "/api/v1/api-docs/openapi.json"
    body = httpx.get(url, timeout=timeout).json()
    return body.get("data", body) if isinstance(body, dict) else body


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
    return path.startswith(EXCLUDE_PATH_PREFIXES)


def _fallback_op_id(method: str, path: str) -> str:
    slug = path.strip("/").replace("/api/v1/", "").replace("{", "").replace("}", "")
    slug = slug.replace("/", "_").replace("-", "_")
    return f"{method.lower()}_{slug}"
