"""A loopback HTTP server for lab fixtures: the lab decides, request by request, what the server answers.

Used by the PY-M05 labs so that timeouts, retries and pagination can be practised without any network, account or cost.
The server listens on 127.0.0.1 on a free port, keeps a log of every request it receives, and can delay, drop or corrupt
an answer on purpose.

    def app(request: Request) -> Reply:
        return Reply(body={"path": request.path})

    with ScriptedServer(app) as server:
        httpx.get(server.url + "/hello").json()      # {'path': '/hello'}
        server.requests                              # [Request(method='GET', path='/hello', ...)]
"""
from __future__ import annotations

import http.server
import json
import sys
import threading
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import parse_qs, urlsplit


@dataclass
class Request:
    number: int                      # 1 for the first request the server received
    method: str
    path: str
    query: dict[str, list[str]]
    headers: dict[str, str]          # lower-case names
    body: bytes = b""

    def param(self, name: str, default: str | None = None) -> str | None:
        values = self.query.get(name)
        return values[0] if values else default


@dataclass
class Reply:
    status: int = 200
    body: bytes | str | dict | list | None = None     # a dict or list is sent as JSON
    headers: dict[str, str] = field(default_factory=dict)
    delay: float = 0.0               # seconds to wait before answering
    drop: bool = False               # close the connection without sending anything
    content_type: str | None = None  # default: application/json for dict/list, text/plain otherwise


class ScriptedServer:
    def __init__(self, app: Callable[[Request], Reply]) -> None:
        self.app = app
        self.requests: list[Request] = []
        self._lock = threading.Lock()
        self._stopping = threading.Event()
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
            wbufsize = 65536                       # headers and body leave in one write ...
            disable_nagle_algorithm = True         # ... without waiting for a delayed acknowledgement (40 ms per request otherwise)

            def _serve(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                parts = urlsplit(self.path)
                with owner._lock:
                    number = len(owner.requests) + 1
                    request = Request(number, self.command, parts.path, parse_qs(parts.query), {k.lower(): v for k, v in self.headers.items()}, body)
                    owner.requests.append(request)
                reply = owner.app(request)
                if reply.delay and owner._stopping.wait(reply.delay):
                    return
                if reply.drop:
                    self.close_connection = True
                    return
                payload, ctype = reply.body, reply.content_type
                if isinstance(payload, (dict, list)):
                    payload, ctype = json.dumps(payload).encode("utf-8"), ctype or "application/json"
                elif isinstance(payload, str):
                    payload = payload.encode("utf-8")
                payload = payload or b""
                self.send_response(reply.status)
                self.send_header("Content-Type", ctype or "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                for name, value in reply.headers.items():
                    self.send_header(name, value)
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(payload)

            do_GET = do_POST = do_PUT = do_DELETE = do_HEAD = _serve

            def log_message(self, *args: object) -> None:
                pass

        class Server(http.server.ThreadingHTTPServer):
            daemon_threads = True
            block_on_close = False

            def handle_error(self, request, client_address) -> None:
                if not isinstance(sys.exc_info()[1], ConnectionError):      # clients that give up on purpose are not worth a traceback
                    super().handle_error(request, client_address)

        self._httpd = Server(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._httpd.server_address[1]}"

    def __enter__(self) -> "ScriptedServer":
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stopping.set()
        self._httpd.shutdown()
        self._httpd.server_close()
