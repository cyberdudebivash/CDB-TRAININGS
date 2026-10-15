"""A local document server for the PY-M06 independent lab: serve(count, latency) starts it and returns (base_url, stop).

Document i has (i % 7) + 3 words, so the expected counts are known. Every answer takes `latency` seconds, like a remote service would. Used by your benchmark script;
the checks start their own, more hostile servers.
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import unquote

for _parent in Path(__file__).resolve().parents:                    # find courses/python-engineering/labs/_tools whatever the folder this file was copied to
    if (_parent / "labs" / "_tools" / "scripted_server.py").exists():
        sys.path.insert(0, str(_parent / "labs" / "_tools"))
        break
from scripted_server import Reply, ScriptedServer  # noqa: E402


def doc_text(i: int) -> str:
    return " ".join(f"word{i}x{j}" for j in range((i % 7) + 3))


def serve(count: int = 40, latency: float = 0.05):
    def app(request):
        name = unquote(request.path.removeprefix("/docs/"))
        if not request.path.startswith("/docs/") or not name.isdigit() or int(name) >= count:
            return Reply(404, "no such document")
        return Reply(200, doc_text(int(name)), content_type="text/plain; charset=utf-8", delay=latency)

    server = ScriptedServer(app).__enter__()
    return server.url, lambda: server.__exit__(None, None, None)
