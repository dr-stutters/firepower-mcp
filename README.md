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

## Setup

```bash
cp .env.example .env       # set FMC_URL / FMC_USERNAME / FMC_PASSWORD
uv run fmc-mcp             # starts the stdio MCP server
uv run python tests/smoke_test.py   # read-only sanity check against your FMC
```

`.env` keys: `FMC_URL`, `FMC_USERNAME`, `FMC_PASSWORD`, `FMC_DOMAIN` (default
`Global`), `FMC_VERIFY_SSL` (default `false`), `FMC_TIMEOUT` (default `60`).

## Connecting an MCP client

The included [.mcp.json](.mcp.json) registers the server as `fmc`. In Claude Code,
start it inside this repo, or add to your client config:

```json
{ "mcpServers": { "fmc": { "command": "uv", "args": ["run", "fmc-mcp"] } } }
```

## How it works

FMC auth differs from most REST APIs: `POST /api/fmc_platform/v1/auth/generatetoken`
(HTTP Basic) returns the access token, refresh token, and default domain UUID in
**response headers**. The client caches the token (re-authenticating on 401) and
scopes config calls under `/api/fmc_config/v1/domain/{uuid}/…`. Ids are UUIDs
returned by the `list` tools; after config changes, `fmc_deploy` the devices.

The FMC config API is enormous and schema-driven — reach for `fmc_search_spec` +
`fmc_get_definition` before hand-writing any complex body.

## Roadmap

- **FDM (on-box / local-mode) API** — this server covers the FMC (management
  center) API; the per-device FDM REST API is a possible future addition.

## Security notes

`.env` is gitignored — never commit credentials. Use a least-privilege FMC API
user. TLS verification is off by default for lab self-signed certs; set
`FMC_VERIFY_SSL=true` against a trusted CA.
