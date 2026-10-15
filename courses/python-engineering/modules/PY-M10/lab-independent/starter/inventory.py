"""inventory - STARTER of the PY-M10 independent lab (intentionally incomplete): a multi-tenant asset inventory API.

Only the three names the tests call are here; read README.md for the specification. Everything else - how you store assets, how you check keys, how you structure the application -
is your design. Standard library, FastAPI, Starlette and pydantic only.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import FastAPI


class SettingsError(ValueError):
    """The configuration is unusable."""


@dataclass(frozen=True, slots=True)
class Settings:
    """db_path (not empty); rate_limit: authenticated requests per key per 60-second window (an int from 1 to 10000, a bool is not one); max_body: bytes (an int from 1 to 1000000);
    clock: seconds since the epoch, the only source of time. Raise SettingsError for anything unusable."""

    db_path: str
    rate_limit: int = 60
    max_body: int = 8192
    clock: Callable[[], float] = time.time

    def __post_init__(self) -> None:
        raise NotImplementedError("validate the settings")


class KeyStore:
    """API keys by identifier; only a hash of each secret is kept."""

    def add(self, key_id: str, secret: str, tenant: str, scope: str) -> None:
        """Register a key (ValueError for a bad value or a key id that is already registered; see README.md)."""
        raise NotImplementedError("register a key")

    def check(self, key_id: str, secret: str) -> tuple[str, str] | None:
        """(tenant, scope) for a valid key, else None - doing the same work, with a constant-time comparison, for an unknown key id as for a wrong secret."""
        raise NotImplementedError("check a key")


def create_app(settings: Settings, keys: KeyStore) -> FastAPI:
    """A ready application serving the API of README.md; creates its table when it is built."""
    raise NotImplementedError("build the application")
