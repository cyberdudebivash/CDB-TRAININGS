"""Fixtures for the PY-M10 independent-lab checks (the published ones). The module under test is starter/inventory.py; LAB_PROJECT=<dir> points at another folder containing
inventory.py. LAB_TARGET=import is used by the instructors' mutation check. The application is built inside each test, never in a fixture, so that unfinished work is a failed
check and not a set-up error."""
from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parent.parent
FOLDER = Path(os.environ["LAB_PROJECT"]) if os.environ.get("LAB_PROJECT") else LAB / "starter"
T0 = 1_791_979_200.0                                         # 2026-10-14T12:00:00Z
SECRETS = {"aw": "A" * 23 + "w", "ar": "B" * 23 + "r", "gw": "C" * 23 + "g"}
KEYS = {"aw": ("acmewrite1", SECRETS["aw"], "acme", "write"), "ar": ("acmeread01", SECRETS["ar"], "acme", "read"), "gw": ("globexwrite", SECRETS["gw"], "globex", "write")}


@pytest.fixture(scope="session")
def inv():
    if os.environ.get("LAB_TARGET") == "import":
        return importlib.import_module("inventory")
    spec = importlib.util.spec_from_file_location("inventory_under_test", FOLDER / "inventory.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["inventory_under_test"] = module
    spec.loader.exec_module(module)
    return module


class Clock:
    def __init__(self) -> None:
        self.now = T0

    def __call__(self) -> float:
        return self.now


class Env:
    """The application, a client and three keys: aw (tenant acme, write), ar (acme, read), gw (globex, write)."""

    def __init__(self, inv, tmp_path, **settings) -> None:
        from fastapi.testclient import TestClient

        self.clock = Clock()
        settings.setdefault("rate_limit", 10_000)
        self.path = str(tmp_path / "inventory.db")
        self.keys = inv.KeyStore()
        for kid, secret, tenant, scope in KEYS.values():
            self.keys.add(kid, secret, tenant, scope)
        self.app = inv.create_app(inv.Settings(db_path=self.path, clock=self.clock, **settings), self.keys)
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def h(self, who: str = "aw", **extra: str) -> dict[str, str]:
        kid, secret, _, _ = KEYS[who]
        return {"X-API-Key": f"{kid}.{secret}", **extra}


@pytest.fixture
def make_env(inv, tmp_path):
    """make_env(**settings) -> Env; call it inside the test."""
    return lambda **settings: Env(inv, tmp_path, **settings)
