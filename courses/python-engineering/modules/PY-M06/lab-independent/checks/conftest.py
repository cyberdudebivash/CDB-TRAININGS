"""Fixtures for the PY-M06 independent-lab checks (the published ones). The module under test is starter/wordjob.py; LAB_PROJECT=<dir> points at another folder containing wordjob.py."""
from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
from pathlib import Path
from urllib.parse import unquote

import httpx
import pytest

LAB = Path(__file__).resolve().parents[1]
FOLDER = Path(os.environ["LAB_PROJECT"]) if os.environ.get("LAB_PROJECT") else LAB / "starter"
sys.path.insert(0, str(LAB.parents[2] / "labs" / "_tools"))
from scripted_server import Reply, ScriptedServer  # noqa: E402


@pytest.fixture(scope="session")
def wordjob():
    spec = importlib.util.spec_from_file_location("wordjob_under_test", FOLDER / "wordjob.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["wordjob_under_test"] = module
    spec.loader.exec_module(module)
    return module


def doc_text(i: int) -> str:
    return " ".join(f"word{i}x{j}" for j in range((i % 7) + 3))      # (i % 7) + 3 words


class Docs:
    """GET /docs/<id>: the text of document <id> after `latency` seconds. `faults` maps an id to the Reply to give instead."""

    def __init__(self, count: int = 24, latency: float = 0.03) -> None:
        self.docs = {str(i): doc_text(i) for i in range(count)}
        self.faults: dict[str, Reply] = {}
        self.latency = latency
        self.server: ScriptedServer | None = None

    def handle(self, request) -> Reply:
        if not request.path.startswith("/docs/"):
            return Reply(404, "not found")
        name = unquote(request.path.removeprefix("/docs/"))
        if name in self.faults:
            return self.faults[name]
        if name in self.docs:
            return Reply(200, self.docs[name], content_type="text/plain; charset=utf-8", delay=self.latency)
        return Reply(404, "no such document")

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.server.url, timeout=10.0, trust_env=False, limits=httpx.Limits(max_connections=100))

    def sync_client(self) -> httpx.Client:
        return httpx.Client(base_url=self.server.url, timeout=10.0, trust_env=False)


@pytest.fixture
def docs():
    current = Docs()
    with ScriptedServer(current.handle) as server:
        current.server = server
        yield current


@pytest.fixture
def run():
    """run(main): run a coroutine function in a fresh event loop; a function that never finishes fails after 30 seconds."""
    def runner(main, timeout: float = 30.0):
        async def guarded():
            async with asyncio.timeout(timeout):
                return await main()

        return asyncio.run(guarded())

    return runner


@pytest.fixture
def reply():
    return Reply
