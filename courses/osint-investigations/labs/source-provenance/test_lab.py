import unittest
from provenance import Evidence,assess
C='A fictional transit museum reopened after renovation'
def r(i,origin,yes=True):return Evidence(i,'Synthetic publisher',origin,C,yes,b'fictional record: '+i.encode())
class ProvenanceTests(unittest.TestCase):
 def test_two_independent_origins_corroborate(self):
  self.assertTrue(assess([r('a','primary'),r('b','independent')],C)['corroborated'])
 def test_echoed_reporting_is_not_independent(self):
  report=assess([r('a','shared-wire'),r('b','shared-wire')],C)
  self.assertEqual(report['independent_support_groups'],1);self.assertFalse(report['corroborated'])
 def test_conflicting_evidence_fails_closed(self):
  self.assertFalse(assess([r('a','g1'),r('b','g2'),r('c','g3',False)],C)['corroborated'])
 def test_hashes_trace_evidence(self):
  rows=assess([r('abc','one')],C)['evidence_hashes']
  self.assertEqual(len(rows[0]['sha256']),64)
 def test_duplicate_ids_rejected(self):
  with self.assertRaisesRegex(ValueError,'duplicate'):assess([r('a','g1'),r('a','g2')],C)
 def test_mixed_claims_rejected(self):
  x=Evidence('a','p','g','another claim',True,b'fake')
  with self.assertRaisesRegex(ValueError,'mixed'):assess([x],C)
if __name__=='__main__':unittest.main()
