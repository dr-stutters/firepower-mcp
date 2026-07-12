"""Access Control Policy tools (read)."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..client import FMCClient
from ..spec import SpecCache
from . import dumps


def register(mcp: FastMCP, client: FMCClient, spec: SpecCache) -> None:
    @mcp.tool()
    async def fmc_list_access_policies() -> str:
        """List Access Control Policies (name + id) - needed to register devices."""
        items = await client.list_all(client.config_path("/policy/accesspolicies"))
        return dumps([{"name": p.get("name"), "id": p.get("id")} for p in items])

    @mcp.tool()
    async def fmc_get_access_policy(policy_id: str) -> str:
        """Get an Access Control Policy by id."""
        return dumps(await client.get(client.config_path(f"/policy/accesspolicies/{policy_id}")))
