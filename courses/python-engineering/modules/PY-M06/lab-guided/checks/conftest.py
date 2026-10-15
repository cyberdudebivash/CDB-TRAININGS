"""Fixtures for the PY-M06 guided-lab checks. LAB_TARGET=starter (default, your working copy) or solution (the public reference)."""
from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[1]
TARGET = LAB / os.environ.get("LAB_TARGET", "starter")


@pytest.fixture(scope="session")
def jr():
    if os.environ.get("LAB_TARGET") == "import":              # instructors' mutation check: the module under test comes from the import path
        return importlib.import_module("jobrunner")
    spec = importlib.util.spec_from_file_location("jobrunner_under_test", TARGET / "jobrunner.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["jobrunner_under_test"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def run():
    """Run a coroutine function to completion in a fresh event loop: run(main). A function that never finishes fails the test after 10 seconds instead of hanging it."""
    def runner(main, timeout: float = 10.0):
        async def guarded():
            async with asyncio.timeout(timeout):
                return await main()

        return asyncio.run(guarded())

    return runner
