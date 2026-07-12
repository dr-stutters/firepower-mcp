"""Interface tools: physical interfaces, VTIs, loopbacks."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import FMCClient
from ..spec import SpecCache
from . import dumps


def register(mcp: FastMCP, client: FMCClient, spec: SpecCache) -> None:
    def dev(device_id: str, rel: str) -> str:
        return client.config_path(f"/devices/devicerecords/{device_id}{rel}")

    @mcp.tool()
    async def fmc_list_physical_interfaces(device_id: str) -> str:
        """List a device's physical interfaces (name, ifname, ip, zone, mode, enabled)."""
        items = await client.list_all(dev(device_id, "/physicalinterfaces"))
        out = []
        for i in items:
            ip = (i.get("ipv4", {}) or {}).get("static", {}) if isinstance(i.get("ipv4"), dict) else {}
            out.append({"name": i.get("name"), "id": i.get("id"), "ifname": i.get("ifname"),
                        "ip": f"{ip.get('address')}/{ip.get('netmask')}" if ip.get("address") else None,
                        "zone": (i.get("securityZone") or {}).get("name"),
                        "mode": i.get("mode"), "enabled": i.get("enabled")})
        return dumps(out)

    @mcp.tool()
    async def fmc_update_physical_interface(
        device_id: str,
        interface_id: str,
        ifname: str | None = None,
        ipv4_address: str | None = None,
        prefix: str = "24",
        zone_id: str | None = None,
        zone_name: str | None = None,
        enabled: bool = True,
    ) -> str:
        """Configure a physical interface (routed mode): ifname, IPv4, zone, enable.

        Fetches the interface, applies the given fields, and PUTs it back.
        """
        cur = await client.get(dev(device_id, f"/physicalinterfaces/{interface_id}"))
        body: dict[str, Any] = {k: v for k, v in cur.items() if k not in ("links", "metadata")}
        body["mode"] = "NONE"  # routed
        body["enabled"] = enabled
        if ifname is not None:
            body["ifname"] = ifname
        if ipv4_address is not None:
            body["ipv4"] = {"static": {"address": ipv4_address, "netmask": prefix}}
        if zone_id is not None:
            body["securityZone"] = {"id": zone_id, "type": "SecurityZone",
                                    **({"name": zone_name} if zone_name else {})}
        return dumps(await client.put(
            dev(device_id, f"/physicalinterfaces/{interface_id}"), json_body=body))

    @mcp.tool()
    async def fmc_list_vtis(device_id: str) -> str:
        """List a device's virtual tunnel interfaces (VTIs)."""
        return dumps(await client.list_all(dev(device_id, "/virtualtunnelinterfaces")))

    @mcp.tool()
    async def fmc_create_vti(
        device_id: str,
        ifname: str,
        tunnel_id: int,
        tunnel_type: str,
        source_interface_id: str,
        source_interface_name: str,
        borrow_loopback_id: str,
        borrow_loopback_name: str,
        tunnel_zone_id: str,
    ) -> str:
        """Create a route-based VTI that borrows its IP from a loopback.

        Args:
            tunnel_type: 'DYNAMIC' (hub DVTI) or 'STATIC' (spoke SVTI).
            source_interface_id/name: the outside PhysicalInterface the tunnel
                sources from (e.g. Ethernet0/0).
            borrow_loopback_id/name: the LoopbackInterface whose /32 the VTI
                borrows (ipAddressAssignmentType BORROW_IP_FROM_INTERFACE).
            tunnel_zone_id: security zone for the VTI (e.g. a TUNNEL zone).
        """
        body = {
            "type": "VTIInterface", "tunnelType": tunnel_type, "ifname": ifname,
            "tunnelId": tunnel_id, "enabled": True, "ipsecMode": "ipv4",
            "tunnelSource": {"id": source_interface_id, "type": "PhysicalInterface",
                             "name": source_interface_name},
            "ipAddressAssignmentType": "BORROW_IP_FROM_INTERFACE",
            "borrowIPfrom": {"id": borrow_loopback_id, "type": "LoopbackInterface",
                             "name": borrow_loopback_name},
            "securityZone": {"id": tunnel_zone_id, "type": "SecurityZone"},
        }
        return dumps(await client.post(
            dev(device_id, "/virtualtunnelinterfaces"), json_body=body))

    @mcp.tool()
    async def fmc_delete_vti(device_id: str, vti_id: str) -> str:
        """Delete a VTI by id."""
        return dumps(await client.delete(dev(device_id, f"/virtualtunnelinterfaces/{vti_id}")))

    @mcp.tool()
    async def fmc_list_loopbacks(device_id: str) -> str:
        """List a device's loopback interfaces."""
        return dumps(await client.list_all(dev(device_id, "/loopbackinterfaces")))

    @mcp.tool()
    async def fmc_create_loopback(
        device_id: str, loopback_id: int, ifname: str, address: str, netmask: str = "32",
    ) -> str:
        """Create a loopback interface (commonly a /32 used as a VTI tunnel IP)."""
        body = {"type": "LoopbackInterface", "name": f"Loopback{loopback_id}",
                "loopbackId": loopback_id, "ifname": ifname, "enabled": True,
                "ipv4": {"static": {"address": address, "netmask": netmask}}}
        return dumps(await client.post(dev(device_id, "/loopbackinterfaces"), json_body=body))

    @mcp.tool()
    async def fmc_delete_loopback(device_id: str, loopback_id: str) -> str:
        """Delete a loopback interface by id."""
        return dumps(await client.delete(dev(device_id, f"/loopbackinterfaces/{loopback_id}")))
