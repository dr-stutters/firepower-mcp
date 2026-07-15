"""Configuration for the FMC MCP server, loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    base_url: str
    username: str
    password: str
    domain: str
    verify_ssl: bool
    timeout: float


def load_settings() -> Settings:
    """Build settings from FMC_* environment variables.

    A local .env is honored - both the one next to this project and one in the
    current working directory (so the server works standalone and when launched
    from a parent project like cml-mcp via `uv run --directory`).
    """
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    load_dotenv()  # also honor .env in the current working directory
    # shared secrets base for the whole MCP suite (../.env, one level above the
    # repos) - lowest precedence: process env > this repo's .env > shared. Skipped
    # silently if absent, so standalone clones are unaffected.
    load_dotenv(Path(__file__).resolve().parents[3] / ".env")

    host = os.environ.get("FMC_URL") or os.environ.get("FMC_HOST", "")
    if not host:
        raise RuntimeError(
            "FMC_URL is not set. Set FMC_URL (e.g. https://192.0.2.11), "
            "FMC_USERNAME and FMC_PASSWORD in the environment or a .env file."
        )
    if not host.startswith(("http://", "https://")):
        host = f"https://{host}"
    host = host.rstrip("/")

    username = os.environ.get("FMC_USERNAME", "")
    password = os.environ.get("FMC_PASSWORD", "")
    if not username or not password:
        raise RuntimeError("FMC_USERNAME and FMC_PASSWORD must be set.")

    domain = os.environ.get("FMC_DOMAIN", "Global").strip() or "Global"
    verify = os.environ.get("FMC_VERIFY_SSL", "false").strip().lower() in ("1", "true", "yes")
    timeout = float(os.environ.get("FMC_TIMEOUT", "60"))

    return Settings(
        base_url=host,
        username=username,
        password=password,
        domain=domain,
        verify_ssl=verify,
        timeout=timeout,
    )
