"""Object tools: networks, hosts, ranges, IPv4 address pools, security zones, route-maps."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from ..client import FMCClient
from ..spec import SpecCache
from . import dumps

# Common object collection names under /object/.
_OBJECT_TYPES = (
    "networks", "hosts", "ranges", "networkgroups", "ipv4addresspools",
    "securityzones", "routemaps", "standardcommunitylists", "interfacegroups",
)


def register(mcp: FastMCP, client: FMCClient, spec: SpecCache) -> None:
    @mcp.tool()
    async def fmc_list_objects(object_type: str) -> str:
        """List reusable objects of a given type under /object/{type}.

        Common types: networks, hosts, ranges, networkgroups, ipv4addresspools,
        securityzones, routemaps, standardcommunitylists. For anything else use
        fmc_search_spec('object') to find the collection name.
        """
        return dumps(await client.list_all(client.config_path(f"/object/{object_type}")))

    @mcp.tool()
    async def fmc_create_object(object_type: str, body: str) -> str:
        """Create an object under /object/{type} from a JSON body.

        Use fmc_get_definition to find the schema. Examples:
          networks  -> {"type":"Network","name":"NET-A","value":"10.0.0.0/24"}
          hosts     -> {"type":"Host","name":"H1","value":"10.0.0.1"}
          ranges    -> {"type":"Range","name":"R1","value":"10.0.0.10-10.0.0.20"}
          ipv4addresspools -> {"type":"IPv4AddressPool","name":"P1",
                               "ipAddressRange":"10.0.0.100-10.0.0.200","mask":"255.255.255.0"}
        """
        return dumps(await client.post(
            client.config_path(f"/object/{object_type}"), json_body=json.loads(body)))

    @mcp.tool()
    async def fmc_delete_object(object_type: str, object_id: str) -> str:
        """Delete an object by type + id."""
        return dumps(await client.delete(
            client.config_path(f"/object/{object_type}/{object_id}")))

    @mcp.tool()
    async def fmc_list_security_zones() -> str:
        """List security zones (name + id) - shorthand for fmc_list_objects('securityzones')."""
        items = await client.list_all(client.config_path("/object/securityzones"))
        return dumps([{"name": z.get("name"), "id": z.get("id")} for z in items])
