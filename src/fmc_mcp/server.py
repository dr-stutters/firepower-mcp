"""FMC (Firepower Management Center) MCP server entry point."""

from __future__ import annotations

import argparse

from mcp.server.fastmcp import FastMCP

from .client import FMCClient
from .config import load_settings
from .spec import SpecCache
from .tools import register_all


def build_server() -> FastMCP:
    settings = load_settings()
    client = FMCClient(settings)
    spec = SpecCache(client)
    mcp = FastMCP(
        "fmc",
        instructions=(
            "Tools for Cisco Secure Firewall Management Center (FMC) - manage "
            "Firepower Threat Defense (FTD) devices via the FMC REST API: register/"
            "deploy devices, configure interfaces/VTIs/loopbacks, objects, "
            "site-to-site & SD-WAN (AUTO_VPN) topologies, routing (BGP/OSPF/EIGRP), "
            "and FTD HA pairs. The FMC config API is huge and schema-driven: use "
            "fmc_search_spec + fmc_get_definition to find endpoints and exact model "
            "fields/enums, and fmc_api_call for anything without a dedicated tool. "
            "Ids are UUIDs returned by the list tools. After config changes, "
            "fmc_deploy the affected devices."
        ),
    )
    register_all(mcp, client, spec)
    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="FMC MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP transport (default: stdio)",
    )
    args = parser.parse_args()
    build_server().run(transport=args.transport)


if __name__ == "__main__":
    main()
