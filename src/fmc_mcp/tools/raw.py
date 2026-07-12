"""Generic escape hatch + API Explorer spec search - full coverage of the FMC API."""

from __future__ import annotations

import json
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from ..client import FMCClient
from ..spec import SpecCache
from . import dumps


def register(mcp: FastMCP, client: FMCClient, spec: SpecCache) -> None:
    @mcp.tool()
    async def fmc_api_call(
        method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
        path: str,
        config_domain: bool = True,
        query_params: dict[str, Any] | None = None,
        body: str | None = None,
    ) -> str:
        """Call any FMC REST API endpoint directly (authenticated).

        The escape hatch for anything without a dedicated tool. Use
        fmc_search_spec / fmc_get_definition first to find the endpoint + schema.

        Args:
            method: HTTP method.
            path: For config endpoints, a path RELATIVE to the domain root, e.g.
                '/devices/devicerecords' or '/policy/ftds2svpns' (config_domain
                is prefixed automatically). For platform/api-explorer endpoints,
                pass config_domain=False and a FULL path, e.g.
                '/api/fmc_platform/v1/info/serverversion'.
            config_domain: True (default) prefixes
                '/api/fmc_config/v1/domain/{uuid}'. Set False for full paths.
            query_params: Optional query params (e.g. {'expanded': True}).
            body: Optional request body as JSON text.
        """
        real = client.config_path(path) if config_domain else path
        json_body: Any = None
        content: str | None = None
        if body is not None:
            try:
                json_body = json.loads(body)
            except json.JSONDecodeError:
                content = body
        return dumps(await client.request(
            method, real, params=query_params, json_body=json_body, content=content,
        ))

    @mcp.tool()
    async def fmc_search_spec(
        query: str,
        kind: Literal["both", "paths", "definitions"] = "both",
    ) -> str:
        """Search the FMC API Explorer OpenAPI spec (fmc.json).

        Substring-matches API operations (method + path + summary) and/or schema
        definition names. The fast way to discover endpoints and models before
        hand-writing a request. Follow up with fmc_get_definition for a schema's
        exact fields/enums.

        Args:
            query: Substring to match (e.g. 'vti', 'ftds2svpn', 'devicehapair').
            kind: 'paths', 'definitions', or 'both' (default).
        """
        return dumps(await spec.search(query, kind=kind))

    @mcp.tool()
    async def fmc_get_definition(name: str) -> str:
        """Dump a schema definition from the API Explorer spec.

        Returns the model's properties (name -> type/enum/$ref/description) and
        required fields - e.g. 'FTDVTIInterface', 'FTDS2SVpnModel', 'VpnEndpoint',
        'IAutoVpnSettings'. This is how you find non-obvious fields and enum
        values (e.g. topologyType 'AUTO_VPN', ipAddressAssignmentType
        'BORROW_IP_FROM_INTERFACE').

        Args:
            name: Schema/definition name (exact, or a unique substring).
        """
        return dumps(await spec.get_definition(name))
