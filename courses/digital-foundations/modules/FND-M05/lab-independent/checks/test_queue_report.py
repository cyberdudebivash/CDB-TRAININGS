"""Public independent learner acceptance tests: initial intentional failures are expected."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'starter'))
from queue_report import summarize_queues as _learner_function

def summarize_queues(records):
    try:return _learner_function(records)
    except NotImplementedError:
        raise AssertionError('FND-M05 STARTER INCOMPLETE: implement summarize_queues in starter/queue_report.py') from None

class QueueReportContract(unittest.TestCase):
    def test_totals_and_sorting(self):
        self.assertEqual(summarize_queues([
            {'id':'R-001','queue':'Beta','state':'OPEN'},
            {'id':'R-002','queue':'Alpha','state':'CLOSED'},
            {'id':'R-003','queue':'Alpha','state':'OPEN'}]),
            {'total':3,'queues':[{'queue':'Alpha','open':1,'closed':1},{'queue':'Beta','open':1,'closed':0}]})
    def test_empty_is_valid(self):
        self.assertEqual(summarize_queues([]),{'total':0,'queues':[]})
    def test_all_closed(self):
        self.assertEqual(summarize_queues([{'id':'R-001','queue':'Team','state':'CLOSED'}]),{'total':1,'queues':[{'queue':'Team','open':0,'closed':1}]})
    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):summarize_queues([{'id':'R-001','queue':'X','state':'OPEN'}]*2)
    def test_bad_state_rejected(self):
        with self.assertRaises(ValueError):summarize_queues([{'id':'R-001','queue':'X','state':'WAITING'}])
    def test_extraneous_field_rejected(self):
        with self.assertRaises(ValueError):summarize_queues([{'id':'R-001','queue':'X','state':'OPEN','is_admin':True}])
    def test_incorrect_container_rejected(self):
        with self.assertRaises(ValueError):summarize_queues('not-a-list')
    def test_invalid_id_rejected(self):
        with self.assertRaises(ValueError):summarize_queues([{'id':'$(shell)','queue':'X','state':'OPEN'}])
    def test_queue_name_rejected(self):
        with self.assertRaises(ValueError):summarize_queues([{'id':'R-001','queue':'X;Y','state':'OPEN'}])
    def test_bounded_length(self):
        row={'id':'R-001','queue':'X','state':'OPEN'}
        with self.assertRaises(ValueError):summarize_queues([row]*1001)

if __name__=='__main__':unittest.main()
