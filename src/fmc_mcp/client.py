"""Async HTTP client for the Cisco Secure Firewall Management Center (FMC) REST API.

Handles FMC's token authentication transparently: it POSTs Basic credentials to
`/api/fmc_platform/v1/auth/generatetoken`, which returns the access token, a
refresh token, and the default domain UUID in RESPONSE HEADERS (not the body).
Subsequent requests carry the `X-auth-access-token` header; on 401 the client
re-authenticates once. FMC config endpoints are domain-scoped, so the client
exposes `config_path()` / `platform_path()` helpers.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx

from .config import Settings


class FMCAPIError(Exception):
    """Raised when the FMC API returns an error response."""

    def __init__(self, status_code: int, method: str, path: str, detail: str):
        self.status_code = status_code
        super().__init__(f"FMC API error {status_code} on {method} {path}: {detail}")


class FMCClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._token: str | None = None
        self._refresh_token: str | None = None
        self._domain_uuid: str | None = None
        self._auth_lock = asyncio.Lock()
        self._http = httpx.AsyncClient(
            base_url=settings.base_url,
            verify=settings.verify_ssl,
            timeout=settings.timeout,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------
    async def _authenticate(self) -> None:
        resp = await self._http.post(
            "/api/fmc_platform/v1/auth/generatetoken",
            auth=(self.settings.username, self.settings.password),
        )
        if resp.status_code not in (200, 204):
            raise FMCAPIError(
                resp.status_code, "POST", "/api/fmc_platform/v1/auth/generatetoken",
                f"authentication failed: {resp.text[:500]}",
            )
        token = resp.headers.get("X-auth-access-token")
        if not token:
            raise FMCAPIError(
                resp.status_code, "POST", "/api/fmc_platform/v1/auth/generatetoken",
                "no X-auth-access-token header in response",
            )
        self._token = token
        self._refresh_token = resp.headers.get("X-auth-refresh-token")
        self._domain_uuid = resp.headers.get("DOMAIN_UUID")
        # Resolve a non-default domain by name if requested.
        if self.settings.domain and self.settings.domain.lower() != "global":
            await self._resolve_domain(self.settings.domain)

    async def _resolve_domain(self, name: str) -> None:
        resp = await self._http.get(
            "/api/fmc_platform/v1/info/domain",
            headers={"X-auth-access-token": self._token or ""},
        )
        if resp.status_code < 400:
            for dom in resp.json().get("items", []):
                if dom.get("name", "").lower() == name.lower():
                    self._domain_uuid = dom.get("uuid")
                    return

    async def _ensure_token(self) -> None:
        if self._token is None:
            async with self._auth_lock:
                if self._token is None:
                    await self._authenticate()

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------
    @property
    def domain_uuid(self) -> str | None:
        return self._domain_uuid

    def config_path(self, rel: str) -> str:
        """Build a domain-scoped fmc_config path from a relative path.

        e.g. config_path('/devices/devicerecords') ->
             '/api/fmc_config/v1/domain/{uuid}/devices/devicerecords'
        """
        if not rel.startswith("/"):
            rel = "/" + rel
        return f"/api/fmc_config/v1/domain/{self._domain_uuid}{rel}"

    def platform_path(self, rel: str) -> str:
        if not rel.startswith("/"):
            rel = "/" + rel
        return f"/api/fmc_platform/v1{rel}"

    # ------------------------------------------------------------------
    # Requests
    # ------------------------------------------------------------------
    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        content: bytes | str | None = None,
        headers: dict[str, str] | None = None,
        raw_response: bool = False,
    ) -> Any:
        """Issue an authenticated request against the FMC API.

        `path` is a full API path (e.g. '/api/fmc_config/v1/domain/.../devices/...'
        or '/api/fmc_platform/v1/info/serverversion'). Use config_path()/
        platform_path() to build domain-scoped and platform paths.
        """
        await self._ensure_token()
        if not path.startswith("/"):
            path = "/" + path
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        for attempt in (1, 2):
            req_headers = {"X-auth-access-token": self._token or ""}
            if headers:
                req_headers.update(headers)
            resp = await self._http.request(
                method,
                path,
                params=params or None,
                json=json_body,
                content=content,
                headers=req_headers,
            )
            if resp.status_code == 401 and attempt == 1:
                async with self._auth_lock:
                    self._token = None
                    await self._authenticate()
                continue
            break

        if resp.status_code >= 400:
            detail = resp.text[:2000]
            try:
                err = resp.json()
                if isinstance(err, dict):
                    e = err.get("error") or err
                    msgs = e.get("messages") if isinstance(e, dict) else None
                    if isinstance(msgs, list) and msgs:
                        detail = "; ".join(str(m.get("description", m)) for m in msgs)
                    else:
                        detail = e.get("description") or e.get("detail") or detail
                    if not isinstance(detail, str):
                        detail = json.dumps(detail)[:2000]
            except Exception:
                pass
            raise FMCAPIError(resp.status_code, method.upper(), path, detail)

        if raw_response:
            return resp
        if resp.status_code == 204 or not resp.content:
            return None
        ctype = resp.headers.get("content-type", "")
        if "application/json" in ctype:
            return resp.json()
        return resp.text

    async def get(self, path: str, **kw: Any) -> Any:
        return await self.request("GET", path, **kw)

    async def post(self, path: str, **kw: Any) -> Any:
        return await self.request("POST", path, **kw)

    async def put(self, path: str, **kw: Any) -> Any:
        return await self.request("PUT", path, **kw)

    async def patch(self, path: str, **kw: Any) -> Any:
        return await self.request("PATCH", path, **kw)

    async def delete(self, path: str, **kw: Any) -> Any:
        return await self.request("DELETE", path, **kw)

    # ------------------------------------------------------------------
    # Convenience helpers used by multiple tools
    # ------------------------------------------------------------------
    async def list_all(self, path: str, params: dict[str, Any] | None = None) -> list[dict]:
        """GET a paginated collection and return all items across pages."""
        params = dict(params or {})
        params.setdefault("limit", 1000)
        params.setdefault("expanded", True)
        offset = 0
        items: list[dict] = []
        while True:
            params["offset"] = offset
            page = await self.get(path, params=params)
            batch = page.get("items", []) if isinstance(page, dict) else []
            items.extend(batch)
            paging = page.get("paging", {}) if isinstance(page, dict) else {}
            count = paging.get("count", len(items))
            if offset + len(batch) >= count or not batch:
                break
            offset += len(batch)
        return items

    async def device_id_by_name(self, name: str) -> str | None:
        for d in await self.list_all(self.config_path("/devices/devicerecords")):
            if d.get("name") == name:
                return d.get("id")
        return None
