from __future__ import annotations

from typing import Any

import httpx

from .config import Config
from .errors import TornixError


class TornixClient:
    def __init__(self, config: Config, *, transport: httpx.BaseTransport | None = None,
                 timeout: float = 30.0, retries: int = 2) -> None:
        self.config = config
        self._transport = transport
        self._org_resolved: dict[str, str] = {}
        # Default transport retries transient connection failures; tests inject a mock.
        if transport is None:
            transport = httpx.HTTPTransport(retries=retries)
        self._http = httpx.Client(
            base_url=config.api_url or "",
            timeout=timeout,
            transport=transport,
            headers={"Accept": "application/json"},
        )

    # ── headers ──
    def _headers(self, extra: dict | None = None) -> dict:
        h: dict[str, str] = {}
        bearer = self.config.api_key or self.config.token
        if bearer:
            h["Authorization"] = f"Bearer {bearer}"
        org = None if "X-Organization-ID" in (extra or {}) else self._effective_org()
        if org:
            h["X-Organization-ID"] = org
        if extra:
            h.update(extra)
        # A None value drops that header (e.g. listing orgs without scoping to one).
        return {k: v for k, v in h.items() if v is not None}

    def _effective_org(self) -> str | None:
        """The org id to send. `--org` may be an id or a NAME; a name is resolved once
        against the caller's own org list. `all` is handled by the CLI fan-out, never sent."""
        from .orgs import ALL, fetch_orgs, is_uuid, resolve_org
        org = self.config.org_id
        if not org or org.lower() == ALL:
            return None
        if is_uuid(org):
            return org
        if org not in self._org_resolved:
            self._org_resolved[org] = resolve_org(fetch_orgs(self), org)
        return self._org_resolved[org]

    # ── core request ──
    def request(self, method: str, path: str, *, params: dict | None = None,
                json: Any = None, headers: dict | None = None,
                envelope: bool = False) -> Any:
        try:
            resp = self._http.request(method, path, params=_clean(params),
                                      json=json, headers=self._headers(headers))
        except httpx.HTTPError as e:
            raise TornixError(str(e), status=None, code="network") from e
        if resp.status_code >= 400:
            raise self._to_error(resp)
        if resp.status_code == 204 or not resp.content:
            return None
        body = resp.json()
        # When envelope=True, return the full parsed body without unwrapping.
        if envelope:
            return body
        # Backend wraps successful payloads in {"data": …}. Unwrap when present.
        if isinstance(body, dict) and set(body.keys()) <= {"data", "meta", "count"} and "data" in body:
            return body["data"]
        return body

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, **kw):
        return self.request("POST", path, **kw)

    def patch(self, path, **kw):
        return self.request("PATCH", path, **kw)

    def put(self, path, **kw):
        return self.request("PUT", path, **kw)

    def delete(self, path, **kw):
        return self.request("DELETE", path, **kw)

    def _to_error(self, resp: httpx.Response) -> TornixError:
        msg, code, hint = resp.reason_phrase, None, None
        try:
            b = resp.json()
            if isinstance(b, dict):
                inner = b.get("error") if isinstance(b.get("error"), dict) else b
                msg = inner.get("message") or inner.get("error") or msg
                code = inner.get("code")
        except Exception:
            pass
        if resp.status_code == 403:
            hint = "API key may be missing a required scope (see `tornix auth keys scopes`)."
        return TornixError(str(msg), status=resp.status_code, code=code, hint=hint)

    def close(self) -> None:
        self._http.close()


def _clean(params: dict | None) -> dict | None:
    if not params:
        return params
    return {k: v for k, v in params.items() if v is not None}
