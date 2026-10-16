"""FND-M03 guided lab contract and failure-injection tests (offline loopback)."""
from __future__ import annotations
import http.client
import socket
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'solution'))
from http_trace import local_http_server, request_local, trace_request


class HTTPTraceContract(unittest.TestCase):
    def test_health_returns_observed_http_status(self):
        evidence = trace_request('/health')
        self.assertEqual(evidence['status'], 200)
        self.assertEqual(evidence['payload']['status'], 'ok')
        self.assertEqual(evidence['network_host'], '127.0.0.1')
        self.assertEqual(evidence['transport'], 'tcp-loopback')
        self.assertEqual(evidence['http_version'], 'HTTP/1.1')

    def test_missing_returns_404_without_exception(self):
        evidence = trace_request('/missing')
        self.assertEqual(evidence['status'], 404)
        self.assertEqual(evidence['payload']['error'], 'not_found')

    def test_content_type_is_explicit_json(self):
        self.assertEqual(trace_request()['content_type'], 'application/json; charset=utf-8')

    def test_rejects_unsafe_paths(self):
        with local_http_server() as port:
            for path in ('/', '//evil.test', 'http://example.test/', '/../../secrets', '/health?redirect=1'):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    request_local(port, path)

    def test_rejects_ports_outside_tcp_range_and_bools(self):
        for port in (0, -1, 65536, '80', True):
            with self.subTest(port=port), self.assertRaises(ValueError):
                request_local(port)

    def test_rejects_unbounded_timeout(self):
        with local_http_server() as port:
            for timeout in (0, -1, 20, True, '3'):
                with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                    request_local(port, timeout=timeout)

    def test_unknown_route_is_rejected_by_server(self):
        with local_http_server() as port:
            c = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
            try:
                c.request('GET', '/not-allowed', headers={'Connection': 'close'})
                response = c.getresponse()
                self.assertEqual(response.status, 400)
                self.assertEqual(response.getheader('Cache-Control'), 'no-store')
                self.assertEqual(response.getheader('X-Content-Type-Options'), 'nosniff')
                response.read()
            finally:
                c.close()

    def test_body_length_header_matches_bytes(self):
        with local_http_server() as port:
            c = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
            try:
                c.request('GET', '/health', headers={'Connection': 'close'})
                response = c.getresponse()
                body = response.read()
                self.assertEqual(len(body), int(response.getheader('Content-Length')))
            finally:
                c.close()

    def test_live_port_is_ephemeral_and_loopback(self):
        with local_http_server() as port:
            self.assertGreater(port, 0)
            self.assertEqual(request_local(port)['status'], 200)

    def test_server_stops_after_context(self):
        with local_http_server() as port:
            self.assertEqual(request_local(port)['status'], 200)
        with self.assertRaises((OSError, ConnectionError, TimeoutError, socket.timeout)):
            request_local(port, timeout=.15)

    def test_multiple_sequential_requests(self):
        with local_http_server() as port:
            statuses = [request_local(port, p)['status'] for p in ('/health', '/missing', '/health')]
        self.assertEqual(statuses, [200, 404, 200])

    def test_no_dns_or_real_customer_data_claims(self):
        data = trace_request()
        self.assertNotIn('resolved_dns_name', data)
        self.assertEqual(data['payload']['origin'], 'synthetic-loopback')


if __name__ == '__main__':
    unittest.main()
