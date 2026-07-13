"""FMC-free unit tests for the client + config.

No live FMC needed - httpx.MockTransport supplies canned responses, so these run
anywhere (CI included). Run: `uv run pytest`.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from fmc_mcp.client import FMCAPIError, FMCClient
from fmc_mcp.config import Settings, load_settings


def run(coro):
    return asyncio.run(coro)


def _settings(domain: str = "Global") -> Settings:
    return Settings(base_url="https://fmc.example.com", username="a", password="b",
                    domain=domain, verify_ssl=False, timeout=5)


def _client(handler, domain: str = "Global") -> FMCClient:
    c = FMCClient(_settings(domain))
    c._http = httpx.AsyncClient(base_url=c.settings.base_url, transport=httpx.MockTransport(handler))
    return c


def _token_resp():
    return httpx.Response(204, headers={"X-auth-access-token": "TOK", "DOMAIN_UUID": "DUUID"})


# --------------------------------------------------------------------------
# config
# --------------------------------------------------------------------------
def test_load_settings_adds_scheme_and_defaults_domain(monkeypatch):
    monkeypatch.setattr("fmc_mcp.config.load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("FMC_URL", "fmc.example.com")
    monkeypatch.setenv("FMC_USERNAME", "a")
    monkeypatch.setenv("FMC_PASSWORD", "b")
    monkeypatch.delenv("FMC_DOMAIN", raising=False)
    s = load_settings()
    assert s.base_url == "https://fmc.example.com" and s.domain == "Global"


def test_load_settings_missing_url_raises(monkeypatch):
    monkeypatch.setattr("fmc_mcp.config.load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("FMC_URL", raising=False)
    monkeypatch.delenv("FMC_HOST", raising=False)
    with pytest.raises(RuntimeError):
        load_settings()


# --------------------------------------------------------------------------
# token auth: token + domain come from RESPONSE HEADERS, then X-auth-access-token
# --------------------------------------------------------------------------
def test_authenticate_reads_token_and_domain_from_headers():
    def handler(req):
        if req.url.path.endswith("/auth/generatetoken"):
            return _token_resp()
        assert req.headers.get("X-auth-access-token") == "TOK"
        return httpx.Response(200, json={"ok": True})

    c = _client(handler)
    assert run(c.request("GET", "/api/fmc_platform/v1/info/serverversion")) == {"ok": True}
    assert c.domain_uuid == "DUUID"


# --------------------------------------------------------------------------
# path helpers
# --------------------------------------------------------------------------
def test_config_and_platform_path():
    c = _client(lambda _r: _token_resp())
    c._domain_uuid = "abc"
    assert c.config_path("/devices/devicerecords") == "/api/fmc_config/v1/domain/abc/devices/devicerecords"
    assert c.platform_path("info/serverversion") == "/api/fmc_platform/v1/info/serverversion"


# --------------------------------------------------------------------------
# 401 -> clear token, re-auth, retry once
# --------------------------------------------------------------------------
def test_401_triggers_reauth_then_retries():
    state = {"n": 0}

    def handler(req):
        if req.url.path.endswith("/auth/generatetoken"):
            return _token_resp()
        state["n"] += 1
        if state["n"] == 1:
            return httpx.Response(401, json={})
        return httpx.Response(200, json={"ok": True})

    assert run(_client(handler).request("GET", "/x")) == {"ok": True} and state["n"] == 2


# --------------------------------------------------------------------------
# error extraction: error.messages[].description
# --------------------------------------------------------------------------
def test_error_extraction_from_messages():
    def handler(req):
        if req.url.path.endswith("/auth/generatetoken"):
            return _token_resp()
        return httpx.Response(400, json={"error": {"messages": [{"description": "Invalid object name"}]}})

    with pytest.raises(FMCAPIError) as ei:
        run(_client(handler).request("POST", "/x", json_body={}))
    assert ei.value.status_code == 400 and "Invalid object name" in str(ei.value)
