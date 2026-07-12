"""FTD HA pair tools: list/get status, form, action, break."""

from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP

from ..client import FMCClient
from ..spec import SpecCache
from . import dumps

_HA = "/devicehapairs/ftddevicehapairs"


def register(mcp: FastMCP, client: FMCClient, spec: SpecCache) -> None:
    @mcp.tool()
    async def fmc_list_ha_pairs() -> str:
        """List FTD HA pairs with primary/secondary current status."""
        items = await client.list_all(client.config_path(_HA))
        out = []
        for p in items:
            md = p.get("metadata", {})
            out.append({"name": p.get("name"), "id": p.get("id"),
                        "primary": md.get("primaryStatus", {}).get("currentStatus"),
                        "secondary": md.get("secondaryStatus", {}).get("currentStatus")})
        return dumps(out)

    @mcp.tool()
    async def fmc_get_ha_pair(ha_id: str) -> str:
        """Get full detail for one HA pair by id."""
        return dumps(await client.get(client.config_path(f"{_HA}/{ha_id}")))

    @mcp.tool()
    async def fmc_form_ha(
        name: str,
        primary_device_id: str,
        secondary_device_id: str,
        failover_interface_id: str,
        failover_interface_name: str,
        active_ip: str = "192.168.254.1",
        standby_ip: str = "192.168.254.2",
        subnet_mask: str = "255.255.255.0",
        shared_key: str = "cisco123",
    ) -> str:
        """Form an active/standby FTD HA pair over a single failover link.

        Both devices must be registered, deployed/clean, and share a dedicated
        failover interface (unconfigured, connected between them and STARTED). If
        the secondary hangs at 'Unknown', deploy the pair (fmc_deploy) - a pending
        config push blocks the sync.

        Args:
            failover_interface_id/name: the dedicated failover PhysicalInterface
                on the PRIMARY (e.g. Ethernet0/3). LAN + stateful share it
                (useSameLinkForFailovers).
        """
        fo = {"useIPv6Address": "false", "subnetMask": subnet_mask,
              "interfaceObject": {"id": failover_interface_id,
                                  "type": "PhysicalInterface",
                                  "name": failover_interface_name},
              "standbyIP": standby_ip, "logicalName": "FAILOVER", "activeIP": active_ip}
        body = {"type": "DeviceHAPair", "name": name,
                "primary": {"id": primary_device_id},
                "secondary": {"id": secondary_device_id},
                "ftdHABootstrap": {"isEncryptionEnabled": "false",
                                   "sharedKey": shared_key,
                                   "useSameLinkForFailovers": "true",
                                   "lanFailover": fo, "statefulFailover": fo}}
        return dumps(await client.post(client.config_path(_HA), json_body=body))

    @mcp.tool()
    async def fmc_ha_action(
        ha_id: str,
        action: Literal["SWITCH", "HABREAK", "FORCEBREAK", "SUSPEND", "RESUME"],
    ) -> str:
        """Act on an HA pair: SWITCH (swap active), SUSPEND/RESUME, HABREAK/FORCEBREAK.

        The id must be in the body (FMC requires it) - handled here.
        """
        body = {"id": ha_id, "type": "DeviceHAPair", "action": action}
        return dumps(await client.put(client.config_path(f"{_HA}/{ha_id}"), json_body=body))

    @mcp.tool()
    async def fmc_break_ha(ha_id: str) -> str:
        """Dissolve an HA pair (DELETE). Note: fails if a VPN topology still
        references the pair - remove those endpoints first."""
        return dumps(await client.delete(client.config_path(f"{_HA}/{ha_id}")))
