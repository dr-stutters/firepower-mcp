"""Site-to-site VPN / SD-WAN tools: ftds2svpns topologies + endpoints."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from ..client import FMCClient
from ..spec import SpecCache
from . import dumps


def register(mcp: FastMCP, client: FMCClient, spec: SpecCache) -> None:
    @mcp.tool()
    async def fmc_list_s2s_topologies() -> str:
        """List site-to-site VPN / SD-WAN topologies (name, id, type)."""
        items = await client.list_all(client.config_path("/policy/ftds2svpns"))
        return dumps([{"name": t.get("name"), "id": t.get("id"),
                       "topologyType": t.get("topologyType")} for t in items])

    @mcp.tool()
    async def fmc_get_s2s_topology(topology_id: str) -> str:
        """Get a topology (incl. autoVpnSettings) by id."""
        return dumps(await client.get(client.config_path(f"/policy/ftds2svpns/{topology_id}")))

    @mcp.tool()
    async def fmc_create_auto_vpn_topology(
        name: str,
        spoke_svti_zone_id: str,
        as_number: int = 65000,
        community: int = 1000,
        enable_multipath: bool = False,
    ) -> str:
        """Create an SD-WAN AUTO_VPN hub-and-spoke topology with auto-BGP.

        topologyType MUST be AUTO_VPN for autoVpnSettings to persist (under
        HUB_AND_SPOKE the FMC silently drops it). Requires export-controlled
        Smart License features (see fmc_license_status). Add endpoints with
        fmc_add_endpoint (hub interface = a DVTI + an IPv4AddressPool; spoke
        interface = the physical WAN, FMC auto-builds the SVTI).

        Args:
            spoke_svti_zone_id: security zone FMC puts auto-created spoke SVTIs in.
            as_number: overlay iBGP AS (default 65000).
            community: BGP community tag for the overlay (default 1000).
            enable_multipath: True for ECMP across parallel overlays.
        """
        body = {
            "name": name, "topologyType": "AUTO_VPN", "routeBased": True,
            "ikeV2Enabled": True, "ikeV1Enabled": False,
            "autoVpnSettings": {
                "routeSettings": {
                    "enableBgp": True, "autonomousSystemNumber": as_number,
                    "communityAttribute": community,
                    "communityTagToAdvertiseLearntRoutes": community,
                    "enableMultiPath": enable_multipath,
                    "distributeConnectedNetwork": {
                        "enableDistribution": True,
                        "interfaceSelection": "INSIDE_INTERFACE"},
                },
                "spokeSvtiSecurityZone": {"id": spoke_svti_zone_id,
                                          "type": "SecurityZone"},
            },
        }
        return dumps(await client.post(
            client.config_path("/policy/ftds2svpns"), json_body=body))

    @mcp.tool()
    async def fmc_create_s2s_topology(body: str) -> str:
        """Create any site-to-site VPN topology from a raw JSON body (advanced).

        Use fmc_get_definition('FTDS2SVpnModel') for the schema.
        """
        return dumps(await client.post(
            client.config_path("/policy/ftds2svpns"), json_body=json.loads(body)))

    @mcp.tool()
    async def fmc_delete_s2s_topology(topology_id: str) -> str:
        """Delete a site-to-site VPN topology by id."""
        return dumps(await client.delete(client.config_path(f"/policy/ftds2svpns/{topology_id}")))

    @mcp.tool()
    async def fmc_list_endpoints(topology_id: str) -> str:
        """List a topology's endpoints (name, peerType, device, interface)."""
        items = await client.list_all(
            client.config_path(f"/policy/ftds2svpns/{topology_id}/endpoints"))
        out = []
        for e in items:
            out.append({"name": e.get("name"), "id": e.get("id"),
                        "peerType": e.get("peerType"),
                        "isPrimaryHub": e.get("isPrimaryHub"),
                        "device": (e.get("device") or {}).get("name"),
                        "interface": (e.get("interface") or {}).get("name")})
        return dumps(out)

    @mcp.tool()
    async def fmc_add_endpoint(topology_id: str, body: str) -> str:
        """Add an endpoint to a topology from a JSON body.

        For AUTO_VPN: the HUB endpoint uses interface = a DVTI plus
        ipv4PoolsForSpokeVti (an IPv4AddressPool) and isPrimaryHub true; the SPOKE
        endpoint uses interface = the physical WAN (FMC auto-builds the SVTI).
        Use fmc_get_definition('VpnEndpoint') for the schema.
        """
        return dumps(await client.post(
            client.config_path(f"/policy/ftds2svpns/{topology_id}/endpoints"),
            json_body=json.loads(body)))

    @mcp.tool()
    async def fmc_delete_endpoint(topology_id: str, endpoint_id: str) -> str:
        """Delete a topology endpoint by id."""
        return dumps(await client.delete(
            client.config_path(f"/policy/ftds2svpns/{topology_id}/endpoints/{endpoint_id}")))
