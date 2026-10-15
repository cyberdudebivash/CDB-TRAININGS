"""Fixtures for the PY-M09 guided-lab checks. LAB_TARGET=starter (default) or solution (the public reference); `import` is used by the instructors' mutation check.

`oracle` is checks/slow_baseline.py: the slow program the lab starts from, whose answers yours must reproduce exactly. Timings are compared as ratios or against budgets that are
an order of magnitude away from both a correct and an unscalable solution, never against the clock of one machine.
"""
from __future__ import annotations

import importlib
import importlib.util
import os
import random
import sys
import time
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parent.parent
TARGET = LAB / os.environ.get("LAB_TARGET", "starter")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def pk():
    if os.environ.get("LAB_TARGET") == "import":
        return importlib.import_module("perfkit")
    return _load("perfkit_under_test", TARGET / "perfkit.py")


@pytest.fixture(scope="session")
def oracle():
    return _load("slow_baseline", LAB / "checks" / "slow_baseline.py")


def make_lines(n, seed=7, ips=500, users=6000, attackers=6, malformed_every=37):
    """n log lines like a busy server's: a few attackers fail in rapid runs, many users, some malformed lines. Deterministic."""
    rnd = random.Random(seed)
    pool = [f"10.{i // 250}.{i % 250}.{1 + i % 200}" for i in range(ips)]
    bad = pool[:attackers]
    names = [f"user{i:04d}" for i in range(users)]
    ts = 1_760_000_000
    run_ip, run_left = None, 0
    for i in range(n):
        if run_left == 0 and rnd.random() < 0.02:
            run_ip, run_left = rnd.choice(bad), rnd.randint(6, 12)
        attack = run_left > 0
        if attack:
            run_left -= 1
        ts += rnd.choice([0, 1, 1]) if attack else rnd.choice([1, 1, 2, 5, 30])
        s = ts % 86400
        day = "2026-10-%02d" % (1 + (ts // 86400) % 28)
        ip = run_ip if attack else pool[rnd.randrange(attackers, ips)]
        ok = False if attack else rnd.random() < 0.55
        user = names[min(int(rnd.expovariate(1 / (users / 5))), users - 1)]
        line = f"{day}T{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}Z {ip} {user} {'OK' if ok else 'FAIL'}"
        if i % malformed_every == malformed_every - 1:
            line = rnd.choice(["garbage", line.replace("Z", ""), line.replace(ip, "999.1.1.1"), "", line + " extra"])
        yield line


@pytest.fixture
def workload():
    """workload(n, **kw) -> list of n lines."""
    return lambda n, **kw: list(make_lines(n, **kw))


@pytest.fixture
def lazy_lines():
    """lazy_lines(n, **kw) -> a generator that produces each line (a new str) when asked and keeps none of them."""
    return lambda n, **kw: make_lines(n, **kw)


def best_time(fn, tries=3, stop_above=None):
    """The smallest of up to `tries` wall-clock timings of fn(); gives up early once one run exceeds `stop_above` seconds (an unscalable solution should not be timed three times)."""
    best = float("inf")
    for _ in range(tries):
        started = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - started)
        if stop_above is not None and best > stop_above:
            break
    return best


@pytest.fixture
def timing():
    return best_time
