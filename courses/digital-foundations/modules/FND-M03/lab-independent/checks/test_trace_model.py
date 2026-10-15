"""Public student checks. An untouched starter should FAIL with actionable messages."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'starter'))
from trace_model import diagnose as _diagnose


def diagnose(events):
    try:
        return _diagnose(events)
    except NotImplementedError:
        raise AssertionError('FND-M03 STARTER INCOMPLETE: implement diagnose() in starter/trace_model.py') from None


class StudentTraceContract(unittest.TestCase):
    def test_healthy_session(self):
        result = diagnose([{'stage':'DNS','state':'OK'},{'stage':'TCP','state':'OK'},
                           {'stage':'TLS','state':'OK'},{'stage':'HTTP','state':'OK','status':200}])
        self.assertEqual(result, {'healthy': True, 'failed_stage': None, 'http_status': 200})

    def test_dns_failure_stops_progression(self):
        self.assertEqual(diagnose([{'stage':'DNS','state':'FAIL'}]),
                         {'healthy':False,'failed_stage':'DNS','http_status':None})

    def test_tcp_failure_stops_progression(self):
        self.assertEqual(diagnose([{'stage':'DNS','state':'OK'},{'stage':'TCP','state':'FAIL'}])['failed_stage'],'TCP')

    def test_tls_failure_stops_progression(self):
        self.assertEqual(diagnose([{'stage':'DNS','state':'OK'},{'stage':'TCP','state':'OK'},
                                   {'stage':'TLS','state':'FAIL'}])['failed_stage'],'TLS')

    def test_http_server_error_not_healthy(self):
        out=diagnose([{'stage':'DNS','state':'OK'},{'stage':'TCP','state':'OK'},
                      {'stage':'TLS','state':'OK'},{'stage':'HTTP','state':'OK','status':503}])
        self.assertFalse(out['healthy']);self.assertEqual(out['failed_stage'],'HTTP');self.assertEqual(out['http_status'],503)

    def test_rejects_out_of_sequence_stages(self):
        with self.assertRaises(ValueError):diagnose([{'stage':'TCP','state':'OK'}])

    def test_rejects_duplicate_stages(self):
        with self.assertRaises(ValueError):diagnose([{'stage':'DNS','state':'OK'},{'stage':'DNS','state':'OK'}])

    def test_rejects_unknown_stage_and_state(self):
        for bad in ([{'stage':'SMTP','state':'OK'}],[{'stage':'DNS','state':'PENDING'}]):
            with self.subTest(bad=bad),self.assertRaises(ValueError):diagnose(bad)

    def test_rejects_injection_fields(self):
        with self.assertRaises(ValueError):diagnose([{'stage':'DNS','state':'OK','command':'curl secret'}])

    def test_rejects_invalid_http_status_and_missing_status(self):
        base=[{'stage':'DNS','state':'OK'},{'stage':'TCP','state':'OK'},{'stage':'TLS','state':'OK'}]
        for last in ({'stage':'HTTP','state':'OK','status':True},{'stage':'HTTP','state':'OK'},
                     {'stage':'HTTP','state':'OK','status':99}):
            with self.subTest(last=last),self.assertRaises(ValueError):diagnose(base+[last])

    def test_rejects_unbounded_trace(self):
        with self.assertRaises(ValueError):diagnose([{'stage':'DNS','state':'OK'}]*101)

    def test_rejects_empty_trace_and_bad_container(self):
        for bad in ([], 'DNS OK', {'stage':'DNS'},None):
            with self.subTest(bad=bad),self.assertRaises(ValueError):diagnose(bad)

if __name__=='__main__':unittest.main()
