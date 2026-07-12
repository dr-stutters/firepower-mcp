"""Smoke test: drive the FMC MCP tool layer against a live FMC.

Read-only. Requires a .env (FMC_URL/FMC_USERNAME/FMC_PASSWORD) pointing at a
reachable FMC. Run: `uv run python tests/smoke_test.py`
"""

from __future__ import annotations

import asyncio
import json

from fmc_mcp.server import build_server


async def call(mcp, tool, /, **args) -> str:
    result = await mcp.call_tool(tool, args)
    # FastMCP returns a list of content blocks; take the text.
    if isinstance(result, tuple):
        result = result[0]
    parts = []
    for block in result:
        parts.append(getattr(block, "text", str(block)))
    return "\n".join(parts)


async def main() -> None:
    mcp = build_server()
    tools = {t.name for t in await mcp.list_tools()}
    assert {"fmc_list_devices", "fmc_search_spec", "fmc_get_definition",
            "fmc_deploy", "fmc_form_ha"} <= tools, "core tools missing"
    print(f"[ok] server built, {len(tools)} tools registered")

    ver = await call(mcp, "fmc_server_version")
    print(f"[ok] fmc_server_version -> {ver[:80].splitlines()[0] if ver else ''}")

    devs = json.loads(await call(mcp, "fmc_list_devices"))
    print(f"[ok] fmc_list_devices -> {len(devs)} devices: {sorted(d['name'] for d in devs)}")

    ha = json.loads(await call(mcp, "fmc_list_ha_pairs"))
    print(f"[ok] fmc_list_ha_pairs -> {[(h['name'], h['primary'], h['secondary']) for h in ha]}")

    topos = json.loads(await call(mcp, "fmc_list_s2s_topologies"))
    print(f"[ok] fmc_list_s2s_topologies -> {[(t['name'], t['topologyType']) for t in topos]}")

    search = json.loads(await call(mcp, "fmc_search_spec", query="ftds2svpn", kind="definitions"))
    assert "FTDS2SVpnModel" in search.get("definitions", []), "spec search failed"
    print(f"[ok] fmc_search_spec('ftds2svpn') -> {search['definitions'][:3]}")

    d = json.loads(await call(mcp, "fmc_get_definition", name="IAutoVpnSettings"))
    assert "properties" in d, "get_definition failed"
    print(f"[ok] fmc_get_definition('IAutoVpnSettings') -> {list(d['properties'])}")

    print("\nSMOKE TEST PASSED")


if __name__ == "__main__":
    asyncio.run(main())
