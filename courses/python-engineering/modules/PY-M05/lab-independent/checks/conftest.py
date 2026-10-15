"""Fixtures for the PY-M05 independent-lab checks (the published ones). The module under test is starter/feedsync.py; LAB_PROJECT=<dir> points at another folder containing feedsync.py."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import httpx
import pytest

LAB = Path(__file__).resolve().parents[1]
FOLDER = Path(os.environ["LAB_PROJECT"]) if os.environ.get("LAB_PROJECT") else LAB / "starter"
sys.path.insert(0, str(LAB.parents[2] / "labs" / "_tools"))
from scripted_server import Reply, ScriptedServer  # noqa: E402


@pytest.fixture(scope="session")
def feedsync():
    spec = importlib.util.spec_from_file_location("feedsync_under_test", FOLDER / "feedsync.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["feedsync_under_test"] = module
    spec.loader.exec_module(module)
    return module


def item(sku: str, price: str = "10.00", *, updated: str = "2026-10-01T08:00:00Z", **extra) -> dict:
    return {"sku": sku, "price": price, "currency": "EUR", "updated_at": updated, **extra}


class Feed:
    """A vendor feed split into pages of `per_page` items. `pages` is a list of item lists; `next` links are absolute, as the specification allows."""

    def __init__(self, pages: list[list]) -> None:
        self.pages = pages
        self.faults: list[Reply | None] = []        # answers for the next requests; None means answer normally
        self.server: ScriptedServer | None = None
        self.clients: list[httpx.Client] = []

    def handle(self, request) -> Reply:
        if request.path != "/v2/prices":
            return Reply(404, {"error": "not found"})
        if self.faults:
            fault = self.faults.pop(0)
            if fault is not None:
                return fault
        number = int(request.param("page_token", "0"))
        following = f"{self.server.url}/v2/prices?page_token={number + 1}" if number + 1 < len(self.pages) else None
        return Reply(body={"data": self.pages[number], "next": following})

    def client(self, timeout: float = 2.0) -> httpx.Client:
        client = httpx.Client(base_url=self.server.url, timeout=timeout, follow_redirects=False, trust_env=False)
        self.clients.append(client)
        return client


@pytest.fixture
def feed():
    pages = [[item("AAA-1", "1.00"), item("AAA-2", "2.00")], [item("BBB-1", "3.00", discount_pct=10), item("BBB-2", "4.00")], [item("CCC-1", "5.00")]]
    current = Feed(pages)
    with ScriptedServer(current.handle) as server:
        current.server = server
        yield current
    for client in current.clients:
        client.close()


class Clock:
    """A fake clock: time passes only when the code under test asks to sleep."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def reply():
    return Reply
