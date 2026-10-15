"""FND-M03 local-only HTTP trace lab: no public services, DNS queries or customer data.

A server thread binds 127.0.0.1 and an ephemeral port. The client uses a fixed
loopback endpoint with a maximum response size and timeout. Python 3.11+.
"""
from __future__ import annotations

import http.client
import json
import secrets
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Iterator

MAX_BODY = 4096
REQUEST_TIMEOUT_SECONDS = 3


class _LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False


class _Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'CDBTrainingLab/1.0'
    sys_version = ''

    def do_GET(self) -> None:
        # Request paths are deliberately narrow: no arbitrary files or proxies.
        path = self.path
        if path == '/health':
            status, data = 200, {'status': 'ok', 'origin': 'synthetic-loopback'}
        elif path == '/missing':
            status, data = 404, {'error': 'not_found'}
        else:
            status, data = 400, {'error': 'invalid_lab_route'}
        raw = json.dumps(data, separators=(',', ':'), sort_keys=True).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format: str, *args: object) -> None:
        # Avoid logging potentially untrusted request path into a public terminal.
        pass


@contextmanager
def local_http_server() -> Iterator[int]:
    """Yield an ephemeral *loopback* port; shut down cleanly on exit."""
    server = _LocalServer(('127.0.0.1', 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        if thread.is_alive():
            raise RuntimeError('loopback server failed to stop')


def request_local(port: int, path: str = '/health', *, timeout: float = REQUEST_TIMEOUT_SECONDS) -> dict:
    """Make a bounded GET request without DNS, redirects, or external hosts."""
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('port must be a local TCP port 1..65535')
    if path not in ('/health', '/missing'):
        raise ValueError('path must be an approved exercise route')
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 5:
        raise ValueError('timeout must be in (0, 5] seconds')
    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=timeout)
    try:
        conn.request('GET', path, headers={'Accept': 'application/json', 'Connection': 'close'})
        response = conn.getresponse()
        if response.version != 11:
            raise ValueError('unexpected HTTP protocol version')
        declared = response.getheader('Content-Length')
        if declared is None or not declared.isdecimal() or int(declared) > MAX_BODY:
            raise ValueError('missing or oversized response Content-Length')
        body = response.read(MAX_BODY + 1)
        if len(body) > MAX_BODY or len(body) != int(declared):
            raise ValueError('invalid response length')
        if response.getheader('Content-Type') != 'application/json; charset=utf-8':
            raise ValueError('unexpected Content-Type')
        data = json.loads(body.decode('utf-8'))
        return {
            'transport': 'tcp-loopback',
            'network_host': '127.0.0.1',
            'request_path': path,
            'http_version': 'HTTP/1.1',
            'status': response.status,
            'content_type': response.getheader('Content-Type'),
            'payload': data,
        }
    finally:
        conn.close()


def trace_request(path: str = '/health') -> dict:
    """Perform a new controlled live TCP exchange, then return synthetic trace metadata."""
    with local_http_server() as port:
        return request_local(port, path)
