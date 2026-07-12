"""Routing tools: BGP, OSPF, EIGRP per device.

The routing bodies are large and schema-driven; these tools give dedicated
get/list/delete plus create-from-JSON-body (use fmc_get_definition for schemas).
A companion `/routing/bgp` config MERGES into an auto-VPN-managed BGP process -
handy to add redistribution or an eBGP LAN neighbor to an SD-WAN overlay.
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from ..client import FMCClient
from ..spec import SpecCache
from . import dumps


def register(mcp: FastMCP, client: FMCClient, spec: SpecCache) -> None:
    def rt(device_id: str, rel: str) -> str:
        return client.config_path(f"/devices/devicerecords/{device_id}/routing{rel}")

    # ---- BGP ----
    @mcp.tool()
    async def fmc_get_bgp(device_id: str) -> str:
        """Get a device's BGP general settings + address-family config."""
        gs = await client.get(rt(device_id, "/bgpgeneralsettings"))
        bg = await client.get(rt(device_id, "/bgp"))
        return dumps({"bgpgeneralsettings": gs, "bgp": bg})

    @mcp.tool()
    async def fmc_enable_bgp(device_id: str, as_number: str) -> str:
        """Enable BGP (create bgpgeneralsettings with an AS). Merges with any auto-VPN BGP."""
        return dumps(await client.post(rt(device_id, "/bgpgeneralsettings"),
                     json_body={"asNumber": as_number, "type": "bgpgeneralsettings",
                                "routerId": "AUTOMATIC"}))

    @mcp.tool()
    async def fmc_create_bgp(device_id: str, body: str) -> str:
        """Create a /routing/bgp config from JSON (neighbors, redistributeProtocols).

        Use fmc_get_definition('BGPIPvAddressFamilyModel') / ('IBGPAddressFamilyModel').
        PUT gotcha: strip the deprecated addressFamilyIPv4.maximumPaths field.
        """
        return dumps(await client.post(rt(device_id, "/bgp"), json_body=json.loads(body)))

    @mcp.tool()
    async def fmc_delete_bgp(device_id: str, bgp_id: str) -> str:
        """Delete a /routing/bgp object by id."""
        return dumps(await client.delete(rt(device_id, f"/bgp/{bgp_id}")))

    # ---- OSPF ----
    @mcp.tool()
    async def fmc_get_ospf(device_id: str) -> str:
        """Get a device's OSPFv2 processes."""
        return dumps(await client.list_all(rt(device_id, "/ospfv2routes")))

    @mcp.tool()
    async def fmc_create_ospf(device_id: str, body: str) -> str:
        """Create an OSPFv2 process from JSON. Use fmc_get_definition('OspfRoute')."""
        return dumps(await client.post(rt(device_id, "/ospfv2routes"), json_body=json.loads(body)))

    @mcp.tool()
    async def fmc_delete_ospf(device_id: str, ospf_id: str) -> str:
        """Delete an OSPFv2 process by id."""
        return dumps(await client.delete(rt(device_id, f"/ospfv2routes/{ospf_id}")))

    # ---- EIGRP ----
    @mcp.tool()
    async def fmc_get_eigrp(device_id: str) -> str:
        """Get a device's EIGRP processes."""
        return dumps(await client.list_all(rt(device_id, "/eigrproutes")))

    @mcp.tool()
    async def fmc_create_eigrp(device_id: str, body: str) -> str:
        """Create an EIGRP process from JSON. Use fmc_get_definition('EigrpPolicyModel')."""
        return dumps(await client.post(rt(device_id, "/eigrproutes"), json_body=json.loads(body)))

    @mcp.tool()
    async def fmc_delete_eigrp(device_id: str, eigrp_id: str) -> str:
        """Delete an EIGRP process by id."""
        return dumps(await client.delete(rt(device_id, f"/eigrproutes/{eigrp_id}")))
