import unittest
from datetime import datetime,timedelta,timezone
from triage import AuthEvent,detect
NOW=datetime(2026,10,14,10,tzinfo=timezone.utc)
def e(n,*,user='analyst',src='sandbox',success=False,minutes=0):
 return AuthEvent(str(n),user,src,success,NOW+timedelta(minutes=minutes))
class TriageTests(unittest.TestCase):
 def test_threshold_crossing(self):
  x=detect([e(1),e(2,minutes=1),e(3,minutes=2)])
  self.assertEqual(len(x),1);self.assertEqual(x[0]['event_ids'],['1','2','3'])
 def test_older_events_outside_window(self):
  self.assertFalse(detect([e(1),e(2,minutes=10),e(3,minutes=11)]))
 def test_success_not_counted(self):
  self.assertFalse(detect([e(1),e(2,minutes=1,success=True),e(3,minutes=2)]))
 def test_isolates_sources_and_accounts(self):
  self.assertFalse(detect([e(1),e(2,src='other'),e(3,user='different')]))
 def test_timezone_required(self):
  bad=AuthEvent('x','a','s',False,datetime(2026,10,14))
  with self.assertRaises(ValueError):detect([bad])
 def test_invalid_threshold_types_are_rejected(self):
  for threshold in (2.5,'3',True,False,1,101):
   with self.subTest(threshold=threshold),self.assertRaisesRegex(ValueError,'settings'):
    detect([],threshold=threshold)
 def test_invalid_event_outcome_is_rejected(self):
  invalid=AuthEvent('evt','account','source',1,NOW)
  with self.assertRaisesRegex(ValueError,'event fields'):detect([invalid])
 def test_invalid_window_type_is_rejected(self):
  with self.assertRaisesRegex(ValueError,'settings'):detect([],window='five-minutes')
 def test_duplicate_ids_rejected(self):
  with self.assertRaisesRegex(ValueError,'duplicate'):detect([e(1),e(1)])
if __name__=='__main__':unittest.main()
