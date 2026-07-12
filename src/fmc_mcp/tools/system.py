"""System / platform tools: domains, version, licensing."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..client import FMCClient
from ..spec import SpecCache
from . import dumps


def register(mcp: FastMCP, client: FMCClient, spec: SpecCache) -> None:
    @mcp.tool()
    async def fmc_domains() -> str:
        """List FMC domains (name + uuid), and show which domain this server targets."""
        data = await client.get(client.platform_path("/info/domain"))
        return dumps({"active_domain_uuid": client.domain_uuid, "domains": data})

    @mcp.tool()
    async def fmc_server_version() -> str:
        """Get the FMC server version / build / model info."""
        return dumps(await client.get(client.platform_path("/info/serverversion")))

    @mcp.tool()
    async def fmc_license_status() -> str:
        """Get Smart License registration + entitlement status.

        Key fields: regStatus (REGISTERED/EVALUATION), authStatus, virtualAccount,
        and exportControl (True unlocks export-controlled features like the SD-WAN
        auto-VPN wizard).
        """
        return dumps(await client.get(client.platform_path("/license/smartlicenses")))

    @mcp.tool()
    async def fmc_register_eval_license() -> str:
        """Put a fresh FMC into Smart License EVALUATION mode.

        A brand-new FMCv must be licensed (even in eval) before it will register
        managed devices. POSTs registrationType=EVALUATION.
        """
        return dumps(await client.post(
            client.platform_path("/license/smartlicenses"),
            json_body={"registrationType": "EVALUATION"},
        ))
