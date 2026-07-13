# Firepower MCP Server

An [MCP](https://modelcontextprotocol.io) server for **Cisco Secure Firewall
Management Center (FMC)** — manage Firepower Threat Defense (FTD) devices through
the FMC REST API from any MCP client (Claude Code, etc.).

It mirrors the design of the companion [CML MCP](https://github.com/dr-stutters/cml-mcp):
a thin, fully-async FastMCP server with dedicated tools per domain plus a generic
escape hatch and — the killer feature — a **spec search** over the FMC API
Explorer OpenAPI document, so you can discover any endpoint and its exact schema
in seconds instead of guessing.

## What it can do

**51 tools** across devices, deploy, interfaces/VPN, routing, HA, policies, and
system — plus spec search and a generic escape hatch:

- **Devices** — list / get / register / delete FTDs, health roll-up
- **Deploy** — list deployable devices; deploy pending config and poll to done
- **Interfaces** — physical interfaces (ifname/IP/zone), VTIs (incl.
  borrow-IP-from-loopback), loopbacks
- **Objects** — networks, hosts, ranges, IPv4 address pools, security zones,
  route-maps
- **VPN / SD-WAN** — site-to-site & `AUTO_VPN` topologies + endpoints
- **Routing** — BGP (general + neighbors/redistribution), OSPF, EIGRP
- **HA** — form / status / SWITCH-SUSPEND-RESUME / break FTD HA pairs
- **Policies** — access control policies (read)
- **System** — domains, server version, Smart License status + eval registration
- **Spec search** — `fmc_search_spec` (paths + schema names) and
  `fmc_get_definition` (a model's exact fields/enums)
- **Escape hatch** — `fmc_api_call` for any endpoint (auto domain-scoping)

## Requirements

- Python ≥ 3.11 and [uv](https://docs.astral.sh/uv/)
- Reachable FMC with API access (an admin/API user)

## Install

```bash
git clone https://github.com/dr-stutters/firepower-mcp
cd firepower-mcp && uv sync
```

## Configure

Copy `.env.example` to `.env` (gitignored) and point it at your FMC:

`FMC_URL`, `FMC_USERNAME`, `FMC_PASSWORD`, `FMC_DOMAIN` (default
`Global`), `FMC_VERIFY_SSL` (default `false`), `FMC_TIMEOUT` (default `60`).

## How to use this

Run standalone (stdio): `uv run fmc-mcp` — the included [.mcp.json](.mcp.json)
registers it as `fmc` in Claude Code when started inside this repo, or add it to
any MCP client:

```json
{ "mcpServers": { "fmc": { "command": "uv", "args": ["run", "fmc-mcp"] } } }
```

It's built to be driven by an AI agent. In the
[cml-mcp](https://github.com/dr-stutters/cml-mcp) lab suite it's wired in as the
`fmc` server, owned by the **firewall-engineer** agent (tool prefix `mcp__fmc__*`)
— FMC/FTD work in lab requests fans out to it automatically. Standalone, just
describe what you want:

> "Register the FTD at 198.18.128.23 with reg key cisco123key and deploy."

> "Build a hub-and-spoke SD-WAN auto-VPN topology from NYC to the three branches."

> "Pair these two FTDs into HA and show me the failover state."

Start with `fmc_server_version` to confirm reachability, and reach for
`fmc_search_spec` + `fmc_get_definition` before hand-writing any request body —
the FMC API is schema-driven and the spec search knows every endpoint.

## How it works

FMC auth differs from most REST APIs: `POST /api/fmc_platform/v1/auth/generatetoken`
(HTTP Basic) returns the access token, refresh token, and default domain UUID in
**response headers**. The client caches the token (re-authenticating on 401) and
scopes config calls under `/api/fmc_config/v1/domain/{uuid}/…`. Ids are UUIDs
returned by the `list` tools; after config changes, `fmc_deploy` the devices.

The FMC config API is enormous and schema-driven — reach for `fmc_search_spec` +
`fmc_get_definition` before hand-writing any complex body.

## Test

```bash
uv run pytest                         # unit tests - no FMC needed (run in CI)
uv run python tests/smoke_test.py     # read-only sanity check against your FMC
```

Unit tests mock the HTTP layer (header-based token auth, domain scoping, error
extraction); `ruff` + `pytest` run in CI on every push. The live validation
lives in the CML lab suite: FMC-managed registration, HA pairing, and the full
Secure Firewall SD-WAN CVD (auto-VPN overlay, ECMP, dual hub) were all driven
end-to-end through these tools.

## Roadmap

- **FDM (on-box / local-mode) API** — this server covers the FMC (management
  center) API; the per-device FDM REST API is a possible future addition.

## Security notes

`.env` is gitignored — never commit credentials. Use a least-privilege FMC API
user. TLS verification is off by default for lab self-signed certs; set
`FMC_VERIFY_SSL=true` against a trusted CA.
