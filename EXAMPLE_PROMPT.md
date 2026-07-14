# Example prompts — Firepower (FMC) MCP

Copy any prompt below to an AI agent (Claude Code, Claude Desktop, …) with the
**`fmc`** MCP server connected. Describe the outcome — the agent picks the tools.
Names in `code` show which tools each prompt exercises.

**Always start with:** *"Confirm the FMC is reachable and show its version."*
→ `fmc_server_version`. The FMC config API is huge and schema-driven — reach for
`fmc_search_spec` + `fmc_get_definition` before hand-writing any body.

## One end-to-end scenario

> **"Register the FTD at 198.18.128.23 to this FMC (reg key `cisco123key`, access
> policy `Default`). Once it's up, create a loopback (10.0.0.1/32), a VTI that borrows
> that loopback's IP, an OSPF process advertising the inside network, then deploy and
> tell me when it's done."**

Exercises: `fmc_register_device` → (poll `fmc_get_device` / `fmc_device_health`) →
`fmc_create_loopback` → `fmc_create_vti` → `fmc_create_ospf` → `fmc_deploy`
(deploy-and-wait).

## Focused tasks (one area each)

**Register + deploy**
> "Register the FTD at 198.18.128.23 with reg key `cisco123key`, then deploy all pending
> config."  *(`fmc_register_device` → `fmc_deployable_devices` → `fmc_deploy`)*

**Interfaces / zones**
> "Set Gig0/0 as `outside` with 203.0.113.2/30 in the WAN zone, and show me all the
> physical interfaces."  *(`fmc_update_physical_interface` / `fmc_list_physical_interfaces`)*

**Objects**
> "Create host objects for the three branch peers and a network object for 10.0.0.0/8."
> *(`fmc_create_object`)*

**SD-WAN / VPN**
> "Build a hub-and-spoke AUTO_VPN SD-WAN topology from the NYC hub to the three branch
> FTDs."  *(`fmc_create_auto_vpn_topology` / `fmc_add_endpoint`)*

**Routing**
> "Enable BGP AS 65001 on this FTD, add the branch as a neighbor, and redistribute
> connected."  *(`fmc_enable_bgp` / `fmc_create_bgp`)*

**HA / failover**
> "Pair these two FTDs into an HA failover pair, then fail over to the standby and show
> me it took over."  *(`fmc_form_ha` → `fmc_ha_action` → `fmc_get_ha_pair`)*

**Discover an endpoint you don't have a tool for**
> "Find the FMC API path + schema for NAT policies."  *(`fmc_search_spec` /
> `fmc_get_definition` → `fmc_api_call`)*

## Tips

- **Deploy after config changes** — nothing is live on the FTD until `fmc_deploy`.
- **"Booted" ≠ "ready":** a fresh FTD reaches BOOTED fast but its registration
  services take 10–20 min; poll `fmc_device_health`.
- A brand-new FMC won't register devices until it's **licensed** — enable Evaluation
  Mode first (`fmc_register_eval_license`).
- IDs are UUIDs from the `fmc_list_*` tools; `fmc_api_call` reaches anything without a
  dedicated tool.
