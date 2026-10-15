"""Fixtures for the PY-M05 guided-lab checks: a loopback catalogue API with scripted faults. LAB_TARGET=starter (default) or solution (the public reference)."""
from __future__ import annotations

import importlib.util
import os
import sys
from collections import deque
from pathlib import Path

import httpx
import pytest

LAB = Path(__file__).resolve().parents[1]
TARGET = LAB / os.environ.get("LAB_TARGET", "starter")
sys.path.insert(0, str(LAB.parents[2] / "labs" / "_tools"))
from scripted_server import Reply, Request, ScriptedServer  # noqa: E402


@pytest.fixture(scope="session")
def syncer():
    spec = importlib.util.spec_from_file_location("syncer_under_test", TARGET / "syncer.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["syncer_under_test"] = module
    spec.loader.exec_module(module)
    return module


class Catalogue:
    """GET /products?limit=N[&cursor=C] -> {"items": [...], "next_cursor": "cur-K" | null}. `faults` are answers given to the next requests instead of the real one."""

    def __init__(self, count: int = 7) -> None:
        self.products = [{"id": i, "name": f"item-{i}", "price_cents": 100 * i, "currency": "USD", "tags": ["t"] if i % 2 else []} for i in range(1, count + 1)]
        self.faults: deque[Reply | None] = deque()          # None means: answer normally
        self.server: ScriptedServer | None = None

    def handle(self, request: Request) -> Reply:
        if request.path != "/products":
            return Reply(404, {"error": "not found"})
        if self.faults:
            fault = self.faults.popleft()
            if fault is not None:
                return fault
        limit = int(request.param("limit", "50"))
        cursor = request.param("cursor")
        offset = int(cursor.removeprefix("cur-")) if cursor else 0
        items = self.products[offset:offset + limit]
        following = offset + limit
        return Reply(body={"items": items, "next_cursor": f"cur-{following}" if following < len(self.products) else None})

    @property
    def calls(self) -> list[Request]:
        return self.server.requests

    def client(self, timeout: float = 2.0) -> httpx.Client:
        client = httpx.Client(base_url=self.server.url, timeout=timeout, follow_redirects=False, trust_env=False)
        self._clients.append(client)
        return client


@pytest.fixture
def api():
    catalogue = Catalogue()
    catalogue._clients = []
    with ScriptedServer(catalogue.handle) as server:
        catalogue.server = server
        yield catalogue
    for client in catalogue._clients:
        client.close()


@pytest.fixture
def sleeps():
    """A stand-in for time.sleep that records what was asked instead of waiting."""
    class Recorder(list):
        def __call__(self, seconds: float) -> None:
            self.append(seconds)
    return Recorder()


@pytest.fixture
def reply():
    return Reply
