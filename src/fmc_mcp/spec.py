"""Fetch, cache and search the FMC API Explorer OpenAPI spec (fmc.json).

The spec at `GET /api/api-explorer/fmc.json` is the authoritative source for
every FMC request/response schema (~9 MB). Fetching it once and searching its
`paths` and `definitions` turns hours of 422/400 guessing into seconds.
"""

from __future__ import annotations

from typing import Any

from .client import FMCClient

SPEC_PATH = "/api/api-explorer/fmc.json"


class SpecCache:
    def __init__(self, client: FMCClient):
        self._client = client
        self._spec: dict[str, Any] | None = None

    async def load(self) -> dict[str, Any]:
        if self._spec is None:
            self._spec = await self._client.get(SPEC_PATH)
        return self._spec

    @staticmethod
    def _defs(spec: dict[str, Any]) -> dict[str, Any]:
        return spec.get("definitions") or spec.get("components", {}).get("schemas") or {}

    async def search(self, query: str, kind: str = "both", limit: int = 60) -> dict[str, Any]:
        """Substring-search operations (paths) and/or schema names (definitions)."""
        spec = await self.load()
        q = query.lower()
        out: dict[str, Any] = {}
        if kind in ("both", "paths"):
            ops = []
            for path, methods in spec.get("paths", {}).items():
                for method, op in methods.items():
                    if method not in ("get", "post", "put", "patch", "delete"):
                        continue
                    summary = (op.get("summary") or op.get("description") or "").strip()
                    line = f"{method.upper():6s} {path}  {summary.splitlines()[0][:100] if summary else ''}"
                    if q in line.lower():
                        ops.append(line)
            out["paths"] = sorted(ops)[:limit]
        if kind in ("both", "definitions"):
            defs = self._defs(spec)
            out["definitions"] = sorted(n for n in defs if q in n.lower())[:limit]
        return out

    async def get_definition(self, name: str) -> dict[str, Any]:
        """Return a schema definition's properties (name -> type/enum/ref)."""
        spec = await self.load()
        defs = self._defs(spec)
        if name not in defs:
            # try a case-insensitive / substring match for convenience
            matches = [n for n in defs if name.lower() == n.lower()] or \
                      [n for n in defs if name.lower() in n.lower()]
            if not matches:
                return {"error": f"definition '{name}' not found",
                        "did_you_mean": sorted(defs)[:0]}
            name = matches[0]
        d = defs[name]
        props: dict[str, Any] = {}
        for pname, pv in (d.get("properties") or {}).items():
            ref = pv.get("$ref", "").split("/")[-1]
            if pv.get("type") == "array":
                it = pv.get("items", {})
                ref = "[" + (it.get("$ref", "").split("/")[-1] or it.get("type", "?")) + "]"
            entry: dict[str, Any] = {"type": pv.get("type") or ref or "?"}
            if ref and "$ref" in pv:
                entry["ref"] = ref
            if "enum" in pv:
                entry["enum"] = pv["enum"]
            if pv.get("description"):
                entry["description"] = pv["description"][:160]
            props[pname] = entry
        return {"name": name, "required": d.get("required"), "properties": props}
