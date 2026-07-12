"""Managed device (FTD) tools: list/get/register/delete + health."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import FMCClient
from ..spec import SpecCache
from . import dumps


def register(mcp: FastMCP, client: FMCClient, spec: SpecCache) -> None:
    @mcp.tool()
    async def fmc_list_devices() -> str:
        """List all managed devices (name, id, model, health, sw version)."""
        items = await client.list_all(client.config_path("/devices/devicerecords"))
        out = [
            {"name": d.get("name"), "id": d.get("id"), "model": d.get("model"),
             "health": d.get("healthStatus"), "version": d.get("sw_version")}
            for d in items
        ]
        return dumps(out)

    @mcp.tool()
    async def fmc_get_device(device_id: str) -> str:
        """Get full details for one managed device by id."""
        return dumps(await client.get(client.config_path(f"/devices/devicerecords/{device_id}")))

    @mcp.tool()
    async def fmc_device_health() -> str:
        """Quick health roll-up: each device name -> healthStatus (green/red/...)."""
        items = await client.list_all(client.config_path("/devices/devicerecords"))
        return dumps({d.get("name"): d.get("healthStatus") for d in items})

    @mcp.tool()
    async def fmc_register_device(
        name: str,
        host_name: str,
        reg_key: str,
        access_policy_id: str,
        license_caps: list[str] | None = None,
        performance_tier: str = "FTDv50",
        nat_id: str | None = None,
    ) -> str:
        """Register an FTD device to this FMC (async - poll fmc_list_devices for green).

        The device must already be reachable at host_name with a matching day-0
        `configure manager add <fmc> <reg_key>`. FMC completes registration over
        ~10-20 min.

        Args:
            name: Device display name in FMC.
            host_name: Device management IP/host.
            reg_key: The shared registration key.
            access_policy_id: Access Control Policy id to assign (see
                fmc_list_access_policies).
            license_caps: e.g. ['ESSENTIALS','IPS','MALWARE_DEFENSE','URL'].
            performance_tier: FTDv performance tier (default FTDv50).
            nat_id: Optional NAT id when the device initiates registration.
        """
        body: dict[str, Any] = {
            "name": name, "hostName": host_name, "regKey": reg_key, "type": "Device",
            "license_caps": license_caps or ["ESSENTIALS"],
            "performanceTier": performance_tier,
            "accessPolicy": {"id": access_policy_id, "type": "AccessPolicy"},
        }
        if nat_id:
            body["natID"] = nat_id
        return dumps(await client.post(
            client.config_path("/devices/devicerecords"), json_body=body))

    @mcp.tool()
    async def fmc_delete_device(device_id: str) -> str:
        """Unregister/delete a managed device from FMC by id."""
        return dumps(await client.delete(
            client.config_path(f"/devices/devicerecords/{device_id}")))
