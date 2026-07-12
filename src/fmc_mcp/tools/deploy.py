"""Deployment tools: list deployable devices, deploy pending config (with wait)."""

from __future__ import annotations

import asyncio
import time

from mcp.server.fastmcp import FastMCP

from ..client import FMCClient
from ..spec import SpecCache
from . import dumps


def register(mcp: FastMCP, client: FMCClient, spec: SpecCache) -> None:
    @mcp.tool()
    async def fmc_deployable_devices() -> str:
        """List devices with pending (undeployed) configuration changes."""
        items = await client.list_all(
            client.config_path("/deployment/deployabledevices"))
        out = [{"name": i.get("name") or i.get("device", {}).get("name"),
                "device_id": i.get("device", {}).get("id") or i.get("id"),
                "version": str(i.get("version"))} for i in items]
        return dumps(out)

    @mcp.tool()
    async def fmc_deploy(device_names: list[str] | None = None, wait: bool = True) -> str:
        """Deploy pending config to devices and (optionally) poll to completion.

        Args:
            device_names: Names to deploy; omit to deploy ALL deployable devices.
            wait: If True (default), poll the deploy task until it finishes
                (SUCCESS/FAILED) or ~15 min elapses.
        """
        want = {n.lower() for n in device_names} if device_names else None
        items = await client.list_all(
            client.config_path("/deployment/deployabledevices"))
        devmap = {}
        for i in items:
            nm = i.get("name") or i.get("device", {}).get("name")
            did = i.get("device", {}).get("id") or i.get("id")
            devmap[nm] = (did, str(i.get("version")))
        targets = {n: v for n, v in devmap.items() if (want is None or n.lower() in want)}
        if not targets:
            return dumps({"deployable": list(devmap), "deployed": [],
                          "note": "nothing pending for the requested devices"})
        version = max(v for _, v in targets.values())
        req = await client.post(
            client.config_path("/deployment/deploymentrequests"),
            json_body={"type": "DeploymentRequest", "version": version,
                       "forceDeploy": True, "ignoreWarning": True,
                       "deviceList": [d for d, _ in targets.values()]})
        task = (req.get("metadata", {}).get("task", {}) or {}).get("id") or req.get("id")
        result = {"deploying": list(targets), "task": task}
        if wait and task:
            t0 = time.time()
            status = "PENDING"
            while time.time() - t0 < 900:
                ts = await client.get(client.config_path(f"/job/taskstatuses/{task}"))
                status = str(ts.get("status", "?")).upper()
                if status in ("SUCCESS", "COMPLETED", "DEPLOYED", "FAILED"):
                    break
                await asyncio.sleep(20)
            result["final_status"] = status
        return dumps(result)
